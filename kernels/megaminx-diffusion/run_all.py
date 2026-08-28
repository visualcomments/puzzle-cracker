#!/usr/bin/env python3
"""Megaminx diffusion solver: train + solve in one Kaggle GPU kernel.

Competition : cayley-py-megaminx
Metric      : total path length over solved scrambles (shorter = better)

Pipeline:
  1. extract the bundled pilgrim/ framework + data from the private dataset;
  2. train a Pilgrim MLP (diffusion-distance predictor) on random walks;
  3. run wide batched GPU beam search over the 1001 test scrambles;
  4. write /kaggle/working/submission.csv (initial_state_id,path).

Env knobs: PZ_TRAIN (0/1), PZ_EPOCHS, PZ_KMAX, PZ_HD1/HD2/NRD, PZ_BATCH,
PZ_B (beam width), PZ_STEPS, PZ_ATTEMPTS, PZ_MODEL_ID, PZ_EPOCH.
"""
import os, sys, json, time, glob, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = "/kaggle/input"

# find the private dataset mount
def find_dataset():
    for d in sorted(glob.glob(f"{INPUT}/*")):
        if os.path.exists(os.path.join(d, "puzzle_info.json")) and \
           os.path.exists(os.path.join(d, "p055.json")):
            return d
    return None

def main():
    ds = find_dataset()
    print("dataset dir:", ds, flush=True)
    # extract pilgrim.tar if present (flat layout otherwise)
    work = "/kaggle/working"
    os.makedirs(work, exist_ok=True)
    for f in os.listdir(ds):
        if f.endswith(".tar"):
            print("extracting", f, flush=True)
            subprocess.run(["tar", "xf", os.path.join(ds, f), "-C", work], check=True)
    # copy all top-level files into work so relative imports resolve
    for f in os.listdir(ds):
        if not f.endswith(".tar"):
            dst = os.path.join(work, f)
            if not os.path.exists(dst):
                shutil.copy(os.path.join(ds, f), dst)
    print("work contents:", sorted(os.listdir(work)), flush=True)

    # Training
    train_flag = int(os.environ.get("PZ_TRAIN", "1"))
    if train_flag:
        print("=== TRAINING ===", flush=True)
        subprocess.run([sys.executable, os.path.join(work, "train_megaminx.py")], check=True)
    else:
        # ensure logs/weights are present (mounted or copied)
        pass

    # Solving
    print("=== SOLVING ===", flush=True)
    os.chdir(work)
    env = dict(os.environ)
    env["PZ_DATA"] = ds
    env["PZ_OUT"] = "/kaggle/working/submission.csv"
    subprocess.run([sys.executable, os.path.join(work, "solve_megaminx.py")], check=True, env=env)
    print("=== DONE ===", flush=True)

if __name__ == "__main__":
    main()
