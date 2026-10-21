#!/usr/bin/env python3
"""Behavioral canary for the /sisyphus Claude Code port.

Each case runs `claude -p` headless in a fresh copy of fixture/, captures the
stream-json transcript, and checks delegation (Agent subagent_type), text,
and file effects. Runs on the user's Claude subscription.

  python3 run.py              # all cases
  python3 run.py quick-fix    # selected case ids
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / "cases.json").read_text())["cases"]
ALLOWED = ["Read", "Glob", "Grep", "Agent", "Write", "Edit", "Skill", "TodoWrite",
           "Bash(ls:*)", "Bash(rg:*)", "Bash(cat:*)", "Bash(python3 -m py_compile:*)", "Bash(mkdir:*)",
           "Bash(python3 -m unittest:*)", "Bash(python3 -m pytest:*)", "Bash(git diff:*)"]
TIMEOUT = 900


def run_case(case: dict) -> dict:
    work = Path(tempfile.mkdtemp(prefix=f"sisyphus-eval-{case['id']}-"))
    shutil.copytree(HERE / "fixture", work, dirs_exist_ok=True)
    before = {p.name: p.read_text() for p in work.iterdir() if p.is_file()}
    before_names = set(before)
    cmd = ["claude", "-p", case["prompt"], "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--allowedTools", *ALLOWED]
    try:
        proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=TIMEOUT)
        raw = proc.stdout
        if not raw.strip():
            print(f"[{case['id']}] claude exited {proc.returncode}: {proc.stderr[:300]}", file=sys.stderr)
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
    (work / ".eval-stream.jsonl").write_text(raw)  # full transcript for diagnosis
    agents, edits, denied, text = [], [], [], []
    per_message = {}  # lead assistant message id -> Agent calls launched in it
    sub_edits = []  # Write/Edit made inside subagents
    nested = []  # Agent calls made by subagents
    briefs = []  # prompts of the lead's Agent calls
    api_error = ""
    for line in raw.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            text.append(ev.get("result") or "")
            if ev.get("is_error") and ev.get("api_error_status"):
                api_error = f"API {ev['api_error_status']}: {(ev.get('result') or '')[:120]}"
        msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
        content = msg.get("content") if isinstance(msg.get("content"), list) else []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                inp = block.get("input") or {}
                if block.get("name") == "Agent":
                    agents.append(inp.get("subagent_type") or "general-purpose")
                    if ev.get("parent_tool_use_id") is not None:
                        nested.append(inp.get("subagent_type") or "general-purpose")
                    if ev.get("parent_tool_use_id") is None:
                        briefs.append(inp.get("prompt") or "")
                        mid = msg.get("id") or id(ev)
                        per_message[mid] = per_message.get(mid, 0) + 1
                if block.get("name") in ("Write", "Edit", "NotebookEdit"):
                    target = inp.get("file_path") or ""
                    (edits if ev.get("parent_tool_use_id") is None else sub_edits).append(target)
            if block.get("type") == "text":
                text.append(block.get("text") or "")
            if block.get("type") == "tool_result" and "Prometheus planning mode may only write" in json.dumps(block.get("content")):
                denied.append("prometheus-md-only")
            if block.get("type") == "tool_result" and "Strict router:" in json.dumps(block.get("content")):
                denied.append("strict-router")
    after = {p.name: p.read_text() for p in work.iterdir() if p.is_file()}
    changed = [n for n in before if after.get(n) != before[n]]
    omo_files = [str(p.relative_to(work)) for p in (work / ".omo").rglob("*") if p.is_file()] if (work / ".omo").exists() else []
    alltext = "\n".join(text)

    fails = []
    if "max_agents" in case and len(agents) > case["max_agents"]:
        fails.append(f"agents {agents} > max {case['max_agents']}")
    if "min_agents" in case and len(agents) < case["min_agents"]:
        fails.append(f"agents {agents} < min {case['min_agents']}")
    max_parallel = max(per_message.values(), default=0)
    if "min_parallel" in case and max_parallel < case["min_parallel"]:
        fails.append(f"max agents per lead message {max_parallel} < {case['min_parallel']}")
    if case.get("lead_must_not_edit"):
        lead_product = [e for e in edits if "/.omo/" not in e]
        if lead_product and len(denied) < len(lead_product):
            fails.append(f"lead edited product files: {lead_product}")
    if "agents_any_of" in case and not set(agents) & set(case["agents_any_of"]):
        fails.append(f"none of {case['agents_any_of']} delegated (got {agents})")
    for s in case.get("text_contains", []):
        if s not in alltext:
            fails.append(f"text missing {s!r}")
    if case.get("must_not_edit") and changed:
        fails.append(f"files changed {changed}")
    for n in case.get("product_files_unchanged", []):
        if n in changed:
            fails.append(f"product file changed: {n}")
    if "only_edits_under" in case:
        stray = [e for e in edits if case["only_edits_under"] not in e]
        if stray and not denied:
            fails.append(f"edits outside {case['only_edits_under']}: {stray}")
    wanted_any = case.get("briefs_contain_any")
    if wanted_any and not any(x in b for b in briefs for x in wanted_any):
        fails.append(f"no lead brief contains any of {wanted_any}")
    for n, s in case.get("file_contains", {}).items():
        if s not in after.get(n, ""):
            fails.append(f"{n} lacks {s!r}")
    if not raw.strip():
        fails.append("no output (auth or CLI failure)")
    if api_error:
        fails.insert(0, f"not a behavioral result, {api_error}")
    return {"id": case["id"], "pass": not fails, "fails": fails, "agents": agents, "max_parallel": max_parallel, "nested": nested,
            "lead_edits": edits, "subagent_edits": sub_edits,
            "changed": changed, "omo_files": omo_files, "denied": denied, "workdir": str(work)}


def main() -> None:
    wanted = set(sys.argv[1:])
    results = [run_case(c) for c in CASES if not wanted or c["id"] in wanted]
    for r in results:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"{status} {r['id']}: agents={r['agents']} parallel={r['max_parallel']} nested={r['nested']} changed={r['changed']} "
              f"lead_edits={r['lead_edits']} omo={r['omo_files']} denied={r['denied']}")
        for f in r["fails"]:
            print(f"   - {f}")
    print(f"{sum(r['pass'] for r in results)}/{len(results)} passed")
    (HERE / "last-run.json").write_text(json.dumps(results, indent=2))
    sys.exit(0 if all(r["pass"] for r in results) else 1)


if __name__ == "__main__":
    main()
