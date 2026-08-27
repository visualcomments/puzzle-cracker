"""Detect the face structure of a 54-facelet cube-like puzzle.

Competition slice-cube puzzles expose their six faces as the six colour
classes of the solved state (9 facelets each).  Face turns are the moves
that affect all nine facelets of one face (all but its centre in the
slice-turn model).  The adapter returns:

    (face_turns, face_of)
      * face_turns: canonical face label ('U','R','F','D','L','B') -> the
        puzzle's move name for that face;
      * face_of:    facelet index -> canonical face label.

The staged solver derives its cubie model from the moves themselves, so the
adapter only needs the orientation conventions (which face is 'U' etc.).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..group import Puzzle

FACES = ["U", "R", "F", "D", "L", "B"]


class CubeDetector:
    def __init__(self, puzzle: Puzzle) -> None:
        self.puzzle = puzzle

    def detect(self) -> Optional[Tuple[Dict[str, str], Dict[int, str]]]:
        pz = self.puzzle
        if pz.n != 54:
            return None
        # 1) faces = colour classes of the solved state with 9 facelets
        classes: Dict[str, List[int]] = {}
        for i, tok in enumerate(pz.solved):
            classes.setdefault(tok, []).append(i)
        faces = [g for g in classes.values() if len(g) == 9]
        if len(faces) != 6:
            return None
        face_of: Dict[int, int] = {}
        for fi, group in enumerate(faces):
            for pos in group:
                face_of[pos] = fi

        # 2) adjacency: face A touches face B iff a move moves a facelet
        # between them
        adj = [set() for _ in range(6)]
        for _, perm in pz.moves.items():
            for i in range(54):
                j = perm[i]
                if i != j and face_of[i] != face_of[j]:
                    adj[face_of[i]].add(face_of[j])
        if any(len(a) != 4 for a in adj):
            return None
        opposite = {}
        for fi in range(6):
            opp = [f for f in range(6) if f != fi and f not in adj[fi]]
            if len(opp) != 1:
                return None
            opposite[fi] = opp[0]

        # 3) face turns: a move affecting all facelets of a face except the
        # centre (slice-turn model) or all 9 (face-turn model)
        turns: Dict[int, str] = {}
        for mname, perm in pz.moves.items():
            affected = [i for i in range(54) if perm[i] != i]
            for fi, group in enumerate(faces):
                hit = len([i for i in affected if i in group]) in (8, 9)
                if hit and len(group) == 9:
                    turns[fi] = mname
        if len(turns) != 6:
            return None

        # 4) canonical labels: pick face0 as U; opposite as D; the ring order
        # is read from the U-turn's ring flow
        u_face = 0
        d_face = opposite[u_face]
        u_turn = pz.moves[turns[u_face]]
        nbrs = list(adj[u_face])
        ring_next: Dict[int, int] = {}
        for n in nbrs:
            nxt = set()
            for i in faces[n]:
                j = u_turn[i]
                if j != i and face_of[j] != u_face and face_of[j] != n:
                    nxt.add(face_of[j])
            if len(nxt) != 1:
                return None
            ring_next[n] = nxt.pop()
        if len(ring_next) != 4 or set(ring_next.values()) != set(nbrs):
            return None
        f_face = nbrs[0]
        r_face = ring_next[f_face]
        b_face = ring_next[r_face]
        l_face = ring_next[b_face]
        label = {u_face: "U", d_face: "D", f_face: "F",
                 r_face: "R", b_face: "B", l_face: "L"}
        face_turns = {lab: turns[fi] for fi, lab in label.items()}
        face_label = {i: label[face_of[i]] for i in range(54)}
        return face_turns, face_label


def detect_face_turns(puzzle: Puzzle) -> Optional[Tuple[Dict[str, str], Dict[int, str]]]:
    return CubeDetector(puzzle).detect()