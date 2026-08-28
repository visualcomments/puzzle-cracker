#!/usr/bin/env bash
# Puzzle Cracker - cross-platform installer.
#
# 1. creates a venv and installs the package;
# 2. writes ~/.kaggle/kaggle.json from the KAGGLE_KEY env (KGAT_...);
# 3. scaffolds a SEPARATE working project (default: ../puzzle-cracker-workspace
#    or $PZ_WORKSPACE) with its own AGENTS.md + skills + data/outputs dirs;
# 4. registers the agent in the installed clients:
#      - OpenCode        : ${XDG_CONFIG_HOME:-~/.config}/opencode/agent/
#      - DeepSeek Harness: `dsh plugin add` (bundle in deploy/dsh-plugin)
#      - Claude Code     : ~/.claude/skills symlink farm
#      - Cursor          : ~/.cursor/skills symlink farm
#      - pi / Codex      : AGENTS.md-based (documented in docs/deployment.md)

set -euo pipefail

PZ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="${PZ_WORKSPACE:-$PZ_ROOT/../puzzle-cracker-workspace}"
VENV="${PZ_ROOT}/.venv"

echo "== puzzle-cracker installer =="
echo "  repo     : $PZ_ROOT"
echo "  workspace: $WORKSPACE"

# 1) venv + package
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -e "$PZ_ROOT" || "$VENV/bin/pip" install -q "$PZ_ROOT"

# 2) Kaggle credentials
if [ -n "${KAGGLE_KEY:-}" ]; then
  mkdir -p "$HOME/.kaggle"
  cat > "$HOME/.kaggle/kaggle.json" <<EOF
{"username": "${KAGGLE_USERNAME:-kaggle}", "key": "${KAGGLE_KEY}"}
EOF
  chmod 600 "$HOME/.kaggle/kaggle.json"
  echo "  wrote ~/.kaggle/kaggle.json (credentials kept out of the repo)"
elif [ -f "$HOME/.kaggle/kaggle.json" ]; then
  echo "  using existing ~/.kaggle/kaggle.json"
else
  echo "  !! no KAGGLE_KEY - set it now or export it later:"
  echo "     export KAGGLE_KEY=KGAT_...   (then: make data)"
fi

# 3) scaffold a separate working project
mkdir -p "$WORKSPACE"/{data,outputs,docs/scorecards,cache/tables}
ln -sfn "$PZ_ROOT/AGENTS.md"      "$WORKSPACE/AGENTS.md"
ln -sfn "$PZ_ROOT/CLAUDE.md"      "$WORKSPACE/CLAUDE.md"
ln -sfn "$PZ_ROOT/puzzle_cracker" "$WORKSPACE/puzzle_cracker"
ln -sfn "$PZ_ROOT/.agents"        "$WORKSPACE/.agents"
echo "  scaffolded workspace: $WORKSPACE"

# 4) register agents
CFG="${XDG_CONFIG_HOME:-$HOME/.config}"
# OpenCode agent
mkdir -p "$CFG/opencode/agent"
if [ ! -e "$CFG/opencode/agent/puzzle-cracker.md" ]; then
  cat > "$CFG/opencode/agent/puzzle-cracker.md" <<EOF
---
description: Puzzle Cracker - twisty-puzzle Kaggle competition solver agent (Rubik's cube family, Megaminx, CayleyPy graphs).
---

You are the Puzzle Cracker agent.  Operate from $WORKSPACE.
Read AGENTS.md first.  Use make run/verify/demo; iterate strategy -> score ->
distil into puzzle_cracker/strategy.py.  Never print credentials.
EOF
  echo "  registered opencode agent: puzzle-cracker"
else
  echo "  opencode agent exists (skipped)"
fi

# DeepSeek Harness plugin (bundled in this repo)
if command -v dsh >/dev/null 2>&1; then
  dsh plugin --profile web add "file:$PZ_ROOT/deploy/dsh-plugin" 2>/dev/null \
    && echo "  registered deepseek-harness plugin" \
    || echo "  !! dsh plugin add failed (install pnpm, re-run)"
else
  echo "  dsh not found - to register manually: dsh plugin add file:$PZ_ROOT/deploy/dsh-plugin"
fi

# Claude Code + Cursor skill symlink farms
for client in claude cursor; do
  target="$CFG/$client/skills"
  mkdir -p "$target"
  for skill in "$PZ_ROOT"/.agents/skills/*/; do
    name="$(basename "$skill")"
    [ -e "$target/$name" ] || ln -s "$skill" "$target/$name"
  done
  echo "  linked skills into $client"
done

echo
echo "== done =="
echo " next: cd $WORKSPACE && make data && make demo"
echo " agent docs: $PZ_ROOT/docs/deployment.md"