# Codex native runtime

This adapter retains the shared Sisyphus orchestration contract without
claiming Claude Code tools, agent names, models, hooks, or subscription
behavior. Use the collaboration and filesystem tools actually available in the
current Codex session; do not call external model APIs for this skill.

## Dispatch and ownership

1. Establish the requested outcome, repository instructions, allowed side
   effects, acceptance checks, and non-goals.
2. Split only independent work into tracks. Each writing brief must name the
   exact files or non-overlapping symbols it owns, relevant invariants, and its
   verification command. A shared file needs a single assigned writer until a
   handoff is explicit.
3. Use the native collaboration tool and only roles that it exposes. Do not
   invent OmO or Claude specialist identities when they are unavailable.
4. Dispatch disjoint writers together when the current harness has capacity.
   This skill imposes no single-writer or delegation-depth policy; actual
   concurrency, permissions, and available roles are runtime constraints.
5. The lead is the final integration owner. After writers return, inspect the
   combined diff and affected dependencies, resolve only integration issues
   within the authorized scope, and run targeted deterministic checks. Treat
   agent claims as evidence to verify, not proof.

## Lenses

Read `SKILL_DIR/runtime/lenses.md`: it lists the user's seven prompts kept as
lenses in `SKILL_DIR/lenses/` and when each one applies. The triggers hold in
Codex too. Map each "who applies it" role to the closest native role available
here (an explorer for `metis`/`oracle`, a worker for the executors, a reviewer
for the verifier), name the lens with its absolute path in that brief, and
apply `deeper-brief` and `heist-crew` yourself. Without subagents, run the
lens phases yourself.

## Review and completion

For material changes, use an independent available reviewer after integration.
If reviewed artifacts or relevant dependencies change afterward, revalidate the
affected scope. Preserve unrelated concurrent changes. Return the outcome,
changed paths, exact verification results, and remaining uncertainty.

Codex permissions and repository instructions override this adapter. Do not
commit, push, deploy, or broaden authorization merely because Sisyphus is in
use.
