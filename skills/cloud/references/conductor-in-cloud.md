# Conductor in the cloud (decision 2026-10-20)

The conductor runs as a cloud session by default, so coordination keeps going when the Mac sleeps.

## Placement

- Conversation started locally: publish the state (below), then call `move_to_cloud` with `skip_push: true` BEFORE launching leads. Foreign untracked or uncommitted local files never justify a new conductor. On a `move_to_cloud` refusal: (a) the user declined → stop, say in French that nothing moved, ask what they want; (b) environment / GitHub / unknown-id → back to SKILL.md §1, fix, call again, NEVER `start_session`; (c) any other refusal while §1 shows a `hosted:true`, `fitsRepository:true` environment → only then `start_session` a new conductor, quote the refusal in French, say this conversation stays local. Trivial request (one small topic, under ~1 h): no leads, no pack; the cloud session does the work itself.
- New work: tell the user, in French, to start in the cloud. Code tab → selector under the composer (shows « Local » by default) → « Cloud », or start at claude.ai/code. The app has no "cloud by default" setting that Claude can change.

## State branch name

`<topic>` is a short slug of the chantier (e.g. `home-v2-fix`), so two conductors in one repo never overwrite each other. Before first use, `git ls-remote origin "refs/heads/notes/conductor-<topic>-*"` must be empty. If non-empty and the existing state is the same work, ask the user in French whether to reuse it; otherwise pick another slug. If this conversation already called `move_to_cloud`, or `list_sessions` shows a cloud session with this title or branch, give its link and stop: never create a second conductor without the user's explicit OK. Watch only the topics listed in YOUR state.md; never answer a status you did not launch.

## What does not travel

Local memory, local plan/todo folders and local skills stay on the Mac. Replace them with a notes branch `notes/conductor-<topic>-state`, pushed with the plumbing and guard of SKILL.md §2 (fast-forward with `commit-tree -p <parent>`, never `--force`; reference-only, never merged). Never push a refspec with an empty source: an empty `${C}` deletes the remote branch. A push rejected by protection or rules: do not loop over other names, tell the user in French which ref was rejected and why (channels are then down).

- `state.md`: topics, phases, leads with session links, branch shas, owner decisions pending, sessions to archive, "LOCAL CHECKS OWED".
- Copies of the plan and decision files the conductor needs, one file each (text only; large or private files such as zips, exports, assets never go on notes branches: Mode A locally, or LOCAL CHECKS OWED).
- Only shas confirmed via `git ls-remote`; anything still local goes under LOCAL CHECKS OWED. Never secrets or `.env` content.

The Sisyphus pack AND this skill are vendored in the repo's `.claude/` (`sync.sh --project`), so a cloud session that checks out a branch with the pack has /cloud and /sisyphus; the `move_to_cloud` summary only gives the `git show` command for `state.md`. A handoff (`cloud-SKILL.md`, `cloud-<reference>.md`, the runtime) on `notes/conductor-<topic>-handoff` is published ONCE, and only when a lead's base branch has no `.claude/skills/` (SKILL.md §2 « Pack check »). Then, for each such lead, the cloud conductor copies it server-side, no local paths:

```bash
git fetch origin notes/conductor-<topic>-handoff:refs/remotes/origin/notes/conductor-<topic>-handoff && git push --no-verify origin "refs/remotes/origin/notes/conductor-<topic>-handoff:refs/heads/notes/<lead-topic>-handoff"
```

`<lead-topic>-*` must be unused on the remote first (`git ls-remote`); no `--force` on a handoff branch that exists and is not yours.

Before `move_to_cloud`, the local session publishes the state (and the handoff, if one is needed). The cloud conductor reads `notes/conductor-<topic>-state` first and updates it at every milestone (it replaces local memory for this purpose).

## Capabilities and limits

- Can: start lead sessions (observed: a cloud lead started child cloud sessions; if `start_session` is unavailable, do the topic in-session with `Agent` subagents and say so); read and answer notes branches.
- **Watch guarantee.** Never end a turn without an armed watch: Monitor (max 30 min, re-armed on each expiry) or Bash `run_in_background` with an until-loop exiting on any head change or error, over an explicit `ls-remote` of the status refs of YOUR topics (command in SKILL.md §4, prints `ERR ls-remote` on failure). Neither tool: say in French that monitoring stops when the turn ends and the user must send « continue ». Record « watch armed until <UTC> » in state.md.
- **Staleness** (SKILL.md §5b step 0): lead status older than 45 min, or none 15 min after launch → tell the user in French and record it.
- **Quota** is unknown in the cloud (`claude-usage` is local-only): half the soft cap (≤2–3 parallel children), « quota unchecked » in state.md.
- Cannot: local-only checks (Docker images, local browser, local MCP, local files). List each under "LOCAL CHECKS OWED" in `state.md` and ask the user to run them, or to open a local session for them when the Mac is awake. That local session is an optional helper only; it never conducts.
- Launches may still need the user's « Démarrer » click (SKILL.md §7).
- Permission mode: on start or move, tell the user (French) to switch this conductor to « Auto (Recommandé) » if the selector shows another; same reminder once per lead launch batch; relay any lead's BLOCKED SESSIONS (SKILL.md §7).

## state.md template (written by the /cloud takeover, SKILL.md §0 step 2)

```markdown
# Conductor state (updated <UTC date>)
## Goal (user's words)
## Decisions taken
## Topics and phases
| Topic | Phase | Status (todo/running/done) | Branch @ sha | Lead session link |
## Done / remaining work
## Branches and shas (base, integration, track)
## Owner decisions pending
## LOCAL CHECKS OWED
## Running sessions (links)
## Watch (armed until <UTC>) / quota unchecked
## Sessions to archive or continue
## Files published alongside (plans, memory copies)
```
