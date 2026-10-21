#!/usr/bin/env python3
"""Build Claude Code subagents and lead modes from the vendored OmO render.

Source: vendor/omo-4.19.4/rendered (oh-my-openagent 4.19.4 prompts rendered for
Claude Opus 5 by scripts/render-omo.mjs, with jesseoue/opencode-configs
prompt_append files). Output: agents/*.md (Claude subagents) and modes/*.md
(lead instructions loaded by SKILL.md). Edit this script, never the outputs.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "omo-4.19.4" / "rendered"
# Subagents go next to the skills dir: <pack>/agents, <project>/.claude/agents or ~/.claude/agents.
AGENTS_OUT = ROOT.parents[1] / "agents"
MODES_OUT = ROOT / "modes"
LEAF = (ROOT / "runtime" / "leaf.md").read_text()
ROUTER = (ROOT / "runtime" / "router.md").read_text()
LENSES = (ROOT / "runtime" / "lenses.md").read_text()
# Per-mode note appended to LENSES: how each lead mode activates the lenses.
LENS_MODE_NOTES = {
    "sisyphus": "Sisyphus: the strict router waves above name the lens of each brief.",
    "prometheus": "Prometheus: run `goal-beyond-goal` and `assumption-breaker` yourself during the interview, use `three-decisions` for the questions you put to the user, and write into each plan task the lens its executor and verifier must carry.",
    "atlas": "Atlas: pass each task brief through `deeper-brief`, give executors `experts-toolkit` and the verification of their claims `assumption-breaker`; on resume run `assumption-breaker` on the plan checkboxes before continuing.",
    "hephaestus": "Hephaestus: apply the lenses yourself: `assumption-breaker` on the beliefs your task rests on before editing and on every resume, `experts-toolkit` for the work, `goal-beyond-goal` when the outcome is unstated.",
}
DELEGATION = json.loads((ROOT / "runtime" / "delegation.json").read_text())
UPSTREAM_REV = (ROOT / "vendor" / "omo-4.19.4" / "UPSTREAM_OPENCONFIG_REV").read_text().strip()
READ_ONLY = "Edit, Write, NotebookEdit"

# name: (source file, read_only, description)
AGENTS = {
    "oracle": ("agents/oracle.md", True,
               "OmO Oracle: read-only high-IQ consultant for architecture, hard debugging, security and adjudication. Consult before risky implementation or after repeated failures."),
    "librarian": ("agents/librarian.md", True,
                  "OmO Librarian: read-only reference search across official docs, OSS repos and the web (Context7-first). Use for library/API/version questions."),
    "explore": ("agents/explore.md", True,
                "OmO Explore: read-only contextual grep of the codebase — patterns, entry points, call paths, returned as path:line. Fire in parallel for broad recon."),
    "metis": ("agents/metis.md", True,
              "OmO Metis: read-only pre-planning consultant that surfaces hidden intent, false premises, scope and acceptance gaps before a plan is written."),
    "momus": ("agents/momus.md", True,
              "OmO Momus: read-only plan executability gate. Reviews a plan file and returns OKAY or REJECT with at most three verified blockers."),
    "multimodal-looker": ("agents/multimodal-looker.md", True,
                          "OmO Multimodal-Looker: read-only analysis of images, screenshots, PDFs and diagrams."),
    "plan": ("agents/plan.md", True,
             "OmO plan agent: turns an analysis bundle into a sequenced, parallelized plan with verification gates (used by hyperplan phase 7). Read-only; returns the plan."),
    "hephaestus": ("agents/hephaestus.md", False,
                   "OmO Hephaestus: autonomous deep worker that owns a code path end-to-end. Launch it as a team-mode member or as the implementer of an approved plan (strict router pipeline); for a one-off deep task use the 'deep' category."),
    "sisyphus-junior": ("agents/sisyphus-junior.md", False,
                        "OmO Sisyphus-Junior: focused executor for a well-scoped delegated task; cannot re-delegate."),
}

CATEGORIES = {
    "quick": "Trivial tasks: single-file changes, typo fixes, simple modifications.",
    "deep": "Goal-oriented autonomous problem-solving; thorough research before action, one goal per call.",
    "ultrabrain": "Genuinely hard logic-heavy or architecture decisions; decision memo with assumptions, alternatives and failure modes.",
    "visual-engineering": "Frontend, UI/UX, design system, styling, animation — implement UI that follows the repo design system.",
    "artistry": "Creative, unconventional approaches and design direction beyond standard patterns.",
    "writing": "Documentation, prose and technical writing from source of truth.",
    "bug-hunt": "Reproduce, find root cause, apply minimal fix, verify.",
    "refactor-safe": "Tests-first, behavior-preserving refactors in small steps.",
    "arch-review": "Coupling, cohesion, blast radius and security posture review, findings first.",
    "unspecified-low": "Tasks that fit no other category and need low effort.",
    "unspecified-high": "Tasks that fit no other category and need high effort.",
}

# Claude model per subagent (frontmatter `model:`). Full ids, not aliases: the
# `sonnet` alias resolved to Sonnet 5, not 5.5 (eval run 2026-10-02). Founder rule
# (2026-10-21): Haiku for reading, Opus for judgement, Sonnet for scoped execution.
# The table in the orchestration-pack README mirrors this map. The lead modes
# run on the session model.
OPUS = "claude-opus-5-5"
SONNET = "claude-sonnet-5-5"
HAIKU = "claude-haiku-5-5"
MODELS = {
    "explore": HAIKU,
    "librarian": HAIKU,
    "multimodal-looker": HAIKU,
    "quick": HAIKU,
    "metis": OPUS,
    "momus": OPUS,
    "oracle": OPUS,
    "plan": OPUS,
    "bug-hunt": OPUS,
    "arch-review": OPUS,
    "ultrabrain": OPUS,
    "hephaestus": OPUS,
    "deep": OPUS,
    "unspecified-high": OPUS,
    "writing": SONNET,
    "refactor-safe": SONNET,
    "visual-engineering": SONNET,
    "artistry": SONNET,
    "unspecified-low": SONNET,
    "sisyphus-junior": SONNET,
}
if set(MODELS) != set(AGENTS) | set(CATEGORIES) or not set(MODELS.values()) <= {OPUS, SONNET, HAIKU}:
    raise SystemExit(f"MODELS must give every agent and category exactly one of: {OPUS}, {SONNET}, {HAIKU}")

# Content-aware lanes are Venice-only upstream; map them onto ported categories. They
# stay `kind: category` members (explore/oracle are hard-rejected as teammates
# upstream); the member prompts keep their read-only constraint.
TEAM_CATEGORY_MAP = {"content-aware-fast": "quick", "content-aware-deep": "deep"}
SKIP_TEAMS = {"content-aware-audit"}

MODES = {
    "sisyphus": "agents/sisyphus.md",
    "prometheus": "agents/prometheus.md",
    "atlas": "agents/atlas.md",
    "hephaestus": "agents/hephaestus.md",
}

HEADING_MODEL_TAG = re.compile(
    r"\s*\((?=[^)]*(?:unmoderated|GLM|DeepSeek|Gemini|Venice|Qwen|Kimi|MiniMax|Hermes))[^)]*\)")
# Sentences that only describe upstream model/provider lanes (and the Venice/Hermes
# content-aware lanes, not ported): every role runs on Claude here (model per role: MODELS).
SENTENCE_DROP = re.compile(
    r"unmoderated|all un-?moderated|Routes? Pro 0813|Escalates to GLM|content-aware|context-aware|Venice|"
    r"OpenRouter|_API_KEY|\bGLM\b|DeepSeek|\bKimi\b|Laguna|\bQwen\b|MiniMax|Hermes 4|gpt-5\.6|GPT-5\.6",
    re.IGNORECASE)
# Rewrites applied before SENTENCE_DROP so the useful part of the line survives.
MODEL_SUBS = [
    (re.compile(r"based on GPT-5\.6"), "running on Claude"),
    (re.compile(r"THIS CATEGORY USES A [A-Z/ ]+MODEL \([^)]*\)\."), "THIS CATEGORY IS FOR SMALL, TIGHTLY SCOPED WORK."),
    (re.compile(r"The model executing this task is optimized for speed over depth\."),
     "The executor favours speed over depth."),
    (re.compile(r" \(Domain-Optimized Models\)"), ""),
    (re.compile(r"Each category is configured with a model optimized for that domain\."),
     "Each category carries domain-specific instructions and runs on the Claude model set in its agent definition."),
    (re.compile(r"because each category runs on a model optimized for that specific domain"),
     "because each category carries instructions tuned for that domain"),
    (re.compile(r"GLM 5\.3 max \([^)]*\)\."), "maximum-effort mode."),
    (re.compile(r" — don't burn Pro/GLM"), ""),
    (re.compile(r"the category model routes you"), "the category brief scopes you"),
    (re.compile(r"Smaller models benefit from explicit guardrails"), "Fast executors need explicit guardrails"),
]
# Strict router (runtime/router.md): the Opus-rendered Sisyphus prompt pushes small work
# onto the lead. The user chose the fork's codex-router behaviour instead.
ROUTER_SUBS = [
    ("Small local work you can finish in a handful of tool calls is YOURS - do it directly.",
     "You orchestrate and verify; specialists do the work (strict router contract above)."),
    (("3. **OVER-DELEGATION**: You reach for subagents more readily than the work justifies. Delegate ONLY for a "
     "matching specialist domain or a genuinely independent, sizeable track (wide multi-file investigation, parallel "
     "research). Work you can finish in a handful of tool calls → do it yourself. NEVER spawn a subagent to verify or "
     "double-check your own work. One agent when one suffices; keep spawn counts low."),
     ("3. **UNDER-DELEGATION**: You reach for direct tools when a specialist owns the work. Exploration, research, "
     "planning and edits always go to the matching specialist; you brief, sequence and verify. Launch independent "
     "tracks together in one message; one agent per track, never one agent per trivial step.")),
    ("Execute DIRECTLY, then verify through ACTUAL USE:",
     "Drive the delivery pipeline to the end, then verify through ACTUAL USE:"),
    ("- **Trivial** (single file, known location) → direct tools, unless Key Trigger applies",
     "- **Trivial** (single file, known location) → `quick` for an edit, `explore` for a lookup"),
    ("- **Explicit** (specific file/line, clear command) → execute directly",
     "- **Explicit** (specific file/line, clear command) → the matching category with that exact instruction"),
    ("3. Neither, or you can finish it in a handful of tool calls → do it YOURSELF.",
     "3. Neither → `quick` or `unspecified-low`. Never do it yourself."),
    ("**DELEGATE BY DOMAIN AND SIZE, NOT BY DEFAULT.** Delegation multiplies cost and wall-clock time on small tasks.",
     "**DELEGATE BY DOMAIN, SIZE THE BRIEF.** Group small related edits into one brief."),
    ("- **DO NOT spawn for trivial work** (one file edit, one search, function you can already see).",
     "- **Batch trivial work**: one `quick` brief for several small edits, not one agent per edit."),
    ("- Trivial local reads/edits → direct tools. Don't spawn explore just to open a known path.",
     "- Reading a known path to brief a specialist is fine; edits always go to a category executor."),
    ("- Trivial local paths → direct tools. Spawn `task`/explore only for broad or parallel recon.",
     "- Reading a known path to brief a specialist is fine; edits always go to a category executor."),
]
# Atlas brief template: CodeGraph is not installed here; point the brief at plain tools.
ATLAS_SUBS = [
    (("- codegraph_explore (PRIMARY): One capped call returns source + callers/callees/impact. Use FIRST when "
      "codegraph_* tools are available. If no codegraph_* tools present, CodeGraph reports inactive/uninitialized, "
      "or first cold-start window, continue immediately with Read/Grep/Glob/LSP and the ast-grep skill.\n"
      "- codegraph_search, codegraph_node, codegraph_callers, codegraph_callees, codegraph_impact, codegraph_files, "
      "codegraph_status: Supporting CodeGraph tools for targeted queries.\n"),
     ("- Read/Grep/Glob (or `rg`) and LSP when available: symbols, callers, call paths and impact; "
      "the ast-grep skill for structural patterns.\n")),
]
# Upstream prompts name an OmO code-graph tool that is not installed here: drop it from
# tool lists and keep the plain read/grep/LSP route. build() refuses any leftover mention.
CODE_GRAPH_SUBS = [
    (re.compile(r"\s*/\s*codegraph(?=\s*/)"), ""),          # `grep` / codegraph / LSP
    (re.compile(r"/codegraph\b"), ""),                       # read/grep/codegraph
    (re.compile(r" · codegraph(?= ·)"), ""),                  # `list` · codegraph · LSP
    (re.compile(r" \+ codegraph\b"), ""),                    # ### grep_app + codegraph
]
CODE_GRAPH_DROP_LINE = re.compile(r"^\s*-\s*codegraph:")
CODE_GRAPH_LEFTOVER = re.compile(r"code-?graph", re.IGNORECASE)
# Role-specific structural checks, done with rg / Read / LSP.
STRUCTURE_ROLE = {
    "explore": "map symbols, callers, callees and call paths.",
    "oracle": "check callers and blast radius of the code under review before judging.",
    "metis": "confirm the files and symbols the request assumes actually exist and who depends on them.",
    "momus": "verify that every file, symbol and interface the plan names exists, with its callers.",
    "plan": "list the exact files and symbols each task touches and their dependents.",
    "bug-hunt": "trace the failing path: callers of the faulty symbol and the call path from the entry point.",
    "refactor-safe": "get the full impact (callers, implementations) before any rename or move, and re-check after.",
    "arch-review": "measure coupling and blast radius from real references, not from file names.",
    "deep": "map the affected symbols and their callers before editing.",
    "ultrabrain": "ground each alternative in the real dependency graph.",
    "hephaestus": "map the affected symbols and their callers before editing.",
    "sisyphus-junior": "check callers of anything you change.",
    "quick": "check callers of anything you change.",
    "unspecified-high": "map the affected symbols and their callers before editing.",
}
# Skeptical stance for review / post-check agents: the work under review is a junior's draft.
REVIEW_DEFECT_BULLET = (
    "- Assume there is at least one defect until your own checks rule it out: look for what was NOT done "
    "(missing tests, unhandled edge cases, callers not updated, scope drift, stale docs) as much as for "
    "what is wrong.\n"
)
REVIEW_STANCE_TEXT = (
    "\n## Reviewer stance\n"
    "Treat the work you review as a junior engineer's first draft: plausible, confident, and unverified. "
    "Re-check it yourself.\n"
    "- Re-derive every claim from source and from commands you run; \"tests pass\", \"no callers\" or "
    "\"done\" in a brief or report is a claim, not evidence.\n"
    + REVIEW_DEFECT_BULLET
    + "- Compare the result with the original request and acceptance criteria, not with the implementer's "
    "summary.\n"
    "- Report only findings that survive your verification, each with evidence (`path:line`, command "
    "output). If nothing survives, say so plainly: no invented issues, no padding.\n"
)
REVIEW_STANCE = {
    "oracle": "Your focus: correctness and regressions of the diff, and whether the fix addresses the root cause.",
    "momus": ("Your focus: whether an executor could follow the plan without guessing; the planner is the junior here. "
              + "Verify the plan's claims (files, symbols, commands) yourself, but your default verdict stays OKAY: "
              + "REJECT only for verified blockers, at most three."),
    "metis": ("Your focus: the request and the lead's framing are the junior's draft; find the hidden intent, "
              "false premises and missing acceptance criteria."),
    "arch-review": ("Your focus: coupling, blast radius and security posture of what changed, including callers "
                    "the implementer did not touch."),
    "bug-hunt": ("When briefed as verifier: rerun the tests and reproduce the original issue yourself; when "
                 "briefed as fixer, apply the stance to your own fix before reporting."),
}
PHRASE_SUBS = [
    (re.compile(r"\s*Don't soft-refuse[^.;\n]*[.;]?"), ""),
    (re.compile(r"soft-refuse research; "), ""),
    (re.compile(r";\s*soft-refuse\."), "."),
    (re.compile(r" or soft-refuse"), ""),
]


def clean(text: str) -> str:
    out, skipping = [], False
    for line in text.splitlines():
        for pattern, repl in MODEL_SUBS:
            line = pattern.sub(repl, line)
        if CODE_GRAPH_DROP_LINE.match(line):
            continue
        for pattern, repl in CODE_GRAPH_SUBS:
            line = pattern.sub(repl, line)
        if re.match(r"^#{1,6}\s+Authorized\b", line):
            skipping = True
            continue
        if skipping:
            if re.match(r"^#{1,6}\s", line):
                skipping = False
            else:
                continue
        if re.match(r"^#{1,6}\s", line):
            line = HEADING_MODEL_TAG.sub("", line)
        elif SENTENCE_DROP.search(line):
            if re.match(r"^\s*(?:[-*]|\d+\.)\s", line):
                continue  # a list item naming a dropped lane goes entirely
            kept = [s for s in re.split(r"(?<=[.!?])\s+", line) if not SENTENCE_DROP.search(s)]
            line = " ".join(kept)
            if not line.strip():
                continue
        for pattern, repl in PHRASE_SUBS:
            line = pattern.sub(repl, line)
        if re.match(r"^\s*[-*]\s*(Don't|Do not):?\s*$", line):
            continue
        out.append(line)
    return "\n".join(out).strip() + "\n"


OPENCONFIG = ROOT / "vendor" / "omo-4.19.4" / "openconfig"
# Upstream loads AGENTS.md + prompts/core.md into every session (lead and subagents).
# Keep the sections that define agent behaviour; drop machine setup (oc CLI, Ghostty,
# keys) and model/provider routing, which do not apply on Claude.
GLOBAL_SECTIONS = [
    ("AGENTS.md", ["How to work", "Team eligibility (why)", "Team mode & hyperplan", "What not to do"]),
    ("prompts/core.md", ["How to work (agent pace)", "Research stack (use the right tool)", "Output",
                         "Scope", "Intent and evidence quality"]),
    ("prompts/goal.md", ["What to use instead"]),
]
GLOBAL_SUBS = [
    (re.compile(r"/context-aware-hermes/content-aware-research/content-aware-fast"), ""),
    (re.compile(r", `context-aware-hermes`, `content-aware-research`, `content-aware-fast`"), ""),
    (re.compile(r"GLM-backed categories"), "categories"),
    (re.compile(r" \((?:Pro|Flash → Pro fallbacks)\)"), ""),
    (re.compile(r" \(init when the graph is cold\)"), ""),
    (re.compile(r"\bOpenCode\b"), "Claude Code"),
]
GLOBAL_DROP = re.compile(
    r"OpenRouter|Venice|DeepSeek|GLM|Gemini|Hermes|MiniMax|Qwen|Kimi|Laguna|Flash|content-aware|"
    r"context-aware|Exacto|Cloudflare|\boc\b|\$schema|oh-my-opencode|Ghostty|\.env\b|telemetry|scaffold(?!ing)|"
    r"config repo|package\.json|1049l|^Full detail")


def _section(text: str, title: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m and m.group(2).strip() == title:
            level, out = len(m.group(1)), [line]
            for nxt in lines[i + 1:]:
                h = re.match(r"^(#{1,6})\s", nxt)
                if h and len(h.group(1)) <= level:
                    break
                out.append(nxt)
            return "\n".join(out).strip()
    raise SystemExit(f"upstream section not found: {title!r}")


def _filter_global(text: str) -> str:
    out = []
    for line in text.splitlines():
        for pattern, repl in GLOBAL_SUBS:
            line = pattern.sub(repl, line)
        if GLOBAL_DROP.search(line) and not re.match(r"^#{1,6}\s", line):
            prefix = re.match(r"^(\s*(?:[-*]|\d+\.)?\s*)", line).group(1)
            kept = [s for s in re.split(r"(?<=[.!?])\s+", line[len(prefix):]) if not GLOBAL_DROP.search(s)]
            if not kept:
                continue
            line = prefix + " ".join(kept)
        out.append(line)
    return "\n".join(out)


def global_instructions() -> str:
    parts = ["# Global instructions (jesseoue/opencode-configs, loaded in every upstream session)", "",
             "Upstream loads these rules into every session next to the agent prompt. Model/provider "
             "routing and OpenConfig machine setup are omitted: every role here runs on Claude (Haiku, Sonnet or Opus per role, see the README model table), "
             "and tool names map to Claude Code as described in the runtime section."]
    for rel, titles in GLOBAL_SECTIONS:
        text = (OPENCONFIG / rel).read_text()
        parts.append(f"\n<!-- {rel} -->")
        parts.extend("\n" + _filter_global(_section(text, t)) for t in titles)
    return clean("\n".join(parts))


GLOBALS = global_instructions()


def build_teams() -> set:
    src_dir = ROOT / "vendor" / "omo-4.19.4" / "teams"
    out_dir = ROOT / "teams"
    out_dir.mkdir(exist_ok=True)
    written = set()
    for src in sorted(src_dir.glob("*.json")):
        spec = json.loads(src.read_text())
        if spec["name"] in SKIP_TEAMS:
            continue
        for m in spec["members"]:
            if m.get("kind") == "category" and m["category"] in TEAM_CATEGORY_MAP:
                m["category"] = TEAM_CATEGORY_MAP[m["category"]]
            if "prompt" in m:
                m["prompt"] = re.sub(r"AUTHORIZED:[^.]*\.\s*", "", m["prompt"])
                for pattern, repl in CODE_GRAPH_SUBS:
                    m["prompt"] = pattern.sub(repl, m["prompt"])
            # Claude runtime: members are Agent calls; subagent_type is the agent name.
            m["agent"] = m.get("subagent_type") or m.get("category")
        (out_dir / src.name).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
        written.add(src.name)
    for stale in out_dir.glob("*.json"):
        if stale.name not in written:
            stale.unlink()
    return written


CALLER_WARNING = re.compile(r"<Caller_Warning>\n(.*?)</Caller_Warning>\n?", re.DOTALL)


def category_body(name: str) -> str:
    raw = (VENDOR / "categories" / f"{name}.md").read_text()
    raw = re.sub(r"^<!-- description:.*?-->\n", "", raw)
    # <Caller_Warning> tells the caller how to brief this category: it goes to the
    # lead's roster, not into the executor's own prompt.
    raw = CALLER_WARNING.sub("", raw)
    base = (VENDOR / "agents" / "sisyphus-junior.base.md").read_text()
    return base.rstrip() + "\n\n" + raw


# Team membership rules from upstream prompts/core.md (team eligibility matrix).
TEAM_REJECTED = {"explore", "librarian", "oracle", "metis", "momus", "multimodal-looker", "plan"}


def _append_section(src_text: str) -> str:
    """The jesseoue prompt_append: from the last top-level heading to the end."""
    heads = [m.start() for m in re.finditer(r"^# ", src_text, re.MULTILINE)]
    return src_text[heads[-1]:] if heads else ""


def roster_entry(name: str, kind: str, desc: str, read_only: bool, src_text: str) -> str:
    append = clean(_append_section(src_text))
    lines = append.splitlines()
    title = re.sub(r"^#\s+", "", lines[0]).strip() if lines else ""
    if not re.search(r" — |^Category:", title):  # no jesseoue prompt_append (e.g. plan)
        lines, title = [], ""
    paras = [b.strip() for b in "\n".join(lines[1:]).split("\n\n") if b.strip()]
    intro = next((b for b in paras if not b.startswith(("#", "-", "`", "|", "<"))), "")
    donts, deliver, section, in_code = [], [], "", False
    for line in lines[1:]:
        if line.startswith("```"):
            in_code = not in_code
            continue
        if not in_code and line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if in_code and section == "deliverable" and line.startswith("## "):
            deliver.append(line[3:].strip())
        elif not in_code and "don't" in section and line.startswith("- "):
            donts.append(line[2:].strip())
    access = "read-only" if read_only else "edits files"
    team = "never a team member" if name in TEAM_REJECTED else "team-eligible"
    out = [f"### `{name}` — {kind} · {MODELS[name]} · {access} · {team}", "",
           f"- **When**: {desc}"]
    if title:
        out.append(f"- **Upstream role**: {title}. {intro}".rstrip())
    if deliver:
        out.append("- **Returns**: " + " · ".join(deliver))
    if donts:
        out.append("- **Rules**: " + " ".join(donts))
    if name in STRUCTURE_ROLE:
        out.append(f"- **Structure check**: {STRUCTURE_ROLE[name]}")
    if name in REVIEW_STANCE:
        out.append("- **Stance**: reviewer — re-checks the work as a junior's draft; brief it with the original "
                   "request and acceptance criteria, not only the implementer's summary.")
    subs = DELEGATION["delegators"].get(name)
    out.append("- **Can delegate to**: " + (", ".join(f"`{a}`" for a in subs) if subs else "nobody (leaf)"))
    warn = CALLER_WARNING.search(src_text)
    if warn:
        brief = clean(warn.group(1)).strip()
        out += ["- **How to brief it** (caller rules from OmO):", "", *("  " + x if x else "" for x in brief.splitlines())]
    return "\n".join(out)


def build_roster() -> str:
    parts = ["# Agent roster (generated from each agent's own prompt — read before delegating)", "",
             ("You do not see the specialists' system prompts: Claude Code loads each one only inside "
             "the subagent. This roster is your view of them: when to use each, what it returns, what "
             "it must not get, and how to brief it. Each agent runs on the Claude model shown in its heading "
             "(set by its definition: do not pass `model` when launching it); they also differ by "
             "prompt, permissions and scope."), "", "## Specialists", ""]
    for name, (src, ro, desc) in AGENTS.items():
        parts += [roster_entry(name, "specialist", desc, ro, (VENDOR / src).read_text()), ""]
    parts += ["## Category executors (Sisyphus-Junior + category context)", ""]
    for name, desc in CATEGORIES.items():
        parts += [roster_entry(name, "category", desc, False, (VENDOR / "categories" / f"{name}.md").read_text()), ""]
    return "\n".join(parts)


def delegation_rights(name: str) -> str:
    allowed = DELEGATION["delegators"].get(name)
    if not allowed:
        return ("\n## Your delegation rights\n\nNone: you are a leaf. Do not call `Agent`; a hook denies it.\n")
    names = ", ".join(f"`{a}`" for a in allowed)
    return ("\n## Your delegation rights\n\n"
            f"You may launch these subagents with `Agent`: {names}. Anything else is denied by a hook.\n"
            "- Use them for evidence you need and for disjoint sub-tracks, several `Agent` calls in ONE "
            "message when independent, each with `run_in_background: false`: they still run in parallel, "
            "and you get their results directly. Never use `run_in_background: true` as a subagent: its "
            "completion notification goes to the main session, not to you, so you would wait forever.\n"
            "- Brief each one fully (goal, project root, scope, expected output); they cannot "
            "see your context. Give executors disjoint file ownership.\n"
            "- Stay within the lead's brief: no new scope. Do not launch agents for work you can see in one read.\n"
            "- Never launch `ocx-*` agents.\n")


def write_agent(name: str, desc: str, body: str, read_only: bool, src: str) -> None:
    fm = ["---", f"name: {name}", f'description: "{desc}"', f"model: {MODELS[name]}"]
    if read_only:
        fm.append(f"disallowedTools: {READ_ONLY}")
    fm.append("---")
    header = (f"<!-- Generated by sisyphus/scripts/build.py from oh-my-openagent 4.19.4 ({src}) "
              f"+ jesseoue/opencode-configs {UPSTREAM_REV}. Do not edit. -->")
    ro = "\nYou are read-only: do not create, modify or delete files (including via Bash).\n" if read_only else ""
    cg = (f"\nStructure check for this role: with `rg`, Read and LSP when available, {STRUCTURE_ROLE[name]} "
          "Verify each claim in source.\n") if name in STRUCTURE_ROLE else ""
    stance_text = REVIEW_STANCE_TEXT.replace(REVIEW_DEFECT_BULLET, "") if name == "momus" else REVIEW_STANCE_TEXT
    stance = (stance_text + REVIEW_STANCE[name] + "\n") if name in REVIEW_STANCE else ""
    text = ("\n".join(fm) + "\n\n" + header + "\n\n" + clean(body) + ro + cg + stance + "\n" + GLOBALS + "\n" + LEAF
            + delegation_rights(name))
    (AGENTS_OUT / f"{name}.md").write_text(text)


def main() -> None:
    AGENTS_OUT.mkdir(exist_ok=True)
    MODES_OUT.mkdir(exist_ok=True)
    expected = set()
    for name, (src, ro, desc) in AGENTS.items():
        write_agent(name, desc, (VENDOR / src).read_text(), ro, src)
        expected.add(f"{name}.md")
    for name, desc in CATEGORIES.items():
        write_agent(name, f"OmO category executor '{name}' (Sisyphus-Junior + category context): {desc}",
                    category_body(name), False, f"categories/{name}.md")
        expected.add(f"{name}.md")
    for stale in AGENTS_OUT.glob("*.md"):
        if stale.name not in expected:
            stale.unlink()
            print("removed stale", stale.name)
    ROSTER = build_roster()
    for name, src in MODES.items():
        body = clean((VENDOR / src).read_text()) + "\n" + GLOBALS
        if name == "sisyphus":
            for old, new in ROUTER_SUBS:
                if old not in body:
                    raise SystemExit(f"router substitution target not found: {old[:60]!r}")
                body = body.replace(old, new)
            body = ROUTER + "\n" + ROSTER + "\n" + body
        elif name == "atlas":
            for old, new in ATLAS_SUBS:
                if old not in body:
                    raise SystemExit(f"atlas substitution target not found: {old[:60]!r}")
                body = body.replace(old, new)
            body = ROSTER + "\n" + body
        body = LENSES + "\n" + LENS_MODE_NOTES[name] + "\n\n" + body
        (MODES_OUT / f"{name}.md").write_text(
            f"<!-- Generated by sisyphus/scripts/build.py from oh-my-openagent 4.19.4 ({src}) "
            f"+ jesseoue/opencode-configs {UPSTREAM_REV}. Do not edit. -->\n\n" + body)
    teams = build_teams()
    for out in [*AGENTS_OUT.glob("*.md"), *MODES_OUT.glob("*.md"), *(ROOT / "teams").glob("*.json")]:
        hit = CODE_GRAPH_LEFTOVER.search(out.read_text())
        if hit:
            raise SystemExit(f"code-graph reference left in generated {out.relative_to(ROOT.parents[1])}: {hit.group(0)!r}")
    print(f"{len(expected)} agents, {len(MODES)} modes, {len(teams)} teams")


if __name__ == "__main__":
    main()
