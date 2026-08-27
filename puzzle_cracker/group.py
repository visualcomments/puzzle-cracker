"""Permutation-group engine for puzzle cracking.

Everything in the harness is expressed as permutations acting on labelled
positions (tiles / stickers / facelets / cubies).  A *move* is a permutation
(array ``p`` where ``p[i]`` is the index that ends up in slot ``i`` after the
move), a *state* is a tuple of tokens (colors/ids) at each position, and
applying a move to a state is a plain index lookup.

The module is deliberately dependency-free: the whole harness runs on the
standard library (+tqdm optional).  Cayley graph terminology is used so that
the code maps 1:1 onto the CayleyPy competition family (Santa 2023,
``cayley-py-*``, ``cayleypy-*``).
"""

from __future__ import annotations

import random
from collections import deque
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Perm = Tuple[int, ...]
State = Tuple[str, ...]

# --------------------------------------------------------------------------- #
# permutation helpers
# --------------------------------------------------------------------------- #

def identity_perm(n: int) -> Perm:
    return tuple(range(n))


def compose(p: Perm, q: Perm) -> Perm:
    """Return p∘q: apply q first, then p.  p∘q[i] == p[q[i]]."""
    return tuple(p[q[i]] for i in range(len(p)))


def inverse_perm(p: Perm) -> Perm:
    inv = [0] * len(p)
    for i, v in enumerate(p):
        inv[v] = i
    return tuple(inv)


def perm_from_cycles(n: int, cycles: Sequence[Sequence[int]]) -> Perm:
    """Build a permutation (as array) from disjoint cycles (0-based)."""
    p = list(range(n))
    for cyc in cycles:
        for a, b in zip(cyc, cyc[1:] + cyc[:1]):
            p[a] = b
    return tuple(p)


def apply_perm(state: Sequence, p: Perm) -> State:
    """Apply move ``p`` to ``state``: new[i] = old[p[i]]."""
    return tuple(state[p[i]] for i in range(len(p)))


def oneline_to_cycles(p: Perm) -> List[List[int]]:
    seen = [False] * len(p)
    cycles = []
    for i in range(len(p)):
        if seen[i] or p[i] == i:
            continue
        cyc = []
        j = i
        while not seen[j]:
            seen[j] = True
            cyc.append(j)
            j = p[j]
        cycles.append(cyc)
    return cycles


# --------------------------------------------------------------------------- #
# Puzzle definition
# --------------------------------------------------------------------------- #

class Puzzle:
    """A Cayley graph: state space + move generators + solved state.

    ``moves`` maps a move name to the permutation (as an array).  The inverse
    move is added automatically as ``-name`` unless already present.
    ``solved`` is the solved/central state as a tuple.
    """

    def __init__(
        self,
        name: str,
        moves: Dict[str, Perm],
        solved: State,
        *,
        add_inverses: bool = True,
        metric: Optional[str] = None,
    ) -> None:
        self.name = name
        self.metric = metric or "QTM"
        self._moves: Dict[str, Perm] = dict(moves)
        if add_inverses:
            for m, p in list(self._moves.items()):
                if not m.startswith("-") and "-" + m not in self._moves:
                    self._moves["-" + m] = inverse_perm(p)
        # stable move order (sorted so results are deterministic)
        self.move_names: Tuple[str, ...] = tuple(sorted(self._moves))
        self.moves: Dict[str, Perm] = {k: self._moves[k] for k in self.move_names}
        self.solved: State = tuple(solved)
        self.n: int = len(self.solved)

    # -- state helpers ------------------------------------------------------ #
    def apply(self, state: State, move: str) -> State:
        return apply_perm(state, self.moves[move])

    def apply_seq(self, state: State, seq: Sequence[str]) -> State:
        for m in seq:
            state = apply_perm(state, self.moves[m])
        return state

    def scrambled(self, length: int, rng: Optional[random.Random] = None) -> Tuple[State, List[str]]:
        """Random walk of ``length`` moves; returns (state, moves used)."""
        rng = rng or random.Random()
        state = self.solved
        seq: List[str] = []
        for _ in range(length):
            m = rng.choice(self.move_names)
            state = self.apply(state, m)
            seq.append(m)
        return state, seq

    def is_solved(self, state: State) -> bool:
        return state == self.solved

    # -- structural helpers -------------------------------------------------- #
    def neighbours(self, state: State) -> Iterable[Tuple[str, State]]:
        for m in self.move_names:
            yield m, apply_perm(state, self.moves[m])

    def move_effect_on_positions(self, move: str) -> Perm:
        return self.moves[move]

    def __repr__(self) -> str:
        return f"Puzzle({self.name!r}, n={self.n}, #moves={len(self.move_names)}, |solved|={len(self.solved)})"


