#!/usr/bin/env bash
# Copy the orchestration pack (skills/, agents/, hooks/) into a .claude/ directory and
# register its hooks. Idempotent.
#
#   ./sync.sh --project <repo>   into <repo>/.claude/ (hooks run from $CLAUDE_PROJECT_DIR)
#   ./sync.sh --home             into ~/.claude/, after a backup to ~/.claude/backup-orchestration-<date>/
#   ./sync.sh --cloud            into ~/.claude/ of a cloud container (setup script), with the permission rules
#   ./sync.sh --check <repo>     prints OK or STALE (installed sha vs this checkout's HEAD)
#   ./sync.sh --bootstrap <repo> writes only <repo>/.claude/settings.json: a SessionStart hook that,
#                                in cloud sessions, clones this public repo and runs --session, plus
#                                the pack's hooks (run from ~/.claude) and permission rules. Once per repo.
#   ./sync.sh --session          into ~/.claude/, files only (run by the bootstrap hook)
#
# Writes .claude/ORCHESTRATION_VERSION and .claude/ORCHESTRATION_MANIFEST. Removes only files
# listed in the previous manifest that are gone from the source. Settings: keeps every key and
# every hook it does not manage; replaces the managed Sisyphus hook entries. --project also adds
# the fragment's permissions.allow / permissions.deny rules (the Mac's ~/.claude never reaches a
# cloud session); --home leaves permissions untouched so other repos keep their behaviour.
# --cloud is --home for a fresh cloud container: no backup, the permission rules are added, and
# permissions.defaultMode is set to "auto" (honoured from user settings, ignored from project
# settings), since that container only ever runs these sessions. It also registers a SessionStart
# hook that re-runs sync.sh --cloud from the session's own clone of this repo, so every session
# gets the current pack even when the environment cache skips the setup script.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
MANAGED_DIRS=(skills agents hooks)
# Hook entries this pack owns (current wrapper, or the older direct python registration).
MANAGED_RE='sisyphus_hooks\.py|/\.claude/hooks/sisyphus\.sh|(claude-orchestration|orchestration-pack)/sync\.sh --|\.cache/orchestration-pack'
# Where cloud sessions clone the repos attached to their project.
CLOUD_CLONE=/home/user/orchestration-pack
REPO_URL=https://github.com/ArnaudLafosse92100/orchestration-pack
# Bootstrap hook: cloud sessions only (the Mac uses --home), never fails the session.
BOOTSTRAP_CMD='[ "$CLAUDE_CODE_REMOTE" = true ] || exit 0; d="$HOME/.cache/orchestration-pack"; { if [ -d "$d/.git" ]; then git -C "$d" pull -q --ff-only; else git clone -q --depth 1 --branch main '"$REPO_URL"' "$d"; fi; } >/dev/null 2>&1; [ -x "$d/sync.sh" ] && "$d/sync.sh" --session >/dev/null 2>&1; true'

