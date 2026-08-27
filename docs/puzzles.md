# Puzzles and algorithms

## The simple elegant algorithm the harness distils

**Phase-reduction on the Cayley graph.**  For the 3x3x3 the solver drives
the cube down through four nested subgroups; every phase is a single BFS
parent-tree over a tiny reduced coordinate space (see the `rubiks-cube`
skill for the table).  The result: a solver that stores only parent pointers
(a few tens of MB), solves in milliseconds, and reads like a proof:

    1. fix edge orientation        (2048 states)
    2. fix corner orientation +
       E-slice edge placement      (1 082 565 states)
    3. fix corner permutation      (<= 20 160 states)
    4. fix the remaining edges     (<= ~967 680 states)

The same idea in miniature solves the 2x2x2 and small graph puzzles
exactly via **bidirectional BFS**, and the huge ones (Megaminx, 4x4x4+,
big reversals) via **colour-guided beam search** on the competition's own
facelet model.

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