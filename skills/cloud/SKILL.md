---
name: cloud
description: "Run heavy multi-topic work as Claude Code cloud sessions (the conductor is itself a cloud session; ONE cloud lead per independent topic orchestrates its own subagents; fallback: fan-out of per-track sessions) so it survives the Mac going to sleep or off, with preflight, self-contained briefs, local-to-cloud moves and branch monitoring. Invoking /cloud in any conversation hands it over to the cloud as conductor. Use when the user invokes /cloud, or says 'lance ça dans le cloud', 'fais-le tourner sur le cloud', 'le Mac va se couper', 'multi-agents en cloud', 'relancer en cloud', 'basculer les sessions dans le cloud', 'orchestrateur cloud', 'mets ça en cloud', 'sessions cloud'."
---

# /cloud — cloud conductor plus one cloud lead per topic

Facts below come from a real incident (2026-10-20). Treat them as rules. Detail for edge cases: `references/failure-modes.md`.

## 0. Default flow: /cloud = takeover

Invoking /cloud in ANY conversation is the user's request to move the session (`move_to_cloud`): this conversation becomes the cloud conductor, which creates one lead per topic; leads create their children and subagents. Follow at once when invoked locally:

0. Gate. `get_session("self")`: `isRemote: true` means already in the cloud: skip steps 3 and 4 (step 2 still writes `state.md`; the pack question is the §2 « Pack check »). If this conversation already called `move_to_cloud`, or `list_sessions` shows a cloud session with this title or branch, give its link and stop. Never create a second conductor without the user's explicit OK. A subagent never moves or starts sessions: return « lancez /cloud dans la conversation principale ». **Trivial request** (one small topic, under ~1 h): no leads, no pack; write `state.md`, run `move_to_cloud`, the cloud session does the work itself.
1. Preflight as in §1: hosted environment, repo on GitHub, base branches pushed, quota.
2. Capture the conversation into `notes/conductor-<topic>-state/state.md` (template: `references/conductor-in-cloud.md`): `<topic>` = short slug (e.g. `home-v2-fix`); `git ls-remote origin "refs/heads/notes/conductor-<topic>-*"` must be empty. If non-empty and the existing state is the same work, ask the user in French whether to reuse it; otherwise pick another slug. Content: goal in the user's words, decisions, done/remaining work as topics with phases, branches + shas, owner decisions pending, LOCAL CHECKS OWED, links to running sessions. Non-trivial work: copy any plan or memory files (text only) next to `state.md`, with the §2 plumbing. Run the §2 « Pack check »: publish `notes/conductor-<topic>-handoff` only for a base branch without the pack.
3. Lose nothing the cloud needs. Commit the session's own work; if the branch is main or a shared base, first `git switch -c cloud/<topic>-wip`. Push with `git push -u origin HEAD`; if the pre-push hook rejects it, checkpoint with `--no-verify` to `cloud/<topic>-wip` and say so in French. `state.md` lists only shas confirmed via `git ls-remote`; anything still local goes under LOCAL CHECKS OWED. Untracked or ignored files (`.omo/`, `tmp/`) and changes this session did not make are NEVER a reason to start a new conductor: leave them alone. Large or private files (zips, exports, assets) never go on notes branches: Mode A locally, or LOCAL CHECKS OWED.
4. Call `move_to_cloud` with `environment_id` (§1), `skip_push: true` and a summary of at most 4000 characters. **Trivial request: no handoff branch; the summary only says `git fetch origin notes/conductor-<topic>-state:refs/remotes/origin/notes/conductor-<topic>-state && git show origin/notes/conductor-<topic>-state:state.md`, then do the work.** Otherwise the summary says: /cloud and /sisyphus are in the repo's `.claude/skills/` (vendored by `sync.sh`), so run /cloud (if the session does not list it, read `.claude/skills/cloud/SKILL.md`); read `git fetch origin notes/conductor-<topic>-state:refs/remotes/origin/notes/conductor-<topic>-state && git show origin/notes/conductor-<topic>-state:state.md`, then follow §5a/§5b. Only when the moved branch has no `.claude/skills/cloud/` (§2 « Pack check ») does it give the handoff instead: `git fetch origin notes/conductor-<topic>-handoff:refs/remotes/origin/notes/conductor-<topic>-handoff && git show origin/notes/conductor-<topic>-handoff:cloud-SKILL.md`. One French line with the cloud link, then stop working locally.
   - Refusal (a) the user declined: stop, say in French that nothing moved, ask what they want.
   - Refusal (b) environment / GitHub / unknown-id: go back to §1, fix, call `move_to_cloud` again. NEVER `start_session`.
   - Refusal (c) any other, while §1 shows a `hosted:true`, `fitsRepository:true` environment: only then `start_session` a new conductor, quote the refusal in French, say this conversation stays local and this local conversation does not conduct or launch leads. The new conductor's prompt is the move summary (same fetch/show commands), and `background` is ≥80 chars.
   - After the move: if the result says this session is kept, tell the user in French that this local conversation stays open and is inert, and offer to archive it once they have opened the cloud link. If `move_to_cloud` returned no result (sleep, network), `list_sessions` first for a cloud session with the same title or branch; if one exists, give its link and do not move again.
   - Why move: a moved conversation launches its leads FROM the cloud (a cloud lead started 5 children with no « Démarrer » click); a locally started conductor costs one click per session and leaves two conversations.
