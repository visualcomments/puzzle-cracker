#!/usr/bin/env python3
"""Megaminx diffusion VALIDATION run (small config, fast, self-contained).

Runs the full train+solve pipeline with tiny params and a 12-case slice to
verify correctness on Kaggle GPU before the full-scale run.
"""
import os, sys, json, time, glob, shutil, subprocess

# ---- tiny config ----
os.environ.setdefault("PZ_EPOCHS", "64")
os.environ.setdefault("PZ_KMAX", "60")
os.environ.setdefault("PZ_HD1", "256")
os.environ.setdefault("PZ_HD2", "64")
os.environ.setdefault("PZ_NRD", "1")
os.environ.setdefault("PZ_BATCH", "4096")
os.environ.setdefault("PZ_B", str(2 ** 12))
os.environ.setdefault("PZ_STEPS", "80")
os.environ.setdefault("PZ_ATTEMPTS", "2")
os.environ.setdefault("PZ_LIMIT", "12")
os.environ.setdefault("PZ_WORK", "/kaggle/working")

def main():
    HERE = os.path.dirname(os.path.abspath(__file__))
    INPUT = "/kaggle/input"
    work = os.environ["PZ_WORK"]
    os.makedirs(work, exist_ok=True)

    # find the private dataset mount
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

    print("=== TRAINING ===", flush=True)
    subprocess.run([sys.executable, os.path.join(work, "train_megaminx.py")], check=True, env=env)

    print("=== SOLVING ===", flush=True)
    subprocess.run([sys.executable, os.path.join(work, "solve_megaminx.py")], check=True, env=env)

    print("=== VALIDATION SUBMISSION ===", flush=True)
    if os.path.exists(os.path.join(work, "submission.csv")):
        with open(os.path.join(work, "submission.csv")) as f:
            content = f.read()
        print(content[:2000], flush=True)
    print("=== DONE ===", flush=True)

if __name__ == "__main__":
    main()