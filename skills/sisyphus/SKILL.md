---
name: sisyphus
description: Run Sisyphus/oh-my-openagent (OmO) orchestration in Claude Code or Codex. Use only when the user explicitly asks for Sisyphus/OmO orchestration, parallel specialist work, ultrawork, hyperplan, team mode, or start-work.
---

# Sisyphus

## Select the native runtime

- In Codex, read and follow `SKILL_DIR/runtime/codex.md`. It is the complete
  native adapter and supersedes the Claude-specific instructions below.
- In Claude Code, continue with the Claude runtime below.

## Shared orchestration contract

Use parallel implementation only for genuinely independent tracks. Give every
writer explicit, disjoint file ownership and the shared contract it must
preserve. The lead remains the final integration owner: it reconciles the
resulting diff, validates cross-track behavior, runs the applicable checks,
and reports evidence. Do not silently revert another writer's work.

# Claude Code runtime

This skill turns the current Claude Code session into an OmO primary agent.
Everything runs here, on the user's Claude subscription — no external model
APIs, no proxy. Model names that appear in the loaded prompts describe the
original OpenCode routing and do not apply. Each subagent runs on the model
set in its definition, generated from `MODELS` in `scripts/build.py` (full ids,
never the aliases). The model table lives in the orchestration-pack README
(source repo `ArnaudLafosse92100/orchestration-pack`): Haiku 5.5 for reading,
Opus 5.5 for judgement, Sonnet 5.5 for scoped execution. The lead runs on the
session model.

`SKILL_DIR` = the directory containing this file.

## 1. Preflight

The OmO subagents must be installed as Claude subagents: explore, librarian,
oracle, metis, momus, multimodal-looker, plan, hephaestus (team-mode member
only: upstream it is a primary agent), sisyphus-junior, and the category executors quick, deep, ultrabrain, visual-engineering, artistry,
writing, bug-hunt, refactor-safe, arch-review, unspecified-low,
unspecified-high. If an `Agent` call with one of these names is rejected as
unknown, the orchestration pack is not installed here: tell the user to run
`<orchestration-pack>/sync.sh --bootstrap <repo>` (cloud; or `--home` on the Mac) from the source
repo `ArnaudLafosse92100/orchestration-pack`, open a new session, and stop. Never imitate a specialist with a generic agent.

## 2. Pick the mode from the invocation

