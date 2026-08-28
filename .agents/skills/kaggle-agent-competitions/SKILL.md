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

## Competition family (the full manifest)

The manifest lives in `puzzle_cracker/competitions.py` - the single source
of truth.  All 14 refs:

| ref | kind | loader |
| --- | --- | --- |
| `santa-2023` | santa (csv) | `puzzles.load_santa_2023` |
| `cayley-py-444/555/666/777-cube` | agent (json) | `load_agent_competition` |
| `cayley-py-megaminx` | agent | `load_agent_competition` |
| `cayleypy-ihes-cube` | agent | `load_agent_competition` |
| `cayley-py-professor-tetraminx-solve-optimally` | agent | `load_agent_competition` |
| `cayleypy-reversals`, `cayleypy-transposons` | graphs | `load_server_competition` |
| `cayleypy-christophers-jewel` | agent | `load_agent_competition` |
| `cayleypy-glushkov`, `cayleypy-rapapport-m2`, `lrx-oeis-...` | raw | raw loader (moves-undefined) |

Components the agent should use:

- `competitions.status(data_dir)` - per-ref: `data` / `moves-undefined` /
  `forbidden` / `missing` / `no-credentials`;
- `competitions.fetch_all(data_dir)` - download everything the token can
  reach (uses `KAGGLE_KEY` / `~/.kaggle/kaggle.json`);
- `competitions.load_all(data_dir)` - load every local competition into
  `{puzzle, cases}` bundles;
- `make data-all` / `make run-all` - the same as one-liners;
- `python -m puzzle_cracker.harness --all` - harness over all local comps.

Known access state with the KGAT credential: 11/14 datasets downloadable;
`cayley-py-555/666/777-cube` list their files but download returns 403
(participant access per competition) - treat as out of scope, note it.

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