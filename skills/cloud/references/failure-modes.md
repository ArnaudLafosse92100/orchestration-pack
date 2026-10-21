# Failure modes and what to say (French wording for the user)

Summary lives in `SKILL.md`. Each case: symptom, action.

- **`move_to_cloud` refused.** (a) user declined: « Rien n'a été déplacé. Que souhaitez-vous faire ? ». (b) environment / GitHub / unknown id: back to SKILL.md §1, fix, call again, never `start_session`. (c) other refusal with a `hosted:true` + `fitsRepository:true` target: `start_session` a new conductor, quote the refusal, « cette conversation reste locale ».
- **`move_to_cloud` returned nothing** (sleep, network). `list_sessions`; a cloud session with the same title or branch exists: give its link, do not move again.
- **Local session kept after the move.** « Cette conversation locale reste ouverte mais inerte ; je peux l'archiver quand vous avez ouvert le lien cloud. » Archiving removes its worktree: only with nothing uncommitted or unpushed.
- **Lead silent** (status older than 45 min, or none 15 min after launch). « lead <topic> silencieux depuis <n> min : probablement « Bloquée », en attente de « Démarrer », ou quota épuisé ; ouvrez <lien> ». Record it in state.md. After a quota reset, list the silent leads to continue.
- **Lead stopped and the conductor is local.** `SendMessage` fails (« No agent named … is reachable ») and git answers are not read by a stopped session. Say: « Je ne peux pas relancer une session cloud depuis cette conversation locale : ouvrez « <titre> » (barre latérale ou claude.ai/code) et envoyez « continue », en Mode « Auto » si elle affiche « Bloquée » ou « Démarrer ». » Before saying it, check its track branches: it may have pushed its final commits and stopped before its final status.
- **Usage limit hit (HTTP 429).** It stops every session of the account at once (conductor, leads, local agents). After the reset: resume local agents with SendMessage, push a dated « resume » note on each `notes/<topic>-answers`, and ask the user to send « continue » to each silent cloud lead.
- **zsh pitfalls in plumbing.** `"$G:refs/heads/x"` applies the `:r` modifier (write `"${G}:refs/heads/x"`); `${P:+-p $P}` is passed as ONE word (`-p sha`) and `git commit-tree` rejects it: pass `-p "${P}"` explicitly. Keep answers history by adding `-p "$(git rev-parse origin/notes/<topic>-answers)"`.
- **Quota unknown in the cloud.** `claude-usage` is local-only. Use half the soft cap (≤2–3 parallel children), write « quota unchecked » in state.md.
- **Core of the work needs prod, DB, Stripe, local MCP or Keychain secrets.** Do not move. Explain in French, propose Mode A: cloud tracks for code only, the rest stays local. Never put secrets or `.env` content in a brief, in `background` or on a notes branch (repo history keeps them forever).
- **Large or private files** (zips, exports, assets). Not on notes branches. Mode A locally, or list under LOCAL CHECKS OWED.
- **Notes push rejected** (branch protection, rules). Do not try other names. Tell the user which ref was rejected and why; the channels are down until they fix it.
- **Topic name already used.** `git ls-remote origin "refs/heads/notes/<topic>-*"` non-empty: pick another slug. Never `--force` a handoff branch that exists and is not yours.
- **Empty `${C}` after plumbing.** The guard prints « plumbing failed, nothing pushed » and exits. An empty source in a refspec deletes the remote branch, so never skip the guard.
- **No watch tool.** Neither `Monitor` nor `run_in_background` available: say in French that monitoring stops when the turn ends and that the user must send « continue ».
- **`start_session` unavailable in a cloud session.** Do the topic in-session with `Agent` subagents and say so.
- **claude.ai shows no sessions.** Check it is signed in to the same account as the desktop app.
- **Status push stalls on a permission prompt in Auto mode (2026-10-21).** Cause: the push named its destination through a variable (`"${C}:refs/heads/${B}"`); allow rules match the command TEXT, so `refs/heads/notes/*` never matched. Fix: write every push destination literally (`refs/heads/notes/<topic>-status`). Same for any rule: a variable in the matched part of a command defeats it.
