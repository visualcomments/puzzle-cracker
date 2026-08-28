#!/usr/bin/env python3
"""Validate a megaminx submission locally: apply each path to its initial
state and verify it reaches the solved state.  Prints solve rate, total
moves, mean length, and the implied score.

Usage: python scripts/validate_submission.py <submission.csv>
"""
import csv
import json
import sys

DATA = "data/cayley-py-megaminx"


def load_puzzle():
    with open(f"{DATA}/puzzle_info.json") as f:
        info = json.load(f)
    central = tuple(info["central_state"])
    gens = {n: tuple(p) for n, p in info["generators"].items()}
    return central, gens


def main():
    sub_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/submission.csv"
    central, gens = load_puzzle()
    with open(f"{DATA}/test.csv") as f:
        test = {r["initial_state_id"]: tuple(int(x) for x in r["initial_state"].split(","))
                for r in csv.DictReader(f)}
    solved_cnt = 0
    total_moves = 0
    bad = 0
    empty = 0
    with open(sub_path) as f:
        rows = list(csv.DictReader(f))
    print(f"rows: {len(rows)}")
    for r in rows:
        cid = r["initial_state_id"]
        path = r["path"].strip()
        st = test[cid]
        if not path:
            empty += 1
            continue
        for m in path.split("."):
            st = tuple(st[p] for p in gens[m])
        if st == central:
            solved_cnt += 1
            total_moves += len(path.split("."))
        else:
            bad += 1
    print(f"solved: {solved_cnt}/{len(rows)}  empty: {empty}  invalid: {bad}")
    print(f"total moves: {total_moves}  mean over solved: "
          f"{total_moves/max(solved_cnt,1):.2f}")
    print(f"implied score (solved only): {total_moves}")


if __name__ == "__main__":
    main()