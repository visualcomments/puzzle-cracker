"""Megaminx solving.

The megaminx (12 faces x 10 facelets) has a state space far beyond exact
search, so the harness uses a *per-face colour-guided beam search*: the
heuristic is the number of facelets not sitting on their home face, and a
wide beam tours the Cayley graph under the 24 face turns.  This is the
same pattern the CayleyPy community uses for the huge slice-cube graphs
(here without the learned diffusion estimator; the neural upgrade path is
documented in docs/puzzles.md).

For short scrambles a greedy best-first pass usually finds the inverse walk
immediately; the beam then polishes.  The interface matches the generic
solvers (puzzle, state, budgets -> Optional[list[str]]).
"""

from __future__ import annotations

from typing import Callable, List, Optional

from ..group import Puzzle, State
from . import generic


def facelet_home_heuristic(puzzle: Puzzle) -> Callable[[State], int]:
    """Heuristic for facelet puzzles: number of facelets not on a home
    face.  Every move fixes at most ~15 facelets, so this is a good beam
    ranking signal (not admissible - use with beam/greedy)."""
    solved = puzzle.solved

    def h(state: State) -> int:
        return sum(1 for a, b in zip(state, solved) if a != b)

    return h


def solve_megaminx(puzzle: Puzzle, state: State, *,
                   time_budget_s: float = 60.0,
                   max_nodes: int = 8_000_000,
                   beam_width: int = 8192) -> Optional[List[str]]:
    """Two-stage megaminx solve: greedy best-first, then wide beam search."""
    h = facelet_home_heuristic(puzzle)
    res = generic.solve_greedy(puzzle, state, h, max_nodes=max_nodes // 4)
    if res is not None:
        return res
    return generic.solve_beam(puzzle, state, h,
                              beam_width=beam_width,
                              max_nodes=max_nodes,
                              time_budget_s=time_budget_s)


def solve_any_big(puzzle: Puzzle, state: State, *,
                  time_budget_s: float = 60.0) -> Optional[List[str]]:
    """Generic solver for huge Cayley graphs (megaminx, 4x4x4+, big
    reversals): greedy first, then beam."""
    return solve_megaminx(puzzle, state, time_budget_s=time_budget_s)