die() { echo "sync.sh: $*" >&2; exit 1; }
usage() { sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

source_sha() {
  local sha
  sha="$(git -C "$SRC" rev-parse HEAD)"
  [[ -z "$(git -C "$SRC" status --porcelain -- "${MANAGED_DIRS[@]}" settings.fragment.json)" ]] || sha="${sha}-dirty"
  echo "$sha"
}

check() {
  local dest="$1/.claude/ORCHESTRATION_VERSION" installed
  [[ -f "$dest" ]] || { echo "STALE (no ORCHESTRATION_VERSION in $1/.claude)"; return 1; }
  installed="$(sed -n 's/^sha=//p' "$dest")"
  if [[ "$installed" == "$(source_sha)" ]]; then echo "OK ($installed)"; else
    echo "STALE (installed ${installed:-?}, source $(source_sha))"; return 1; fi
}

install() {
  local claude="$1" hook_root="$2" new_manifest old_manifest f
  mkdir -p "$claude"
  new_manifest="$(mktemp)"
  # Tracked files only: no caches, no local leftovers.
  git -C "$SRC" ls-files -- "${MANAGED_DIRS[@]}" | sort > "$new_manifest"
  [[ -s "$new_manifest" ]] || die "no tracked files under ${MANAGED_DIRS[*]} in $SRC"

  old_manifest="$claude/ORCHESTRATION_MANIFEST"
  if [[ -f "$old_manifest" ]]; then
    comm -23 <(sort "$old_manifest") "$new_manifest" | while IFS= read -r f; do
      [[ -n "$f" && "$f" != /* && "$f" != *..* ]] || continue
      rm -f "$claude/$f" && echo "removed  $f"
    done
  fi

  while IFS= read -r f; do
    mkdir -p "$claude/$(dirname "$f")"
    # rm first: never write through a symlink (e.g. ~/.claude/agents/*.md -> another repo).
    if ! cmp -s "$SRC/$f" "$claude/$f" || [[ -L "$claude/$f" ]]; then
      rm -f "$claude/$f"
      cp -p "$SRC/$f" "$claude/$f"
    fi
  done < "$new_manifest"
  mv "$new_manifest" "$old_manifest"

  [[ "$3" == files ]] || merge_settings "$claude/settings.json" "$hook_root" "$3"
  printf 'version=%s\nsha=%s\nsynced=%s\nsource=ArnaudLafosse92100/orchestration-pack\n' \
    "$(cat "$SRC/VERSION")" "$(source_sha)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$claude/ORCHESTRATION_VERSION"
  echo "synced $(wc -l < "$old_manifest" | tr -d ' ') files into $claude ($(cat "$SRC/VERSION"), $(source_sha))"
}

merge_settings() {
  local settings="$1" hook_root="$2" with_permissions="$3" frag tmp
  frag="$(sed "s|\\\$CLAUDE_PROJECT_DIR/.claude|${hook_root}|g" "$SRC/settings.fragment.json")"
  [[ -f "$settings" ]] || echo '{}' > "$settings"
  jq -e . "$settings" >/dev/null || die "$settings is not valid JSON, left untouched"
  tmp="$(mktemp)"
  jq --argjson frag "$frag" --arg re "$MANAGED_RE" --arg perms "$with_permissions" '
    def managed: any(.hooks[]?; (.command // "") | test($re));
    def add_rules($have; $new): ($have // []) as $h | $h + ($new - $h);
    ((.hooks // {}) | with_entries(.value |= map(select(managed | not)))) as $clean
    | .hooks = (reduce ($frag.hooks | to_entries[]) as $e ($clean; .[$e.key] = ((.[$e.key] // []) + $e.value))
                | with_entries(select(.value | length > 0)))
    | if $perms == "yes" then
        reduce (($frag.permissions // {}) | to_entries[]) as $p (.; .permissions[$p.key] = add_rules(.permissions[$p.key]; $p.value))
      else . end
  ' "$settings" > "$tmp"
  if cmp -s "$tmp" "$settings"; then rm -f "$tmp"; else mv "$tmp" "$settings"; fi
}

set_default_mode() {
  local settings="$1" mode="$2" tmp
  tmp="$(mktemp)"
  jq --arg m "$mode" '.permissions.defaultMode = $m' "$settings" > "$tmp"
  if cmp -s "$tmp" "$settings"; then rm -f "$tmp"; else mv "$tmp" "$settings"; fi
}

add_cloud_autosync() {
  local settings="$1" cmd tmp
  cmd="[ -x $CLOUD_CLONE/sync.sh ] && $CLOUD_CLONE/sync.sh --cloud >/dev/null 2>&1; true"
  tmp="$(mktemp)"
  jq --arg c "$cmd" '.hooks.SessionStart = ((.hooks.SessionStart // []) + [{hooks: [{type: "command", command: $c}]}])' \
    "$settings" > "$tmp"
  if cmp -s "$tmp" "$settings"; then rm -f "$tmp"; else mv "$tmp" "$settings"; fi
}

bootstrap_repo() {
  local claude="$1/.claude" settings frag tmp
  settings="$claude/settings.json"
  mkdir -p "$claude"
  # A repo that vendored the pack (--project) drops its copy: ~/.claude now holds it.
  if [[ -f "$claude/ORCHESTRATION_MANIFEST" ]]; then
    while IFS= read -r f; do
      [[ -n "$f" && "$f" != /* && "$f" != *..* ]] && rm -f "$claude/$f"
    done < "$claude/ORCHESTRATION_MANIFEST"
    find "$claude/skills" "$claude/agents" "$claude/hooks" -type d -empty -delete 2>/dev/null || true
    rm -f "$claude/ORCHESTRATION_MANIFEST" "$claude/ORCHESTRATION_VERSION"
    echo "removed the vendored pack copy from $claude"
  fi
  [[ -f "$settings" ]] || echo '{}' > "$settings"
  jq -e . "$settings" >/dev/null || die "$settings is not valid JSON, left untouched"
  # Pack hooks run from ~/.claude, cloud only (the Mac registers them in its own ~/.claude), and are
  # skipped until the bootstrap has synced. exec keeps the hook's exit code (Stop can block).
  frag="$(jq --arg c "$BOOTSTRAP_CMD" '
    .hooks |= with_entries(.value |= map(.hooks |= map(.command |= (
      capture("sisyphus\\.sh\" (?<arg>[a-z]+)$") as $m
      | "[ \"$CLAUDE_CODE_REMOTE\" = true ] && [ -f \"$HOME/.claude/hooks/sisyphus.sh\" ] && exec bash \"$HOME/.claude/hooks/sisyphus.sh\" \($m.arg) || true"))))
    | .hooks.SessionStart = [{hooks: [{type: "command", command: $c}]}]' "$SRC/settings.fragment.json")"
  tmp="$(mktemp)"
  jq --argjson frag "$frag" --arg re "$MANAGED_RE" '
    def managed: any(.hooks[]?; (.command // "") | test($re));
    def add_rules($have; $new): ($have // []) as $h | $h + ($new - $h);
    ((.hooks // {}) | with_entries(.value |= map(select(managed | not)))) as $clean
    | .hooks = (reduce ($frag.hooks | to_entries[]) as $e ($clean; .[$e.key] = ((.[$e.key] // []) + $e.value))
                | with_entries(select(.value | length > 0)))
    | reduce (($frag.permissions // {}) | to_entries[]) as $p (.; .permissions[$p.key] = add_rules(.permissions[$p.key]; $p.value))
  ' "$settings" > "$tmp"
  if cmp -s "$tmp" "$settings"; then rm -f "$tmp"; else mv "$tmp" "$settings"; fi
  echo "bootstrap written to $settings"
}

backup_home() {
  local claude="$HOME/.claude" dest f
  dest="$claude/backup-orchestration-$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$dest"
  [[ -f "$claude/settings.json" ]] && cp -p "$claude/settings.json" "$dest/"
  git -C "$SRC" ls-files -- "${MANAGED_DIRS[@]}" | while IFS= read -r f; do
    [[ -e "$claude/$f" || -L "$claude/$f" ]] || continue
    mkdir -p "$dest/$(dirname "$f")"
    cp -RP "$claude/$f" "$dest/$f"   # -P keeps symlinks as symlinks
  done
  echo "backup   $dest"
}

[[ $# -ge 1 ]] || usage
command -v jq >/dev/null || die "jq is required"
git -C "$SRC" rev-parse HEAD >/dev/null 2>&1 || die "$SRC is not a git checkout with a commit"

case "$1" in
  --project)
    [[ $# -eq 2 && -d "$2" ]] || usage
    install "$(cd "$2" && pwd -P)/.claude" '$CLAUDE_PROJECT_DIR/.claude' yes ;;
  --home)
    [[ $# -eq 1 ]] || usage
    backup_home
    install "$HOME/.claude" '$HOME/.claude' no ;;
  --cloud)
    [[ $# -eq 1 ]] || usage
    install "$HOME/.claude" '$HOME/.claude' yes
    set_default_mode "$HOME/.claude/settings.json" auto
    add_cloud_autosync "$HOME/.claude/settings.json" ;;
  --session)
    [[ $# -eq 1 ]] || usage
    install "$HOME/.claude" '$HOME/.claude' files ;;
  --bootstrap)
    [[ $# -eq 2 && -d "$2" ]] || usage
    bootstrap_repo "$(cd "$2" && pwd -P)" ;;
  --check)
    [[ $# -eq 2 && -d "$2" ]] || usage
    check "$(cd "$2" && pwd -P)" ;;
  *) usage ;;
esac
