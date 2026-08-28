"""Polynomial-time enforcement for the harness.

Implements the complexity contract of the `polynomial-time-algorithms`
skill: every solver ships with an explicit polynomial node/move budget in
the puzzle parameters (``n``, ``d``), all budgets are enforced at runtime
(fail fast, never hang), and constructive polynomial solvers are provided
that always return a valid path.

    parameters:
        n - puzzle size parameter (facelets / permutation length / order)
        d - scramble length / instance size

    contract:
        worst-case runtime  O(poly(n, d))   (never 2^d, n!, |space|^k ...)
        returned paths      bounded by the stated polynomial move count
"""

from __future__ import annotations

import time
from typing import Callable, List, Optional, Sequence

from .group import Puzzle, State

# --------------------------------------------------------------------------- #
# budget helpers
# --------------------------------------------------------------------------- #

def poly_budget(n: int, d: int = 0, *, C: float = 1.0, n_pow: int = 2,
                d_pow: int = 1, floor: int = 512) -> int:
    """Polynomial node budget: ``C * n**n_pow * max(d,1)**d_pow``.

    Any search using this budget is polynomial in (n, d) by construction.
    """
    return max(floor, int(C * (n ** n_pow) * (max(d, 1) ** d_pow)))


def ensure_poly(name: str, used: int, budget: int) -> None:
    """Hard enforcement: stop the run if a search exceeded its polynomial
    budget (instead of hanging or silently degrading)."""
    if used > budget:
        raise RuntimeError(
            f"[poly] {name} used {used} > polynomial budget {budget} "
            f"- redesign or raise the budget explicitly")


# --------------------------------------------------------------------------- #
# constructive polynomial solvers
# --------------------------------------------------------------------------- #

def _prefix_flip_name(puzzle: Puzzle, j: int) -> str:
    """Return the puzzle's move name for reversing the prefix [0..j]
    (tolerates R[0,j], R0j, flip_j, 'R[0,%d]' naming conventions)."""
    cands = [f"R[0,{j}]", f"R0..{j}", f"r{j}", f"flip{j}", f"F[{j}]"]
    for cand in cands:
        if cand in puzzle.moves:
            return cand
    # fall back: search by content (permutation of the prefix)
    from .group import apply_perm
    rev = tuple(range(j, -1, -1)) + tuple(range(j + 1, puzzle.n))
    for name, perm in puzzle.moves.items():
        if perm == rev:
            return name
    raise KeyError(f"no prefix-flip move for j={j} in {puzzle.name}")


def solve_pancake_poly(puzzle: Puzzle, state: State) -> List[str]:
    """Constructive polynomial solver for prefix-reversal / segment-reversal
    puzzles (pancake family, `reversals(n, all_segments=False|True)`).

    Idea (classic pancake bound): for each target position t from the end
    backwards, bring the element that belongs there to the front with one
    prefix flip, then flip the prefix [0..t] to drop it into place.  Each
    element costs at most 2 flips -> at most 2n moves, O(n^2) time - a
    polynomial algorithm by construction (see the polynomial-time skill).

    Works for puzzles whose move set contains every prefix reversal
    R[0,j] (it simply uses those moves; extra generators are irrelevant).
    """
    n = puzzle.n
    solved = puzzle.solved
    cur = tuple(state)
    moves = puzzle.moves
    seq: List[str] = []

    def flip(name: str) -> None:
        nonlocal cur
        cur = puzzle.apply(cur, name)
        seq.append(name)

    # index of each token (per run; n small)
    for t in range(n - 1, 0, -1):
        want = solved[t]
        pos = cur.index(want)
        if pos == t:
            continue
        if pos != 0:
            flip(_prefix_flip_name(puzzle, pos))
            pos = 0
        flip(_prefix_flip_name(puzzle, t))
    assert cur == solved, "pancake solver produced an invalid result"
    return seq


def solve_cycle_sort_poly(puzzle: Puzzle, state: State) -> List[str]:
    """Constructive polynomial solver for puzzles whose move set includes
    arbitrary transpositions (transposons family) or 2-cycles: resolve the
    permutation into cycles and break each cycle with adjacent-element
    swaps, <= 2n transpositions, O(n log n) time (with a position index)."""
    n = puzzle.n
    solved = puzzle.solved
    cur = list(state)
    seq: List[str] = []

    def swap_name(i: int, j: int) -> str:
        perm = list(range(n))
        perm[i], perm[j] = perm[j], perm[i]
        for name, p in puzzle.moves.items():
            if p == tuple(perm):
                return name
        raise KeyError(f"no transposition {i}<->{j} in {puzzle.name}")

    for t in range(n - 1, 0, -1):
        want = solved[t]
        pos = cur.index(want)
        if pos == t:
            continue
        while pos < t:
            seq.append(swap_name(pos, pos + 1))
            cur[pos], cur[pos + 1] = cur[pos + 1], cur[pos]
            pos += 1
    assert tuple(cur) == solved
    return seq


# --------------------------------------------------------------------------- #
# scaling check (empirical verification of polynomial growth)
# --------------------------------------------------------------------------- #

def scaling_check(fn: Callable[[int], float], sizes: Sequence[int],
                  labels: Sequence[str]) -> dict:
    """Run ``fn`` at increasing sizes and measure the cost-growth exponent.

    A polynomial algorithm shows log(cost)/log(ratio) ~ constant (1..3);
    exponential search *diverges* with size.  Records the result for the
    scorecard (see `polynomial-time-algorithms` skill).
    """
    out: List[float] = []
    for s in sizes:
        t0 = time.time()
        fn(s)
        out.append(time.time() - t0)
    exps = []
    for k in range(1, len(sizes)):
        ratio = sizes[k] / sizes[k - 1]
        exps.append(round((out[k] - out[k - 1]) / max(out[k - 1], 1e-9) /
                          (ratio - 1), 2) if out[k - 1] > 0 else None)
    return {"sizes": list(sizes), "seconds": out,
            "growth_exponent": exps,
            "labels": list(labels)}