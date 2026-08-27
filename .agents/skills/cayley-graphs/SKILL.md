---
name: cayley-graphs
description: Solve permutation-group puzzles (reversals, pancake, LRX, TopSpin, 15-puzzle, globe, wreath, transposons) with bidirectional BFS, IDA* and heuristics on the Cayley graph. Use for cayleypy-reversals, cayleypy-transposons, santa-2023 globe/wreath and LRX competitions.
verified: 2026-08-01
---

# Cayley Graphs skill

Many competition puzzles are pure permutation groups: states are
permutations, moves are generators (reversals R[i,j], prefix reversals,
3-cycles, ring rotations...).  The harness treats them all as Cayley graphs:

- **bidirectional BFS** - optimal; use when the group fits in memory
  (<= ~2-4M states: pancake n<=9, globe, LRX n<=8, reversals n<=9);
- **IDA\*** with a heuristic - 15-puzzle (Manhattan), TopSpin (angle sum),
  reversals (linear-combination lower bound);
- **beam search** - fallback for big groups (reversals n=12...).

## Scoring is path length

For the CayleyPy competition family the metric is total path length over
scrambles.  Optimal (biBFS) beats heuristic almost always - but the budget
wins: solve more, then shorten.  Never spend the whole budget on one
scramble when others are still unsolved.

## Data formats

- `puzzle_info.json`: `{"name", "central_state", "generators"}` - agent
  competitions (cayley-py-*);
- `puzzle_info.csv`: Santa 2023 (`cube_n/n/n`, `globe_a/b`, `wreath_a/b`);
- `graphs_info.json/.h5`: `cayleypy-reversals`, `cayleypy-transposons`
  (server competitions; no test.csv - benchmarks are generated locally from
  the graph definitions).

Moves are permutations (array form, 0-based): `new[i] = old[p[i]]`.

## Heuristic catalogue (`puzzle_cracker/solvers/generic.py`)

- `mismatched_count` - ranking signal for beam;
- `manhattan_15` - admissible for the 15-puzzle;
- `color_face_distance` - facelet puzzles.

## When NOT to use

- twisty puzzles with big state spaces: `twisty-puzzles`;
- 3x3x3: `rubiks-cube`.