5. In the cloud the conductor plans the topics, starts ONE lead per topic (§2/§5: contract prompt + DEFAULT DECISIONS), tells the user in French to click « Démarrer » only if the app asks (broadest permission mode), runs §5b and updates its state branch.

## 0b. Founder organisation rules (decisions 2026-10-21) — apply on EVERY /cloud run

These rules sit on top of the Sisyphus behaviour (router/lead/lenses, contract): Sisyphus says HOW each conversation works (intent gate, parallel explore, plan + momus gate, writers, fresh cross-review, evidence); this section says how conversations are NAMED, PLACED, SIZED, MODELLED, ARCHIVED and how open decisions are ARBITRATED.

### 1. Ask first: where does the Orchestrateur live? (one question, in French, before any launch)
« Orchestrateur sur le Mac (sessions rangées sous lui dans la barre latérale, mais il se met en pause quand le Mac dort) ou dans le cloud (jamais de pause, mais liste à plat) ? »
- Mac: the Orchestrateur is a LOCAL desktop-app conversation; it launches each Sous-orchestrateur as a CLOUD session with the desktop app's own session-start tool (`start_session`, target cloud), which the app nests under it. It does NOT `move_to_cloud` itself.
- Cloud: the Orchestrateur is a cloud session (`move_to_cloud`, §0/§5a); it creates Sous-orchestrateurs with `create_session` (claude-code-remote). Fact observed 2026-10-21: the server records `parent_session_id`, but the sidebar does NOT nest sessions created this way; only sessions started by the desktop app from a desktop conversation are nested. Sessions created by any cloud session (Pistes included) always show flat: names carry the hierarchy.

### 2. Three levels, fixed names
- `Orchestrateur — <chantier>`: exactly ONE per chantier; new topics go under it, never a second one. Rename with `set_session_title` if needed.
- `Sous-orchestrateur — <topic> (<phase or 2-3 words>)`: one per topic and phase, created BY the Orchestrateur.
- `Piste — <topic>/<task>`: atomic sessions created BY a Sous-orchestrateur.
Titles under 60 characters. Check `parent_session_id` after each launch; fix drifting titles.

### 3. Atomic Pistes by default (founder choice: "je vois tout, même si ça consomme plus de quota")
- A Sous-orchestrateur splits its plan into small independent tasks and gives EACH its own `Piste` cloud session (writer), plus a separate fresh `Piste — <topic>/relecture-<task>` for its review (writing and reviewing never share a conversation). In-session `Agent` subagents remain for read-only exploration and quick checks.
- At most 3-5 Pistes running at once per Sous-orchestrateur (shared 5-hour quota: a lead hit it on 2026-10-20); start the next one when one finishes. Each Piste has its own branch off the topic integration branch, pushes `notes/<topic>-<task>-status`, reads `notes/<topic>-<task>-answers`.

### 4. Model per role (create_session `model`, Agent `model`)
| Role | Model |
|---|---|
| Orchestrateur | Sonnet 5.5 (monitor, relay, summarise, arbitrate with a fresh Opus subagent when the decision is hard) |
| Sous-orchestrateur | Opus 5.5 (plan, momus gate, review judgement, doctrine) |
| Piste writing delicate domain code (doctrine, state contracts, closing logic) | Opus 5.5 |
| Piste mechanical (docs, renames, running bench/tests, reports, data plumbing) | Haiku 5.5 or Sonnet 5.5 |
| Piste review (fresh, independent) | Opus 5.5 |
| In-session read-only explorers / context readers | Haiku 5.5 (return conclusions, not dumps) |
A session's model is fixed at creation: "read context cheaply first" is done by a Haiku subagent inside the session, never by switching the session's model. Haiku never takes a doctrine decision. If a launch tool has no model field, record "model: session default" in state.md.

### 5. Archiving is mandatory and coherent
An archived session can no longer receive a message, so archive only what will never need a downward answer.
| Who | Archives | Only when | Never when |
|---|---|---|---|
| Sous-orchestrateur | its Pistes | work pushed (branch head = last reported sha), reviewed, merged into the topic integration branch, status done, no open question | waiting for an answer, failed without a decision, unpushed work |
| Orchestrateur | its Sous-orchestrateurs | phase done, branch pushed, final status published, no open question or pending founder decision for that topic | an answer may still have to go down to it |
| Founder | the Orchestrateur | end of chantier | — |
- A later answer for an archived topic goes to a NEW session of the next phase, never to an archived one.
- Every archive is recorded with evidence (`ARCHIVED (sha, status done, tool result)`); `CANNOT ARCHIVE (tool unavailable)` otherwise. The Orchestrateur shows the founder the archive table at each milestone and at the end.
- Archive at each milestone, not only at the end (observed 2026-10-21: 26 finished sessions of one project left open).
- Who actually has the tool (observed 2026-10-21): a cloud session the founder started (claude.ai/code, or a `/cloud` takeover) has `archive_session`, `create_session` and `send_message`; sessions created by `create_session` (Sous-orchestrateurs, Pistes) had none of them. So a Sous-orchestrateur usually records `CANNOT ARCHIVE (tool unavailable)` for its Pistes and lists them as `À ARCHIVER` in its status, and the Orchestrateur archives them when rule 5 holds, with the same evidence. A Mac Orchestrateur archives only if its desktop tools offer an archive tool; otherwise the founder's table.

