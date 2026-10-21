#!/usr/bin/env bash
# Managed by orchestration-pack (sync.sh). Runs the Sisyphus hooks of the skill installed
# next to this hooks dir. Usage: sisyphus.sh prompt|pretool|stop, hook JSON on stdin.
# Never fails the user's turn: a missing python3 or script exits 0 silently.
claude_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# Pack installed both in ~/.claude and in the project: the project copy wins, the home copy steps aside.
if [[ -n "${CLAUDE_PROJECT_DIR:-}" && -f "$CLAUDE_PROJECT_DIR/.claude/hooks/sisyphus.sh" ]]; then
  project_dir="$(cd "$CLAUDE_PROJECT_DIR/.claude" && pwd -P)"
  [[ "$project_dir" != "$claude_dir" ]] && exit 0
fi
script="$claude_dir/skills/sisyphus/scripts/hooks/sisyphus_hooks.py"
[[ -f "$script" ]] && command -v python3 >/dev/null 2>&1 || exit 0
exec python3 "$script" "$@"