# --------------------------------------------------------------------------- #
# generic search utilities (used by bfs / ida / beam / staged)
# --------------------------------------------------------------------------- #

def _state_key(state: State) -> str:
    return "|".join(state)


def bidirectional_bfs(puzzle: Puzzle, start: State, goal: Optional[State] = None,
                      max_states: int = 10_000_000) -> Optional[List[str]]:
    """Shortest path from ``start`` to ``goal`` (default solved) via bi-BFS.

    Returns the list of moves (applied to ``start`` yields ``goal``) or None
    if the space exceeds ``max_states``.
    """
    goal = goal if goal is not None else puzzle.solved
    if start == goal:
        return []
    fwd: Dict[State, Tuple[Optional[str], Optional[State]]] = {start: (None, None)}
    bwd: Dict[State, Tuple[Optional[str], Optional[State]]] = {goal: (None, None)}
    fq, bq = deque([start]), deque([goal])
    meet: Optional[State] = None

    def expand(q, visited, other, fw: bool):
        nonlocal meet
        cur = q.popleft()
        for m in puzzle.move_names:
            nxt = puzzle.apply(cur, m)
            if nxt in visited:
                continue
            visited[nxt] = (m, cur)
            if nxt in other:
                meet = nxt
                return
            q.append(nxt)
            if len(visited) > max_states:
                raise RuntimeError("biBFS space exceeded")

    while fq and bq:
        if len(fq) <= len(bq):
            expand(fq, fwd, bwd, True)
        else:
            expand(bq, bwd, fwd, False)
        if meet is not None:
            break
    if meet is None:
        return None

    # reconstruct: start -> meet (forward) ; meet -> goal (backward reversed)
    seq: List[str] = []
    s = meet
    while s != start:
        m, prev = fwd[s]
        seq.append(m)
        s = prev
    seq.reverse()
    s = meet
    while s != goal:
        m, prev = bwd[s]
        seq.append(inverse_name(puzzle, m))
        s = prev
    return seq


def inverse_name(puzzle: Puzzle, move: str) -> str:
    """Return the name of the inverse of ``move`` (``-f0`` <-> ``f0``)."""
    return move[1:] if move.startswith("-") else "-" + move


def iterdepth_graph_bfs(puzzle: Puzzle, start: State, depth: int,
                        goal: Optional[State] = None) -> Optional[List[str]]:
    """Exhaustive BFS up to ``depth`` layers; returns first solution."""
    goal = goal if goal is not None else puzzle.solved
    if start == goal:
        return []
    frontier = {start: []}
    for _ in range(depth):
        nxt: Dict[State, List[str]] = {}
        for st, seq in frontier.items():
            for m in puzzle.move_names:
                ns = puzzle.apply(st, m)
                if ns in nxt:
                    continue
                nsq = seq + [m]
                if ns == goal:
                    return nsq
                nxt[ns] = nsq
        frontier = nxt
        # prune to keep memory sane
        if len(frontier) > 2_000_000:
            return None
    return None


def group_order(puzzle: Puzzle) -> int:
    """Order of the group generated by the moves (BFS over distinct states)."""
    seen = {puzzle.solved}
    q = deque([puzzle.solved])
    while q:
        st = q.popleft()
        for _, ns in puzzle.neighbours(st):
            if ns not in seen:
                seen.add(ns)
                q.append(ns)
    return len(seen)