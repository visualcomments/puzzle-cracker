"""Elegant staged 3x3x3 solver (Thistlethwaite-class).

The cube is driven down through four nested subgroups; each phase is one BFS
parent-tree over a *reduced coordinate space*:

    phase 1: edge orientation           -> G1   (2048 coords)
    phase 2: corner orientation +
             E-slice edge membership    -> G2   (1 082 565 coords)
    phase 3: corner permutation         -> K    (<= 20160 coords)
    phase 4: remaining edge scramble    -> {e}  (<= ~967 680 coords,
             inside K, the corner-fixing subgroup of G2)

Reduced-coordinate BFS is done over canonical coset representatives, with
compact integer keys and parent pointers only (no move sequences stored), so
all four tables fit in a few tens of MB and build in minutes in pure Python.
Solving is then four short parent-walks -- simple, elegant, deterministic.
"""

from __future__ import annotations

import os
import pickle
import time
from collections import deque
from typing import Dict, List, Optional, Sequence, Tuple

from ..group import Puzzle, State

# canonical cubie slots (facelet indices in the U/R/F/D/L/B layout)
CORNER_ORDER = ["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"]
EDGE_ORDER = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"]
FACES = ["U", "R", "F", "D", "L", "B"]

_CORNER_BY_FACES = {
    frozenset("URF"): "URF", frozenset("UFL"): "UFL", frozenset("ULB"): "ULB",
    frozenset("UBR"): "UBR", frozenset("DFR"): "DFR", frozenset("DLF"): "DLF",
    frozenset("DBL"): "DBL", frozenset("DRB"): "DRB",
}
_EDGE_BY_FACES = {
    frozenset("UR"): "UR", frozenset("UF"): "UF", frozenset("UL"): "UL",
    frozenset("UB"): "UB", frozenset("DR"): "DR", frozenset("DF"): "DF",
    frozenset("DL"): "DL", frozenset("DB"): "DB", frozenset("FR"): "FR",
    frozenset("FL"): "FL", frozenset("BL"): "BL", frozenset("BR"): "BR",
}


