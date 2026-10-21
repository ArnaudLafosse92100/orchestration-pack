# Claude Code runtime for the OmO lead prompts

The mode prompt you just loaded was written for OpenCode + oh-my-openagent
(OmO). You are running inside Claude Code on the user's Claude subscription.
Keep the prompt's behaviour; translate its tool names with this table. Where a
prompt names a model (GLM, DeepSeek, Gemini, GPT…), ignore it: each subagent
runs on the Claude model set in its definition (shown in the roster headings;
the per-role table is in the orchestration-pack README). Do not pass `model` when launching an OmO agent; its definition
decides. The lead runs on the session model.

`SKILL_DIR` below means the directory that contains this sisyphus skill.

## Tool mapping

| OmO / OpenCode | Claude Code |
| --- | --- |
| `task(subagent_type="X", prompt=…)` | `Agent` with `subagent_type: "X"` |
| `task(category="C", load_skills=[…], prompt=…)` | `Agent` with `subagent_type: "C"` (one executor per category). Put `Before starting, read SKILL_DIR/vendor/omo-4.19.4/skills/<skill>/SKILL.md` in the prompt for each `load_skills` entry. |
| `call_omo_agent(subagent_type="explore"/"librarian", …)` | `Agent` with that `subagent_type` |
| `run_in_background=true` | `Agent` with `run_in_background: true` (you are notified on completion) |
| `run_in_background=false` | `Agent` with `run_in_background: false` |
| `background_output(task_id=…)` | Nothing to call: the completion notification carries the result. Never poll. |
| `background_cancel(…)` | `TaskStop` on that agent (load it with ToolSearch if deferred) |
| `task(session_id="ses_…", …)` / session continuity | `SendMessage` to the agent id returned by the earlier `Agent` call |
| `skill(name="X")` | Read `SKILL_DIR/vendor/omo-4.19.4/skills/X/SKILL.md` (and the files it references). If a Claude skill with that name exists, the `Skill` tool is also fine. |
| `question(…)` | `AskUserQuestion` |
| `todowrite` / `task_create` / `task_update` / `task_list` | Todo/task tools if this session has them (load via ToolSearch); otherwise keep the checklist in `.omo/todos/<topic>.md` and update it as you go |
| `read` / `write` / `edit` / hashline edits / `apply_patch` | `Read` / `Write` / `Edit` |
| `grep` / `glob` / `list` | `Grep` / `Glob` if present, otherwise `rg` / `fd` / `ls` via `Bash` |
| `bash` | `Bash` |
| `lsp_diagnostics` | The project's typecheck/lint command on the changed files via `Bash` (e.g. `tsc --noEmit`, `eslint`, `ruff`, `pyright`) |
| `lsp_find_references` / `lsp_rename` / `lsp_goto_definition` | The `LSP` tool when present (load it with ToolSearch if deferred); otherwise `rg` plus careful `Edit` |
| `ast_grep_*` | `sg` (ast-grep CLI) via `Bash` when installed; otherwise `rg` |
| `look_at` | `Read` the image/PDF directly, or delegate to `multimodal-looker` |
| `webfetch` / `websearch` (Exa) | `WebFetch` / `WebSearch` |
| Context7 `resolve-library-id` / `query-docs` | Context7 MCP when present; otherwise `WebFetch` on official versioned docs |
| `grep_app` | `gh search code` via `Bash` |
| `interactive_bash`, monitors, `/goal` | Not available — skip |
| `/start-work` | `/sisyphus start-work` (Atlas mode) |
| `/ulw`, `/hyperplan`, `/team` | The `ulw`, `hyperplan` and `team mode` keywords |
| Hashline edits | `Edit` |

## Primary agents (Hephaestus, Prometheus, Atlas)

Upstream these are primary agents: `task(subagent_type="hephaestus")` fails with
"Cannot delegate to primary agent … Select that agent directly instead." Only
team mode may run Hephaestus, as a member with teammate permission. So when a
prompt says "Deep implementation → Hephaestus" or "Direct implementation
bursts → Hephaestus":

- inside a team run, launch the `hephaestus` member as an `Agent`;
- in wave 3 of the strict router (`runtime/router.md`), launch
  `hephaestus` as an `Agent` with the approved plan path, as the fork's
  `codex-router` does;
- otherwise, do not `Agent`-call `hephaestus`: use the `deep` category (or
  `ultrabrain` when reasoning is the hard part), or tell the user they can
  switch with `/sisyphus hephaestus <task>`.

Prometheus and Atlas are modes, never subagents: suggest `/sisyphus plan` or
`/sisyphus start-work` to the user.

## Precedence

The Claude Code session rules (the user's CLAUDE.md, permissions, commit and
attribution rules) win over the upstream global instructions appended to the
mode prompt.

## Teams (`team_*` tools)

Claude Code has no team mailbox. Run a team as the lead:

- `team_create` -> decide the members from the spec (`SKILL_DIR/teams/<name>.json`) and launch each member as an `Agent` in one message (all of them in parallel: no cap on members or agents in flight), passing the member's full `prompt` from the spec plus the task.
- `team_task_create` / `team_task_list` -> you keep the team task board in `.omo/teams/<run>/tasks.md` and put each member's assigned task (and its `blockedBy` gates) in its brief.
- `team_send_message` -> `SendMessage` to that member's agent id. Members report back through their final result.
- `team_shutdown_request` / `team_approve_shutdown` / `team_delete` -> nothing to do once every member has returned; stop any stragglers with `TaskStop`.
- Rounds (hyperplan cross-attack, etc.): after round N returns, send each member the other members' findings with `SendMessage` for round N+1.

## Subscription only

Everything runs inside this Claude Code session on the user's Claude
subscription. Do not route work to external model APIs or proxies from this
skill.

Only the OmO agents listed in `SKILL.md` belong to this flow. Never launch the
`ocx-*` agents (`ocx-gpt-6-astra`, `ocx-gpt-6-luna`, `ocx-gpt-6-sol`, `ocx-self`):
they are generated by opencodex and route through its proxy to other models.
