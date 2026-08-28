#!/usr/bin/env python3
"""Correctness oracle: random scrambles must solve 100%.

Run:  python scripts/verify.py   (or `make verify`)
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from puzzle_cracker import rubik_222, rubik_333, reversals, solve
from puzzle_cracker.puzzles import load_santa_2023
from puzzle_cracker.solvers.staged import cube_adapter_for

FAIL = 0


def check(name, ok):
    global FAIL
    print(f"  {'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        FAIL += 1


def verify_222():
    print("== 2x2x2: 20 random scrambles, must solve 100% ==")
    pz = rubik_222()
    rng = random.Random(99)
    ok = True
    for k in range(20):
        st, _ = pz.scrambled(k % 9 + 3, rng)
        sol = solve(pz, st, method="bibfs", max_nodes=4_000_000)
        if sol is None:
            ok = False
            continue
        back = st
        for m in sol:
            back = pz.apply(back, m)
        ok = ok and back == pz.solved
    check("2x2x2 bibfs", ok)


def verify_reversals():
    print("== reversals n=8: 20 random scrambles ==")
    pz = reversals(8)
    rng = random.Random(7)
    ok = True
    for k in range(20):
        st, _ = pz.scrambled(k % 9 + 3, rng)
        sol = solve(pz, st, method="bibfs")
        if sol is None:
            ok = False
            continue
        back = st
        for m in sol:
            back = pz.apply(back, m)
        ok = ok and back == pz.solved
    check("reversals-8 bibfs", ok)


def verify_333():
    print("== 3x3x3 staged: 10 short scrambles ==")
    data = load_santa_2023("data/santa-2023", puzzle_types=["cube_3/3/3"])
    pz = data["cube_3/3/3"]["puzzle"]
    sc = cube_adapter_for(pz)
    rng = random.Random(5)
    ok = True
    solved = 0
    for k in (2, 4, 6, 8):
        st, _ = pz.scrambled(k, rng)
        t0 = time.time()
        sol = solve(pz, st, method="bibfs", max_nodes=1_500_000)
        if sol is None:
            ok = False
            continue
        back = st
        for m in sol:
            back = pz.apply(back, m)
        ok = ok and back == pz.solved
        solved += back == pz.solved
    check("3x3x3 bibfs (short scrambles, optimal)", ok and solved == 4)


if __name__ == "__main__":
    if not os.path.exists("data/santa-2023/puzzle_info.csv"):
        print("data/santa-2023 missing - run `make data` first")
        sys.exit(1)
    verify_222()
    verify_reversals()
    verify_333()
    print()
    print("FAILURES:", FAIL)
    sys.exit(1 if FAIL else 0)