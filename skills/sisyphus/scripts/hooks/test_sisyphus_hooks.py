"""Unit tests for sisyphus_hooks.py. Run: python3 -m unittest discover -s scripts/hooks"""
import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sisyphus_hooks as hooks  # noqa: E402


def _tool_use(tool_id, name, tool_input):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]}}


def _tool_result(tool_id, text):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tool_id, "content": text}]}}


class TranscriptCase(unittest.TestCase):
    def transcript(self, records):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")
        self.addCleanup(os.unlink, path)
        return path


class TodoWriteTests(TranscriptCase):
    def test_latest_todowrite_list_wins(self):
        path = self.transcript([
            _tool_use("t1", "TodoWrite", {"todos": [{"content": "a", "status": "pending"}]}),
            _tool_use("t2", "TodoWrite", {"todos": [
                {"content": "a", "status": "completed"}, {"content": "b", "status": "in_progress"}]}),
        ])
        self.assertEqual(hooks.open_todos_from_transcript(path), ["b"])


class TaskToolTests(TranscriptCase):
    def test_created_tasks_stay_open_until_completed(self):
        path = self.transcript([
            _tool_use("c1", "TaskCreate", {"subject": "Write tests", "description": "x"}),
            _tool_result("c1", "Task #1 created successfully: Write tests"),
            _tool_use("c2", "TaskCreate", {"subject": "Fix hook", "description": "y"}),
            _tool_result("c2", [{"type": "text", "text": "Task #2 created successfully: Fix hook"}]),
            _tool_use("u1", "TaskUpdate", {"taskId": "1", "status": "completed"}),
        ])
        self.assertEqual(hooks.open_todos_from_transcript(path), ["Fix hook"])

    def test_deleted_task_is_closed(self):
        path = self.transcript([
            _tool_use("c1", "TaskCreate", {"subject": "Obsolete"}),
            _tool_result("c1", "Task #7 created successfully: Obsolete"),
            _tool_use("u1", "TaskUpdate", {"taskId": "7", "status": "deleted"}),
        ])
        self.assertEqual(hooks.open_todos_from_transcript(path), [])

    def test_task_updated_subject_is_reported(self):
        path = self.transcript([
            _tool_use("c1", "TaskCreate", {"subject": "Old"}),
            _tool_result("c1", "Task #3 created successfully: Old"),
            _tool_use("u1", "TaskUpdate", {"taskId": "3", "subject": "New", "status": "in_progress"}),
        ])
        self.assertEqual(hooks.open_todos_from_transcript(path), ["New"])

    def test_todowrite_and_tasks_combine(self):
        path = self.transcript([
            _tool_use("t1", "TodoWrite", {"todos": [{"content": "todo", "status": "pending"}]}),
            _tool_use("c1", "TaskCreate", {"subject": "task"}),
            _tool_result("c1", "Task #1 created successfully: task"),
        ])
        self.assertEqual(sorted(hooks.open_todos_from_transcript(path)), ["task", "todo"])


class MachinePromptTests(unittest.TestCase):
    def test_harness_injected_prompts_are_detected(self):
        for prompt in (
            "<task-notification>\n<summary>ultrawork done</summary>\n</task-notification>",
            "Another Claude session sent a message:\n<agent-message from=\"x\">\n[Subagent hand-back] hyperplan ulw",
            "<ci-monitor-event>team mode</ci-monitor-event>",
            "  <system-reminder>ulw</system-reminder>",
        ):
            self.assertTrue(hooks.is_machine_prompt(prompt), prompt)

    def test_user_prompts_are_not_machine_prompts(self):
        for prompt in ("ulw fix the bug", "/sisyphus hyperplan", "team mode please"):
            self.assertFalse(hooks.is_machine_prompt(prompt), prompt)


class OnPromptTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(hooks, "STATE_DIR", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        hooks.save_state("s1", {"mode": "sisyphus", "cwd": tmp.name, "started": time.time(), "stop_blocks": 2})

    def run_prompt(self, prompt):
        buf = io.StringIO()
        with redirect_stdout(buf):
            hooks.on_prompt({"session_id": "s1", "prompt": prompt})
        out = buf.getvalue()
        return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""

    def test_user_keyword_injects_and_resets_counter(self):
        ctx = self.run_prompt("ulw refactor this")
        self.assertIn("ultrawork", ctx)
        self.assertEqual(hooks.load_state("s1")["stop_blocks"], 0)

    def test_keyword_context_states_the_banner_itself(self):
        self.assertIn("ULTRAWORK MODE ENABLED!", self.run_prompt("ulw explain app.py"))
        self.assertIn("HYPERPLAN MODE ENABLED!", self.run_prompt("hyperplan the migration"))

    def test_subagent_report_does_not_trigger_keywords_or_reset(self):
        ctx = self.run_prompt(
            "Another Claude session sent a message:\n<agent-message from=\"a\">\n"
            "[Subagent hand-back] mentions hyperplan, ultrawork and team mode")
        self.assertNotIn("detected", ctx)
        self.assertNotIn("HYPERPLAN", ctx)
        self.assertEqual(hooks.load_state("s1")["stop_blocks"], 2)


class AtlasPlanTests(unittest.TestCase):
    def test_atlas_mode_also_reads_open_plan_checkboxes(self):
        with tempfile.TemporaryDirectory() as root:
            plans = Path(root) / ".omo" / "plans"
            plans.mkdir(parents=True)
            (plans / "p.md").write_text("- [x] done\n- [ ] step two\n")
            since = time.time() - 60
            self.assertEqual(hooks.open_todos_from_files(Path(root), since), [])
            self.assertEqual(hooks.open_todos_from_files(Path(root), since, include_plans=True),
                             ["step two (p.md)"])


class PreToolTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        patcher = mock.patch.object(hooks, "STATE_DIR", self.root / "state")
        patcher.start()
        self.addCleanup(patcher.stop)

    def decision(self, mode, rel_path, agent_id=None, tool="Edit"):
        hooks.save_state("s1", {"mode": mode, "cwd": str(self.root), "started": time.time(), "stop_blocks": 0})
        data = {"session_id": "s1", "tool_name": tool, "tool_input": {"file_path": str(rel_path)}}
        if agent_id:
            data["agent_id"] = agent_id
        buf = io.StringIO()
        with redirect_stdout(buf):
            hooks.on_pretool(data)
        out = buf.getvalue()
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "allow"

    def test_sisyphus_lead_cannot_edit_project_files(self):
        self.assertEqual(self.decision("sisyphus", "src/app.py"), "deny")

    def test_atlas_lead_cannot_edit_project_files(self):
        self.assertEqual(self.decision("atlas", "src/app.py"), "deny")

    def test_lead_may_write_omo_state(self):
        self.assertEqual(self.decision("sisyphus", ".omo/plans/p.md"), "allow")

    def test_lead_may_write_its_memory(self):
        memory = Path.home() / ".claude/projects/x/memory/m.md"
        for tool in ("Edit", "Write"):
            self.assertEqual(self.decision("sisyphus", memory, tool=tool), "allow")
            self.assertEqual(self.decision("atlas", memory, tool=tool), "allow")

    def test_lead_may_write_its_scratchpad(self):
        uid = os.getuid()
        for scratch in (f"/private/tmp/claude-{uid}/proj/sess/scratchpad/n.md",
                        f"/tmp/claude-{uid}/proj/sess/scratchpad/n.md"):
            for tool in ("Edit", "Write"):
                self.assertEqual(self.decision("sisyphus", scratch, tool=tool), "allow")

    def test_lead_write_to_project_file_stays_denied(self):
        self.assertEqual(self.decision("sisyphus", self.root / "src" / "app.py", tool="Write"), "deny")
        self.assertEqual(self.decision("sisyphus", Path.home() / ".claude/projects/x/notes.md"), "deny")

    def _symlinked_home(self, link_rel):
        """Temp HOME where <home>/<link_rel> is a symlink to a directory elsewhere."""
        home, elsewhere = self.root / "home", self.root / "elsewhere"
        link = home / link_rel
        link.parent.mkdir(parents=True)
        elsewhere.mkdir()
        link.symlink_to(elsewhere, target_is_directory=True)
        patcher = mock.patch.object(hooks.Path, "home", return_value=home)
        patcher.start()
        self.addCleanup(patcher.stop)
        return home

    def test_lead_may_write_memory_through_symlinked_projects(self):
        home = self._symlinked_home(".claude/projects")
        (home / ".claude/projects/x/memory").mkdir(parents=True)
        self.assertEqual(self.decision("sisyphus", home / ".claude/projects/x/memory/m.md", tool="Write"), "allow")
        self.assertEqual(self.decision("sisyphus", self.root / "src" / "app.py", tool="Write"), "deny")
        self.assertEqual(self.decision("prometheus", home / ".claude/projects/x/memory/m.md"), "deny")

    def test_lead_may_write_memory_through_symlinked_memory_dir(self):
        home = self._symlinked_home(".claude/projects/x/memory")
        self.assertEqual(self.decision("sisyphus", home / ".claude/projects/x/memory/m.md", tool="Write"), "allow")
        self.assertEqual(self.decision("sisyphus", home / ".claude/projects/x/notes.md"), "deny")
        self.assertEqual(self.decision("sisyphus", self.root / "elsewhere" / "../src/app.py"), "deny")

    def test_prometheus_gets_no_memory_allowance(self):
        self.assertEqual(self.decision("prometheus", Path.home() / ".claude/projects/x/memory/m.md"), "deny")

    def test_subagents_may_edit(self):
        self.assertEqual(self.decision("sisyphus", "src/app.py", agent_id="a123"), "allow")

    def test_hephaestus_mode_edits_directly(self):
        self.assertEqual(self.decision("hephaestus", "src/app.py"), "allow")

    def test_prometheus_stays_md_only_even_for_subagents(self):
        self.assertEqual(self.decision("prometheus", "src/app.py", agent_id="a123"), "deny")


class RoleGuardTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        for patcher in (mock.patch.object(hooks, "STATE_DIR", self.root / "state"),
                        mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.root)})):
            patcher.start()
            self.addCleanup(patcher.stop)

    def set_role(self, text):
        (self.root / ".omo").mkdir(exist_ok=True)
        (self.root / ".omo" / "role").write_text(text)

    def output(self, rel_path, tool="Write", agent_id=None):
        data = {"session_id": "no-sisyphus", "tool_name": tool, "tool_input": {"file_path": str(rel_path)}}
        if agent_id:
            data["agent_id"] = agent_id
        buf = io.StringIO()
        with redirect_stdout(buf):
            hooks.on_pretool(data)
        out = buf.getvalue()
        return json.loads(out)["hookSpecificOutput"] if out else None

    def decision(self, rel_path, tool="Write", agent_id=None):
        out = self.output(rel_path, tool, agent_id)
        return out["permissionDecision"] if out else "allow"

    def reason(self, rel_path="src/app.py"):
        return self.output(rel_path)["permissionDecisionReason"]

    def test_no_role_file_means_no_guard(self):
        self.assertEqual(self.decision("src/app.py"), "allow")

    def test_router_cannot_write_project_files(self):
        self.set_role("router\n")
        for tool in ("Write", "Edit", "NotebookEdit"):
            self.assertEqual(self.decision("src/app.py", tool=tool), "deny")

    def test_router_may_write_omo_memory_and_scratchpad(self):
        self.set_role("router")
        self.assertEqual(self.decision(".omo/status.md"), "allow")
        self.assertEqual(self.decision(Path.home() / ".claude/projects/x/memory/m.md"), "allow")
        self.assertEqual(self.decision(f"/tmp/claude-{os.getuid()}/p/s/scratchpad/n.md"), "allow")

    def test_writer_may_write(self):
        self.set_role("writer")
        self.assertEqual(self.decision("src/app.py"), "allow")

    def test_malformed_role_fails_closed(self):
        for text in ("", "Router writer", "admin"):
            self.set_role(text)
            self.assertEqual(self.decision("src/app.py"), "deny", text)

    def test_router_message_names_the_role(self):
        self.set_role("router\n")
        self.assertIn("says `router`", self.reason())

    def test_malformed_role_message_says_why(self):
        for text, expected in (("", "is empty"), ("admin", "holds 'admin'")):
            self.set_role(text)
            reason = self.reason()
            self.assertIn(expected, reason, text)
            self.assertIn("counts as `router`", reason, text)
            self.assertNotIn("says `router`", reason, text)

    def test_unreadable_role_message_says_why(self):
        role = self.root / ".omo" / "role"
        role.parent.mkdir(exist_ok=True)
        role.mkdir()  # a directory where the file should be: read_text raises
        reason = self.reason()
        self.assertIn("cannot be read", reason)
        self.assertIn("counts as `router`", reason)

    def test_router_subagents_may_edit(self):
        self.set_role("router")
        self.assertEqual(self.decision("src/app.py", agent_id="a1"), "allow")

    def test_router_guard_ignores_other_tools(self):
        self.set_role("router")
        self.assertEqual(self.decision("src/app.py", tool="Read"), "allow")


class NestedAgentTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(hooks, "STATE_DIR", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        hooks.save_state("s1", {"mode": "sisyphus", "cwd": tmp.name, "started": time.time(), "stop_blocks": 0})

    def decision(self, target, caller=None):
        data = {"session_id": "s1", "tool_name": "Agent", "tool_input": {"subagent_type": target}}
        if caller:
            data.update({"agent_id": "a1", "agent_type": caller})
        buf = io.StringIO()
        with redirect_stdout(buf):
            hooks.on_pretool(data)
        out = buf.getvalue()
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "allow"

    def test_lead_launches_anything(self):
        self.assertEqual(self.decision("hephaestus"), "allow")

    def test_hephaestus_launches_executors_and_helpers(self):
        self.assertEqual(self.decision("deep", "hephaestus"), "allow")
        self.assertEqual(self.decision("explore", "hephaestus"), "allow")

    def test_executor_launches_read_only_helpers_only(self):
        self.assertEqual(self.decision("explore", "deep"), "allow")
        self.assertEqual(self.decision("quick", "deep"), "deny")

    def test_leaves_cannot_delegate(self):
        self.assertEqual(self.decision("explore", "explore"), "deny")
        self.assertEqual(self.decision("librarian", "quick"), "deny")

    def test_ocx_agents_are_never_nested(self):
        self.assertEqual(self.decision("ocx-gpt-6-sol", "hephaestus"), "deny")


if __name__ == "__main__":
    unittest.main()