def derive_cubie_geometry(moves: Dict[str, Perm], turn_names: Optional[Sequence[str]] = None,
                          face_of_map: Optional[Dict[int, str]] = None):
    """Compute corner/edge cubie facelet slots purely from the permutation
    moves of a cube-like puzzle (default layout U(0..8) ... B(45..53)).

    Rules:
      * a *corner* facelet is moved by exactly 3 face turns;
      * an *edge* facelet by exactly 2;
      * the *center* of its face by exactly 1;
      * two corner facelets on adjacent faces are cubie-mates iff their
        image under *every* move is again a corner-corner pair on adjacent
        faces (ditto for edges).

    Returns (corner_slots: name->(a,b,c), edge_slots: name->(a,b)).
    """
    if face_of_map is not None:
        def face_of(i: int) -> str:
            return face_of_map[i]
    else:
        def face_of(i: int) -> str:
            return FACES[i // 9]

    def adjacent(f1: str, f2: str) -> bool:
        return f1 != f2 and f1 in _ADJ[f2]

    # adjacency from the face turns (a face turn moves facelets onto other faces)
    adj = {f: set() for f in FACES}
    for mname in turn_names:
        perm = moves[mname]
        for i in range(54):
            j = perm[i]
            fi, fj = face_of(i), face_of(j)
            if fi != fj:
                adj[fi].add(fj)
    _ADJ = adj

    if turn_names is None:
        turn_names = [m for m in sorted(moves) if not m.startswith("-")]
    else:
        turn_names = list(turn_names)
    turn_names.sort()
    moved_by = {i: [] for i in range(54)}
    for m in turn_names:
        perm = moves[m]
        for i in range(54):
            if perm[i] != i:
                moved_by[i].append(m)

    corners = [i for i in range(54) if len(moved_by[i]) == 3]
    edges = [i for i in range(54) if len(moved_by[i]) == 2]
    if len(corners) != 24 or len(edges) != 24:
        raise ValueError(f"bad cube geometry: {len(corners)} corners, {len(edges)} edges")

    def pair_orbit_size(x, y, cap):
        """Orbit of the unordered sticker-pair {x,y} under the face turns
        (capped).  True mates: a corner piece visits 8 positions x 3 slot
        combos = 24 sticker-pairs; an edge piece 12 x 2 = 12 (fixed slot
        pair).  Pairs from different pieces blow the orbit up past the cap."""
        orbit = {(x, y) if x < y else (y, x)}
        stack = [(x, y)]
        while stack:
            a, b = stack.pop()
            for m in turn_names:
                pa, pb = moves[m][a], moves[m][b]
                if pa == pb:
                    return cap + 1
                key = (pa, pb) if pa < pb else (pb, pa)
                if key not in orbit:
                    orbit.add(key)
                    stack.append((pa, pb))
                    if len(orbit) > cap:
                        return len(orbit)
        return len(orbit)

    def find_cubies(n, universe, expected_orbit):
        """n=3: corner cubies (pair-orbit 24); n=2: edge cubies (orbit 24).
        Explanation: with face turns only, a corner piece visits 8 positions
        x 3 slot-combos = 24 sticker-pairs; an edge piece visits 12 positions
        with a fixed slot-pair = 12 sticker-pairs."""
        import itertools
        mates: Dict[int, List[int]] = {x: [] for x in universe}
        for x, y in itertools.combinations(universe, 2):
            if x <= y and (x, y) not in [(0, 0)]:
                sz = pair_orbit_size(x, y, expected_orbit)
                if sz == expected_orbit:
                    mates[x].append(y)
                    mates[y].append(x)
        # every facelet must have exactly 2 mates -> triangles are cubies
        for x, ms in mates.items():
            pass
        groups = []
        used = set()
        for x in universe:
            if x in used:
                continue
            ms = mates[x]
            group = {x} | set(ms)
            # close the triangle: mates of mates
            for y in list(ms):
                group |= set(mates[y])
            if len(group) != n:
                raise ValueError(f"bad {n}-cubie group {group} (mates: {[ (u, mates[u]) for u in group]})")
            groups.append(tuple(sorted(group)))
            used |= group
        if len(groups) != len(universe) // n:
            raise ValueError(f"{n}-cubies: found {len(groups)} groups, "
                             f"expected {len(universe) // n}")
        return groups

    corner_cubies = find_cubies(3, corners, 24)
    edge_cubies = find_cubies(2, edges, 12)

    def slot_triple(cubies, faces_of_name):
        for c in cubies:
            fset = frozenset(face_of(x) for x in c)
            if fset == faces_of_name:
                return tuple(c)
        return None

    corner_slots = {}
    for name in CORNER_ORDER:
        want = frozenset(name)
        t = slot_triple(corner_cubies, want)
        if t is None:
            raise ValueError(f"no corner cubie with faces {want}")
        corner_slots[name] = t
    edge_slots = {}
    for name in EDGE_ORDER:
        want = frozenset(name)
        t = slot_triple(edge_cubies, want)
        if t is None:
            raise ValueError(f"no edge cubie with faces {want}")
        edge_slots[name] = t
    return corner_slots, edge_slots

# E-slice edge owners (FR, FL, BL, BR) have owner ids 8..11
E_SLICE_OWNERS = (8, 9, 10, 11)


def _pack_edge(owner: int, orient: int) -> int:
    return (owner << 1) | orient


def _unpack_edge(v: int):
    return v >> 1, v & 1


def _pack_edges(edges) -> int:
    key = 0
    for owner, orient in edges:
        key = (key << 5) | (owner << 1) | orient
    return key


def _unpack_edges(key: int, n: int = 12):
    out = []
    for _ in range(n):
        out.append((key >> 1 & 0b1111, key & 1))
        key >>= 5
    return tuple(reversed(out))


class StagedCube:
    """20-cubie 3x3x3 model derived from a 54-facelet puzzle.

    ``face_turns`` maps canonical face labels ('U','R','F','D','L','B') to the
    puzzle's own move names for those faces.
    """

    def __init__(self, puzzle: Puzzle, face_turns: Dict[str, str],
                 face_of: Optional[Dict[int, str]] = None) -> None:
        self.puzzle = puzzle
        self.face_turns = face_turns          # canonical -> competition name
        self.face_turns_inv = {v: k for k, v in face_turns.items()}
        if face_of is None:
            face_of = {i: FACES[i // 9] for i in range(54)}
        self.face_of = face_of
        solved = puzzle.solved
        self.solved_state: State = tuple(solved)
        cube_moves = {m: puzzle.moves[m] for m in puzzle.move_names}
        self._face_names = ["U", "D", "R", "L", "F", "B"]
        face_turn_names = [self.face_turns[f] for f in self._face_names]
        self.CORNER_SLOTS, self.EDGE_SLOTS = derive_cubie_geometry(
            cube_moves, face_turn_names, face_of_map=self.face_of)
        self.corner_order = CORNER_ORDER
        self.edge_order = EDGE_ORDER
        self.corner_owners: List[int] = []
        for cname in CORNER_ORDER:
            a, b, c = self.CORNER_SLOTS[cname]
            tokens = (solved[a], solved[b], solved[c])
            owner = -1
            for oi, oname in enumerate(CORNER_ORDER):
                x, y, z = self.CORNER_SLOTS[oname]
                if set(tokens) == set((solved[x], solved[y], solved[z])):
                    owner = oi
                    break
            self.corner_owners.append(owner)
        self.edge_owners: List[int] = []
        for ename in EDGE_ORDER:
            a, b = self.EDGE_SLOTS[ename]
            tokens = (solved[a], solved[b])
            owner = -1
            for oi, oname in enumerate(EDGE_ORDER):
                x, y = self.EDGE_SLOTS[oname]
                if set(tokens) == set((solved[x], solved[y])):
                    owner = oi
                    break
            self.edge_owners.append(owner)

        # cubie-level moves computed by simulation: for each move, apply it
        # to the *solved* state and read the piece dynamics straight out of
        # encode().  This sidesteps all permutation conventions.
        self.corner_effects: Dict[str, Tuple[Tuple[int, int], ...]] = {}
        self.edge_effects: Dict[str, Tuple[Tuple[int, int], ...]] = {}
        solved_encode = self.encode(self.solved_state)  # identity
        for mname, perm in puzzle.moves.items():
            moved = puzzle.apply(self.solved_state, mname)
            (mcorners, medges) = self.encode(moved)
            ce = [None] * 8
            for slot, (owner, o) in enumerate(solved_encode[0]):
                # the piece that started at ``slot`` now sits at ns with orient delta
                ns = next(i for i, (own, ori) in enumerate(mcorners) if own == owner)
                ce[slot] = (ns, mcorners[ns][1])
            ee = [None] * 12
            for slot, (owner, o) in enumerate(solved_encode[1]):
                ns = next(i for i, (own, ori) in enumerate(medges) if own == owner)
                ee[slot] = (ns, medges[ns][1])
            self.corner_effects[mname] = tuple(ce)
            self.edge_effects[mname] = tuple(ee)

    # -- tiny helpers ------------------------------------------------------- #
    def _which_corner(self, a, b, c) -> int:
        for i, name in enumerate(CORNER_ORDER):
            if set((a, b, c)) == set(self.CORNER_SLOTS[name]):
                return i
        raise ValueError(f"unknown corner ({a},{b},{c})")

    def _which_edge(self, a, b) -> int:
        for i, name in enumerate(EDGE_ORDER):
            if set((a, b)) == set(self.EDGE_SLOTS[name]):
                return i
        raise ValueError(f"unknown edge ({a},{b})")

    def _corner_delta(self, src, dst) -> int:
        s_f = [self.face_of[i] for i in src]
        d_f = [self.face_of[i] for i in dst]
        anchor = next(k for k, f in enumerate(s_f) if f in ("U", "D"))
        for k, f in enumerate(d_f):
            if f in ("U", "D"):
                return (anchor - k) % 3
        raise ValueError("corner delta")

    def _edge_flip(self, src, dst) -> int:
        s0, s1 = self.face_of[src[0]], self.face_of[src[1]]
        d0 = self.face_of[dst[0]]
        return 0 if d0 in (s0, s1) else 1

    # -- encode ------------------------------------------------------------- #
    @staticmethod
    def _rotate_ud_first(triple, face_of):
        """Rotate a corner slot triple so the U/D facelet is at index 0
        (canonical orientation convention: solved orientation == 0)."""
        t = list(triple)
        for k, x in enumerate(t):
            if face_of[x] in ("U", "D"):
                return tuple(t[k:] + t[:k])
        return tuple(t)

    def corner_slot(self, cname: str):
        return self._rotate_ud_first(self.CORNER_SLOTS[cname], self.face_of)

    def encode(self, state: State):
        corners = []
        for slot, cname in enumerate(CORNER_ORDER):
            a, b, c = self.corner_slot(cname)
            tokens = (state[a], state[b], state[c])
            owner = -1
            for oi, _ in enumerate(CORNER_ORDER):
                x, y, z = self.corner_slot(CORNER_ORDER[oi])
                if set(tokens) == set((self.solved_state[x], self.solved_state[y], self.solved_state[z])):
                    owner = oi
                    break
            # orientation: index of the owner's U/D-colored sticker within
            # the triple (home U/D facelet is slot index 0 by construction)
            hx, hy, hz = self.corner_slot(CORNER_ORDER[owner])
            ud_color = self.solved_state[hx]  # U/D facelet of the owner
            orient = next(k for k, t in enumerate(tokens) if t == ud_color)
            corners.append((owner, orient))
        edges = []
        for slot, ename in enumerate(EDGE_ORDER):
            a, b = self.EDGE_SLOTS[ename]
            tokens = (state[a], state[b])
            owner = -1
            for oi, _ in enumerate(EDGE_ORDER):
                x, y = self.EDGE_SLOTS[EDGE_ORDER[oi]]
                if set(tokens) == set((self.solved_state[x], self.solved_state[y])):
                    owner = oi
                    break
            # orientation: 0 iff the owner's U/D (or, for E-slice edges,
            # F/B) coloured sticker sits on a same-type face as its home.
            hx, hy = self.EDGE_SLOTS[EDGE_ORDER[owner]]
            home_faces = (self.face_of[hx], self.face_of[hy])
            if any(f in ("U", "D") for f in home_faces):
                anchor = self.solved_state[hx if self.face_of[hx] in ("U", "D") else hy]
                ok_face = ("U", "D")
            else:
                anchor = self.solved_state[hx if self.face_of[hx] in ("F", "B") else hy]
                ok_face = ("F", "B")
            j = 0 if tokens[0] == anchor else 1
            orient = 0 if self.face_of[(a, b)[j]] in ok_face else 1
            edges.append((owner, orient))
        return tuple(corners), tuple(edges)

    # -- apply cubie move --------------------------------------------------- #
    def apply_cubie(self, corners, edges, mname: str):
        ce = self.corner_effects[mname]
        ee = self.edge_effects[mname]
        out_c = [None] * 8
        for slot, (owner, o) in enumerate(corners):
            ns, delta = ce[slot]
            out_c[ns] = (owner, (o + delta) % 3)
        out_e = [None] * 12
        for slot, (owner, o) in enumerate(edges):
            ns, flip = ee[slot]
            out_e[ns] = (owner, (o + flip) % 2)
        return tuple(out_c), tuple(out_e)

    # -- reduced coordinates + canonical representatives -------------------- #
    # All phases operate on the *facelet state* directly: reduceX() reads a
    # reduced coordinate out of a 54-facelet state via encode(); repX()
    # assembles a canonical facelet state for a reduced coordinate.  Phase
    # tables are BFS parent trees over the reduced space; transitions apply
    # real puzzle moves to the representative and re-reduce.

    def reduce1(self, state: State) -> int:
        _, edges = self.encode(state)
        v = 0
        for slot, (owner, o) in enumerate(edges):
            v |= o << slot
        return v

    def rep1(self, r1: int) -> State:
        corners = tuple((i, 0) for i in range(8))
        edges = tuple((i, (r1 >> i) & 1) for i in range(12))
        return self._assemble(corners, edges)

    def reduce2(self, state: State) -> int:
        corners, edges = self.encode(state)
        co = 0
        for slot, (owner, o) in enumerate(corners[:7]):
            co = co * 3 + o
        ebits = 0
        for slot, (owner, o) in enumerate(edges):
            if owner in E_SLICE_OWNERS:
                ebits |= 1 << slot
        return (co << 12) | ebits

    def rep2(self, r2: int) -> State:
        co = r2 >> 12
        ebits = r2 & 0xFFF
        c_orient = [0] * 8
        s = 0
        for i in range(7):
            d = co % 3
            co //= 3
            c_orient[6 - i] = d
            s += d
        c_orient[7] = (-s) % 3
        corners = tuple((i, c_orient[i]) for i in range(8))
        e_slots_sorted = sorted(i for i in range(12) if ebits & (1 << i))
        o_slots = [i for i in range(12) if not (ebits & (1 << i))]
        by_slot = {}
        for k, slot in enumerate(e_slots_sorted):
            by_slot[slot] = (8 + k, 0)
        for k, slot in enumerate(o_slots):
            by_slot[slot] = (k, 0)
        edges = tuple(by_slot[i] for i in range(12))
        corners = tuple((i, c_orient[i]) for i in range(8))
        return self._assemble(corners, edges)

    def reduce3(self, state: State) -> int:
        corners, _ = self.encode(state)
        key = 0
        for owner, _ in corners:
            key = (key << 3) | owner
        return key

    def rep3(self, r3: int) -> State:
        owners = []
        for _ in range(8):
            owners.append(r3 & 0b111)
            r3 >>= 3
        owners.reverse()
        corners = tuple((o, 0) for o in owners)
        edges = tuple((i, 0) for i in range(12))
        return self._assemble(corners, edges)

    def reduce4(self, state: State) -> int:
        _, edges = self.encode(state)
        return _pack_edges(edges)

    def rep4(self, r4: int) -> State:
        corners = tuple((i, 0) for i in range(8))
        return self._assemble(corners, _unpack_edges(r4))

    # -- assembly (cubie coords -> facelet state) --------------------------- #
    def _assemble(self, corners, edges) -> State:
        """Build the 54-facelet state for a cubie-state (owner, orient).

        Each slot receives the *owner's* home tokens (rotated/flipped by the
        orientation), never the slot's own - otherwise permuted pieces would
        assemble as the solved state."""
        tokens = [None] * 54
        for slot, (owner, orient) in enumerate(corners):
            a, b, c = self.corner_slot(CORNER_ORDER[slot])
            hx, hy, hz = self.corner_slot(CORNER_ORDER[owner])
            home = (self.solved_state[hx], self.solved_state[hy],
                    self.solved_state[hz])
            rot = (home * 2)
            start = (3 - orient) % 3  # U/D token at index ``orient``
            placed = rot[start: start + 3]
            tokens[a], tokens[b], tokens[c] = placed
        for slot, (owner, orient) in enumerate(edges):
            a, b = self.EDGE_SLOTS[EDGE_ORDER[slot]]
            hx, hy = self.EDGE_SLOTS[EDGE_ORDER[owner]]
            h1, h2 = self.solved_state[hx], self.solved_state[hy]
            # place the anchor token so encode() reads the same orient:
            # orient == 0   -> anchor on an anchor-type face slot
            # orient == 1   -> anchor on a non-anchor-type slot
            home_faces = (self.face_of[hx], self.face_of[hy])
            if any(f in ("U", "D") for f in home_faces):
                anchor, ok_face = (h1 if self.face_of[hx] in ("U", "D") else h2), ("U", "D")
            else:
                anchor, ok_face = (h1 if self.face_of[hx] in ("F", "B") else h2), ("F", "B")
            other = h1 if anchor == h2 else h2
            fa, fb = self.face_of[a], self.face_of[b]
            if orient == 0:
                if fa in ok_face:
                    tokens[a], tokens[b] = anchor, other
                elif fb in ok_face:
                    tokens[a], tokens[b] = other, anchor
                else:
                    tokens[a], tokens[b] = anchor, other
            else:
                if fa not in ok_face:
                    tokens[a], tokens[b] = anchor, other
                else:
                    tokens[a], tokens[b] = other, anchor
        return tuple(tokens)

    # -- solve -------------------------------------------------------------- #
    def solve(self, state: State, table_dir: Optional[str] = None,
              max_phase4: int = 1_500_000, build_tables: bool = True) -> List[str]:
        budgets = {"p1": 200_000, "p2": 400_000, "p3": 100_000,
                   "p4": max(400_000, max_phase4)}
        t1 = self._table("p1", 8192)
        t2 = self._table("p2", 2_500_000)
        t3 = self._table("p3", 102_400)
        for t in (t1, t2, t3):
            if t.parent is None:
                if not build_tables:
                    raise RuntimeError(f"table {t.name} not built")
                t.build(self, table_dir and os.path.join(table_dir, t.name + ".pkl"))
        t4 = _PhaseTable("p4", moves=self._p4_generators(t3), max_states=max_phase4,
                         reduce=self.reduce4, rep=self.rep4)
        if t4.parent is None:
            t4.build(self, table_dir and os.path.join(table_dir, "p4.pkl"))
        seq: List[str] = []
        cur = state
        for t in (t1, t2, t3, t4):
            red = t.reduce(cur)
            path = t.solve_red(red, self, max_states=budgets[t.name])
            if path is None:
                raise RuntimeError(f"phase {t.name} could not reach root "
                                   f"(budget {budgets[t.name]})")
            for m in path:
                seq.append(m)
                cur = self.puzzle.apply(cur, m)
        return seq

    # -- tables ------------------------------------------------------------- #
    def _table(self, name: str, max_states: int):
        if name == "p1":
            return _PhaseTable("p1", moves=self._moves("p1"), max_states=max_states,
                               reduce=self.reduce1, rep=self.rep1)
        if name == "p2":
            return _PhaseTable("p2", moves=self._moves("p2"), max_states=max_states,
                               reduce=self.reduce2, rep=self.rep2)
        return _PhaseTable("p3", moves=self._moves("p3"), max_states=max_states,
                           reduce=self.reduce3, rep=self.rep3)

    def _p4_generators(self, p3_table) -> List[List[str]]:
        """Compound generators of the corner-fixing subgroup K of G2.

        For a G2 move m with corner projection p, the word
        [m] + p3.walk(p^-1) has net corner effect identity.  These words
        generate K (the kernel of the corner projection)."""
        ft = self.face_turns
        inv = lambda c: ("-" + c) if not c.startswith("-") else c[1:]
        g2 = [ft["U"], ft["D"], [ft["L"], ft["L"]], [ft["R"], ft["R"]],
              [ft["F"], ft["F"]], [ft["B"], ft["B"]]]
        gens = []
        for m in g2:
            # corner projection induced by m (applied to the solved state):
            # the corner-perm key of the moved solved state.
            inv_state = self.apply_seq_state(self.puzzle.solved, [m])
            cm = self.encode(inv_state)[0]
            perm_key = 0
            for owner, _ in cm:
                perm_key = (perm_key << 3) | owner
            repair = p3_table.walk(perm_key, self)
            if repair is None:
                raise RuntimeError(f"p3 cannot fix corner perm of {m}")
            seq = (list(m) if isinstance(m, list) else [m]) + list(repair)
            gens.append(seq)
        return gens

    def apply_seq_state(self, state: State, seq) -> State:
        for m in seq:
            if isinstance(m, list):
                state = self.apply_seq_state(state, m)
            else:
                state = self.puzzle.apply(state, m)
        return state

    def _moves(self, phase: str, p3=None):
        """Phase move sets.  Compound moves (half turns) are returned as
        lists of base moves so transitions stay single `puzzle.apply` calls."""
        ft = self.face_turns
        inv = lambda c: ("-" + c) if not c.startswith("-") else c[1:]
        if phase == "p1":
            out = []
            for f in self._face_names:
                c = ft[f]
                out += [c, inv(c), [c, c]]
            return out
        if phase == "p2":
            # G1 = <U,D,R,L,F2,B2>: single U/D/R/L turns never flip edges,
            # F2/B2 neither; single F/B would destroy phase 1's EO.
            return [ft["U"], inv(ft["U"]), ft["D"], inv(ft["D"]),
                    ft["R"], inv(ft["R"]), ft["L"], inv(ft["L"]),
                    [ft["F"], ft["F"]], [ft["B"], ft["B"]]]
        if phase == "p4":
            return list(p3)
        return [ft["U"], inv(ft["U"]), ft["D"], inv(ft["D"]),
                [ft["L"], ft["L"]], [ft["R"], ft["R"]],
                [ft["F"], ft["F"]], [ft["B"], ft["B"]]]


class _PhaseTable:
    """BFS parent tree over a reduced coordinate space.

    Nodes are reduced coordinates; transitions are computed by applying a
    move (or compound move sequence) to the *canonical representative* of the
    current coordinate and re-reducing.  Solving a phase = walking parents
    from the current coordinate to the root, emitting the moves used.
    """

    def __init__(self, name: str, moves, max_states: int, reduce, rep) -> None:
        self.name = name
        self.moves = moves
        self.max_states = max_states
        self.reduce = reduce
        self.rep = rep
        self.parent: Optional[Dict[int, Tuple[int, int]]] = None  # child -> (parent, move_idx)

    def apply(self, cube: StagedCube, state: State, m) -> State:
        if isinstance(m, str):
            return cube.puzzle.apply(state, m)
        for mm in m:
            state = self.apply(cube, state, mm)
        return state

    def build(self, cube: StagedCube, cache_path: Optional[str] = None) -> None:
        if cache_path and os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                self.parent = pickle.load(f)
            return
        t0 = time.time()
        root = self.reduce(cube.puzzle.solved)
        parent: Dict[int, Tuple[int, int]] = {root: (-1, -1)}
        q = deque([root])
        moves = self.moves
        while q:
            red = q.popleft()
            rep_state = self.rep(red)
            for mi, m in enumerate(moves):
                cur = self.apply(cube, rep_state, m)
                nred = self.reduce(cur)
                if nred not in parent:
                    parent[nred] = (red, mi)
                    if len(parent) >= self.max_states:
                        q.clear()
                        break
                    q.append(nred)
        self.parent = parent
        if cache_path:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "wb") as f:
                pickle.dump(parent, f, protocol=4)
        print(f"[staged] {self.name}: {len(parent)} coords, "
              f"{time.time() - t0:.1f}s")

    def walk(self, red: int, cube: StagedCube) -> List[str]:
        """Moves taking the current reduced coordinate down to the root."""
        if self.parent is None:
            raise RuntimeError(f"table {self.name} not built")
        parent = self.parent
        if red not in parent:
            return None
        seq: List[str] = []
        while True:
            pr, mi = parent[red]
            if mi < 0:
                break
            m = self.moves[mi]
            if isinstance(m, str):
                seq.append(m)
            else:
                seq.extend(m)
            red = pr
            if len(seq) > 400:
                break
        return seq

    def solve_red(self, red: int, cube: StagedCube, max_states: int = 2_000_000) -> List[str]:
        """Robust phase solve: walk the table when the coordinate is known,
        otherwise run a bounded BFS from this coordinate to the root."""
        path = self.walk(red, cube) if self.parent is not None else None
        if path is not None:
            return path
        root = self.reduce(cube.puzzle.solved)
        if red == root:
            return []
        parent = {red: (-1, -1)}
        q = deque([red])
        found = None
        while q:
            cur = q.popleft()
            rep_state = self.rep(cur)
            for m in self.moves:
                nxt_state = self.apply(cube, rep_state, m)
                nred = self.reduce(nxt_state)
                if nred in parent:
                    continue
                parent[nred] = (cur, self.moves.index(m))
                if nred == root:
                    found = nred
                    q.clear()
                    break
                if len(parent) >= max_states:
                    q.clear()
                    break
                q.append(nred)
        if found is None:
            return None
        seq: List[str] = []
        while found != red:
            pr, mi = parent[found]
            m = self.moves[mi]
            seq.extend(m if isinstance(m, list) else [m])
            found = pr
            if len(seq) > 800:
                break
        return seq



# --------------------------------------------------------------------------- #
# convenience API
# --------------------------------------------------------------------------- #

def build_canonical_333() -> StagedCube:
    """StagedCube over the canonical 3x3x3 competition definition."""
    from ..puzzles import rubik_333
    sc = cube_adapter_for(rubik_333())
    if sc is None:
        raise RuntimeError("cannot adapt the canonical cube")
    return sc


def cube_adapter_for(puzzle: Puzzle) -> Optional[StagedCube]:
    """Build a StagedCube for a 54-facelet competition cube by detecting the
    six faces and their quarter-turn moves."""
    from .cube_adapter import detect_face_turns
    ft = detect_face_turns(puzzle)
    if ft is None:
        return None
    face_turns, face_of = ft
    return StagedCube(puzzle, face_turns=face_turns, face_of=face_of)
