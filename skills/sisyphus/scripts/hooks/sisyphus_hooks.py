#!/usr/bin/env python3
"""Claude Code hooks reproducing the core oh-my-openagent runtime hooks for /sisyphus.

Active only in sessions where the user invoked /sisyphus (state is keyed by
session_id in ~/.claude/state/sisyphus/), except the role guard, which follows
<project>/.omo/role in every session. Subcommands:

  prompt   UserPromptSubmit  start/stop mode, keyword-detector (ulw, hyperplan, team mode);
                             harness-injected prompts (task notifications, subagent
                             hand-backs) never trigger keywords or reset the counter
  pretool  PreToolUse        role guard (any session): when <project>/.omo/role says `router`
                             (cloud Orchestrateur / Sous-orchestrateur), the main session may
                             only write under .omo/, its memory dir and scratchpad;
                             prometheus-md-only: Prometheus may only write under .omo/;
                             strict router: the Sisyphus/Atlas lead (not its subagents)
                             may only write under .omo/, its memory dir and scratchpad,
                             edits go to specialists;
                             nested Agent calls follow runtime/delegation.json
  stop     Stop              todo-continuation-enforcer (bounded): TodoWrite, TaskCreate/
                             TaskUpdate, .omo/todos; in Atlas mode also .omo/plans

Never fails the user's turn: any internal error exits 0 with no output.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

STATE_DIR = Path.home() / ".claude" / "state" / "sisyphus"
SKILL_DIR = Path(__file__).resolve().parents[2]
MISC = SKILL_DIR / "vendor" / "omo-4.19.4" / "rendered" / "misc"
MAX_STOP_BLOCKS = 3
STATE_TTL_SECONDS = 24 * 3600

START_RE = re.compile(r"^\s*/sisyphus(?::\S+)?(?:\s+(plan|start-work|hephaestus|off|stop))?\b", re.I)
KEYWORDS = [
    ("hyperplan-ultrawork", re.compile(r"\b(?:hpp|hyperplan)\s+(?:ulw|ultrawork)\b|\b(?:ulw|ultrawork)\s+(?:hpp|hyperplan)\b", re.I)),
    ("hyperplan", re.compile(r"\bhyperplan\b|(?<![\w.])hpp\b", re.I)),
    ("ultrawork", re.compile(r"\bultrawork\b|(?<![\w.])ulw\b", re.I)),
    ("team", re.compile(r"\bteam[\s_-]?mode\b", re.I)),
]
# Prompts the harness injects on the user's behalf (background-task notifications,
# subagent hand-backs, CI events). They are not user messages: OmO's
# keyword-detector and the continuation counter only react to real user turns.
MACHINE_PROMPT_RE = re.compile(
    r"^\s*(?:<(?:task-notification|agent-message|ci-monitor-event|system-reminder)\b"
    r"|Another Claude session sent a message:)")
TASK_ID_RE = re.compile(r"Task #(\S+?) created")
CLOSED_TASK_STATUSES = {"completed", "deleted"}


def state_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "unknown")
    return STATE_DIR / f"{safe}.json"


def load_state(session_id: str):
    p = state_path(session_id)
    if not p.exists():
        return None
    try:
        st = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    if time.time() - st.get("updated", 0) > STATE_TTL_SECONDS:
        p.unlink(missing_ok=True)
        return None
    return st


def save_state(session_id: str, st: dict) -> None:
    """Write atomically (temp file in STATE_DIR + os.replace) so concurrent hooks never read a torn file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    st["updated"] = time.time()
    target = state_path(session_id)
    tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(st))
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj))


def mode_header(st: dict) -> str:
    return (f"[sisyphus] active mode: {st['mode']} (mode file: {SKILL_DIR/'modes'/(st['mode'] + '.md')}; "
            f"runtime: {SKILL_DIR/'runtime'/'lead.md'}).")


def is_machine_prompt(prompt: str) -> bool:
    return bool(MACHINE_PROMPT_RE.match(prompt))


def on_prompt(data: dict) -> None:
    sid = data.get("session_id", "")
    prompt = data.get("prompt", "") or ""
    st = load_state(sid)
    if is_machine_prompt(prompt):
        if st:
            emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                         "additionalContext": mode_header(st)}})
        return
    m = START_RE.match(prompt)
    if m:
        arg = (m.group(1) or "").lower()
        if arg in ("off", "stop"):
            state_path(sid).unlink(missing_ok=True)
            return
        mode = {"plan": "prometheus", "start-work": "atlas", "hephaestus": "hephaestus"}.get(arg, "sisyphus")
        st = {"mode": mode, "cwd": data.get("cwd") or os.getcwd(), "started": time.time(), "stop_blocks": 0}
    if not st:
        return
    st["stop_blocks"] = 0
    save_state(sid, st)

    notes = []
    for name, rx in KEYWORDS:
        if rx.search(prompt):
            if name == "hyperplan-ultrawork":
                notes.append(f"HYPERPLAN ULTRAWORK: say 'HYPERPLAN ULTRAWORK MODE ENABLED!' once, then follow {MISC/'hyperplan.md'} and {MISC/'ultrawork.md'}.")
                break
            if name == "ultrawork":
                f = MISC / ("ultrawork.planner.md" if st["mode"] == "prometheus" else "ultrawork.md")
                notes.append(f"OmO keyword 'ultrawork' detected: begin your next reply with 'ULTRAWORK MODE ENABLED!', "
                              f"then read {f} now and follow it exactly.")
            elif name == "hyperplan":
                notes.append(f"OmO keyword 'hyperplan' detected: begin your next reply with 'HYPERPLAN MODE ENABLED!', "
                              f"then read {MISC/'hyperplan.md'} now and follow it exactly.")
            elif name == "team":
                notes.append(f"OmO keyword 'team mode' detected: read {MISC/'team.md'} now and follow it exactly.")
    header = mode_header(st)
    emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                 "additionalContext": "\n".join([header, *notes])}})


