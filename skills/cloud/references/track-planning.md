# Track planning: shared files, track size, quota

Summary lives in `SKILL.md` §2, §5 and the preflight. Placeholders only; adapt to the repo.

## Split by files, not only by theme

1. When planning, list every shared, conflict-prone file: locale/i18n JSON, lint baselines, lockfiles, generated types, shared primitives, central config.
2. Each shared file gets ONE owner track. Cross-cutting edits to it (for example translations) go either in a single track scheduled LAST, or are written as fragments by each track and folded once by the integrator.
3. Merge as you go: each track is merged into `<topic>/integration` as soon as it passes review, so later tracks rebase onto real state, not on a stale base.
4. Lint baselines and similar generated files are regenerated or pruned after each merge, never hand-merged.

Plan table to put in `status.md`: `shared file | owner track | cross-cutting edits | when folded`.

## Fewer, bigger tracks

- Default: one cloud lead per topic, using in-session subagents.
- Child cloud sessions only for tracks that are long (more than ~1 h of work), truly independent (disjoint files) and need their own context.
- Soft cap: no more than ~5 parallel writers or children per lead, unless the files are proven disjoint. Reasons: coordination cost, merge conflicts, quota burn.

## DEFAULT DECISIONS block (every brief)

Pre-answer the predictable questions so the lead never stalls:

```
DEFAULT DECISIONS (apply, then record each one used in status.md)
- PR shape: <one PR per topic | none, branches only>
- Naming: <branch, commit and track naming rules>
- Scope edges: <what is in, what is explicitly out, how to treat adjacent findings>
- When blocked: <skip and list as owner decision | use fallback X>
- Environment-only failures: <failing checks to ignore once proven identical on BASE, with the proof command>
Escalate to the conductor only for real owner decisions or contradictions.
```

## Quota and models

- Before launching several leads or sessions (local): `/claude-usage` (skill `claude-usage`) if available, else ask the user. Fan out to what the weekly and 5-hour budgets allow; queue the rest. In the cloud quota is unknown: half the soft cap (≤2–3 parallel children), record « quota unchecked »; if quota runs out sessions stop, and the conductor lists the silent leads after reset.
- Sonnet-class subagents for read-only exploration and mechanical work; Opus for planning, review and hard fixes.
- Each lead states the model per role in its plan. This applies only to in-session `Agent` subagents; `start_session` model/effort do not apply to cloud sessions.
- Quota low: fewer parallel children, one at a time if needed.
