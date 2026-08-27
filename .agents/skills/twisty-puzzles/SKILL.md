---
name: twisty-puzzles
description: Solve megaminx, pyraminx, picture cubes, big cubes (4x4x4+) and other twisty puzzles with colour-guided beam search and the reduction roadmap. Use for the cayley-py-megaminx and NxNxN slice-cube competitions.
verified: 2026-08-01
---

# Twisty Puzzles skill

Puzzles with huge state spaces (megaminx ~10^65, 4x4x4 ~10^45, 5x5x5+ ...)
cannot be solved by exact search.  The harness uses **colour-guided beam
search** on the competition's own facelet model:

- heuristic: number of facelets not on their home face;
- beam width 4k-16k, node budget capped, time budget per scramble;
- greedy best-first first (usually finds short-scramble inverses instantly),
  then the wide beam.

This mirrors how the CayleyPy competition is actually won: beam search
guided by a learned diffusion-distance heuristic (khoruzhii/cayleypy-cube,
NeurIPS 2025 spotlight).  The harness ships the heuristic-free baseline;
the neural upgrade path is documented in `docs/puzzles.md`.

## Big-cube roadmap

For 4x4x4+ the honest baseline is: solve as many short scrambles as the beam
can reach, then extend with:

1. **reduction** - fix centres, pair edges, then solve as a 3x3x3 with the
   staged solver; the 3x3 machinery already handles the tail;
2. **two-phase layer rotors** - precompute macro tables for the outer
   layers (this is the classic big-cube approach at competition quality);
3. **learned heuristics** - train the diffusion-distance regressor on the
   puzzle's own random walks (see `cayley-py-*` puzzle_info generators).

## Megaminx specifics

- 12 faces x 10 facelets; 24 face turns in the competition data;
- each turn fixes at most ~15 facelets, so the home-face heuristic ranks
  cleanly;
- scrambles are often short random walks - the greedy pass solves them, the
  beam polishes the rest.

## When NOT to use

- 3x3x3 / small cubes: staged solver (`rubiks-cube` skill);
- pure permutation puzzles (reversals, LRX, TopSpin...): `cayley-graphs`.