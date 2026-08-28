#!/usr/bin/env python3
"""Megaminx diffusion-heuristic beam solver (runs on Kaggle GPU).

Loads the trained Pilgrim predictor and runs wide batched GPU beam search
over the 1001 test scrambles (khoruzhii/cayleypy-cube, NeurIPS 2025).
Writes /kaggle/working/submission.csv.

Env: PZ_WORK, PZ_B, PZ_STEPS, PZ_ATTEMPTS, PZ_MODEL_ID (optional auto),
PZ_EPOCH (optional auto-highest), PZ_LIMIT.
"""
import csv, glob, json, os, sys, time, torch
WORK = os.environ.get("PZ_WORK", "/kaggle/working")
os.chdir(WORK)
sys.path.insert(0, WORK)
from pilgrim import Pilgrim, Searcher

GROUP_ID = 55
TARGET_ID = 0
B = int(os.environ.get("PZ_B", str(2 ** 18)))
NUM_STEPS = int(os.environ.get("PZ_STEPS", "250"))
NUM_ATTEMPTS = int(os.environ.get("PZ_ATTEMPTS", "3"))
DATA_DIR = os.environ.get("PZ_DATA", WORK)
OUT = os.environ.get("PZ_OUT", "/kaggle/working/submission.csv")
CASE_LIMIT = int(os.environ.get("PZ_LIMIT", "0")) or None

def pick_model():
    """Auto-discover the best-trained weights (highest epoch)."""
    cands = glob.glob(f"weights/p{GROUP_ID:03d}-t{TARGET_ID:03d}_*_e*.pth")
    if not cands:
        raise FileNotFoundError("no trained weights found in weights/")
    # parse model_id and epoch
    best = None
    for c in cands:
        base = os.path.basename(c)
        # p055-t000_<mid>_e<epoch>.pth
        mid = int(base.split("_")[1])
        epoch = int(base.split("_e")[1].replace(".pth", ""))
        if best is None or epoch > best[1]:
            best = (c, epoch, mid)
    return best

def main():
    print("puzzle-cracker megaminx diffusion solver start", flush=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("device:", device, "gpu:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none", flush=True)

    with open(f"generators/p{GROUP_ID:03d}.json") as f:
        data = json.load(f)
    move_names = data["move_names"]
    all_moves = torch.tensor(data["moves"], dtype=torch.int64, device=device)
    V0 = torch.load(f"targets/p{GROUP_ID:03d}-t{TARGET_ID:03d}.pt", weights_only=True, map_location=device)
    num_classes = int(torch.unique(V0).numel())
    state_size = all_moves.size(1)
    n_gens = all_moves.size(0)

    # model id / epoch
    if os.environ.get("PZ_MODEL_ID"):
        model_id = int(os.environ["PZ_MODEL_ID"])
        epoch = int(os.environ.get("PZ_EPOCH", "0"))
        weights_path = f"weights/p{GROUP_ID:03d}-t{TARGET_ID:03d}_{model_id}_e{epoch:05d}.pth"
        info_path = f"logs/model_p{GROUP_ID:03d}-t{TARGET_ID:03d}_{model_id}.json"
    else:
        weights_path, epoch, model_id = pick_model()
        info_path = f"logs/model_p{GROUP_ID:03d}-t{TARGET_ID:03d}_{model_id}.json"
    print(f"using weights={weights_path} epoch={epoch} model_id={model_id}", flush=True)

    with open(info_path) as f:
        info = json.load(f)

    model = Pilgrim(num_classes=num_classes, state_size=state_size,
                    hd1=info["hd1"], hd2=info["hd2"], nrd=info["nrd"],
                    dropout_rate=info.get("dropout", 0.0))
    state = torch.load(weights_path, weights_only=False, map_location="cpu")
    model.load_state_dict(state, strict=True)
    model.eval()
    if device.type == "cuda":
        model.half()
        model.dtype = torch.float16
    else:
        model.dtype = torch.float32
    model.to(device)
    if int(V0.min()) < 0:
        model.z_add = -int(V0.min())

    searcher = Searcher(model=model, all_moves=all_moves, V0=V0, device=device, verbose=0)

    tests = torch.load(f"datasets/p{GROUP_ID:03d}-t{TARGET_ID:03d}-megatest.pt",
                       weights_only=False, map_location=device)
    if CASE_LIMIT:
        tests = tests[:CASE_LIMIT]

    # competition test.csv ids (from the mounted data or dataset copy)
    test_csv = os.path.join(DATA_DIR, "test.csv")
    with open(test_csv) as f:
        test_rows = list(csv.DictReader(f))
    test_ids = [r["initial_state_id"] for r in test_rows]
    if CASE_LIMIT:
        test_ids = test_ids[:CASE_LIMIT]

    print(f"solving {tests.size(0)} cases...", flush=True)
    t0 = time.time()
    solved_cnt = 0
    total_moves = 0
    rows = {}
    for i, st in enumerate(tests):
        result = searcher.get_solution(st, B=B, num_steps=NUM_STEPS, num_attempts=NUM_ATTEMPTS)
        moves, attempts = result[:2]
        cid = test_ids[i]
        if moves is not None:
            seq = [int(m) for m in moves]
            cur = st.clone()
            for m in seq:
                cur = torch.gather(cur, 0, all_moves[m])
            if bool((cur == V0).all()):
                rows[cid] = ".".join(move_names[m] for m in seq)
                solved_cnt += 1
                total_moves += len(seq)
            else:
                rows[cid] = ""
        else:
            rows[cid] = ""
        if (i + 1) % 25 == 0 or i == len(tests) - 1:
            print(f"[{i+1}/{len(tests)}] solved={solved_cnt} moves={total_moves} "
                  f"elapsed={time.time()-t0:.0f}s", flush=True)

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["initial_state_id", "path"])
        for cid in test_ids:
            w.writerow([cid, rows.get(cid, "")])
    print(f"done: {solved_cnt}/{len(tests)} solved, {total_moves} total moves, "
          f"mean={total_moves/max(solved_cnt,1):.2f}, {time.time()-t0:.0f}s -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
