# Deployment: this repo as an agent everywhere

The repository is self-deploying: `make install` (or `deploy/install.sh`)

1. creates a venv and installs the package;
2. writes `~/.kaggle/kaggle.json` from `KAGGLE_KEY`;
3. scaffolds a **separate working project** (`puzzle-cracker-workspace/`
   next to the repo, or `PZ_WORKSPACE`) with symlinked AGENTS.md / CLAUDE.md
   / puzzle_cracker / skills;
4. registers the agent:

| Client | Mechanism |
| --- | --- |
| OpenCode | `~/.config/opencode/agent/puzzle-cracker.md` |
| DeepSeek Harness | `dsh plugin add file:<repo>/deploy/dsh-plugin` (bundle with `dsh.bundle.patch`) |
| Claude Code | reads `CLAUDE.md`; skills via `~/.claude/skills/` symlinks |
| Cursor | reads `AGENTS.md`; skills via `~/.cursor/skills/` |
| pi, Codex, Gemini CLI | AGENTS.md-aware: run them from the repo/workspace root |
| VS Code / Copilot | AGENTS.md-aware |

## How the pieces fit

```
puzzle-cracker/                  (this repo = the template)
├── AGENTS.md                    agent policy (source of truth)
├── CLAUDE.md                    thin import for Claude Code
├── puzzle_cracker/              the solver engine
├── .agents/skills/              the real skill files
├── .claude/skills/  -> symlinks
├── .cursor/skills/  -> symlinks
├── deploy/                      installer + client wiring + dsh bundle
└── data/ outputs/ cache/        competition data + runs (git-ignored)

puzzle-cracker-workspace/        (separate working project, created by make install)
├── AGENTS.md -> ../puzzle-cracker/AGENTS.md
├── puzzle_cracker -> (symlink)
├── data/ outputs/ docs/scorecards/
└── .agents -> (symlink)
```

A fresh agent dropped into the workspace has the policy, the engine, the
skills and the data flow ready: `make data && make demo && make run`.

## Manual registration

```bash
# OpenCode: an agent definition pointing at the workspace
opencode agent add puzzle-cracker --prompt "$(cat AGENTS.md)"

# DeepSeek Harness (profile plugin)
dsh plugin add file:$(pwd)/deploy/dsh-plugin

# Claude Code / Cursor skill symlinks
mkdir -p ~/.claude/skills ~/.cursor/skills
for s in .agents/skills/*; do ln -s "$(pwd)/$s" ~/.claude/skills/; ln -s "$(pwd)/$s" ~/.cursor/skills/; done
```

## Notes

- Store the Kaggle token only in `~/.kaggle/kaggle.json` / env; never inside
  the repo.  GitHub tokens likewise.
- Uninstall: `make uninstall` removes the workspace and the registrations.
- The dsh bundle is a plain `dsh.bundle.patch` package; review
  `deploy/dsh-plugin/index.js` before loading (third-party code discipline).