| Invocation | Mode file (read it fully, then act as that agent) |
| --- | --- |
| `/sisyphus` or `/sisyphus <task>` (default) | `SKILL_DIR/modes/sisyphus.md` — strict router: its first section (`runtime/router.md`, from the fork's `codex-router`) overrides the rest; then the generated agent roster (when/how/what each agent returns, from its own prompt) |
| `/sisyphus plan <task>` | `SKILL_DIR/modes/prometheus.md` — Prometheus planner; it loads the `ulw-plan` skill first |
| `/sisyphus start-work [plan path]` | `SKILL_DIR/modes/atlas.md` — Atlas plan executor, plus `SKILL_DIR/vendor/omo-4.19.4/rendered/misc/start-work.md` as the session brief |
| `/sisyphus hephaestus <task>` | `SKILL_DIR/modes/hephaestus.md` — autonomous deep worker |

Then read `SKILL_DIR/runtime/lead.md`. It maps every OmO tool the mode prompt
mentions (`task`, `call_omo_agent`, `background_output`, `skill`, `question`,
`team_*`, `lsp_*`, …) to its Claude Code equivalent. The mode prompt defines
behaviour; `runtime/lead.md` defines how to execute it here.

Stay in the chosen mode for the rest of the task, including follow-up turns,
until the user ends it or invokes a different mode.

## 3. Keyword expansions (OmO keyword-detector)

Check the user's message on every turn. If it contains one of these keywords,
read the listed file and follow it exactly in addition to the mode:

| Keyword (case-insensitive, whole word) | Inject |
| --- | --- |
| `ultrawork`, `ulw` | `SKILL_DIR/vendor/omo-4.19.4/rendered/misc/ultrawork.md` (in Prometheus mode use `ultrawork.planner.md`) |
| `hyperplan`, `hpp` | `SKILL_DIR/vendor/omo-4.19.4/rendered/misc/hyperplan.md`, which loads the `hyperplan` skill |
| `hyperplan ultrawork` / `hpp ulw` (either order) | both of the above, with the single banner `HYPERPLAN ULTRAWORK MODE ENABLED!` |
| `team mode`, `team-mode` | `SKILL_DIR/vendor/omo-4.19.4/rendered/misc/team.md`, which loads the `team-mode` skill |

`skill(name="X")` in any of these means: read
`SKILL_DIR/vendor/omo-4.19.4/skills/X/SKILL.md` and the files it references.

## 4. Runtime hooks

`scripts/hooks/sisyphus_hooks.py` (registered by the pack's `settings.fragment.json`
through `.claude/hooks/sisyphus.sh`, in the project's or the user's `.claude/settings.json`)
reproduces the core OmO hooks, only for sessions where `/sisyphus` was invoked:

- keyword-detector: injects the ultrawork / hyperplan / team files above. Only real user prompts count: background-task notifications and subagent hand-backs never trigger keywords.
- prometheus-md-only: in `plan` mode, writes outside `<project>/.omo/` are denied.
- strict router: in `sisyphus` and `start-work` (Atlas) modes, the lead's own `Write`/`Edit`/`NotebookEdit` outside `<project>/.omo/` are denied, except its own memory (`~/.claude/projects/*/memory/`) and session scratchpad (`/tmp/claude-<uid>/`, `/private/tmp/claude-<uid>/`); subagent calls (hook input with `agent_id`) are not affected, so edits go to specialists.
- todo-continuation-enforcer: while todos stay open (TodoWrite, TaskCreate/TaskUpdate tasks, `- [ ]` items in `.omo/todos/*.md` edited this session, and in Atlas mode `.omo/plans/*.md` too, standing in for the boulder continuation), stopping is blocked up to 3 times in a row; the counter resets on each user message.

Not ported: ralph-loop, the full boulder state machine and stop-continuation-guard. Their stand-ins are the Atlas plan scan above, the 3-block cap and `/sisyphus off`.

`/sisyphus off` ends the mode for the session.

## 5. Configuration carried over from jesseoue/opencode-configs

- `sisyphus_agent.tdd: true` — plans and implementations are TDD-oriented: write or update the failing test first, then the code, then run the tests.
- `start_work.auto_commit: false` — never commit unless the user asks.
- Team limits: upstream caps teams at 4 parallel members and 5 per team; here the user removed every cap: no limit on parallel agents, parallel editors, nested helpers or concurrent topics (see `runtime/router.md`). 80 turns per member, 45 minutes wall clock.
- Team specs live in `SKILL_DIR/teams/*.json`; run them as described in `runtime/lead.md`.
- `git_master` asks for no commit footer and no co-author line. When the user asks for a commit, the session's own attribution rules take precedence over this.
- `/goal` is disabled upstream; use `/sisyphus start-work` for plan execution.

## 6. Provenance

- Prompts: oh-my-openagent 4.19.4 rendered for `anthropic/claude-opus-5` by `scripts/render-omo.mjs` (Hephaestus uses its GPT-5.6 prompt: OmO ships no Claude variant), with the `prompt_append` files of jesseoue/opencode-configs at `vendor/omo-4.19.4/UPSTREAM_OPENCONFIG_REV`.
- Global instructions: the behaviour sections of upstream `AGENTS.md`, `prompts/core.md` and `prompts/goal.md` (vendored in `vendor/omo-4.19.4/openconfig/`) are appended to every mode and agent, without model routing or OpenConfig machine setup.
- `scripts/build.py` generates `agents/` and `modes/` from `vendor/`. It removes the upstream "Authorized / no refusals / unmoderated" passages. Edit the build script, never the generated files.
- Not ported: content-aware-* lanes (team members on `content-aware-fast` / `content-aware-deep` run as the `quick` / `deep` categories), context-aware-hermes, the DeepSeek/Venice Sisyphus variants, multi-provider model routing and fallbacks.
