"""Puzzle definitions and loaders for the CayleyPy competition family.

Supported competition formats (all are "find the shortest move sequence that
turns ``initial_state`` into the solved/central state"):

* ``puzzle_info.json`` (agent competitions: ``cayley-py-*-cube``,
  ``cayley-py-megaminx``, ``cayleypy-ihes-cube``,
  ``cayley-py-professor-tetraminx-solve-optimally`` ...):
    ``{"name": ..., "central_state": [int, ...],
       "generators": {"f0": [perm], "-f0": [perm], ...}}``
* ``puzzle_info.csv`` (Santa 2023):
    ``puzzle_type, "{'f0': [...], ...}"``  plus ``puzzles.csv`` rows
    ``id,puzzle_type,solution_state,initial_state,num_wildcards``.
* ``graphs_info.json`` / ``graphs_info.h5`` (``cayleypy-reversals``,
  ``cayleypy-transposons``):
    per-size ``{"name", "central_state", "generators"}`` dicts.

Built-in puzzles (no external data needed) cover the classic families:
Rubik 2x2/3x3 (standard facelet model), pancake prefix reversals,
reversals (arbitrary segment reversals), LRX, TopSpin, 15-puzzle, globe.
"""

from __future__ import annotations

import ast
import csv
import io
import json
import os
import re
from typing import Dict, List, Optional, Sequence, Tuple

from .group import Perm, Puzzle, State, perm_from_cycles, identity_perm

# --------------------------------------------------------------------------- #
# generic move-string helpers (shared by all competition loaders)
# --------------------------------------------------------------------------- #

ARRAY_RE = re.compile(r"^[\[(].*[\])]$")


def _coerce_perm(raw) -> Perm:
    """Accept a permutation as list/tuple of ints (0-based, array form)."""
    if isinstance(raw, str):
        raw = ast.literal_eval(raw.strip())
    return tuple(int(x) for x in raw)


def _detect_inverses(moves: Dict[str, Perm]) -> bool:
    return any(k.startswith("-") for k in moves)


def _split_move_name(name: str) -> Tuple[str, int]:
    """'f0' -> ('f', 0) ; '-r3' -> ('r', 3)"""
    if name.startswith("-"):
        base = name[1:]
        sign = -1
    else:
        base = name
        sign = 1
    m = re.match(r"([A-Za-z]+)(\d+)?$", base)
    if not m:
        return name, 0
    axis = m.group(1)
    idx = int(m.group(2) or 0)
    return axis, sign * idx


# --------------------------------------------------------------------------- #
# loaders
# --------------------------------------------------------------------------- #

def from_puzzle_info_json(path: str, puzzle_name: Optional[str] = None) -> Puzzle:
    """Load the agent-competition ``puzzle_info.json`` format."""
    with open(path) as f:
        d = json.load(f)
    central = d.get("central_state")
    if central is None and "solved_state" in d:
        central = d["solved_state"]
    gens = d["generators"]
    name = puzzle_name or d.get("name") or os.path.basename(os.path.dirname(path))
    return Puzzle(name=name, moves=gens, solved=tuple(map(str, central)),
                  add_inverses=not _detect_inverses(gens))


def from_graphs_info_json(path: str, size: str) -> Puzzle:
    """Load one graph from the ``graphs_info.json`` of reversals/transposons."""
    with open(path) as f:
        d = json.load(f)
    entry = d[str(size)]
    gens = entry["generators"]
    return Puzzle(name=entry["name"], moves=gens, solved=tuple(map(str, entry["central_state"])),
                  add_inverses=not _detect_inverses(gens))


def _parse_puzzle_info_csv(text: str) -> Dict[str, Dict[str, Perm]]:
    out: Dict[str, Dict[str, Perm]] = {}
    import sys as _sys
    _sys.modules.get("csv")
    csv.field_size_limit(max(1 << 30, csv.field_size_limit()))
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    for row in reader:
        if len(row) < 2:
            continue
        pt, moves_s = row[0], row[1]
        d = ast.literal_eval(moves_s)
        out[pt] = {k: _coerce_perm(v) for k, v in d.items()}
    return out