# Lead modes that only orchestrate: their own writes are limited to .omo/.
ORCHESTRATOR_MODES = {"sisyphus", "atlas"}
DELEGATION_FILE = SKILL_DIR / "runtime" / "delegation.json"


def _delegators() -> dict:
    try:
        return json.loads(DELEGATION_FILE.read_text()).get("delegators", {})
    except (OSError, ValueError):
        return {}


def check_nested_agent(data: dict):
    """Deny reason when a subagent launches an Agent outside runtime/delegation.json."""
    if not data.get("agent_id"):
        return None  # the lead may launch any agent
    caller = data.get("agent_type") or "?"
    target = (data.get("tool_input") or {}).get("subagent_type") or "general-purpose"
    allowed = _delegators().get(caller, [])
    if target in allowed:
        return None
    rights = ", ".join(allowed) if allowed else "none (leaf agent)"
    return (f"Sisyphus delegation rights: `{caller}` may not launch `{target}` (allowed: {rights}). "
            "Finish what you can and tell the lead in your result what it should delegate.")


def _lead_private_path(path: Path) -> bool:
    """True for the lead's own memory (~/.claude/projects/*/memory/) or session scratchpad (/tmp/claude-<uid>/).

    Checks both the lexical path and its resolved form against both raw and resolved roots, so a
    symlinked ~/.claude, projects dir or memory dir (e.g. memory -> external drive) still matches.
    """
    candidates = {Path(os.path.normpath(path)), path.resolve()}
    base = Path.home() / ".claude" / "projects"
    for projects in {base, base.resolve()}:
        for p in candidates:
            rel = p.relative_to(projects).parts if projects in p.parents else ()
            if len(rel) >= 3 and rel[1] == "memory":
                return True
    uid = os.getuid()
    raw = {Path(f"/tmp/claude-{uid}"), Path(f"/private/tmp/claude-{uid}")}
    scratch = raw | {s.resolve() for s in raw}
    return any(s in p.parents for s in scratch for p in candidates)


WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
ROLES = {"router", "writer"}


def session_role(root: Path):
    """(role, problem) from <root>/.omo/role: (None, None) without the file. A malformed or unreadable
    file counts as router; `problem` then says why, for the deny message."""
    role_file = root / ".omo" / "role"
    if not os.path.lexists(role_file):
        return None, None
    try:
        role = role_file.read_text().strip().lower()
    except (OSError, UnicodeDecodeError) as exc:
        return "router", f"cannot be read ({type(exc).__name__})"
    if role in ROLES:
        return role, None
    shown = role if len(role) <= 40 else role[:40] + "..."
    return "router", f"holds {shown!r} instead of `router` or `writer`" if role else "is empty"


def check_role_guard(data: dict):
    """Deny reason when a `router` session (not its subagents) writes outside .omo/, its memory or scratchpad."""
    if data.get("tool_name") not in WRITE_TOOLS or data.get("agent_id"):
        return None
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()).resolve()
    role, problem = session_role(root)
    if role != "router":
        return None
    tool_input = data.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not target:
        return None
    path = Path(target)
    if not path.is_absolute():
        path = root / path
    lexical = Path(os.path.normpath(path))
    allowed = root / ".omo"
    resolved = path.resolve()
    if resolved == allowed or allowed in resolved.parents or _lead_private_path(lexical):
        return None
    role_file = root / ".omo" / "role"
    state = (f"{role_file} {problem}, which counts as `router` (fail closed); write `router` or `writer` "
             "in it to state the role" if problem else f"{role_file} says `router`")
    return (f"Role guard: {state} (Orchestrateur / Sous-orchestrateur), "
            f"so this session only orchestrates and may write only under {allowed}, its memory dir and its "
            "scratchpad. Hand the edit to a Piste (writer session) or a category executor subagent; "
            "never work around this with Bash redirections.")


