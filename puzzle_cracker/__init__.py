"""API surface of the puzzle-cracker package."""

__version__ = "0.1.0"

from .group import Puzzle, State
from . import puzzles, solvers
from .solvers import solve, solve_staged
from .puzzles import (
    rubik_222, rubik_333, reversals, lrx, topspin, fifteen_puzzle, globe,
    load_cayleypy_puzzle,
)

__all__ = [
    "__version__", "Puzzle", "State", "puzzles", "solvers", "solve",
    "solve_staged", "rubik_222", "rubik_333", "reversals", "lrx", "topspin",
    "fifteen_puzzle", "globe", "load_cayleypy_puzzle",
]