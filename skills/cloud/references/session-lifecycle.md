# Session lifecycle: continue, hand over, archive

Summary lives in `SKILL.md` §8. This file holds the full rules and formats.

## Decision per session

- **Continue** when ALL hold: it owns the branch/files of the new work; `<branch>` head is still its own last push; same topic; same task or a follow-up on its own leftovers. How: the user reopens it (or SendMessage if reachable) with a follow-up brief that includes the current branch sha.
- **New lead (next phase)** when the topic enters its next phase (build, review and validate, release preparation), the old conversation is unreachable or no longer owns the branch, or other agents changed the branch since its last push. Re-derive leftovers from commits and `notes/<topic>-status`, put them in the new brief, then list the old conversation for archiving.
- **Archive** when any one holds: topic or phase finished and the next phase has its own lead; branch merged or taken over; it reported done and leftovers were transferred; a newer session supersedes it; it moved to the cloud (local copy).
- **Keep** when it is running, owns a branch nobody else touches, or waits on an owner decision.
- **Never archive with uncommitted or unpushed work**: branch head must equal the last reported sha. Archiving is reversible for the conversation, but `archive_session` removes the session's worktree by default.
- **One writer per branch.** A superseded session is archived first, or at least told to stop.

## Who archives what

| Session | Archived by | Condition |
| --- | --- | --- |
| Child cloud session created by a lead | that lead (if it has an archive tool) | work merged/integrated into `<topic>/integration`, child status done, no leftovers |
| Child session, lead has no tool | nobody yet | lead writes `CANNOT ARCHIVE (tool unavailable)` and lists it for the conductor |
| Sous-orchestrateur (lead) created by the Orchestrateur | the Orchestrateur, by itself, no prior OK (`SKILL.md` §0b rule 5) | phase done, branch pushed (head = last reported sha), final status published, no open question or pending founder decision for that topic |
| Lead, Orchestrateur has no tool | nobody yet | Orchestrateur records `CANNOT ARCHIVE (tool unavailable)` and puts it in the founder's table |
| Sessions the Orchestrateur did not create (earlier conductor, older sessions, another chantier) | the user, via the conductor's table, or the conductor after the user agrees | listed under "SESSIONS TO ARCHIVE OR CONTINUE" |
| Local session | conductor with `archive_session` | after the user agrees; reversible for the conversation, but it removes the session's worktree by default, so never with uncommitted or unpushed work |
| Orchestrateur | the founder | end of chantier |

A lead never assumes a session was archived: it records `ARCHIVED (evidence: tool result or session state)` or `CANNOT ARCHIVE (tool unavailable)`.

## status.md block (lead, per child)

```
## CHILD SESSIONS
| child | track | branch | head sha | state | merged into integration | archive |
| <name/link> | <track> | <branch> | <sha> | done / running / blocked | yes (<merge sha>) / no | ARCHIVED (<evidence>) / CANNOT ARCHIVE (tool unavailable) / KEEP (<reason>) |

## SESSIONS TO ARCHIVE OR CONTINUE   (sessions this lead did NOT create)
- <session/link>, branch <b>, last sha <sha>: archive | continue because <reason>
```

## Conductor table for the user (French)

It lists what was archived at this milestone (`ARCHIVED`) and what is left. Archiving deletes no commits, but it does remove the worktree. Merge the lead's `CANNOT ARCHIVE` rows and its "SESSIONS TO ARCHIVE OR CONTINUE" list with the conductor's own inventory, into ONE table:

| Session | Action (Garder / Archiver / Continuer) | Raison | Lien | Où |
| --- | --- | --- | --- | --- |
| <name> | Archiver | travail fusionné, aucun reste | <claude.ai/code/session_…> | claude.ai/code, ou menu « … » de la barre latérale → Archiver |

Run this check at every milestone (phase done, hand-off, merge), proactively, without waiting to be asked.

## Clean up at the end of a topic

When the topic's PR is merged or the topic is abandoned:

1. Ask the user to confirm, because it is a remote deletion. Then: `git push origin --delete notes/<topic>-status notes/<topic>-answers notes/<topic>-handoff` (and `notes/conductor-<topic>-handoff` / `-state`).
2. Delete merged track and integration branches the same way, with the user's OK.
3. Remove leftover local worktrees (`git worktree list`, then `git worktree remove <path>`).
4. Attachments on notes branches: text first. Binaries such as images only when indispensable, only the specific files, small. Never bulk-push folders: blobs stay in repo history forever.
