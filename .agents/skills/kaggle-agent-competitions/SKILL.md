---
name: kaggle-agent-competitions
description: Wire the Kaggle API token, download competition data for the CayleyPy puzzle family, understand the data formats, and write valid submissions. Use whenever handling Kaggle competition data in this harness.
verified: 2026-08-01
---

# Kaggle Agent Competitions skill

## Credentials

The harness uses a Kaggle API credential of the form `KGAT_<hex>` (an agent
token that authenticates the API - without it `/api/v1/...` returns 401).

Precedence:
1. env `KAGGLE_USERNAME` / `KAGGLE_KEY` (or `KAGGLE_TOKEN`);
2. `~/.kaggle/kaggle.json` (written by `make setup`).

The token is a **secret**: never commit it, print it, or log it.  Prefer
reading it from the environment at run time in one place
(`puzzle_cracker/kaggle_client.py`).

## Competition family

The CayleyPy puzzle competitions (see `docs/competitions.md`):

- `santa-2023` - cubes 2x2..33x33, globe, wreath (classic dataset);
- `cayley-py-444/555/666/777-cube` - NxNxN slice-cube agent competitions;
- `cayley-py-megaminx` - megaminx, 120 facelets, 24 face turns;
- `cayleypy-reversals`, `cayleypy-transposons` - graphs_info server comps;
- `cayleypy-ihes-cube`, `cayley-py-professor-tetraminx-solve-optimally`,
  `cayleypy-christophers-jewel`, `cayleypy-glushkov`,
  `cayleypy-rapapport-m2`, `lrx-oeis-a-186783-brainstorm-math-conjecture`.

Some entries can be listed but not downloaded with a given credential
(403) - treat them as out of scope for runs and note it.

## Data formats (read before writing a loader)

- `puzzle_info.json`: `{"name", "central_state", "generators": {name: perm}}`
  - agent competitions; moves are array-form 0-based permutations
    (`new[i] = old[p[i]]`); inverses appear as `-name`.
- `puzzle_info.csv` (Santa 2023): `puzzle_type, "{'f0': [...], ...}"`.
- `puzzles.csv` (Santa): `id, puzzle_type, solution_state, initial_state,
  num_wildcards`.
- `test.csv` (agent comps): `initial_state_id, initial_state, comment` -
  the comment often carries `generated rw, len=K` (scramble length).
- `graphs_info.json/.h5`: per-size graph definitions (reversals /
  transposons); server competitions may not ship a test.csv.

## Submissions

Format: `initial_state_id,path` where `path` = dot-separated moves
(`f1`, `-d0.d2`, `R[0,2]`).  The path must map the initial state onto the
central/solved state.  `puzzle_cracker/scoring.write_submission` writes it.

## Rules of the road

1. Never modify official data files.
2. Run final scoring on official data; iterate on local random-walk
   benchmarks.
3. A valid solve beats a shorter one that does not verify - always validate
   before submitting.
4. Token-gated CC-BY/competition data stays out of the repo (gitignored
   `data/`).