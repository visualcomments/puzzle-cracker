"""The distilled puzzle-cracking strategy (the deliverable).

This module is the *simple and elegant algorithm* the harness produces:
one short BFS parent-tree per phase over a tiny reduced coordinate space,
so the whole 3x3x3 solver is a handful of dictionary lookups.  Exact
bidirectional BFS and colour-guided beam search cover the rest of the
puzzle family.  Run the harness (`python -m puzzle_cracker.harness ...`)
to regenerate this artifact with a fresh scorecard.

Algorithm (Rubik's cube 3x3x3, Thistlethwaite-class phase reduction):

    phase 1: fix edge orientation        (2048 reduced states)
    phase 2: fix corner orientation +
             E-slice edge placement      (1 082 565 reduced states)
    phase 3: fix corner permutation      (<= 20 160 reduced states)
    phase 4: fix the remaining edges     (<= ~967 680 reduced states,
             inside the corner-fixing subgroup of G2)

Every phase table is a BFS **parent tree**: child coordinate -> (parent,
move).  Solving a phase is walking from the current coordinate up to the
root.  No move sequences are stored, so the tables are a few tens of MB and
build in minutes in pure Python; solves are milliseconds.  The competition
slice-turn model is adapted automatically (faces = colour classes of the
solved state; face turns = all-but-centre moves).

Other puzzles:

    + 2x2x2, reversals n<=9, globe, LRX n<=8: bidirectional BFS (exact);
    + 15-puzzle: IDA* with Manhattan distance;
    + megaminx / 4x4x4+ / reversals n>=12: colour-guided beam search.

Scorecards live in docs/scorecards/; run `make verify` for the oracle.
"""

from .solvers import solve, solve_staged
from .scoring import evaluate, write_submission, summarize

__all__ = ["solve", "solve_staged", "evaluate", "write_submission", "summarize"]