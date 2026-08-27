---
name: rubiks-cube
description: Solve 3x3x3 and 2x2x2 Rubik's cubes (and the NxNxN slice-cube family) with the staged phase-reduction solver, BFS tables, and the competition cube adapter. Use when cracking cube puzzles in the CayleyPy Kaggle competitions.
verified: 2026-08-01
---

# Rubik's Cube skill

The harness solves cubes with a *phase-reduction* algorithm in the spirit of
Thistlethwaite: the cube is driven down through four nested subgroups; each
phase is a single BFS parent-tree over a small reduced coordinate space.

## The four phases (simple and elegant)

| phase | target | reduced coordinate | space |
| --- | --- | --- | --- |
| 1 | edge orientation = 0 | 12 EO bits (even parity) | 2048 |
| 2 | corner orientation = 0 + E-slice membership fixed | 3^7 x 495 | 1 082 565 |
| 3 | corner permutation solved | corner owners x 8 | <= 20 160 |
| 4 | remaining edge scramble (inside the corner-fixing subgroup of G2) | packed edge state | <= ~967 680 |

Phase tables store **parent pointers only** (child key -> (parent, move)),
so the whole solver is a few tens of MB and builds in minutes in pure
Python. Solving is four parent-walks: look up the reduced coordinate of the
current state, walk to the root, apply the moves.

## Move sets per phase

- phase 1: all 18 face turns (U, U', U2 ...);
- phase 2: G1 = <U,D,R,L,F2,B2> - single U/D/R/L turns never flip edges;
  single F/B would destroy phase 1's edge orientation;
- phase 3: G2 = <U,D,R2,L2,F2,B2>;
- phase 4: compound generators [m + corner-repair(m)] that fix corners.

## Competition cube adapter

Competitions use a *slice-turn* facelet model (faces = colour classes of the
solved state, face turns = moves that affect all facelets of a face except
its centre). `puzzle_cracker/solvers/cube_adapter.py` detects:
- the six faces (color classes of 9);
- face turns (moves affecting 8 or 9 facelets of one class);
- canonical labels U/R/F/D/L/B via the U-turn ring flow.

The cubie model (corners/edges/orientations) is then **derived from the
moves** by orbit analysis:
- a corner facelet is moved by exactly 3 face turns; an edge by 2;
- two facelets are cubie-mates iff the orbit of their sticker-pair under the
  face turns closes into exactly 24 pairs (corners) / 12 (edges).

This makes the solver representation-agnostic: identical code solves the
canonical cube and any competition cube with a different layout.

## Usage

```python
from puzzle_cracker.puzzles import load_santa_2023
from puzzle_cracker.solvers.staged import cube_adapter_for

data = load_santa_2023("data/santa-2023", puzzle_types=["cube_3/3/3"])
pz = data["cube_3/3/3"]["puzzle"]
sc = cube_adapter_for(pz)
sol = sc.solve(scramble_state, table_dir="cache/tables")  # competition move names
```

## When NOT to use

- 2x2x2 small puzzles: bidirectional BFS (optimal, instant);
- megaminx / 4x4x4+: use the `twisty-puzzles` / `cayley-graphs` skills
  (beam search, reduction);
- solving for *shortest possible* (God's number territory): phase 4 is a
  bounded search; for deep-optimal use the diffusion-heuristic beam search
  documented in docs/puzzles.md (khoruzhii/cayleypy-cube).