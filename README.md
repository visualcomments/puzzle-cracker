# Puzzle Cracker

A self-deploying **puzzle-cracking harness** for the twisty-puzzle family of
Kaggle competitions powered by [CayleyPy](https://github.com/cayleypy/cayleypy):
Rubik's Cube (2x2x2..7x7x7), Megaminx, and the permutation-graph puzzles
(reversals, transposons, ihes-cube, tetraminx, LRX...).

Modeled on the [SECS](https://github.com/EvilFreelancer/secs) pattern - an
`AGENTS.md`-rooted agent harness with a curated skill tree - Puzzle Cracker
turns any AI coding agent into a puzzle-solving specialist that **loads
competition data, solves scrambles, scores runs, and distils a simple
elegant algorithm** with the best achievable score.

## What it does

```
load data  ->  solve scrambles  ->  score (solve rate + total moves)
     ->  iterate strategy  ->  distil puzzle_cracker/strategy.py
```

* **The algorithm**: phase-reduction on the Cayley graph.  The 3x3x3 solver
  walks the cube down four nested subgroups with four BFS parent-tree tables
  (2048 / 1 082 565 / <=20 160 / <=967 680 states) - simple, elegant,
  deterministic, competitive.  2x2x2 and small graph puzzles (reversals,
  globe, LRX...) get **exact bidirectional BFS** (verified optimal);
  huge ones (Megaminx, 4x4x4+, reversals n>=12) get colour-guided beam
  search.  Every claim in this repo is backed by a scramble -> solve ->
  verify run (`make verify`).
* **Data**: token-gated Kaggle access for the whole CayleyPy family
  (`santa-2023`, `cayley-py-444/555/666/777-cube`, `cayley-py-megaminx`,
  `cayleypy-reversals`, `cayleypy-transposons`, `cayleypy-ihes-cube` and
  more).
* **Agents**: drops this repo into any agent that reads `AGENTS.md`
  (OpenCode, DeepSeek Harness, pi, Cursor, Codex) - with symlink farms and
  an installable DeepSeek Harness plugin bundle.

## Quick start

```bash
make setup                 # venv + deps + Kaggle credential (KAGGLE_KEY)
make data                  # download competition data
make demo                  # solve random 2x2x2 / 3x3x3 / reversals, score
make run REF=santa-2023 PUZZLE=cube_3/3/3 METHOD=staged
make data-all              # download every reachable CayleyPy competition
make run-all               # harness over all 14 competitions (manifest-driven)
make verify                # correctness oracle
make install               # scaffold a separate project + register agents
```

## Layout

| Path | What it is |
| --- | --- |
| `AGENTS.md` / `CLAUDE.md` | agent policy (source of truth / thin import) |
| `puzzle_cracker/` | solver engine: group core, staged cube solver, generic search, scoring, harness, kaggle client |
| `.agents/skills/` | six curated agent skills (rubiks-cube, twisty-puzzles, cayley-graphs, kaggle-agent-competitions, algo-distillation, scoring-and-benchmarks) |
| `.claude/skills/`, `.cursor/skills/` | symlink farms for Claude Code / Cursor |
| `deploy/` | installer (`make install`), OpenCode/DSH/Claude/Cursor wiring, DeepSeek Harness plugin bundle |
| `data/`, `outputs/`, `cache/` | competition data, runs, solver tables (git-ignored) |
| `docs/` | competitions, algorithms, deployment, scorecards |

## Research roots

* SECS - the harness pattern this repo mirrors: https://github.com/EvilFreelancer/secs
* CayleyPy - the competition library: https://github.com/cayleypy/cayleypy
* Diffusion-heuristic short-path search (autonomous solver for these
  puzzles): https://github.com/khoruzhii/cayleypy-cube

## License

MIT - see [LICENSE](LICENSE).  Competition data is owned by Kaggle and its
hosts and is not distributed with this repo.