def on_pretool(data: dict) -> None:
    reason = check_role_guard(data)
    if reason:
        emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                     "permissionDecisionReason": reason}})
        return
    st = load_state(data.get("session_id", ""))
    if not st:
        return
    if data.get("tool_name") == "Agent":
        reason = check_nested_agent(data)
        if reason:
            emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                         "permissionDecisionReason": reason}})
        return
    mode = st.get("mode")
    if mode == "prometheus":
        reason = "Prometheus planning mode may only write plan artifacts under {allowed}. " \
                 "Execution belongs to /sisyphus start-work."
    elif mode in ORCHESTRATOR_MODES and not data.get("agent_id"):
        # Hook inputs carry agent_id only for subagent tool calls: those do the edits.
        reason = "Strict router: the {mode} lead only orchestrates and may write only under {allowed}, " \
                 "its memory dir (~/.claude/projects/*/memory/) and its session scratchpad (/tmp/claude-<uid>/). " \
                 "Delegate this edit to the matching category executor (quick, deep, bug-hunt, refactor-safe, " \
                 "visual-engineering, writing...) or hephaestus in the delivery pipeline."
    else:
        return
    tool_input = data.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not target:
        return
    root = Path(st.get("cwd") or data.get("cwd") or os.getcwd()).resolve()
    path = Path(target)
    if not path.is_absolute():
        path = root / path
    lexical = Path(os.path.normpath(path))
    path = path.resolve()
    allowed = root / ".omo"
    if path == allowed or allowed in path.parents:
        return
    if mode in ORCHESTRATOR_MODES and _lead_private_path(lexical):
        return
    emit({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason.format(allowed=allowed, mode=mode)}})


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def open_todos_from_transcript(transcript: str) -> list:
    """Open items from the latest TodoWrite list plus TaskCreate/TaskUpdate tasks."""
    latest = None
    pending_creates = {}  # tool_use id -> subject, until its result gives the task id
    tasks = {}  # task id -> {"subject", "status"}
    try:
        with open(transcript, encoding="utf-8") as fh:
            for line in fh:
                if not any(k in line for k in ('"TodoWrite"', '"TaskCreate"', '"TaskUpdate"', "created")):
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                content = (rec.get("message") or {}).get("content") or []
                for block in content if isinstance(content, list) else []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        name, args = block.get("name"), block.get("input") or {}
                        if name == "TodoWrite":
                            latest = args.get("todos")
                        elif name == "TaskCreate":
                            pending_creates[block.get("id")] = args.get("subject") or "?"
                        elif name == "TaskUpdate" and str(args.get("taskId")) in tasks:
                            task = tasks[str(args["taskId"])]
                            task["status"] = args.get("status") or task["status"]
                            task["subject"] = args.get("subject") or task["subject"]
                    elif block.get("type") == "tool_result" and block.get("tool_use_id") in pending_creates:
                        m = TASK_ID_RE.search(_result_text(block.get("content")))
                        subject = pending_creates.pop(block["tool_use_id"])
                        if m:
                            tasks[m.group(1)] = {"subject": subject, "status": "pending"}
    except OSError:
        return []
    todos = [t.get("content", "?") for t in (latest or []) if t.get("status") != "completed"]
    return todos + [t["subject"] for t in tasks.values() if t["status"] not in CLOSED_TASK_STATUSES]


def open_todos_from_files(root: Path, since: float, include_plans: bool = False) -> list:
    """Unchecked `- [ ]` items in .omo/todos (and .omo/plans for Atlas) edited this session."""
    items = []
    dirs = [root / ".omo" / "todos"] + ([root / ".omo" / "plans"] if include_plans else [])
    for d in dirs:
        if not d.is_dir():
            continue
        for f in d.glob("*.md"):
            if f.stat().st_mtime < since:
                continue
            for line in f.read_text(errors="ignore").splitlines():
                m = re.match(r"^\s*[-*]\s*\[ \]\s*(.+)", line)
                if m:
                    items.append(f"{m.group(1).strip()} ({f.name})")
    return items


def on_stop(data: dict) -> None:
    sid = data.get("session_id", "")
    st = load_state(sid)
    if not st or st.get("mode") == "prometheus":
        return
    if st.get("stop_blocks", 0) >= MAX_STOP_BLOCKS:
        return
    todos = open_todos_from_transcript(data.get("transcript_path") or "")
    todos += open_todos_from_files(Path(st.get("cwd") or os.getcwd()), st.get("started", 0),
                                   include_plans=st.get("mode") == "atlas")
    if not todos:
        return
    st["stop_blocks"] = st.get("stop_blocks", 0) + 1
    save_state(sid, st)
    listed = "\n".join(f"- {t}" for t in todos[:15])
    emit({"decision": "block", "reason": (
        f"[sisyphus todo-continuation {st['stop_blocks']}/{MAX_STOP_BLOCKS}] Open todos remain:\n{listed}\n"
        "Continue working on them. If one is blocked or no longer relevant, mark it completed or cancelled "
        "with a one-line reason, or ask the user — then stop.")})


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"prompt": on_prompt, "pretool": on_pretool, "stop": on_stop}.get(cmd, lambda _d: None)(data)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never break the user's session
        pass