### 5bis. Upward message when a turn ends (founder decision 2026-10-21)
Every Sous-orchestrateur and every Piste messages its PARENT session as soon as it finishes a turn that produced something, and always when its task is entirely done. Never end silently.
1. The message is the FIRST line of `status.md`, pushed with it: `MESSAGE MONTANT : <line of step 2>`. This is the normal path. It works whatever the tools: the parent's §4 watch fires on the status head change and reads that line (§5b step 1). Some sessions may lack `send_message` (one observed on 2026-10-21, while verif-104 had it, item 5): no `send_message` is not an error, no warning, nothing else to do.
   - Check once per session whether `send_message` (claude-code-remote) exists (ToolSearch `select:send_message`) and write the result in status (`send_message: present | absent`). Present: after the push, also send the same line to the parent session id given in the brief (`PARENT: <session id>`): Piste → its Sous-orchestrateur, Sous-orchestrateur → the Orchestrateur. It wakes the parent sooner; the status line stays the record.
2. Exactly one of two kinds, first word fixed:
   - `INFO — <topic>/<task> : <1-3 lines: new fact, milestone, question or blocker>. Statut notes/<…>-status @ <sha>.`
   - `FINI, À ARCHIVER — <topic>/<task> : branche <branch> @ <sha>, statut done, aucune question ouverte, rien de non poussé.` Only when the rule 5 archive conditions hold on the sender's side; otherwise send INFO with what is left.
