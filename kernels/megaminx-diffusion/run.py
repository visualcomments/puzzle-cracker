#!/usr/bin/env python3
"""Megaminx diffusion pipeline kernel entry (runs on Kaggle GPU).

1. find the mounted private dataset (puzzle_info.json + p055.json at top);
2. copy all dataset files into /kaggle/working (dirs recursive);
3. train a Pilgrim MLP distance predictor (capped by PZ_WALL_CAP);
4. run the adaptive diffusion-guided beam solve over the 1001 test cases;
5. write /kaggle/working/submission.csv (initial_state_id,path).

Env: PZ_TRAIN (0/1), PZ_WALL_CAP, PZ_EPOCHS, PZ_B_LIST, PZ_STEPS,
PZ_CASE_BUDGET, PZ_LIMIT.
"""
import os, sys, glob, shutil, subprocess

INPUT = "/kaggle/input"


def find_dataset():
    print("input listing:", os.listdir(INPUT), flush=True)
    for root, dirs, files in os.walk(INPUT):
        if "puzzle_info.json" in files and "p055.json" in files:
            print("dataset dir:", root, flush=True)
            return root
    return None


def main():
    ds = find_dataset()
    print("dataset dir:", ds, flush=True)
    if ds is None:
        raise SystemExit("dataset not mounted")
    work = "/kaggle/working"
    os.makedirs(work, exist_ok=True)
    for name in sorted(os.listdir(ds)):
        s = os.path.join(ds, name)
        d = os.path.join(work, name)
        if os.path.isdir(s):
            print("copying dir", name, flush=True)
            shutil.copytree(s, d, dirs_exist_ok=True)
        elif name.endswith(".tar"):
            print("extracting", name, flush=True)
            subprocess.run(["tar", "xf", s, "-C", work], check=True)
        else:
            shutil.copy(s, d)
    print("work contents:", sorted(os.listdir(work)), flush=True)

    if int(os.environ.get("PZ_TRAIN", "1")):
        print("=== TRAINING ===", flush=True)
        subprocess.run([sys.executable, os.path.join(work, "train_megaminx.py")],
                       check=True)

    print("=== SOLVING ===", flush=True)
    env = dict(os.environ)
    env["PZ_DATA"] = ds
    env["PZ_OUT"] = "/kaggle/working/submission.csv"
    subprocess.run([sys.executable, os.path.join(work, "solve_megaminx.py")],
                   check=True, env=env)
    print("=== DONE ===", flush=True)


if __name__ == "__main__":
    main()