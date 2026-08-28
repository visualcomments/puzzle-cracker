# Puzzles and algorithms

## The simple elegant algorithm the harness distils

**Phase-reduction on the Cayley graph.**  For the 3x3x3 the elegant solver
drives the cube down through four nested subgroups; every phase is a single
BFS parent-tree over a reduced coordinate space (see the `rubiks-cube`
skill for the table):

    1. fix edge orientation        (2048 states)
    2. fix corner orientation +
       E-slice edge placement      (1 082 565 states)
    3. fix corner permutation      (8! = 40 320 states)
    4. fix the remaining edges     (K-subgroup, ~483 840 states)

The reduced-coordinate BFS tables are built and the rep/encode roundtrips
are verified (0/100 failures per phase), but the orientation phases are not
*quotient-closed* (the flip delta depends on the piece type in a slot), so
the table walks currently solve only short scrambles reliably.  The
production path for the 3x3x3 is therefore **bidirectional BFS** (optimal
for scrambles up to ~8-11 moves, verified) with **beam search** for longer
ones; completing the phase tables via a full-state BFS is the documented
next step (see the `rubiks-cube` skill).

The same ideas solve the rest of the family:
2x2x2 and small graph puzzles exactly via **bidirectional BFS**; Megaminx
and 4x4x4+ via **colour-guided beam search**.

## Why the competition is won with beam search

The CayleyPy / Santa competitions reward *shortest total path* on
astronomically large Cayley graphs.  Exact search is impossible for
Megaminx (~10^65) and 4x4x4 (~10^45).  State of the art (khoruzhii's
`cayleypy-cube`, NeurIPS 2025) trains a **diffusion-distance regressor** on
random walks and uses its predictions to rank a batched beam search.  The
harness ships the heuristic-free baseline (solve short scrambles, polish
with the beam) and documents the neural upgrade path:

1. generate training walks with CayleyPy's own generators;
2. train a small MLP/ResNet on (state → distance-to-solved estimate);
3. plug it into `solvers/generic.solve_beam` as the heuristic;
4. measure against the baseline on the held-out set.

## Puzzle-specific notes

### Rubik's Cube
- 2x2x2: bidirectional BFS = exact.
- 3x3x3: staged phase solver; the competition slice-turn model is adapted
  automatically (faces = colour classes, face turns = all-but-centre moves).
- NxNxN slice-cubes (4x4x4+): the beam baseline + reduction roadmap in the
  `twisty-puzzles` skill.  Scrambles in the datasets are random walks of
  known length (comment `len=K`), which the beam uses as a hint.

### Megaminx (cayley-py-megaminx)
- 12 faces x 10 facelets; 24 face turns; per-face colour heuristic.
- Greedy best-first first, then wide beam; a full LBL (commutator-based)
  solver is documented as the reduction roadmap.

### Cayley graph puzzles (reversals, transposons, LRX, TopSpin, globe)
- Small groups: bidirectional BFS optimal; medium: IDA* with a heuristic;
- The `cayleypy-reversals` graphs (n up to 12+) are solved per-size: biBFS
  below ~10, beam above.

## Performance targets

A good run on a competition data set reports:

| Puzzle | target |
| --- | --- |
| 2x2x2 | 100% solve, optimal lengths |
| 3x3x3 scrambles <= 10 | 100% solve |
| 3x3x3 full test set | >= 90% solve, mean < 60 |
| megaminx short scrambles | >= 80% solve |
| reversals n=8 | 100% solve, optimal |

Numbers are recorded in `docs/scorecards/` after every run.