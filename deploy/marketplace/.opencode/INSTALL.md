# Installing Puzzle Cracker for OpenCode

Add the plugin to `opencode.json`:

```json
{ "plugin": ["puzzle-cracker@git+https://github.com/visualcomments/puzzle-cracker.git"] }
```

Or use the per-role agents shipped in `deploy/opencode/agents/`
(Orchestrator, Researcher, Solver, Analyst, Verifier, Distiller):
copy them into `~/.config/opencode/agent/` (the installer does this
automatically).  The repo is AGENTS.md-native, so running OpenCode from the
workspace root also loads the policy + skills directly.
