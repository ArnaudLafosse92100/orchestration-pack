# Cloud track brief template

Copy, fill every field, and send as the `start_session` prompt. The cloud session sees only this text and the pushed repo: no `.omo/`, no scratchpad, no `.env`, no local skills. Replace `<…>`.

```
GOAL AND DONE CRITERIA
<one paragraph goal>
Done when: <observable criteria, tests that must pass, behaviour to verify>

BRANCH AND BASE
Work on branch <track-branch> (BASE = <base-branch>, sha <base-sha>).
Start with: git fetch && git checkout <track-branch> && git pull --ff-only

CURRENT STATE
<what exists>. Any WIP from interrupted agents: re-read it, do not trust it.

SCOPE
Own these files/dirs: <list>. Do NOT touch: <list, including files of other tracks>.
Shared contract to preserve: <types, API shapes, file formats>.
Shared files owned by ANOTHER track (never edit; send fragments to your lead instead): <i18n JSON, lint baseline, lockfile, generated types, shared primitives, central config>.

DÉLÉGATION : règle 6 du §0b du skill /cloud (.claude/skills/cloud/SKILL.md, ~/.claude/skills/cloud/SKILL.md, ou cloud-SKILL.md de la branche handoff), à lire, pas à recopier. Orchestrateur : <session id de l'Orchestrateur>. PARENT : <session id de la session qui crée celle-ci>.

DEFAULT DECISIONS (apply, record each one used in status.md, escalate only real owner decisions or contradictions)
<PR shape; naming; scope edges; what to do when blocked; environment-only failures to ignore once proven on BASE>

PROJECT RULES TO READ FIRST
Read in full before coding: <CLAUDE.md sections, docs paths>. If a doc lives on a notes branch:
git show origin/notes/<topic>:<name>

TDD
Write or update the failing test first, then the code, then run the tests.

CHECKPOINTS
After each logical step and at most every 20 min:
git add -A && git commit -m "wip(<track>): checkpoint <what>" && git push --no-verify origin HEAD:<track-branch>
Never stage .env* or secrets, and never write them in status.md or any notes branch.

ENV SETUP (detected from the repo)
Node <version from CI/.nvmrc>, package manager <from packageManager field>, install with the lockfile (<command>).
Known blocked CDN / download workarounds: <list or "none">.
Tools not available in the cloud (Docker, local MCP servers, Playwright browsers…): write the tests anyway and mark them "not run" in the report.

QUALITY GATE BEFORE THE FINAL PUSH
Run the repo's own scripts: <typecheck>, <lint>, <unit tests>, <build>. All must pass or be reported with the exact failure.

FINAL HISTORY (no rewrite of pushed history: --force and --force-with-lease are denied by the repo settings)
git switch -c <track-branch>-final <BASE-sha> && git merge --squash <track-branch>, then atomic Conventional Commits (feat:, fix:, refactor:, docs:, test:, chore:), one logical change each. Commit bodies cite the project rules applied. End each message with:
Co-Authored-By: Claude <noreply@anthropic.com>
Push with: git push -u origin <track-branch>-final   (no --force, no --no-verify for the final push); report <track-branch>-final as the branch to review and merge.

FORBIDDEN
Any production write (migration, SQL that writes to a production database, deploy, OTA) without the founder's explicit « go » given after you showed the read-only control query result (opening a PR, merging and pushing to main or a shared base are allowed, founder decision 2026-10-29); delete tests; .skip; as any; @ts-ignore; eslint-disable. No local machine lock (lockf) in the cloud.

DEPENDENCIES (only if this track is based on another)
Track <X> (branch origin/<X>) must land <what> first. Every ~10 min: git fetch origin <X> && git log --oneline <old-base-sha>..origin/<X> | grep -i "<marker>"
Wait up to <N> hours, then: git rebase --onto origin/<X> <old-base-sha>
On timeout: checkpoint, push, stop and report.

UPWARD MESSAGE (founder rule, never end a turn silently)
PARENT: <session id of the session that creates this one>
After each turn that produced something, the FIRST line of status.md is the message, pushed with it: « MESSAGE MONTANT : INFO — <topic>/<task> : <1-3 lines>. Statut <ref> @ <sha>. »
When the task is entirely done (pushed, gates run, nothing open): « MESSAGE MONTANT : FINI, À ARCHIVER — <topic>/<task> : branche <b> @ <sha>, statut done, aucune question ouverte, rien de non poussé. »
This status line is the normal channel: it works whatever the tools (a cloud PARENT can also be woken by send_message; a local Mac PARENT cannot be reached from the cloud), and the PARENT's git watch reads it. Check once (ToolSearch select:send_message) and write « send_message: present | absent » in status. Present and no « CANAL MONTANT : statut seulement » below: also send the same line once to PARENT after the push. Refused: normal, the status line already delivered it; keep « MESSAGE MONTANT : … » unchanged (never « NON REMIS »), note « send_message: refusé, canal = statut », stop calling send_message for this session, and never ask the founder to relay.
CANAL MONTANT : <statut seulement | statut + send_message>  (parent fills it; « statut seulement » when the parent is elevated or local)

FINAL REPORT FORMAT
- Commits: sha + subject, one per line
- Files changed
- Each gate result (command, pass/fail, key output)
- Tests written but not run, and why
- Leftovers and decisions needed from the user
```

CHILD OF A LEAD (only when started by a lead): push status.md ('started') to notes/<topic>-<track>-status as your VERY FIRST action, then at each milestone (same plumbing as the lead prompt, including the guard `[ -n "${C}" ] && git cat-file -e "${C}^{commit}" || { echo "plumbing failed, nothing pushed"; exit 1; }` before the push; never push a refspec with an empty source, an empty ${C} deletes the remote branch), read answers on notes/<topic>-<track>-answers, talk only to your lead, and send it the UPWARD MESSAGE (INFO or FINI, À ARCHIVER) at the end of every productive turn.

`background` field of `start_session`: at least 80 characters, saying why the track exists, what it unblocks and what must not break (the app shows it as the session's context).
