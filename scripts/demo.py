#!/usr/bin/env python3
"""End-to-end demo: solve random scrambles across the puzzle family and show
the simple-elegant-algorithm story with real numbers.

Run:  python scripts/demo.py   (or `make demo`)
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from puzzle_cracker import rubik_333, reversals, rubik_222, solve
from puzzle_cracker.puzzles import load_santa_2023
from puzzle_cracker.solvers.staged import cube_adapter_for


def demo_222():
    print("== 2x2x2 Rubik's cube (bidirectional BFS, optimal) ==")
    pz = rubik_222()
    rng = random.Random(1)
    total, solved = 0, 0
    for k in (5, 8, 11):
        st, _ = pz.scrambled(k, rng)
        t0 = time.time()
        sol = solve(pz, st, method="bibfs")
        dt = time.time() - t0
        ok = sol is not None
        if ok:
            back = st
            for m in sol:
                back = pz.apply(back, m)
            ok = back == pz.solved
        print(f"  scramble {k}: solved={ok} len={len(sol) if sol else '-'} "
              f"({dt:.2f}s)")
        solved += ok
        total += 1
    print(f"  {solved}/{total} solved")


def demo_333():
    print()
    print("== 3x3x3 Rubik's cube (staged phase solver) ==")
    data = load_santa_2023("data/santa-2023", puzzle_types=["cube_3/3/3"])
    pz = data["cube_3/3/3"]["puzzle"]
    sc = cube_adapter_for(pz)
    rng = random.Random(2)
    solved = 0
    for k in (1, 2, 3):
        st, _ = pz.scrambled(k, rng)
        t0 = time.time()
        try:
            sol = sc.solve(st, table_dir="cache/tables")
        except Exception:
            sol = None
        ok = sol is not None
        if ok:
            back = st
            for m in sol:
                back = pz.apply(back, m)
            ok = back == pz.solved
        print(f"  scramble {k}: solved={ok} len={len(sol) if sol else '-'} "
              f"({time.time() - t0:.1f}s)")
        solved += ok
    print(f"  {solved}/3 solved on short scrambles (tables cached under "
          "cache/tables); longer scrambles need the table completion "
          "work documented in docs/puzzles.md and the rubiks-cube skill")


def demo_reversals():
    print()
    print("== Reversals n=8 (bidirectional BFS, optimal) ==")
    pz = reversals(8)
    rng = random.Random(3)
    for k in (4, 7, 10):
        st, _ = pz.scrambled(k, rng)
        t0 = time.time()
        sol = solve(pz, st, method="bibfs")
        ok = sol is not None
        if ok:
            back = st
            for m in sol:
                back = pz.apply(back, m)
            ok = back == pz.solved
        print(f"  scramble {k}: solved={ok} len={len(sol) if sol else '-'} "
              f"({time.time() - t0:.2f}s)")


if __name__ == "__main__":
    if not os.path.exists("data/santa-2023/puzzle_info.csv"):
        print("competition data missing - run:  make data   "
              "(KAGGLE_KEY required)")
        sys.exit(1)
    demo_222()
    demo_333()
    demo_reversals()
    print("\nSee docs/puzzles.md for the algorithm write-up "
          "and docs/competitions.md for the family.")