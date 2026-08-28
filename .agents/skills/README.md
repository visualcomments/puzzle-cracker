# Puzzle Cracker - agent skills

Skills are loaded automatically by any agent working in this repository
(AGENTS.md-aware: OpenCode, DeepSeek Harness, pi, Cursor, Codex; Claude Code
via `.claude/skills/` symlinks; Cursor also reads `.cursor/skills/`).

| Skill | What it does |
| --- | --- |
| `rubiks-cube` | staged 4-phase 3x3x3 solver, BFS tables, cube adapter |
| `twisty-puzzles` | megaminx / big cubes: colour-guided beam search + reduction roadmap |
| `cayley-graphs` | permutation-group puzzles: biBFS, IDA*, beam, heuristics |
| `kaggle-agent-competitions` | token wiring, data formats, submissions |
| `polynomial-time-algorithms` | create solvers that run in polynomial time: budgets, constructive patterns, solve-then-shorten |
| `algo-distillation` | turn a working solver into the simple elegant artifact |
| `scoring-and-benchmarks` | metrics, held-out sets, scorecards |
| `self-improvement` | continuous improvement loop: analyze -> change -> regress -> publish |

Each skill is a set of instructions under one `SKILL.md`.  Re-read the
`SKILL.md` before relying on it; treat third-party skills as untrusted until
reviewed.

## Installing globally

Copy (or symlink) `.agents/skills/<name>` into your agent's skills
directory:

- Claude Code: `~/.claude/skills/<name>`;
- Cursor: `~/.cursor/skills/<name>`;
- OpenCode: `~/.config/opencode/skills/<name>` (or `opencode.json` agent
  config, see `deploy/`);
- DeepSeek Harness: `dsh plugin add <bundle>` (see `deploy/dsh-plugin`).

`make install` does all of this automatically.