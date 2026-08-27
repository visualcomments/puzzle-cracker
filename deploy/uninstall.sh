#!/usr/bin/env bash
# Puzzle Cracker - uninstall: remove the workspace scaffold and agent
# registrations created by install.sh.

set -euo pipefail
WORKSPACE="${PZ_WORKSPACE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/../puzzle-cracker-workspace}"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}"

echo "removing workspace: $WORKSPACE"
rm -rf "$WORKSPACE"

echo "removing registered agents/skills"
rm -f "$CFG/opencode/agent/puzzle-cracker.md"
for client in claude cursor; do
  for skill in "$CFG/$client/skills"/*; do
    if [ -L "$skill" ] && [ "$(readlink -f "$skill")" = "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.agents/skills/$(basename "$skill")" ]; then
      rm -f "$skill"
    fi
  done
done
echo "done"