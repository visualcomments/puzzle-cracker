# Competitions

The harness plays the **CayleyPy competition family** on Kaggle: puzzles are
permutation-group/twisty-puzzle scrambles, the metric is total path length
(shorter = better).  All data is accessed with the token-gated Kaggle API
(`KGAT_...` credential; see `puzzle_cracker/kaggle_client.py`).

| Competition | Puzzles | Format |
| --- | --- | --- |
| `santa-2023` | cubes 2x2x2 .. 33x33x33, globe, wreath | puzzle_info.csv + puzzles.csv |
| `cayley-py-444-cube` / `-555` / `-666` / `-777` | NxNxN slice-cubes | puzzle_info.json + test.csv |
| `cayley-py-megaminx` | Megaminx (120 facelets, 24 moves) | puzzle_info.json + test.csv |
| `cayleypy-ihes-cube` | Picture cube (72 facelets) | puzzle_info.json + test.csv |
| `cayley-py-professor-tetraminx-solve-optimally` | Tetraminx | puzzle_info.json + test.csv |
| `cayleypy-reversals` | segment-reversal graphs per size | graphs_info.json/.h5 |
| `cayleypy-transposons` | transposition-path graphs | graphs_info.json/.h5 |
| `cayleypy-christophers-jewel`, `cayleypy-glushkov`, `cayleypy-rapapport-m2`, `lrx-oeis-a-186783-brainstorm-math-conjecture` | GAP / LRX / OEIS families | test.csv + sample_submission |

## Access

```bash
pip install -e .            # or: make setup
export KAGGLE_KEY=KGAT_...  # the credential
make data                   # downloads into data/<ref>/
```

`kaggle_client.list_competitions()` uses the REST API with the Bearer token.

## Data semantics

A scramble is one puzzle instance with an `initial_state` (and a
`solution_state` / `central_state`/ `solved`); the task is a move sequence
`path` that maps `initial_state` onto the solved state.  Moves are array-form
permutations on facelets (0-based): `new[i] = old[p[i]]`.

### Formats in detail

* `puzzle_info.json`: `{"name", "central_state" (partition labels),
  "generators": {"f0": [...], "-f0": [...]}}`; the generators include
  inverses with a `-` prefix.
* `puzzle_info.csv` (Santa): `puzzle_type, "{'f0': [...], ...}"` and
  `puzzles.csv`: `id, puzzle_type, solution_state, initial_state,
  num_wildcards` (wildcards allow discarding positions).
* `test.csv` (agent comps): `initial_state_id, initial_state, comment`
  (the comment often says `generated rw, len=K`).
* `graphs_info.json/.h5`: per-size blocks with `central_state` +
  `generators` (reversals `R[i,j]`, transposons).

## Status of download access (verified with the KGAT credential)

The `KGAT_...` credential authenticates the Kaggle API (401 without it).
`competitions.status(data_dir)` reproduces this table at any time:

| status | refs |
| --- | --- |
| data (ready) | santa-2023, cayley-py-444-cube, cayley-py-megaminx, cayleypy-ihes-cube, cayley-py-professor-tetraminx-solve-optimally, cayleypy-reversals, cayleypy-transposons, cayleypy-christophers-jewel |
| moves-undefined | cayleypy-glushkov, cayleypy-rapapport-m2, lrx-oeis-a-186783 (test data present; generator definitions come from the linked papers) |
| forbidden | cayley-py-555/666/777-cube (files listable; download 403 with this token - participant access per competition) |

`cayleypy-reversals` / `cayleypy-transposons` are server competitions: they
ship graph definitions; the harness scores local random-walk benchmarks
generated from the graph definitions.

## The scoring contract

Score = solve rate and total path length on the official test set (or the
held-out random-walk benchmark).  The harness writes a submission CSV
(`initial_state_id,path`) from any run; validate before submitting.