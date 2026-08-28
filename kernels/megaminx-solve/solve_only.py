#!/usr/bin/env python3
"""Megaminx solve-only kernel (Kaggle GPU) - uses the best trained weights
present in the dataset (no training in this kernel).  For round 2: consumes
weights produced by the TPU trainer kernel.

Env: PZ_B_LIST, PZ_STEPS, PZ_CASE_BUDGET, PZ_WALL, PZ_LIMIT.
"""
import os, sys, glob, json, shutil, subprocess

INPUT = "/kaggle/input"
WORK = "/kaggle/working"


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
    env["PZ_DATA"] = ds
    env["PZ_OUT"] = "/kaggle/working/submission.csv"
    subprocess.run([sys.executable, os.path.join(WORK, "solve_megaminx.py")],
                   check=True, env=env)
    print("=== DONE ===", flush=True)


if __name__ == "__main__":
    main()