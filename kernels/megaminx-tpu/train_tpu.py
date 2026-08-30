#!/usr/bin/env python3
"""Megaminx Pilgrim predictor training on Kaggle TPU (torch_xla).

Extracts the bundled dataset into /kaggle/working, trains the distance
predictor on the TPU device (falls back to the host CPU if xla is not
available), and writes weights + model-info json to /kaggle/working.
The weights are then merged into the dataset and consumed by the GPU
solve-only kernel (PZ_TRAIN=0).

Env: PZ_WALL_CAP (seconds, default 6h), PZ_EPOCHS, PZ_KMAX, PZ_BATCH.
"""
import os, sys, glob, json, shutil, subprocess, time, torch
import torch.nn.functional as F

INPUT = "/kaggle/input"
WORK = "/kaggle/working"
WALL_CAP = float(os.environ.get("PZ_WALL_CAP", str(6 * 3600)))
EPOCHS = int(os.environ.get("PZ_EPOCHS", "4096"))
KMAX = int(os.environ.get("PZ_KMAX", "150"))
HD1 = int(os.environ.get("PZ_HD1", "1024"))
HD2 = int(os.environ.get("PZ_HD2", "256"))
NRD = int(os.environ.get("PZ_NRD", "4"))
BATCH = int(os.environ.get("PZ_BATCH", "10000"))
GROUP_ID = 55
TARGET_ID = 0


def find_dataset():
    for root, dirs, files in os.walk(INPUT):
        if "puzzle_info.json" in files and "p055.json" in files:
            return root
    return None


def main():
    ds = find_dataset()
    print("dataset dir:", ds, flush=True)
    if ds is None:
        raise SystemExit("dataset not mounted")
    os.makedirs(WORK, exist_ok=True)
    for name in sorted(os.listdir(ds)):
        s = os.path.join(ds, name)
        d = os.path.join(WORK, name)
        if os.path.isdir(s):
            print("copying dir", name, flush=True)
            shutil.copytree(s, d, dirs_exist_ok=True)
        elif name.endswith(".tar"):
            print("extracting", name, flush=True)
            subprocess.run(["tar", "xf", s, "-C", WORK], check=True)
        else:
            shutil.copy(s, d)
    os.chdir(WORK)
    sys.path.insert(0, WORK)

    # device: TPU via torch_xla, else host CPU
    TPU = False
    try:
        import torch_xla.core.xla_model as xm
        device = xm.xla_device()
        TPU = True
        print("device: TPU", device, flush=True)
    except Exception as exc:
        device = torch.device("cpu")
        print("xla unavailable -> CPU:", str(exc)[:200], flush=True)

    from pilgrim import Pilgrim

    with open(f"generators/p{GROUP_ID:03d}.json") as f:
        data = json.load(f)
    move_names = data["move_names"]
    all_moves = torch.tensor(data["moves"], dtype=torch.int64, device=device)
    V0 = torch.load(f"targets/p{GROUP_ID:03d}-t{TARGET_ID:03d}.pt",
                    weights_only=True, map_location="cpu").to(device)
    num_classes = int(torch.unique(V0).numel())
    state_size = all_moves.size(1)
    n_gens = all_moves.size(0)
    name2idx = {n: i for i, n in enumerate(move_names)}
    inv = torch.tensor([name2idx[n[1:] if n.startswith("-") else "-" + n]
                        for n in move_names], device=device)

    # CPU copies for walk generation (XLA graph too large when unrolled)
    all_moves_cpu = all_moves.cpu()
    V0_cpu = V0.cpu()
    inv_cpu = inv.cpu()

    print(f"TPU={TPU} generators={n_gens} state={state_size} classes={num_classes} "
          f"Kmax={KMAX} wall={WALL_CAP:.0f}s", flush=True)

    model = Pilgrim(num_classes=num_classes, state_size=state_size,
                    hd1=HD1, hd2=HD2, nrd=NRD, dropout_rate=0.0).to(device)
    if int(V0.min()) < 0:
        model.z_add = -int(V0.min())
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = torch.nn.MSELoss()
    model_id = int(time.time())
    os.makedirs("weights", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    def gen_walks_cpu(k, K_min, K_max):
        """Random walks on the host CPU (multinomial works there; the full
        unrolled graph exceeds TPU HBM).  Returns CPU tensors."""
        total = k * (K_max - K_min + 1)
        Y = torch.arange(K_min, K_max + 1).repeat_interleave(k)
        states = V0_cpu.repeat(total, 1)
        last_moves = torch.full((total,), -1, dtype=torch.int64)
        for t in range(K_max):
            cutoff = 0 if t < K_min else k * (t - K_min + 1)
            if cutoff >= total:
                break
            n_act = total - cutoff
            pm_ = torch.ones((n_act, n_gens), dtype=torch.bool)
            pm_[torch.arange(n_act), inv_cpu[last_moves[cutoff:]]] = False
            nxt = torch.multinomial(pm_.float(), 1).squeeze(-1)
            states[cutoff:] = torch.gather(states[cutoff:], 1, all_moves_cpu[nxt])
            last_moves[cutoff:] = nxt
        perm = torch.randperm(total)
        return states[perm], Y[perm]

    walkers = 1_000_000 // KMAX
    t_start = time.time()
    epoch = 0
    loss = torch.tensor(0.0, device=device)
    for epoch in range(1, EPOCHS + 1):
        X, Y = gen_walks_cpu(walkers, 1, KMAX)
        X, Y = X.to(device), Y.to(device)
        model.train()
        for i in range(0, X.size(0), BATCH):
            xb, yb = X[i:i + BATCH], Y[i:i + BATCH].float()
            out = model(xb)
            loss = criterion(out, yb)
            optimizer.zero_grad()
            loss.backward()
            if TPU:
                import torch_xla.core.xla_model as xm
                xm.optimizer_step(optimizer)
            else:
                optimizer.step()
        if TPU:
            import torch_xla.core.xla_model as xm
            xm.mark_step()
        if (epoch & (epoch - 1)) == 0 or epoch % 256 == 0:
            sd = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            torch.save(sd, f"weights/p{GROUP_ID:03d}-t{TARGET_ID:03d}_{model_id}_e{epoch:05d}.pth")
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] "
                  f"epoch {epoch} loss {loss.item():.3f}", flush=True)
        if time.time() - t_start > WALL_CAP:
            print(f"wall cap {WALL_CAP:.0f}s reached at epoch {epoch}", flush=True)
            break

    sd = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    torch.save(sd, f"weights/p{GROUP_ID:03d}-t{TARGET_ID:03d}_{model_id}_e{epoch:05d}.pth")
    info = {"model_id": model_id, "hd1": HD1, "hd2": HD2, "nrd": NRD,
            "dropout": 0.0, "epochs": epoch, "K_max": KMAX}
    with open(f"logs/model_p{GROUP_ID:03d}-t{TARGET_ID:03d}_{model_id}.json", "w") as f:
        json.dump(info, f)
    print(f"TPU training done. model_id={model_id} epochs={epoch}", flush=True)


if __name__ == "__main__":
    main()