"""Scoring and evaluation for puzzle-cracking runs.

The harness reports, for every puzzle in a competition data set:

    * solve rate            - fraction of scrambles solved within budget;
    * total moves           - sum of |solution| over solved scrambles;
    * mean solution length  - total / solved count;
    * strategy score        - a single number: (solved / total) * (1 + q),
                              where q is a normalized optimality bonus.

For the CayleyPy competition family "best score" means shortest total path
length, so the default report is the total-moves table with solve rate.
"""

from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .group import Puzzle, State


@dataclass
class CaseResult:
    case_id: str
    solved: bool
    moves: Optional[List[str]]
    length: int
    time_s: float


@dataclass
class RunReport:
    puzzle_name: str
    results: List[CaseResult] = field(default_factory=list)

    @property
    def solved(self) -> int:
        return sum(1 for r in self.results if r.solved)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def total_moves(self) -> int:
        return sum(r.length for r in self.results if r.solved)

    @property
    def mean_length(self) -> float:
        n = self.solved
        return self.total_moves / n if n else float("inf")

    @property
    def solve_rate(self) -> float:
        return self.solved / self.total if self.total else 0.0

    @property
    def score(self) -> float:
        """Impossible-to-reach-0 style metric: solve rate * (length factor).

        The exact competition metric is kept pluggable; this default rewards
        solving everything with short paths."""
        if self.total == 0:
            return 0.0
        rate = self.solved / self.total
        if self.solved == 0:
            return 0.0
        # length bonus: 1.0 when mean == 1 move, → 0 as mean grows
        mb = 1.0 / (1.0 + self.mean_length)
        return 100.0 * rate * mb

    def table(self) -> str:
        lines = [f"== {self.puzzle_name} ==",
                 f"  solved {self.solved}/{self.total} "
                 f"({100 * self.solve_rate:.1f}%)",
                 f"  total moves : {self.total_moves}",
                 f"  mean length : {self.mean_length:.2f}",
                 f"  score       : {self.score:.2f}"]
        return "\n".join(lines)


def evaluate(puzzle: Puzzle, cases: Sequence[dict],
             solver: Callable[[State], Optional[List[str]]],
             time_budget_s: float = 30.0, verbose: bool = True,
             progress_every: int = 50) -> RunReport:
    """Solve ``cases`` (each has ``initial_state``) with ``solver``."""
    report = RunReport(puzzle.name)
    t0 = time.time()
    for i, case in enumerate(cases):
        st = State(case["initial_state"])
        c0 = time.time()
        try:
            moves = solver(st)
        except Exception as exc:  # solver must never crash the run
            moves = None
            if verbose:
                print(f"  !! case {case.get('id', i)} raised {exc!r}")
        dt = time.time() - c0
        solved = moves is not None and _validates(puzzle, st, moves)
        report.results.append(CaseResult(
            case_id=str(case.get("id", i)), solved=solved,
            moves=moves if solved else None,
            length=len(moves) if solved and moves else 0,
            time_s=dt))
        if verbose and (i % progress_every == 0 or i == len(cases) - 1):
            print(f"  [{i + 1}/{len(cases)}] "
                  f"elapsed {time.time() - t0:.0f}s")
    return report


def _validates(puzzle: Puzzle, start: State, moves: List[str]) -> bool:
    st = start
    for m in moves:
        st = puzzle.apply(st, m)
    return st == puzzle.solved


def write_submission(report: RunReport, path: str,
                     id_col: str = "id", move_col: str = "moves") -> None:
    """Write a Kaggle-style submission CSV (id, moves/path)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([id_col, move_col])
        for r in report.results:
            w.writerow([r.case_id, ".".join(r.moves) if r.moves else ""])


def summarize(reports: List[RunReport]) -> str:
    lines = ["# puzzle-cracker run summary", ""]
    tot_moves = 0
    tot_solved = 0
    tot_cases = 0
    for r in reports:
        lines.append(r.table())
        tot_moves += r.total_moves
        tot_solved += r.solved
        tot_cases += r.total
    lines.append("")
    lines.append(f"TOTAL: {tot_solved}/{tot_cases} solved, {tot_moves} moves")
    return "\n".join(lines)