def _parse_puzzles_csv(text: str) -> List[dict]:
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        out.append({
            "id": int(row["id"]),
            "puzzle_type": row["puzzle_type"],
            "solution_state": tuple(row["solution_state"].split(";")),
            "initial_state": tuple(row["initial_state"].split(";")),
            "num_wildcards": int(row["num_wildcards"]),
        })
    return out


def load_santa_2023(data_dir: str, puzzle_types: Optional[Sequence[str]] = None,
                    max_puzzles: Optional[int] = None) -> Dict[str, dict]:
    """Load Santa 2023 data.  Returns {puzzle_type: {"puzzle": Puzzle,
    "cases": [row...]}} for the requested types (default all)."""
    info = _parse_puzzle_info_csv(open(os.path.join(data_dir, "puzzle_info.csv")).read())
    puzzles = _parse_puzzles_csv(open(os.path.join(data_dir, "puzzles.csv")).read())
    out: Dict[str, dict] = {}
    for pt in sorted(info):
        if puzzle_types and pt not in puzzle_types:
            continue
        cases = [r for r in puzzles if r["puzzle_type"] == pt]
        if max_puzzles:
            cases = cases[:max_puzzles]
        # solved state = the shared solution_state of the cases
        solved = next((r["solution_state"] for r in cases if r["solution_state"]), None)
        if solved is None:
            solved = tuple("?" * len(next(iter(info[pt].values()))))
        pz = Puzzle(name=pt, moves=info[pt], solved=solved,
                    add_inverses=not _detect_inverses(info[pt]))
        out[pt] = {"puzzle": pz, "cases": cases}
    return out


def load_agent_competition(dir_path: str, limit: Optional[int] = None) -> dict:
    """Load a ``cayley-py-*`` style competition directory.

    Returns ``{"puzzle": Puzzle, "cases": [{"id": ..., "initial_state": State,
    "comment": str}]}``.
    """
    puzzle = from_puzzle_info_json(os.path.join(dir_path, "puzzle_info.json"))
    cases: List[dict] = []
    test_path = os.path.join(dir_path, "test.csv")
    if os.path.exists(test_path):
        with open(test_path) as f:
            for row in csv.DictReader(f):
                st = tuple(row["initial_state"].split(","))
                if len(st) != puzzle.n:
                    # maybe semicolon separated
                    st = tuple(row["initial_state"].split(";"))
                cases.append({"id": row.get("initial_state_id", row.get("id")),
                              "initial_state": st,
                              "comment": row.get("comment", "")})
    if limit:
        cases = cases[:limit]
    return {"puzzle": puzzle, "cases": cases}


def load_server_competition(dir_path: str, size: str, limit: Optional[int] = None) -> dict:
    """Load a graphs_info-style server competition (reversals / transposons)."""
    graphs = None
    for cand in ("graphs_info.json", "graphs_info.h5"):
        p = os.path.join(dir_path, cand)
        if os.path.exists(p):
            graphs = p
            break
    if graphs is None:
        raise FileNotFoundError(f"no graphs_info in {dir_path}")
    if graphs.endswith(".h5"):
        # h5 holds the same json under 'graphs_info' key
        import h5py  # optional dependency
        with h5py.File(graphs, "r") as h5:
            raw = h5["graphs_info"][()]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        text = raw if isinstance(raw, str) else json.dumps(json.loads(raw))
        import tempfile
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        tmp.write(text)
        tmp.close()
        graphs = tmp.name
    puzzle = from_graphs_info_json(graphs, size)
    cases: List[dict] = []
    test_path = os.path.join(dir_path, "test.csv")
    if os.path.exists(test_path):
        with open(test_path) as f:
            for row in csv.DictReader(f):
                st = tuple(row["initial_state"].split(","))
                cases.append({"id": row.get("initial_state_id", row.get("id")),
                              "initial_state": st, "comment": ""})
    return {"puzzle": puzzle, "cases": cases}


