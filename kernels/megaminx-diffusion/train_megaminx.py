#!/usr/bin/env python3
"""Megaminx diffusion-predictor training (runs on Kaggle GPU).

Trains the Pilgrim MLP to estimate diffusion distance-to-solved for the
megaminx (120 facelets, 24 face turns), using the competition's own
generators.  All I/O happens under /kaggle/working (cwd).

Usage knobs via env: PZ_EPOCHS, PZ_KMAX, PZ_HD1, PZ_HD2, PZ_NRD, PZ_BATCH.
"""
import os, sys, json, time, torch
WORK = os.environ.get("PZ_WORK", "/kaggle/working")
os.chdir(WORK)
sys.path.insert(0, WORK)
from pilgrim import Pilgrim, Trainer

GROUP_ID = 55
TARGET_ID = 0
EPOCHS = int(os.environ.get("PZ_EPOCHS", "2048"))
KMAX = int(os.environ.get("PZ_KMAX", "150"))
HD1 = int(os.environ.get("PZ_HD1", "1024"))
HD2 = int(os.environ.get("PZ_HD2", "256"))
NRD = int(os.environ.get("PZ_NRD", "4"))
BATCH = int(os.environ.get("PZ_BATCH", "10000"))
WALL_CAP = float(os.environ.get("PZ_WALL_CAP", "0"))  # 0 = no cap

class TimedTrainer(Trainer):
    """Trainer that stops when a wall-clock budget is exhausted."""
    def run(self):
        t_start = time.time()
        for epoch in range(self.num_epochs):
            self.epoch += 1
            X, Y = self.generate_random_walks(k=self.walkers_num, K_min=self.K_min, K_max=self.K_max)
            self._train_epoch(X, Y.float())
            if (self.epoch & (self.epoch - 1)) == 0:
                weights_file = f"{self.weights_dir}/{self.name}_{self.id}_e{self.epoch:05d}.pth"
                torch.save(self.net.state_dict(), weights_file)
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Saved weights at epoch {self.epoch:5d}.", flush=True)
            if WALL_CAP > 0 and (time.time() - t_start) > WALL_CAP:
                print(f"wall cap {WALL_CAP:.0f}s reached at epoch {self.epoch} - stopping", flush=True)
                break
        weights_file = f"{self.weights_dir}/{self.name}_{self.id}_e{self.epoch:05d}.pth"
        torch.save(self.net.state_dict(), weights_file)
        print(f"Finished. Saved final weights at epoch {self.epoch}.", flush=True)

def main():
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

    name2idx = {n: i for i, n in enumerate(move_names)}
    inv = torch.tensor([name2idx[n[1:] if n.startswith("-") else "-"+n] for n in move_names], device=device)

    print(f"generators={n_gens} state_size={state_size} classes={num_classes} Kmax={KMAX}", flush=True)

    model = Pilgrim(num_classes=num_classes, state_size=state_size, hd1=HD1, hd2=HD2, nrd=NRD, dropout_rate=0.0)
    model.to(device)
    if int(V0.min()) < 0:
        model.z_add = -int(V0.min())

    trainer = TimedTrainer(net=model, num_epochs=EPOCHS, device=device, batch_size=BATCH, lr=0.001,
                           name=f"p{GROUP_ID:03d}-t{TARGET_ID:03d}", K_min=1, K_max=KMAX,
                           all_moves=all_moves, inverse_moves=inv, V0=V0)
    trainer.run()

    # write model info json needed by the solver
    os.makedirs("logs", exist_ok=True)
    info_path = f"logs/model_p{GROUP_ID:03d}-t{TARGET_ID:03d}_{trainer.id}.json"
    info = {"model_id": trainer.id, "hd1": HD1, "hd2": HD2, "nrd": NRD, "dropout": 0.0,
            "epochs": trainer.epoch, "K_max": KMAX}
    with open(info_path, "w") as f:
        json.dump(info, f)
    print("training complete. model_id=", trainer.id, "epochs=", trainer.epoch, flush=True)

if __name__ == "__main__":
    main()
