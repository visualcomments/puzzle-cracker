#!/usr/bin/env python3
"""Megaminx diffusion FULL run (self-contained, train + solve).

Large config: bigger model, longer training (time-capped), wide beam.
The training loop is time-capped so the kernel reliably finishes within
the GPU session and leaves enough time to solve all 1001 cases.
"""
import os, sys, json, time, glob, shutil, subprocess

# ---- full config ----
os.environ.setdefault("PZ_EPOCHS", "4096")
os.environ.setdefault("PZ_KMAX", "150")
os.environ.setdefault("PZ_HD1", "1024")
os.environ.setdefault("PZ_HD2", "256")
os.environ.setdefault("PZ_NRD", "4")
os.environ.setdefault("PZ_BATCH", "10000")
os.environ.setdefault("PZ_B", str(2 ** 18))
os.environ.setdefault("PZ_STEPS", "250")
os.environ.setdefault("PZ_ATTEMPTS", "3")
os.environ.setdefault("PZ_WORK", "/kaggle/working")

# time budgets (seconds)
TRAIN_BUDGET = float(os.environ.get("PZ_TRAIN_BUDGET", str(5 * 3600)))
SOLVE_BUDGET = float(os.environ.get("PZ_SOLVE_BUDGET", str(4 * 3600)))

def main():
    HERE = os.path.dirname(os.path.abspath(__file__))
    INPUT = "/kaggle/input"
    work = os.environ["PZ_WORK"]
    os.makedirs(work, exist_ok=True)

    ds = None
    for d in sorted(glob.glob(f"{INPUT}/*")):
        if os.path.exists(os.path.join(d, "puzzle_info.json")) and \
           os.path.exists(os.path.join(d, "p055.json")):
            ds = d
            break
    if ds is None:
        raise FileNotFoundError("private dataset not mounted")
    print("dataset dir:", ds, flush=True)

    for f in os.listdir(ds):
        if f.endswith(".tar"):
            print("extracting", f, flush=True)
            subprocess.run(["tar", "xf", os.path.join(ds, f), "-C", work], check=True)
    for f in os.listdir(ds):
        if not f.endswith(".tar"):
            dst = os.path.join(work, f)
            if not os.path.exists(dst):
                shutil.copy(os.path.join(ds, f), dst)
    print("work contents:", sorted(os.listdir(work)), flush=True)

    os.chdir(work)
    env = dict(os.environ)
    env["PZ_DATA"] = ds
    env["PZ_OUT"] = os.path.join(work, "submission.csv")
    # cap training wall time via env consumed inside train_megaminx.py
    env["PZ_WALL_CAP"] = str(TRAIN_BUDGET)

    print("=== TRAINING ===", flush=True)
    subprocess.run([sys.executable, os.path.join(work, "train_megaminx.py")], check=True, env=env)

    print("=== SOLVING ===", flush=True)
    subprocess.run([sys.executable, os.path.join(work, "solve_megaminx.py")], check=True, env=env)

    print("=== DONE ===", flush=True)

if __name__ == "__main__":
    main()