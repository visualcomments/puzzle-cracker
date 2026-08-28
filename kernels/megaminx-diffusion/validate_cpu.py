#!/usr/bin/env python3
"""Local CPU validation of the megaminx diffusion pipeline (tiny).
Verifies: move application convention, training loop runs, and a small
model + beam search solves short scrambles.  Lightweight - safe on a weak PC.
"""
import os, sys, json, time, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilgrim import Pilgrim, Trainer, Searcher

GROUP_ID = 55
TARGET_ID = 0

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("device:", device)

with open(f"generators/p{GROUP_ID:03d}.json") as f:
    data = json.load(f)
move_names = data["move_names"]
all_moves = torch.tensor(data["moves"], dtype=torch.int64, device=device)
V0 = torch.load(f"targets/p{GROUP_ID:03d}-t{TARGET_ID:03d}.pt", weights_only=True, map_location=device)
num_classes = int(torch.unique(V0).numel())
state_size = all_moves.size(1)
print("generators", all_moves.size(0), "state_size", state_size, "classes", num_classes)

# inverse indices (dash convention)
name2idx = {n: i for i, n in enumerate(move_names)}
inv = torch.tensor([name2idx[n[1:] if n.startswith("-") else "-"+n] for n in move_names], device=device)

# --- validation 1: move convention. Apply U move to solved; then -U should return solved
U = move_names.index("U")
after = torch.gather(V0, 0, all_moves[U])
print("after U:", after[:6], "...")
back = torch.gather(after, 0, all_moves[inv[U]])
print("U then -U == solved:", bool((back == V0).all()))

# --- tiny training run
model = Pilgrim(num_classes=num_classes, state_size=state_size, hd1=128, hd2=32, nrd=1)
trainer = Trainer(net=model, num_epochs=3, device=device, batch_size=2000, lr=0.001,
                  name=f"p{GROUP_ID:03d}-t{TARGET_ID:03d}", K_min=1, K_max=15,
                  all_moves=all_moves, inverse_moves=inv, V0=V0)
trainer.run()
print("training finished, model id:", trainer.id)

# --- validation 2: searcher solves a short scramble
# generate a 5-move random scramble
torch.manual_seed(0)
moves = torch.randint(0, all_moves.size(0), (5,))
st = V0.clone()
for m in moves:
    st = torch.gather(st, 0, all_moves[m])
print("scramble state:", st[:6], "...")

# make the model usable for searching (float32, cpu)
model.eval()
searcher = Searcher(model=model, all_moves=all_moves, V0=V0, device=device)
res = searcher.get_solution(st, B=64, num_steps=60, num_attempts=3)
sol, attempts = res[:2]
print("solution:", None if sol is None else sol.tolist(), "attempts", attempts)
if sol is not None:
    cur = st.clone()
    for m in sol:
        cur = torch.gather(cur, 0, all_moves[m])
    print("verified solved:", bool((cur == V0).all()), "len", len(sol))
    # reconstruct move names
    print("move names:", ".".join(move_names[int(m)] for m in sol))
print("OK")
