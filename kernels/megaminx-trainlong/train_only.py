#!/usr/bin/env python3
"""Megaminx LONG training kernel (Kaggle GPU T4) - trains the Pilgrim
distance predictor for ~9h (K_max=80 for better labels; walkers kept at
1e6 states/epoch) and saves weights + model-info json to /kaggle/working.

Round 2: a much better model than the 301-epoch round-1 run.  Weights are
then merged into the dataset and consumed by the solve-only kernel.

Env: PZ_WALL_CAP (default 32400s = 9h), PZ_EPOCHS, PZ_KMAX, PZ_BATCH.
"""
import os, sys, glob, json, shutil, subprocess

INPUT = "/kaggle/input"
WORK = "/kaggle/working"
WALL_CAP = os.environ.get("PZ_WALL_CAP", "32400")
KMAX = os.environ.get("PZ_KMAX", "80")
EPOCHS = os.environ.get("PZ_EPOCHS", "8192")
BATCH = os.environ.get("PZ_BATCH", "20000")


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
            shutil.copytree(s, d, dirs_exist_ok=True)
        elif name.endswith(".tar"):
            subprocess.run(["tar", "xf", s, "-C", WORK], check=True)
        else:
            shutil.copy(s, d)
    print("work contents:", sorted(os.listdir(WORK)), flush=True)
    env = dict(os.environ)
    env["PZ_WALL_CAP"] = WALL_CAP
    env["PZ_KMAX"] = KMAX
    env["PZ_EPOCHS"] = EPOCHS
    env["PZ_BATCH"] = BATCH
    subprocess.run([sys.executable, os.path.join(WORK, "train_megaminx.py")],
                   check=True, env=env)
    print("=== TRAIN DONE ===", flush=True)


if __name__ == "__main__":
    main()