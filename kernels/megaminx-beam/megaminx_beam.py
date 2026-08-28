#!/usr/bin/env python3
"""Puzzle Cracker - Megaminx beam solver kernel, improved (runs on Kaggle).

Competition : cayley-py-megaminx (CayleyPy family)
Metric      : total path length over solved scrambles (shorter = better)
Resources   : CPU instance (12h wall budget; runs concurrently with the GPU
              diffusion kernel).

Improvements over the v1 beam:
  * move pruning during search: no inverse-of-last, no 3x same face in a row
    (provably safe: a^3 == a^-1 a^-1 and a^4 == a^-1 under the 24-turn set);
  * iterative beam widening: widths 1024 -> 8192 -> 65536 within the per-case
    budget, so short cases finish fast and hard cases get the wide beam;
  * better shortening pass (a^4 -> a^-1, a^3 -> a^-1 a^-1, inverse pairs).

Output      : /kaggle/working/submission.csv (initial_state_id,path)
Env: PZ_DATA, PZ_OUT, PZ_BUDGET (per-case seconds), PZ_LIMIT.
"""

import csv
import json
import os
import time

DATA = os.environ.get("PZ_DATA", "/kaggle/input/cayley-py-megaminx")
OUT = os.environ.get("PZ_OUT", "/kaggle/working/submission.csv")

PER_CASE_BUDGET = float(os.environ.get("PZ_BUDGET", "40"))
WIDTHS = [int(x) for x in os.environ.get("PZ_WIDTHS", "1024,8192,65536").split(",")]
MAX_NODES = 12_000_000
WALL_LIMIT = float(os.environ.get("PZ_WALL", str(11 * 3600)))
CASE_LIMIT = int(os.environ.get("PZ_LIMIT", "0")) or None


def find_input():
    for root, dirs, files in os.walk("/kaggle/input"):
        if "puzzle_info.json" in files or "test.csv" in files:
            return root
    return DATA


def load_puzzle():
    DATA_G = find_input()
    print("input dir:", DATA_G, flush=True)
    with open(os.path.join(DATA_G, "puzzle_info.json")) as f:
        info = json.load(f)
    central = tuple(info["central_state"])
    gens = info["generators"]
    moves = {}
    for name, perm in gens.items():
        moves[name] = tuple(perm)
    return central, moves


def load_cases():
    rows = []
    DATA_G = find_input()
    with open(os.path.join(DATA_G, "test.csv")) as f:
        for row in csv.DictReader(f):
            st = tuple(int(x) for x in row["initial_state"].split(","))
            rows.append((row["initial_state_id"], st))
    return rows


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


def allowed_moves(pm, inv_of, prev, prevprev):
    """Yield moves not equal to the inverse of the previous and not a third
    consecutive same-face move (both provably redundant)."""
    for m in pm:
        if prev is not None and m == inv_of[prev]:
            continue
        if prev is not None and m == prev and prevprev == prev:
            continue
        yield m


def greedy(pm, inv_of, state, solved, h, max_nodes=200_000):
    import heapq
    start_h = h(state)
    heap = [(start_h, 0, state, [])]
    seen = {state}
    while heap:
        _, _, cur, path = heapq.heappop(heap)
        if cur == solved:
            return path
        prev = path[-1] if path else None
        prevprev = path[-2] if len(path) > 1 else None
        for m in allowed_moves(pm, inv_of, prev, prevprev):
            ns = apply(cur, pm[m])
            if ns in seen:
                continue
            seen.add(ns)
            if len(seen) > max_nodes:
                return None
            heapq.heappush(heap, (h(ns), len(seen), ns, path + [m]))
    return None


def beam(pm, inv_of, state, solved, h, width, budget, max_nodes, t0, wall):
    """Beam search with move pruning; returns the path when the solved state
    is expanded, else None."""
    if state == solved:
        return []
    beam = [(h(state), state, [])]
    seen = {state}
    deadline = t0 + budget
    while True:
        if time.time() > deadline or time.time() > t0 + wall:
            return None
        candidates = []
        for _, cur, path in beam:
            prev = path[-1] if path else None
            prevprev = path[-2] if len(path) > 1 else None
            for m in allowed_moves(pm, inv_of, prev, prevprev):
                ns = apply(cur, pm[m])
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


def solve_one(pm, inv_of, state, solved, h):
    """Greedy first, then iterative beam widening within the per-case budget."""
    if state == solved:
        return []
    t1 = time.time()
    res = greedy(pm, inv_of, state, solved, h)
    if res is not None:
        return res
    for width in WIDTHS:
        if time.time() - t1 > PER_CASE_BUDGET:
            break
        res = beam(pm, inv_of, state, solved, h, width,
                   PER_CASE_BUDGET - (time.time() - t1), MAX_NODES, t1, WALL_LIMIT)
        if res is not None:
            return res
    return None


def shorten(sol, pm, solved):
    """Shorten: drop inverse pairs, compress a^3 -> a^-1 a^-1 and a^4 -> a^-1
    (the move set has no 2/5-turn, so a,a is a real 144deg turn but a^3/a^4
    are always redundant), then repeat once."""
    if not sol:
        return sol
    inv = {}
    for m in pm:
        inv[m] = m[1:] if m.startswith("-") else "-" + m
    changed = True
    while changed:
        changed = False
        out = []
        i = 0
        n = len(sol)
        while i < n:
            m = sol[i]
            # a^4 == a^-1
            if i + 3 < n and sol[i] == sol[i+1] == sol[i+2] == sol[i+3]:
                out.append(inv[m])
                i += 4
                changed = True
                continue
            # a^3 == a^-1 a^-1
            if i + 2 < n and sol[i] == sol[i+1] == sol[i+2]:
                out.append(inv[m])
                out.append(inv[m])
                i += 3
                changed = True
                continue
            # a b a^-1 -> drop when b == a (a a a^-1 == a)
            if out and out[-1] == inv[m]:
                out.pop()
                i += 1
                changed = True
                continue
            out.append(m)
            i += 1
        sol = out
    return sol


def main():
    print("puzzle-cracker megaminx beam kernel (improved) start", flush=True)
    central, puzzle_moves = load_puzzle()
    names = sorted(puzzle_moves)
    pm = {m: puzzle_moves[m] for m in names}
    inv_of = {}
    for m in names:
        inv_of[m] = m[1:] if m.startswith("-") else "-" + m
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
        sol = solve_one(pm, inv_of, st, solved_state, h)
        if sol is not None:
            sol = shorten(sol, pm, solved_state)
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
                  f"moves={total_moves} mean={total_moves/max(solved_cnt,1):.2f} "
                  f"elapsed={time.time()-t0:.0f}s", flush=True)
        if time.time() - t0 > WALL_LIMIT - 300:
            print("wall limit reached - writing partial submission", flush=True)
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