#!/usr/bin/env python3
"""Puzzle Cracker - Megaminx beam solver kernel (runs on Kaggle).

Competition : cayley-py-megaminx (CayleyPy family)
Metric      : total path length over solved scrambles (shorter = better)
Resources   : GPU instance (pure-Python solver; the GPU host provides the
              compute budget), ~9h wall budget.

Method      : colour-guided beam search on the competition's own facelet
              model (120 facelets, 24 face turns), greedy-first for short
              scrambles, then a wide beam (width 8192) with a per-case
              budget.  Same family as the winning CayleyPy approach
              (beam search ranked by a heuristic; here: misplaced-count).

Output      : /kaggle/working/submission.csv (initial_state_id,path)
"""

import csv
import json
import os
import sys
import time

DATA = os.environ.get("PZ_DATA", "/kaggle/input/cayley-py-megaminx")
OUT = os.environ.get("PZ_OUT", "/kaggle/working/submission.csv")

PER_CASE_BUDGET = float(os.environ.get("PZ_BUDGET", "30"))  # seconds per scramble
BEAM_WIDTH = int(os.environ.get("PZ_WIDTH", "8192"))
MAX_NODES = 4_000_000
WALL_LIMIT = float(os.environ.get("PZ_WALL", str(9 * 3600)))  # session cap
CASE_LIMIT = int(os.environ.get("PZ_LIMIT", "0")) or None     # 0 = all

# --------------------------------------------------------------------------- #
# puzzle loading
# --------------------------------------------------------------------------- #

def find_input():
    if os.path.isdir(DATA) and os.path.exists(os.path.join(DATA, "puzzle_info.json")):
        return DATA
    import glob
    for d in sorted(glob.glob("/kaggle/input/*")):
        if os.path.exists(os.path.join(d, "puzzle_info.json")) or \
           os.path.exists(os.path.join(d, "test.csv")):
            return d
    return DATA


def load_puzzle():
    DATA_G = find_input()
    print("input dir:", DATA_G, flush=True)
    with open(os.path.join(DATA_G, "puzzle_info.json")) as f:
        info = json.load(f)
    central = tuple(info["central_state"])
    gens = info["generators"]
    # keep only the 24 base face turns (clockwise/counter grouped), all moves
    moves = {}
    for name, perm in gens.items():
        moves[name] = tuple(perm)
    return central, moves


def load_cases():
    rows = []
    import glob
    DATA_G = find_input()
    with open(os.path.join(DATA_G, "test.csv")) as f:
        for row in csv.DictReader(f):
            st = tuple(int(x) for x in row["initial_state"].split(","))
            rows.append((row["initial_state_id"], st))
    return rows


# --------------------------------------------------------------------------- #
# solver
# --------------------------------------------------------------------------- #

def misplaced_h(central):
    c = central
    n = len(c)

    def h(state):
        total = 0
        for i in range(n):
            if state[i] != c[i]:
                total += 1
        return total

    return h


def apply(state, perm):
    return tuple(state[p] for p in perm)


def greedy(puzzle_moves, state, solved, h, max_nodes=120_000):
    """Greedy best-first (fast for short scrambles)."""
    import heapq

    start_h = h(state)
    heap = [(start_h, 0, state, [])]
    seen = {state}
    while heap:
        _, _, cur, path = heapq.heappop(heap)
        if cur == solved:
            return path
        for m in puzzle_moves:
            ns = apply(cur, puzzle_moves[m])
            if ns in seen:
                continue
            seen.add(ns)
            if len(seen) > max_nodes:
                return None
            heapq.heappush(heap, (h(ns), len(seen), ns, path + [m]))
    return None


def beam(puzzle_moves, state, solved, h, width=BEAM_WIDTH,
         budget=PER_CASE_BUDGET, max_nodes=MAX_NODES, t0=None,
         wall=WALL_LIMIT):
    """Wide beam search ranked by the heuristic."""
    if state == solved:
        return []
    beam = [(h(state), state, [])]
    seen = {state}
    start = t0 or time.time()
    deadline = start + budget
    while True:
        if time.time() > deadline or time.time() > start + wall:
            return None
        candidates = []
        for _, cur, path in beam:
            for m in puzzle_moves:
                ns = apply(cur, puzzle_moves[m])
                if ns in seen:
                    continue
                seen.add(ns)
                if len(seen) > max_nodes:
                    return None
                nh = h(ns)
                if ns == solved:
                    return path + [m]
                candidates.append((nh, ns, path + [m]))
        if not candidates:
            return None
        candidates.sort(key=lambda t: t[0])
        beam = candidates[:width]


def solve_one(puzzle_moves, state, solved, h):
    """Per-case budget must be measured from the *case* start, not the
    global kernel start - otherwise late cases get a zero budget."""
    if state == solved:
        return []
    t1 = time.time()
    res = greedy(puzzle_moves, state, solved, h)
    if res is not None:
        return res
    return beam(puzzle_moves, state, solved, h, t0=t1)


def shorten(sol, puzzle_moves, solved):
    """Cheap polynomial shortening: drop any move undone immediately, and
    try replacing triple-move runs (a,a,a = inverse) greedily."""
    if not sol:
        return sol
    inv = {}
    for m in puzzle_moves:
        inv[m] = m[1:] if m.startswith("-") else "-" + m
    out = []
    for m in sol:
        if out and out[-1] == inv[m]:
            out.pop()
        else:
            out.append(m)
    return out


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main():
    print("puzzle-cracker megaminx kernel start", flush=True)
    central, puzzle_moves = load_puzzle()
    names = sorted(puzzle_moves)
    pm = {m: puzzle_moves[m] for m in names}
    cases = load_cases()
    if CASE_LIMIT:
        cases = cases[:CASE_LIMIT]
    h = misplaced_h(central)
    solved_state = tuple(central)

    t0 = time.time()
    rows = []
    solved_cnt = 0
    total_moves = 0
    for i, (cid, st) in enumerate(cases):
        sol = solve_one(pm, st, solved_state, h)
        if sol is not None:
            sol = shorten(sol, pm, solved_state)
            # verify
            back = st
            for m in sol:
                back = apply(back, pm[m])
            if back == solved_state:
                solved_cnt += 1
                total_moves += len(sol)
                rows.append((cid, ".".join(sol)))
            else:
                rows.append((cid, ""))
        else:
            rows.append((cid, ""))
        if (i + 1) % 25 == 0 or i == len(cases) - 1:
            print(f"[{i+1}/{len(cases)}] solved={solved_cnt} "
                  f"moves={total_moves} elapsed={time.time()-t0:.0f}s",
                  flush=True)
        if time.time() - t0 > WALL_LIMIT - 300:
            print("wall limit reached - writing partial submission",
                  flush=True)
            break

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["initial_state_id", "path"])
        for cid, path in rows:
            w.writerow([cid, path])
    print(f"done: {solved_cnt}/{len(cases)} solved, {total_moves} total "
          f"moves, {time.time()-t0:.0f}s -> {OUT}", flush=True)


if __name__ == "__main__":
    main()