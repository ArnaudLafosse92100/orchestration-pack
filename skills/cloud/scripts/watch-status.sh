#!/usr/bin/env bash
# Watch the notes/<topic>-status branches of the topics a conductor launched and print one line
# per change, with the MESSAGE MONTANT first line of the new status.md (SKILL.md §0b rule 5bis, §4).
#
#   bash watch-status.sh [--once] <topic> [<topic>...]     run from a checkout of the repo
#
# Default: endless, one line per change (Monitor tool). --once: exit at the first change
# (Bash run_in_background). Polls one `git ls-remote` every WATCH_INTERVAL seconds (default 15):
# no model call while nothing changes. Last seen heads are kept in .omo/watch-status.<hash>, so a
# change that lands while the watch is re-armed is reported at the next start, never lost.
# Prints `ERR ls-remote` after 3 failed polls in a row, and `ALERT workdir missing` if the
# checkout disappears.
set -u
once=no; [[ "${1:-}" == "--once" ]] && { once=yes; shift; }
[[ $# -ge 1 ]] || { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
interval="${WATCH_INTERVAL:-15}"
workdir="$(pwd -P)"
git rev-parse --git-dir >/dev/null 2>&1 || { echo "ERR not a git checkout: $workdir"; exit 2; }
refs=(); for t in "$@"; do refs+=("refs/heads/notes/${t}-status"); done
mkdir -p .omo
key="$(printf '%s\n' "${refs[@]}" | git hash-object --stdin | cut -c1-12)"
state=".omo/watch-status.${key}"
# First start for these topics: the current heads are the baseline (the conductor read them at launch).
if [[ ! -f "$state" ]]; then
  git ls-remote origin "${refs[@]}" 2>/dev/null | sed '/^$/d' > "$state" || : > "$state"
fi

report() {   # $1 = "sha<TAB>ref" line of a changed head
  local sha="${1%%$'\t'*}" ref="${1#*$'\t'}" topic first
  topic="${ref#refs/heads/notes/}"; topic="${topic%-status}"
  if git fetch -q origin "${ref}:refs/remotes/origin/${ref#refs/heads/}" 2>/dev/null; then
    first="$(git show "${sha}:status.md" 2>/dev/null | head -n 1)"
  else first="(fetch failed)"; fi
  case "$first" in
    "MESSAGE MONTANT"*) echo "STATUS ${topic} @ ${sha:0:7}: ${first}" ;;
    *) echo "STATUS ${topic} @ ${sha:0:7}: updated (no MESSAGE MONTANT line)" ;;
  esac
}

fails=0
while :; do
  [[ -d "$workdir" ]] || { echo "ALERT workdir missing: $workdir"; exit 1; }
  if cur="$(git ls-remote origin "${refs[@]}" 2>/dev/null)"; then
    fails=0
    changed="$(comm -13 <(sort "$state") <(printf '%s\n' "$cur" | sed '/^$/d' | sort))"
    if [[ -n "$changed" ]]; then
      while IFS= read -r line; do report "$line"; done <<< "$changed"
      printf '%s\n' "$cur" | sed '/^$/d' > "$state"
      [[ "$once" == yes ]] && exit 0
    fi
  else
    fails=$((fails + 1))
    if (( fails == 3 )); then echo "ERR ls-remote (3 failed polls)"; [[ "$once" == yes ]] && exit 1; fi
  fi
  sleep "$interval"
done