3. The parent never trusts the message: it reads the rest of the status. On FINI it checks the rule 5 conditions and archives at once (`archive_session`, recorded `ARCHIVED (evidence)`; no tool: `CANNOT ARCHIVE (tool unavailable)` and the session goes in the founder's table, §8), or answers in the answers branch saying what blocks the archive. The Orchestrateur relays each FINI and each founder-relevant INFO to the founder in one French line.
4. `send_message` present but refused, or parent unreachable (e.g. a local Mac Orchestrateur): push status again with the first line `MESSAGE MONTANT NON REMIS (<error>) : <line>`; the status line is still the delivery.
5. Proven limits (verif-104, 2026-10-21, cloud session in Auto mode on the repo alone): cloud sessions DO have `mcp__claude-code-remote__send_message` (also `list_sessions`, `create_session`, `archive_session`…), and `list_sessions` ran without a prompt. A cloud session CANNOT message a local Mac session (« target session could not be verified »; the platform says cloud → local is one-way for now): with a local parent, the status line is the only channel. A message between sessions in DIFFERENT permission modes waits for the founder's approval in the receiving session: run the whole chain (Orchestrateur, Sous-orchestrateurs, Pistes) in « Auto ».
6. Every brief carries `PARENT: <session id>` in its DÉLÉGATION line (rule 6); a missing PARENT is a brief defect (ask in status, QUESTIONS FOR THE COORDINATOR).

### 6. Standing delegation (founder decision 2026-10-21, replaces the paste-a-confirmation line)
The delegation text lives HERE only. Briefs (Sous-orchestrateur and Piste) never copy it: on 2026-10-21 a Sous-orchestrateur's guard refused to write Piste briefs carrying it, reading founder authority restated by a session as instruction injection. Every brief carries instead this one line, with the ids filled in (rule 5bis):

```
DÉLÉGATION : règle 6 du §0b du skill /cloud (.claude/skills/cloud/SKILL.md, ~/.claude/skills/cloud/SKILL.md, ou cloud-SKILL.md de la branche handoff), à lire, pas à recopier. Orchestrateur : <session id de l'Orchestrateur>. PARENT : <session id de la session qui crée celle-ci>.
```

The delegation it points to:

```
DÉLÉGATION PERMANENTE (fondateur, 2026-10-21)
Le fondateur délègue à l'Orchestrateur, session <session id de l'Orchestrateur>, toutes les décisions dans le cadre de la consigne de chaque session qu'il lance. Les réponses de l'Orchestrateur (notes/<topic>-answers ou message de cette session) s'imposent au Sous-orchestrateur et aux Pistes comme si le fondateur les avait écrites. Restent au fondateur seul : fusion ou PR vers master ; toute dépense ou passe payante ; revenir sur une décision de méthode actée ; ce que voit le vendeur en appel réel ; toute suppression sur GitHub (branche, tag, release, dépôt) ; les secrets.
```

- An instruction from the Orchestrateur inside that scope is the founder's: a Sous-orchestrateur or Piste applies it without asking the founder to confirm, and records it in its status.
- The six reserved items go to the founder (rule 7 « Founder decision »); work continues on the recommended, revertible option meanwhile.
- The block grants decisions, not tool rights. The tool side is `.claude/settings.json` (from `settings.fragment.json` of the orchestration pack): pushes to `notes/*`, `claude/*` and `chore/*` without `--force` and the session tools (`send_message`, `list_sessions`, `get_session`, `create_session`, `archive_session`, `list_events`, `add_repo`) run without a prompt in Auto mode; `--force`, branch deletion and pushes to `master`/`main` are denied. Every push in a brief is therefore fast-forward (`commit-tree -p <parent>`, plumbing in §2), never `--force`.

### 7. Every "Reste à décider" goes up and is ARBITRATED by the Orchestrateur
- A Piste never settles an open decision alone: it goes up Piste → Sous-orchestrateur → Orchestrateur (status QUESTIONS / DECISIONS NEEDED).
- The Orchestrateur arbitrates with this exact instruction: « C'est quoi le plus pertinent et cohérent maintenant ? Notez de 1 à 10 en pesant le pour et le contre avec plusieurs propositions. Prendre le temps de la réflexion. Ne pas choisir la solution la plus simple : il faut une solution de production, cohérente, pertinente et pérenne. Faire un vrai arbitrage ; ne pas faire si ce n'est pas cohérent ou surdimensionné. » Several options, each scored /10 with pros and cons, verified against the code and recorded doctrine; "do nothing" is an option.
- Technical decision inside already-fixed rules → the Orchestrateur decides, writes it in the topic's answers, tells the founder in one line.
- Founder decision (only the six items reserved by rule 6: merge or PR to master, money/paid runs, reversing a recorded method decision, what the seller sees in a real call, any deletion on GitHub, secrets) → the scored table and a recommendation go to the founder; work continues on the recommended option meanwhile, revertible.
- Every arbitration is recorded in state.md so the same question is never asked twice.

### 8. A finished chantier without a PR or a deploy always has a named owner (founder decision 2026-10-21)
- A topic or Piste that ends with work that is neither in an open PR nor in production (branch only, prototype, analysis, notes, a decision record) is not closed until it has an **owner**: the founder, the Orchestrateur, or a named session that will act next.
- Its final status and state.md carry one line: `PROPRIÉTAIRE : <qui> — PROCHAINE ACTION : <quoi> — OÙ : <branche@sha ou fichier>`. « personne », « à voir » or an empty owner is not allowed; when nobody will act, the owner is the founder and the next action says « décider : garder, ouvrir une PR ou supprimer ».
- The Orchestrateur checks this line before archiving (rule 5) and lists every owned item in the archive table it shows the founder, so no finished work is left on an orphan branch.

## 1. Preflight (always first)

1. `mcp__ccd_session__list_start_targets` (ToolSearch if deferred), read `cloud`. If `available: false`, act on `reason`: `not_on_screen` → ask the user to bring this conversation on screen and retry; `no_github_remote` / `no_readable_git_checkout` → stop and explain in French, no move, no fallback. Otherwise pick a target with `hosted: true` + `fitsRepository: true`; several fit → `isDefault`, else ask. Pass its id as `environment_id` to `move_to_cloud`.
2. **No hosted environment: do NOT call `start_session` with `target: "cloud"`.** The app turns it into a card whose click starts a LOCAL session (10 "cloud" sessions once ran locally and OOM-killed `tsc`). Stop and tell the user, in French, to create an environment once: desktop Code tab → New session → "Local" selector → Cloud → add environment; or claude.ai/code environment selector. Same Claude account as the desktop app (if claude.ai shows no sessions, check the account first), GitHub connected with the repo accessible, network "Trusted" or wider, no secrets in env vars. Then re-run `list_start_targets`.
3. The repo is on GitHub (`git remote -v`) and every base branch is pushed (`git ls-remote --heads origin <branch>`). Mode A: also each track branch; mode B: the lead creates them.
4. **Quota.** Local: `claude-usage` skill, else ask. Size fan-out to the remaining weekly and 5-hour budget. In the cloud quota is unknown (`claude-usage` is local-only): use half the soft cap (≤2–3 parallel children) and record « quota unchecked » in state.md. If quota runs out mid-run, sessions stop; on reset, §5b step 0 lists the silent leads to continue. Models per role: `references/track-planning.md`.
5. **Fit, and its price.** If the core of the work needs the Mac (prod DB writes, deploys, Stripe, the iOS Simulator, an interactive EAS/Apple login, local MCP servers, Keychain secrets), do not move: explain in French and propose Mode A (cloud tracks for code only, the rest local). **Say the price up front, in French, before launching** (§5a « Placement »): a LOCAL conductor cannot message the cloud sessions it starts, so every stopped lead (quota, « Bloquée », « Démarrer ») needs the user's own click to resume. Never put secrets or `.env` content in a brief, in `background` or on notes branches: they live in repo history forever.

## 2. Launching tracks

Mode B: one `start_session` per TOPIC (brief = lead prompt of the contract). Mode A (fallback): one per track. If `start_session` is unavailable in a cloud session, do the topic in-session with `Agent` subagents and say so.

- **Plan by files, not only by theme.** Shared, conflict-prone files (i18n JSON, lint baselines, lockfiles, generated types, shared primitives, central config) get ONE owner track; cross-cutting edits go in a single LAST track or as fragments folded once. Merge each track into the integration branch as soon as it passes review; regenerate lint baselines, never hand-merge. `references/track-planning.md`.
- One `start_session` per independent track, disjoint files: `target: "cloud"`, `environment`, `initiation: "user_asked"` (only when the user asked; otherwise ask the user first, because proposal cards cannot carry `environment`), `name`, `title` (<60 chars), `prompt`, `background` (≥80 chars, see template). Each track has its own branch, pushed before launch; the brief starts with `git fetch && git checkout <branch> && git pull --ff-only`.
- **Isolation.** Before using a lead topic, `git ls-remote origin "refs/heads/notes/<topic>-*"` must be empty, else pick another slug. No `--force` on a handoff branch that already exists and is not yours (only refresh branches listed in your state.md).
- Cloud sessions CANNOT see local untracked or ignored files. Every brief is self-contained inline.
- **Never push a refspec with an empty source: an empty `${C}` deletes the remote branch.** Every plumbing push is preceded by the guard line below. A notes push rejected by protection or rules: do not loop over other names; tell the user in French which ref was rejected and why (channels are then down).
- Reference docs go to a notes branch without touching the working tree; sessions read `git show origin/notes/<topic>:<name>`:

  ```bash
  P=$(git hash-object -w <file>); T=$(printf "100644 blob %s\t<name>\n" "${P}" | git mktree)
  C=$(echo "docs(notes): … (reference for cloud sessions, never merged)" | git commit-tree "${T}")
  [ -n "${C}" ] && git cat-file -e "${C}^{commit}" || { echo "plumbing failed, nothing pushed"; exit 1; }
  git push --no-verify origin "${C}:refs/heads/notes/<topic>"
  ```

  zsh: write `${C}`, never `$C:` (`:r` is a modifier). `--no-verify`: the pre-push hook checks the main checkout, unrelated to a docs-only ref.
- **Pack check (conductor, before any lead).** Each project repo carries the bootstrap of `ArnaudLafosse92100/orchestration-pack` in `.claude/settings.json` (`sync.sh --bootstrap`): at session start it installs `/cloud`, `/sisyphus`, the agents and the hooks into `~/.claude`, and the repo settings register the hooks. For each base branch a lead will start from:

  ```bash
  git fetch origin <base> && git show "origin/<base>:.claude/settings.json" | grep -q "orchestration-pack" && echo "pack bootstrapped"
  ```

  Bootstrapped (the normal case): no handoff branch; the lead brief uses the « pack in the session » line of the contract. Not bootstrapped (a branch cut before the bootstrap, e.g. the lot): run `sync.sh --bootstrap` on that branch if the topic may change `.claude/`; otherwise publish the handoff below.
- **Publish the handoff ONCE, only for a base without the pack, to `notes/conductor-<topic>-handoff`.** It carries the Sisyphus runtime AND this skill: `cloud-SKILL.md`, every `references/*.md` as `cloud-<name>`, router/lead/lenses, `lens-*`, the contract. Built from the blobs of a branch that has the pack (`SRC`, usually `origin/master`), so it works from a cloud session too, with no local paths:

  ```bash
  SRC=origin/master; git fetch origin master; S=.claude/skills/sisyphus; K=.claude/skills/cloud; L=""
  add() { H=$(git rev-parse --verify -q "${SRC}:$1") && L="${L}100644 blob ${H}\t$2\n" || { echo "missing $1 in ${SRC}"; exit 1; }; }
  add "$S/runtime/router.md" router.md; add "$S/runtime/lead.md" lead.md; add "$S/runtime/lenses.md" lenses.md
  add "$K/SKILL.md" cloud-SKILL.md
  for b in $(git ls-tree --name-only "${SRC}:$K/references/"); do case "$b" in cloud-*) n="$b";; *) n="cloud-$b";; esac; add "$K/references/$b" "$n"; done
  for b in $(git ls-tree --name-only "${SRC}:$S/lenses/"); do add "$S/lenses/$b" "lens-$b"; done
  T=$(printf '%b' "$L" | git mktree); C=$(echo "docs(notes): sisyphus + cloud pack (reference, never merged)" | git commit-tree "${T}")
  [ -n "${C}" ] && git cat-file -e "${C}^{commit}" || { echo "plumbing failed, nothing pushed"; exit 1; }
  git push --no-verify origin "${C}:refs/heads/notes/conductor-<topic>-handoff"
  ```

  Refresh of your own branch: fast-forward, never `--force` (denied by the pack settings): fetch it, `PARENT=$(git rev-parse --verify -q refs/remotes/origin/notes/conductor-<topic>-handoff)`, and build `C` with `git commit-tree "${T}" -p "${PARENT}"`. **Per lead, the cloud conductor copies it server-side, no local paths:**

  ```bash
  git fetch origin notes/conductor-<topic>-handoff:refs/remotes/origin/notes/conductor-<topic>-handoff && git push --no-verify origin "refs/remotes/origin/notes/conductor-<topic>-handoff:refs/heads/notes/<lead-topic>-handoff"
  ```

  With a handoff, the lead brief says: read `git show origin/notes/<lead-topic>-handoff:<file>` for each file first (`cloud-brief-template.md` etc. are there too), then follow the contract; where `router.md`/`lead.md` name OmO agents or tools, use its mapping.
- Briefs from `references/brief-template.md`. The lead prompt says: « push status.md as your VERY FIRST action ('started') ».
- Dependent tracks: Y based on X polls `git fetch` every ~10 min, waits up to N hours, then `git rebase --onto origin/<X> <old-base-sha>`; on timeout it checkpoints and stops.
- Quota-limited surfaces (Artifact publishes): copy the `artifact-publish-batching` rule into any brief that publishes.

## 3. Moving existing LOCAL sessions to the cloud

1. `mcp__ccd_session_mgmt__send_message` (or SendMessage with the `local_…` id) asking the session to: commit its own work (if on main or a shared base, first `git switch -c cloud/<topic>-wip`), run `git push -u origin HEAD` (`--no-verify` only if the pre-push hook rejects it, and say so), stop heavy local commands, then `move_to_cloud` with `environment_id` (`skip_push: true` if already pushed), a summary of remaining work and key rules. A busy session queues the message; `move_to_cloud` fails with "no cloud environment" until the preflight passes.
2. Verify with `list_events`: it must say it moved and give a `claude.ai/code/session_…` link.

## 4. Monitoring (git watch = the normal wake-up; §0b rule 5bis `send_message` wakes the parent sooner when the tool exists)

- **Isolation.** Watch ONLY the status branches of the topics listed in YOUR state.md, with an explicit `ls-remote` over those refs (substitute the topics literally; portable bash/zsh). Never answer a status you did not launch.
- **Watch guarantee.** Never end a turn without an armed watch, local or cloud conductor alike (a cloud session cannot message a local one, so this watch is how a Mac Orchestrateur hears its cloud sessions). Use `scripts/watch-status.sh` next to this file (`~/.claude/skills/cloud/` on the Mac or in a container set up by `sync.sh --cloud`, `.claude/skills/cloud/` in a repo), from a checkout of the repo, with the topics of YOUR state.md written literally. It polls one `git ls-remote` every 15 s (`WATCH_INTERVAL`), costs no model call while nothing changes, and prints one line per change with the child's `MESSAGE MONTANT` line (`STATUS <topic> @ <sha>: MESSAGE MONTANT : FINI, À ARCHIVER — …`): a message pushed by a cloud session reaches you in about 15-20 s. Last seen heads live in `.omo/watch-status.*`, so a change that lands while the watch is being re-armed is reported at the next start.
  - Preferred: Bash `run_in_background` (timeout 7200000) running `bash <dir>/scripts/watch-status.sh --once <topic1> <topic2>`; it exits at the first change, which wakes you; handle it (§5b) and start it again. At most one idle wake every 2 h.
  - Or `Monitor` (timeout 1800000) running the same command without `--once`: one notification per change, re-armed at each 30-min expiry.
  - `ERR ls-remote` (3 failed polls) or `ALERT workdir missing`: fix, then re-arm. Neither tool: say in French that monitoring stops when the turn ends and the user must send « continue ». Record « watch armed until <UTC> » in state.md.
- **Session visibility.** Try `list_sessions` / `get_session` (`isRemote`) and `ListAgents`; cloud sessions receive SendMessage but cannot reply. From a LOCAL conductor they were not listed and not reachable at all (2026-10-21, §5a « Placement »): do not promise the user you can resume them. A session you created is archived as soon as §0b rule 5 holds, without asking (§8); any other session only after the user agrees. What you cannot archive goes in the French table (§8). Transcripts: claude.ai/code.
- **Never claim a session runs in the cloud without evidence**: `get_session` → `isRemote: true`, a `list_events` move confirmation, or a ListAgents cloud row. Local worktree sessions show `isRemote: false` and a `.claude/worktrees/...` cwd.
- Report in French, with links.

## 5. Orchestration model: three levels (decision 2026-10-20)

```
cloud conductor (Sisyphus-style, light)      [optional local helper: local-only checks]
  └─ one cloud LEAD per topic and phase  (strict router: delegates, integrates, gates)
       ├─ in-session subagents (Agent tool): explorers, planner, writers, reviewers
       └─ optional CHILD cloud sessions, one per track (own branch off <topic>/integration)
```

- **Conductor = a cloud session by default; it sees only git** (§5a). Splits the request into independent **topics**, publishes the pack (§2), starts ONE lead per topic and phase (brief = prompt of `references/cloud-orchestrator-contract.md`), monitors, relays, answers, integrates. Stays light: no full suites or builds while leads run; local-only resources run in ONE optional local helper session under a machine lock, or wait in "LOCAL CHECKS OWED".
- **Each lead** behaves like Sisyphus (contract): intent gate, parallel exploration, plan critiqued by a fresh reviewer, writers on disjoint files, evidence-based verification, fresh cross-review, todo discipline. It never writes code itself. **Fewer, bigger tracks:** one lead per topic with in-session subagents is the default; child cloud sessions only for tracks over ~1 h, independent, needing their own context. Soft cap ~5 parallel writers or children per lead (half in the cloud while quota is unchecked).
- **A lead is the sub-conductor of its children**: self-contained brief per child; child pushes `notes/<topic>-<track>-status`, answers via `notes/<topic>-<track>-answers`; the lead aggregates into `notes/<topic>-status`, cross-reviews and merges into `<topic>/integration`. Children talk only to their lead.
- **Channels (git only).** Up: `notes/<topic>-status`. Down: `notes/<topic>-answers`. Leads NEVER talk to each other: cross-topic dependencies go through the conductor.
- **Phases, one lead each**: build, independent review/validation, release preparation. Writing and reviewing never share a conversation.
- **Evidence the cloud cannot see**: attach it in the answers branch, only the files needed.

**Mode B: one lead per topic (DEFAULT).** **Mode A: one session per track, steered by the conductor**, only when: the work needs local-only resources; the user wants to steer each track; or tracks exceed one session's context.

## 5a. Conductor placement (decision 2026-10-20)

Runs in the cloud so coordination does not pause when the Mac sleeps. Full rules: `references/conductor-in-cloud.md`.

- Started locally: publish state to `notes/conductor-<topic>-state` (+ copies of plan/decision files), then `move_to_cloud` BEFORE launching leads.
- New work: tell the user (French) to start in the cloud: Code tab, selector under the composer → « Cloud », or claude.ai/code. No setting changes that default.
- The cloud conductor reads `notes/conductor-<topic>-state` first and updates it at each milestone. It cannot run local-only checks: it lists them under "LOCAL CHECKS OWED" and asks the user.

### Placement: what each choice can and cannot do (observed 2026-10-21)

Facts, not assumptions:

- **A local conductor cannot reach its cloud sessions.** `ListAgents` does not list them, `SendMessage` to their `name` returns « No agent named … is reachable », and `list_sessions {"linked": true}` returns nothing. Its only channel is git (`notes/<topic>-answers`), which a lead reads ONLY while it is running.
- **A stopped lead cannot be woken from git.** Usage limit (HTTP 429, shared by EVERY session of the account: conductor, leads, local agents), « Bloquée », or a card waiting on « Démarrer »: only the user resumes it (sidebar or claude.ai/code → open it → « continue »; Mode « Auto »).
- **The cloud cannot do Mac work:** no Docker (SQL tests), often no Deno until the lead installs it, no Simulator, no interactive Apple/EAS login, no local MCP or Keychain. Those stay local or under LOCAL CHECKS OWED.
- **Not yet proven:** that a cloud conductor can `SendMessage` the sessions it started, or resume one stopped by quota. Before relying on it, test once (send a no-op message to one lead and check its status branch reacts) and record the result here.

Choose and tell the user in French, before launching:

| Setup | Use when | Price |
|---|---|---|
| **Cloud conductor** (default, `move_to_cloud`) | Work is code only | Mac-only checks wait under LOCAL CHECKS OWED; resuming a lead stopped by quota still needs the user (until the test above proves otherwise) |
| **Local conductor + cloud leads** (Mode A) | The critical path needs the Mac (deploys, Stripe, Simulator, EAS) | No message to leads at all: the user must click « continue » on each stopped lead; the conductor only reads `status.md` and pushes `answers.md` |
| **Cloud conductor for code topics + ONE local helper session for Mac work** | Both kinds of work matter | Two conversations; the local helper takes a machine lock and reports through its own status branch |

Whatever the setup: re-check every lead's status at each wake-up (§5b step 0), and when one is silent > 45 min, look at its track branches (`git for-each-ref` + `git log -1 --format=%cr`) before concluding: a lead may have pushed final commits and stopped before writing its final status.

## 5b. Conductor loop (on each status head change, and at each wake-up)

0. **Staleness.** Fetch every status ref first (`git fetch origin notes/<topic>-status:refs/remotes/origin/notes/<topic>-status` per topic). For each lead `running` in state.md: if `git log -1 --format=%ct origin/notes/<topic>-status` is older than 45 min, or there is no status 15 min after launch, check `get_session`/`list_sessions` if visible. Then tell the user in French: « lead <topic> silencieux depuis <n> min : probablement « Bloquée », en attente de « Démarrer », ou quota épuisé ; ouvrez <lien> ». Record it in state.md.
1. Read: `git fetch origin notes/<topic>-status:refs/remotes/origin/notes/<topic>-status && git show origin/notes/<topic>-status:status.md`. Never trust a chat report. A first line `MESSAGE MONTANT …` is the child's upward message (§0b rule 5bis): on `FINI, À ARCHIVER` run the step 5 lifecycle check for that session now.
2. **Verify child sessions appear in the lead's status** (branch, sha, state, ARCHIVED or CANNOT ARCHIVE). A missing child is unknown: ask in `answers.md`.
3. Relay the essentials to the user in French (topic, phase, state, blockers, owner decisions), with links.
4. Answer `answers.md` (`references/conductor-answers-template.md`), attach evidence, push to `notes/<topic>-answers`. Tell blocked leads when a dependency lands.
5. Lifecycle check (§8). Never two writers on one branch.
6. Update `notes/conductor-<topic>-state`: topics, phases, links, shas, what waits on the user, LOCAL CHECKS OWED, watch line.

## 6. After launch

Tell the user, in French and plainly: which topics (and phases) run in the cloud, how to see them (sidebar, claude.ai/code), that the lead will not be notified when they finish and checks GitHub instead, and what needs their decisions (PRs, merges, migrations, deploys).

## 7. Ping-pong protocol (decision 2026-10-20)

Cloud sessions cannot message back. Everything goes through two notes branches per topic, pushed with the §2 plumbing and guard, always fast-forward (`commit-tree -p <parent>` as in the answers template; `--force` is denied by the pack settings).

- **Status and questions.** Every lead pushes `status.md` to `notes/<topic>-status` as its very first action ('started'), at each milestone and BEFORE ending any turn. Content: goal, phase, per-track branch/sha/state, leftovers, gates, blockers, "QUESTIONS FOR THE COORDINATOR", "SESSIONS TO ARCHIVE OR CONTINUE", "NEXT PHASE PROPOSAL", owner decisions.
- **Conductor state.** `notes/conductor-<topic>-state` (one per conductor, never shared); leads do not write it.
- **Answers.** `answers.md` (+ attachments) on `notes/<topic>-answers`.
- **Autonomous leads.** Every brief carries DEFAULT DECISIONS. Leads apply them, record each one used, escalate only real owner decisions or contradictions. If the Mac sleeps, leads keep working on the defaults; the ~30 min wait applies only to questions without a default.
- **Waiting.** After pushing questions, poll `git fetch origin notes/<topic>-answers:refs/remotes/origin/notes/<topic>-answers` every ~5 min up to 30 min, keep working, apply answers. No answer: safest option, recorded.
- **No "done" with leftovers.** Fix them or list them as owner decisions.
- **Conductor side.** `Monitor`/until-loop on `git ls-remote` (§4), then §5b. Cloud transcripts are usually unreadable: `status.md` is the ONLY reliable channel.
- **Gotcha.** Proposal cards (`own_initiative`) cannot carry an `environment`. `start_session` with `environment` can fail with "could not read the user's cloud environments": retry without `environment`.
- **Auto permission mode.** Local `start_session`: `permission_mode: "auto"` (at or below the caller's mode); if refused, default and tell the user. Cloud `start_session` and `move_to_cloud` cannot set it, and a project's `.claude/settings.json` cannot either (`defaultMode: "auto"` is ignored there). An environment whose setup script runs `sync.sh --cloud` (NOUVEAU-COMPTE.md of orchestration-pack) writes it in the container's `~/.claude/settings.json`, so its sessions start in Auto: check the first status says so (`permission mode: auto`). Without that setup script, tell the user in French, once per launch batch, to pick « Mode » → « Auto (Recommandé) », so sessions don't turn « Bloquée ». A conductor that starts or moves to the cloud asks the same for itself. Every lead brief tells the lead to remind the user in its status to set Auto on each child, and to list any « Bloquée » session in status.md.
- **Permission mode is not transferred.** With a broad local mode, a cloud `start_session` is NOT started automatically ("Cette tâche n'a pas été démarrée dans le cloud…"): the user must click « Démarrer » on the card. Say so up front, in French, and advise Auto (or the broadest mode offered).

## 8. Session lifecycle: continue, hand over or archive (decision 2026-10-20)

At EVERY milestone, not only at the end. Details and the French table: `references/session-lifecycle.md`.

- **Inventory first** before any new session: memory/todo file, `git ls-remote origin 'refs/heads/notes/*'`, last commit of each track branch; cloud sessions per §4.
- **Continue** a session only if it owns the branch, the head is its own last push, same topic and task. **New lead** for the next phase, or when the old one is unreachable or the branch changed. **Keep** a running session or one waiting on the owner. **One writer per branch.**
- **A lead archives ONLY sessions it created**, once merged and done with no leftovers; it records per child `ARCHIVED (evidence)` or `CANNOT ARCHIVE (tool unavailable)`. Others go under "SESSIONS TO ARCHIVE OR CONTINUE".
- **Conductor archiving (§0b rule 5, founder decision 2026-10-21).** The Orchestrateur archives its own Sous-orchestrateurs by itself, with no prior OK, as soon as rule 5 holds: phase done, branch pushed (head = last reported sha), final status published, no open question or pending founder decision for that topic. It records `ARCHIVED (evidence)` and shows it in the milestone table. Sessions it did not create (an earlier conductor, a local session, another chantier) get `archive_session` only after the user agrees. No tool: `CANNOT ARCHIVE (tool unavailable)`. Everything not archived goes in ONE French table (Garder / Archiver / Continuer, reason, link, where). Archiving is reversible for the conversation, but `archive_session` removes the session's worktree by default: never archive with uncommitted or unpushed work.

## 9. Clean up at the end of a topic

Only after the user confirms (remote deletion): `git push origin --delete notes/<topic>-status notes/<topic>-answers notes/<topic>-handoff` (and `notes/conductor-<topic>-handoff` / `-state`; legacy unprefixed `notes/conductor-state` branches are cleanup candidates too, with the user's OK). Also delete merged track branches with the user's OK and remove leftover local worktrees. Attachments on notes branches: text first, small specific binaries only when indispensable (`references/session-lifecycle.md`).

## Known limits (keep the user's expectations honest)

- The conductor only sees what leads publish in `status.md`.
- Archiving cloud sessions may not be possible from tools.
- Every launch needs the user's « Démarrer » click when the local permission mode is broad.
- A locally run conductor pauses while the Mac sleeps; move it to the cloud.
- A locally run conductor cannot message the cloud sessions it started (§5a « Placement »): resuming a stopped lead is always the user's click.
- One usage limit for the whole account: when it is hit, the conductor, every lead and every local agent stop together; after the reset, leads do not resume by themselves.
- Permission mode can only be set programmatically for local starts.
- Cloud environments may lack Docker image pulls, browsers or DB access: those checks stay local or with the owner.

## Never

- Start a "cloud" session without a hosted environment, or claim cloud without evidence.
- Use `start_session` as a substitute for a `move_to_cloud` refusal of kind (a) or (b).
- Push a refspec with an empty source, or put secrets or `.env` content on a notes branch.
- Let a cloud session open PRs, merge, push to main or shared bases, apply migrations or deploy, unless the user explicitly asked.
- Copy this skill, or any local skill, into `~/.claude/skills` or `~/.codex/skills` as a physical folder, except through `sync.sh` of the source repo `ArnaudLafosse92100/orchestration-pack` (the single source for /cloud, /sisyphus, their agents and hooks).