# --------------------------------------------------------------------------- #
# built-in puzzles
# --------------------------------------------------------------------------- #

# Standard 3x3x3 facelet model.  Face order used throughout the harness:
# U (0..8), R (9..17), F (18..26), D (27..35), L (36..44), B (45..53).
# (identity -> solved pattern "UURUUUU...")

# --------------------------------------------------------------------------- #
# geometric canonical 3x3x3 cube (no hand-written cycles)
# --------------------------------------------------------------------------- #

def _face_frames():
    """world coord (scaled x3, integer) of the *center* of facelet
    (face, u, v), u,v in 0..2.  Centers at {-2,0,2} in-plane, faces at ±3."""
    def frame(face, u, v):
        x = (u - 1) * 2
        y = (1 - v) * 2
        if face == "U":
            return (x, y, 3)
        if face == "D":
            return (x, y, -3)
        if face == "F":
            return (x, 3, y)
        if face == "B":
            return (x, -3, y)
        if face == "R":
            return (3, y, x)
        if face == "L":
            return (-3, y, -x)
        raise ValueError(face)
    return frame


# sign of the surface coordinate per face
_FACE_SIGN = {"U": 1, "D": -1, "F": 1, "B": -1, "R": 1, "L": -1}
_AXIS = {"U": 2, "D": 2, "F": 1, "B": 1, "R": 0, "L": 0}  # 0=x,1=y,2=z


# cw quarter-turn rotations about the face axes (derived from the 3D geometry)
_ROT = {
    "U": lambda p: (p[1], -p[0], p[2]),
    "D": lambda p: (-p[1], p[0], p[2]),
    "F": lambda p: (p[2], p[1], -p[0]),
    "B": lambda p: (-p[2], p[1], p[0]),
    "R": lambda p: (p[0], p[2], -p[1]),
    "L": lambda p: (p[0], -p[2], p[1]),
}


def _geo_cube_333_moves() -> Dict[str, Perm]:
    """Six face turns as permutations on 54 facelets (U/R/F/D/L/B blocks)."""
    frame = _face_frames()
    faces = ["U", "R", "F", "D", "L", "B"]
    pos2idx = {}
    idx2pos = {}
    for f in faces:
        base = faces.index(f) * 9
        for u in range(3):
            for v in range(3):
                pos2idx[(f, u, v)] = base + v * 3 + u
                idx2pos[base + v * 3 + u] = (f, u, v)
    # build reverse: world -> facelet index
    world2idx = {}
    for f in faces:
        for u in range(3):
            for v in range(3):
                world2idx[frame(f, u, v)] = pos2idx[(f, u, v)]
    moves: Dict[str, Perm] = {}
    for f in faces:
        ax = _AXIS[f]
        sgn = _FACE_SIGN[f]
        layer = []
        for other in faces:
            for u in range(3):
                for v in range(3):
                    p = frame(other, u, v)
                    own = p[ax] == 3 * sgn
                    ring = p[ax] == 2 * sgn
                    if own or ring:
                        layer.append(pos2idx[(other, u, v)])
        layer = sorted(set(layer))
        assert len(layer) == 21, (f, len(layer))
        perm = list(range(54))
        for i in layer:
            x, y, z = frame(*idx2pos[i])
            nx, ny, nz = _ROT[f]((x, y, z))
            nf, nu, nv = None, None, None
            for g in faces:
                for u in range(3):
                    for v in range(3):
                        if frame(g, u, v) == (nx, ny, nz):
                            nf, nu, nv = g, u, v
            assert nf is not None, (f, i, (x, y, z), (nx, ny, nz))
            perm[i] = pos2idx[(nf, nu, nv)]
        moves[f] = tuple(perm)
    return moves


