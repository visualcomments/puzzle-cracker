"""Solver dispatch: pick the right algorithm for a puzzle and budget."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from ..group import Puzzle, State
from . import generic
from .staged import StagedCube, build_canonical_333
from .cube_adapter import detect_face_turns

SOLVERS = {
    "bibfs": generic.solve_bibfs_adaptive,
    "ida": generic.solve_ida,
}


def make_heuristic(puzzle: Puzzle):
    h = generic.manhattan_15(puzzle)
    if h is not None:
        return h
    return generic.mismatched_count(puzzle)


def solve(puzzle: Puzzle, state: State, *,
          method: Optional[str] = None, time_budget_s: float = 30.0,
          max_nodes: int = 2_000_000, table_dir: Optional[str] = None) -> Optional[List[str]]:
    """Solve ``state`` -> ``puzzle.solved`` with an automatic method pick.

    Order: staged (3x3x3-class), bidirectional BFS (small groups, budgeted),
    IDA* (heuristic), beam (huge graphs).  No group-size precomputation: a
    full-group BFS would blow memory on 2x2x2-sized spaces.
    """
    # 3x3x3-class -> staged solver
    if puzzle.n == 54:
        ft = _face_turns_cache(puzzle)
        if ft is not None:
            face_turns, face_of = ft
            sc = StagedCube(puzzle, face_turns, face_of=face_of)
            try:
                return sc.solve(state, table_dir=table_dir)
            except Exception:
                pass

    # bidirectional BFS first (budgeted)
    if method in (None, "bibfs"):
        res = generic.solve_bibfs_adaptive(puzzle, state, max_states=max_nodes)
        if res is not None:
            return res

    # IDA* for medium
    h = make_heuristic(puzzle)
    if method in (None, "ida"):
        res = generic.solve_ida(puzzle, state, h, max_nodes=max_nodes)
        if res is not None:
            return res

    # beam search fallback for huge graphs (megaminx, 4x4x4+...)
    if method in (None, "beam"):
        res = generic.solve_beam(puzzle, state, h,
                                 time_budget_s=time_budget_s, max_nodes=max_nodes * 4)
        return res
    return None


_ft_cache: Dict[str, tuple] = {}


def _face_turns_cache(puzzle: Puzzle):
    key = puzzle.name
    if key in _ft_cache:
        return _ft_cache[key]
    try:
        ft = detect_face_turns(puzzle)
    except Exception:
        ft = None
    _ft_cache[key] = ft
    return ft


def solve_staged(puzzle: Puzzle, state: State, table_dir: Optional[str] = None) -> Optional[List[str]]:
    """Force the staged solver (3x3x3-class puzzles)."""
    ft = _face_turns_cache(puzzle)
    if ft is None:
        return None
    face_turns, face_of = ft
    sc = StagedCube(puzzle, face_turns, face_of=face_of)
    return sc.solve(state, table_dir=table_dir)