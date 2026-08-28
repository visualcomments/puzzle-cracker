"""API surface of the puzzle-cracker package."""

__version__ = "0.1.0"

from .group import Puzzle, State
from . import puzzles, solvers, complexity
from .solvers import solve, solve_staged
from .complexity import (
    poly_budget, ensure_poly, solve_pancake_poly, solve_cycle_sort_poly,
    scaling_check,
)
from .puzzles import (
    rubik_222, rubik_333, reversals, lrx, topspin, fifteen_puzzle, globe,
    load_cayleypy_puzzle,
)

__all__ = [
    "__version__", "Puzzle", "State", "puzzles", "solvers", "complexity",
    "solve", "solve_staged", "rubik_222", "rubik_333", "reversals", "lrx",
    "topspin", "fifteen_puzzle", "globe", "load_cayleypy_puzzle",
    "poly_budget", "ensure_poly", "solve_pancake_poly",
    "solve_cycle_sort_poly", "scaling_check",
]