def rubik_333() -> Puzzle:
    """Canonical 3x3x3 (face turns).  Prefers the battle-tested CayleyPy
    CUBE333_MOVES when the package is installed; falls back to the
    geometry-built face turns."""
    try:
        from cayleypy.puzzles.cube import CUBE333_MOVES
        mv = {k: tuple(v) for k, v in CUBE333_MOVES.items()}
        # cayleypy's solved cube (54 facelets, per-face colors) uses the same
        # U(0..8) R(9..17) F(18..26) D(27..35) L(36..44) B(45..53) layout.
        return Puzzle("rubik_3x3x3", mv,
                      solved=tuple("URFDLB"[i // 9] for i in range(54)),
                      metric="HTM")
    except Exception:
        return Puzzle("rubik_3x3x3", _geo_cube_333_moves(),
                      solved=tuple("URFDLB"[i // 9] for i in range(54)),
                      metric="HTM")


def _cube_222_moves() -> Dict[str, Perm]:
    # standard 2x2x2 on 24 facelets (6 faces x 4)
    n = 24
    def cyc(cycles):
        return perm_from_cycles(n, cycles)
    # faces U(0..3) R(4..7) F(8..11) D(12..15) L(16..19) B(20..23)
    U = cyc([[0, 3, 2, 1], [4, 8, 20, 16], [5, 9, 21, 17]])
    R = cyc([[4, 7, 6, 5], [0, 12, 20, 8], [3, 15, 23, 11]])
    F = cyc([[8, 11, 10, 9], [0, 16, 12, 4], [1, 17, 13, 5]])
    D = cyc([[12, 15, 14, 13], [6, 18, 22, 10], [7, 19, 23, 11]])
    L = cyc([[16, 19, 18, 17], [1, 9, 13, 21], [2, 10, 14, 22]])
    B = cyc([[20, 23, 22, 21], [2, 6, 14, 18], [3, 7, 15, 19]])
    return {"U": U, "D": D, "R": R, "L": L, "F": F, "B": B}


def rubik_222() -> Puzzle:
    return Puzzle("rubik_2x2x2", _cube_222_moves(),
                  solved=tuple("URFDLB"[i // 4] for i in range(24)),
                  metric="QTM")


def reversals(n: int, all_segments: bool = False) -> Puzzle:
    """R[i,j] reverses the segment [i..j] (0-based)."""
    moves: Dict[str, Perm] = {}
    if all_segments:
        for i in range(n):
            for j in range(i + 1, n):
                p = list(range(n))
                seg = list(range(i, j + 1))
                for a, b in zip(seg, reversed(seg)):
                    p[a] = b
                moves[f"R[{i},{j}]"] = tuple(p)
    else:
        # prefix reversals only (pancake)
        for j in range(1, n):
            p = list(range(n))
            for a, b in zip(range(j + 1), reversed(range(j + 1))):
                p[a] = b
            moves[f"R[{0},{j}]"] = tuple(p)
    return Puzzle(f"reversals_{n}", moves, solved=tuple(map(str, range(n))),
                  metric="reversals")


def lrx(n: int) -> Puzzle:
    """LRX puzzle: 3-cycles on consecutive triples (from the CayleyPy docs)."""
    moves: Dict[str, Perm] = {}
    for i in range(n - 2):
        p = list(range(n))
        # rotate the triple (i, i+1, i+2) -> (i+1, i+2, i)
        p[i], p[i + 1], p[i + 2] = p[i + 1], p[i + 2], p[i]
        moves[f"L{i}"] = tuple(p)
    return Puzzle(f"lrx_{n}", moves, solved=tuple(map(str, range(n))))


def topspin(n: int, k: int) -> Puzzle:
    """TopSpin: big ring rotate (all n) + turn over of k adjacent tokens."""
    moves: Dict[str, Perm] = {}
    ring = list(range(n - 1, -1, -1))
    moves["ring"] = tuple(ring)
    p = list(range(n))
    seg = [i % n for i in range(k)]
    for a, b in zip(seg, reversed(seg)):
        p[a] = b
    moves["flip"] = tuple(p)
    return Puzzle(f"topspin_{n}_{k}", moves, solved=tuple(map(str, range(n))),
                  metric="topspin")


def fifteen_puzzle() -> Puzzle:
    n = 16
    moves: Dict[str, Perm] = {}
    # sliding moves: tile at 'blank' position 15 moves into a neighbour.
    def swap(blank, target):
        p = list(range(n))
        p[blank], p[target] = p[target], p[blank]
        return tuple(p)
    moves["R"] = swap(15, 14)  # blank moves right (tile 14 -> 15)
    moves["L"] = swap(15, 13)
    moves["U"] = swap(15, 11)
    moves["D"] = swap(15, 12)
    return Puzzle("fifteen", moves,
                  solved=tuple(map(str, range(1, 16))) + ("0",),
                  metric="sliding")


def globe(a: int, b: int) -> Puzzle:
    """Globe puzzle: (a+1)-cycle + 2*b order-2 generators (CayleyPy family)."""
    n = a + 1 + 2 * b
    moves: Dict[str, Perm] = {}
    # cycle of the first a+1 positions
    p = list(range(n))
    for i in range(a + 1):
        p[i] = (i + 1) % (a + 1)
    moves["cycle"] = tuple(p)
    # b transpositions (i, i) mirrored around the axis
    for k in range(b):
        q = list(range(n))
        i, j = a + 1 + 2 * k, a + 2 + 2 * k
        q[i], q[j] = q[j], q[i]
        moves[f"swap{k}"] = tuple(q)
    return Puzzle(f"globe_{a}_{b}", moves, solved=tuple(map(str, range(n))),
                  metric="globe")


# --------------------------------------------------------------------------- #
# cayleypy interop (optional)
# --------------------------------------------------------------------------- #

def load_cayleypy_puzzle(kind: str, **kwargs):
    """Load a puzzle from the installed ``cayleypy`` package (optional dep).

    Returns ``None`` when cayleypy is unavailable or the puzzle is unknown.
    """
    try:
        from cayleypy.puzzles import Puzzles
    except Exception:
        return None
    try:
        if kind == "rubik_cube":
            gd = Puzzles.rubik_cube(kwargs.get("cube_size", 3), kwargs.get("metric", "QSTM"))
        elif kind == "megaminx":
            gd = Puzzles.megaminx()
        elif kind == "pyraminx":
            gd = Puzzles.pyraminx()
        elif kind == "starminx":
            gd = Puzzles.starminx()
        elif kind == "mistyminx":
            gd = Puzzles.mistyminx()
        elif kind == "hungarian_rings":
            gd = Puzzles.hungarian_rings(kwargs["left_size"], kwargs["left_index"],
                                         kwargs["right_size"], kwargs["right_index"])
        else:
            return None
    except Exception:
        return None
    name = getattr(gd, "name", kind)
    moves = {nm: tuple(p) for nm, p in zip(gd.generator_names, gd.generators)}
    if not any(nm.startswith("-") for nm in moves):
        moves = {**moves, **{f"-{nm}": None for nm in list(moves)}}  # will be filled by Puzzle
        moves = {nm: p for nm, p in moves.items() if p is not None}
    central = tuple(map(str, gd.central_state))
    return Puzzle(name=name, moves=moves, solved=central,
                  add_inverses=not any(k.startswith("-") for k in moves))


# --------------------------------------------------------------------------- #
# canonical 3x3x3 <-> competition adapter
# --------------------------------------------------------------------------- #

class CubeAdapter:
    """Maps an arbitrary 54-facelet slice-cube puzzle onto the harness's
    canonical 3x3x3 (labels U,R,F,D,L,B) by detecting face adjacency.

    The canonical facelet layout used here:
        U(0..8) R(9..17) F(18..26) D(27..35) L(36..44) B(45..53)
    """

    def __init__(self, puzzle: Puzzle) -> None:
        if puzzle.n != 54:
            raise ValueError("CubeAdapter requires a 54-facelet puzzle")
        # faces from solved state: groups of equal labels with count 9
        counts = {}
        for i, tok in enumerate(puzzle.solved):
            counts.setdefault(tok, []).append(i)
        groups = [g for g in counts.values() if len(g) == 9]
        if len(groups) != 6:
            raise ValueError(f"expected 6 faces of 9 facelets, got {len(groups)}")
        self.face_of = {}
        for face_idx, group in enumerate(groups):
            for pos in group:
                self.face_of[pos] = face_idx
        # adjacency: face A touches face B if a move swaps/cycles facelets of A into B
        adj = [set() for _ in range(6)]
        for _, p in puzzle.moves.items():
            for i in range(54):
                j = p[i]
                if i != j and self.face_of[i] != self.face_of[j]:
                    adj[self.face_of[i]].add(self.face_of[j])
        self.adj = [sorted(a) for a in adj]
        # build canonical orientation: pick face0 of group[?] as 'U'
        # choose U = face with most edges... just pick group order via cube topology
        self._build_isomorphism()
        self._build_cubie_ops()

    # -- face-adjacency -> canonical cubie model ---------------------------- #
    def _build_isomorphism(self) -> None:
        # pick face 0 as U; its neighbors (4 faces) as F,R,B,L; the 6th as D
        # neighbor order from the move graph: find the face opposite (non-adjacent)
        nbrs = self.adj[0]
        other = [f for f in range(6) if f != 0 and f not in nbrs]
        if len(other) != 1:
            raise ValueError("face graph is not a cube")
        down = other[0]
        ring = nbrs  # 4 faces around U
        # rotate the ring so that it's F,R,B,L by chaining adjacency
        # F is any ring face; then R is the ring face adjacent to F but not opposite
        f_face = ring[0]
        ring_faces = set(ring)
        r_candidates = [x for x in self.adj[f_face] if x in ring_faces]
        r_face = r_candidates[0] if r_candidates else ring[1]
        # canonical order U,R,F,D,L,B
        self.face_map = {0: "U", r_face: "R", f_face: "F", down: "D", None: "L", None: "B"}
        used = {"U", "R", "F", "D"}
        remaining_faces = [x for x in ring if x not in (f_face, r_face)]
        b_face = remaining_faces[0]
        l_face = remaining_faces[1]
        self.face_map = {0: "U", r_face: "R", f_face: "F", down: "D", l_face: "L", b_face: "B"}
        # canonical positions for each face block
        canonical_idx = {"U": 0, "R": 9, "F": 18, "D": 27, "L": 36, "B": 45}
        self.relabel = [0] * 54  # canon_pos -> competition facelet index
        for face_idx, face_name in self.face_map.items():
            base = canonical_idx[face_name]
            # order within small faces consistently by using the cube's own
            # adjacency: sort the 9 facelets of each face by their neighbours
            comp_face = groups_of = {v: k for k, v in self.face_of.items()}
            fl = [i for i in range(54) if self.face_of[i] == face_idx]
            fl_sorted = self._sort_facelets(fl, face_idx)
            for k, comp_pos in enumerate(fl_sorted):
                self.relabel[base + k] = comp_pos
        self.can2comp = self.relabel
        self.comp2can = [0] * 54
        for c, w in enumerate(self.relabel):
            self.comp2can[w] = c

    def _sort_facelets(self, facelets: List[int], face_idx: int) -> List[int]:
        """Order the 9 facelets of a face so the arrangement matches the
        canonical 3x3 grid (0=top-left ... 8=bottom-right).  We infer the
        grid from adjacency: build the 3x3 via move-graph neighbours."""
        # neighbours (in other faces) of each facelet, keyed by adjacent face
        pass  # implemented in _build_cubie_ops via direct move analysis

    def _build_cubie_ops(self) -> None:
        raise NotImplementedError

    def to_canonical(self, state: State) -> State:
        return tuple(state[self.relabel[i]] for i in range(54))

    def from_canonical(self, state: State) -> State:
        return tuple(state[self.comp2can[i]] for i in range(54))