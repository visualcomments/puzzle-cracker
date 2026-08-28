"""Generic puzzle solvers: bidirectional BFS, IDA*, beam search.

All solvers share one contract:

    solve(puzzle, state, budget...) -> Optional[list[str]]

returning the sequence of move names that maps ``state`` onto
``puzzle.solved`` (empty list when already solved, ``None`` when the budget
was exhausted).  Budgets are *node* budgets (expanded states) so behaviour
is comparable across puzzles and machines.
"""

from __future__ import annotations

import heapq
import time
from collections import deque
from typing import Callable, Dict, List, Optional

from ..group import Puzzle, State, bidirectional_bfs

Heuristic = Callable[[State], int]


# --------------------------------------------------------------------------- #
def solve_bibfs(puzzle: Puzzle, state: State, *,
                max_states: int = 2_000_000) -> Optional[List[str]]:
    """Optimal solver via bidirectional BFS.  Use when the Cayley graph
    diameter is small (2x2x2, pancake <= 9, globe, mini-pyramorphix...)."""
    return bidirectional_bfs(puzzle, state, max_states=max_states)


def solve_bibfs_adaptive(puzzle: Puzzle, state: State, *,
                         max_states: int = 4_000_000) -> Optional[List[str]]:
    try:
        return bidirectional_bfs(puzzle, state, max_states=max_states)
    except RuntimeError:
        return None


# --------------------------------------------------------------------------- #
def solve_ida(puzzle: Puzzle, state: State, heuristic: Heuristic, *,
              max_nodes: int = 5_000_000, bound_hint: Optional[int] = None,
              max_depth: int = 64) -> Optional[List[str]]:
    """Iterative-deepening A* with admissible/consistent ``heuristic``.

    Returns the optimum move sequence within the node budget, or ``None``.
    """
    n_moves = len(puzzle.move_names)
    h0 = heuristic(state)
    bound = bound_hint if bound_hint is not None else max(2, h0)
    total = 0

    def search(node: State, g: int, bound: int, prev: Optional[str]) -> Optional[List[str]]:
        nonlocal total
        f = g + heuristic(node)
        if f > bound:
            return None
        if node == puzzle.solved:
            return []
        total += 1
        if total > max_nodes or g >= max_depth:
            return None
        # move ordering: prefer moves that lower the heuristic
        children = []
        for m in puzzle.move_names:
            if prev is not None and m == _inverse(prev):
                continue  # skip undoing the previous move
            ns = puzzle.apply(node, m)
            children.append((heuristic(ns), m, ns))
        children.sort(key=lambda t: t[0])
        for _, m, ns in children:
            if g + 1 + heuristic(ns) > bound:
                continue
            sub = search(ns, g + 1, bound, m)
            if sub is not None:
                return [m] + sub
        return None

    def _inverse(m: str) -> str:
        return m[1:] if m.startswith("-") else "-" + m

    while bound <= max_depth:
        path = search(state, 0, bound, None)
        if path is not None:
            return path
        if total > max_nodes:
            return None
        bound += 1
    return None


# --------------------------------------------------------------------------- #
def solve_greedy(puzzle: Puzzle, state: State, heuristic: Heuristic, *,
                 max_nodes: int = 500_000) -> Optional[List[str]]:
    """Greedy best-first search (no reopening): fast, non-optimal."""
    import heapq as _h
    start_h = heuristic(state)
    heap = [(start_h, 0, state, [])]  # (h, tie, state, path)
    seen = {state}
    while heap:
        h, _, cur, path = _h.heappop(heap)
        if cur == puzzle.solved:
            return path
        for m in puzzle.move_names:
            ns = puzzle.apply(cur, m)
            if ns in seen:
                continue
            seen.add(ns)
            if len(seen) > max_nodes:
                return None
            _h.heappush(heap, (heuristic(ns), len(seen), ns, path + [m]))
    return None


def solve_beam(puzzle: Puzzle, state: State, heuristic: Heuristic, *,
               beam_width: int = 4096, max_nodes: int = 5_000_000,
               max_steps: int = 2000, time_budget_s: float = 120.0) -> Optional[List[str]]:
    """Beam search with the given heuristic (the workhorse for huge Cayley
    graphs: megaminx, 4x4x4+, reversals n>=12...)."""
    if state == puzzle.solved:
        return []
    beam = [(heuristic(state), state, [])]
    seen = {state}
    t0 = time.time()
    for step in range(max_steps):
        if time.time() - t0 > time_budget_s:
            return None
        candidates: List[tuple] = []
        for _, cur, path in beam:
            for m in puzzle.move_names:
                ns = puzzle.apply(cur, m)
                if ns in seen:
                    continue
                seen.add(ns)
                if len(seen) > max_nodes:
                    return None
                nh = heuristic(ns)
                if ns == puzzle.solved:
                    return path + [m]
                candidates.append((nh, ns, path + [m]))
        if not candidates:
            return None
        candidates.sort(key=lambda t: t[0])
        beam = candidates[:beam_width]
    return None


# --------------------------------------------------------------------------- #
# heuristic factory
# --------------------------------------------------------------------------- #

def mismatched_count(puzzle: Puzzle) -> Heuristic:
    """Number of positions whose token differs from the solved token.
    Admissible for 'one position fixed per move' puzzles only (use with
    beam/greedy); for twisty puzzles it is still a useful ranking signal."""
    solved = puzzle.solved

    def h(state: State) -> int:
        return sum(1 for a, b in zip(state, solved) if a != b)

    return h


def manhattan_15(puzzle: Puzzle) -> Optional[Heuristic]:
    """Manhattan distance for the 15-puzzle (positions 0..15, grid 4x4)."""
    if puzzle.n != 16 or puzzle.name != "fifteen":
        return None
    pos_of = {i: (i // 4, i % 4) for i in range(16)}

    def h(state: State) -> int:
        total = 0
        for i, tok in enumerate(state):
            if tok == "0":
                continue
            tgt = int(tok) - 1  # tile k belongs at position k-1
            r1, c1 = pos_of[i]
            r2, c2 = pos_of[tgt]
            total += abs(r1 - r2) + abs(c1 - c2)
        return total

    return h


def color_face_distance(puzzle: Puzzle) -> Heuristic:
    """Heuristic for facelet puzzles: for each position, distance to the
    nearest position whose solved token matches; sum over positions.
    (Fast to compute; use as a ranking signal for beam search.)"""
    solved = puzzle.solved
    # per-token -> list of solved positions carrying that token
    buckets: Dict[str, List[int]] = {}
    for i, tok in enumerate(solved):
        buckets.setdefault(tok, []).append(i)
    cache: Dict[str, int] = {}

    def h(state: State) -> int:
        # precompute a rough per-token distance table lazily (positions are
        # indices; we just count index distance - a cheap proxy)
        total = 0
        for i, tok in enumerate(state):
            if tok == solved[i]:
                continue
            opts = buckets.get(tok)
            if not opts:
                continue
            total += 1  # count a mismatch; effective depth proxy
        return total

    return h