# Puzzle Cracker - multi-host plugin marketplace

Mirrors the compound-engineering-plugin packaging pattern: one plugin,
per-host manifests.

| host | manifest |
| --- | --- |
| Claude Code | `.claude-plugin/plugin.json` (marketplace install) |
| Cursor | `.cursor-plugin/plugin.json` |
| Codex | `.codex-plugin/plugin.json` |
| OpenCode | `.opencode/INSTALL.md` (+ `deploy/opencode/agents/*.md`) |
| OMP/herdr | `.omp-plugin/marketplace.json` |
| DeepSeek Harness | `deploy/dsh-plugin/` (bundle) |
| AGENTS.md-native | pi, Codex CLI, Gemini CLI: run from the repo/workspace |

The real agent content lives once: `AGENTS.md` (policy), `.agents/skills/`
(skills), `deploy/opencode/agents/` (roles), `docs/` (references) - the
manifests above only point hosts at it.
