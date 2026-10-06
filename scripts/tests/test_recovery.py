from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "skills/harness/scripts/orch.py"


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = self.root / "store"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.forge_file = self.root / "forge.json"
        self.forge_log = self.root / "forge.log"
        self.forge = {"10": {"number": 10, "headRefOid": "a" * 40, "state": "OPEN", "isCrossRepository": False}}
        self.forge_file.write_text(json.dumps(self.forge))
        gh = self.bin / "gh"
        gh.write_text(f"#!{sys.executable}\n" + """import json, os, pathlib, sys
arguments = sys.argv[1:]
with open(os.environ['RECOVERY_FORGE_LOG'], 'a') as stream:
    stream.write(json.dumps(arguments) + '\\n')
if arguments[:2] != ['pr', 'view'] or arguments[3:5] != ['--repo', 'fixture/repo']:
    sys.exit(9)
row = json.loads(pathlib.Path(os.environ['RECOVERY_FORGE_FILE']).read_text()).get(arguments[2])
if row is None:
    sys.exit(4)
print(json.dumps(row))
""")
        gh.chmod(0o755)
        self.env = {**os.environ, "PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
                    "RECOVERY_FORGE_FILE": str(self.forge_file), "RECOVERY_FORGE_LOG": str(self.forge_log)}
        self.call("init")
        self.call("unit", "add", "u1", "--track", "build", "--brief", "briefs/original.md")
        self.call("unit", "set", "u1", "--state", "building", "--pr", "10", "--sha", "a" * 40)
        self.metadata = {"schema_version": 1, "program": "recovery-fixture",
                         "repository": {"name": "fixture/repo", "path": str(self.root)},
                         "authorization": "Implement and merge the declared issue.",
                         "units": [self.unit("u1", "owner-1", "worktree-A")]}
        self.input = self.root / "input.json"
        self.save_checkpoint()

    def unit(self, unit_id, owner_id, scope):
        return {"id": unit_id, "owner_id": owner_id, "work_scope": [scope],
                "brief": "Implement the original request and later correction.",
                "findings": ["The parser failed on empty input."], "evidence": ["reports/reproduction.md"],
                "next_actions": [{"id": "verify-current-head", "kind": "local", "status": "planned", "receipt": None}]}

    def call(self, *arguments, code=0):
        result = subprocess.run([sys.executable, str(SCRIPT), "--store", str(self.store),
                                 *arguments, "--json"], env=self.env, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, code, result.stderr + result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def save_checkpoint(self, code=0):
        self.input.write_text(json.dumps(self.metadata))
        return self.call("checkpoint", "--input", str(self.input), code=code)

    def host_state(self, state="failed", stopped=True, age=0, owners=None):
        path = self.root / "host.json"
        observed = datetime.now(timezone.utc) - timedelta(seconds=age)
        value = {"schema_version": 1, "observed_at": observed.isoformat(), "owners": owners or [
            {"id": "owner-1", "state": state, "writer_stopped": stopped}]}
        path.write_text(json.dumps(value))
        return str(path)

    def inventory(self):
        return {str(path.relative_to(self.store)): (path.read_bytes() if path.is_file() else None,
                                                   path.stat().st_mtime_ns, path.stat().st_mode)
                for path in self.store.rglob("*")}

    def test_checkpoint_carries_authorization_scope_and_consolidated_brief(self):
        checkpoint = json.loads((self.store / "checkpoint.json").read_text())
        self.assertEqual(checkpoint["authorization"], "Implement and merge the declared issue.")
        self.assertEqual(checkpoint["units"][0]["work_scope"], ["worktree-A"])
        result = self.call("pickup", "--host-state", self.host_state())
        unit = result["units"][0]
        self.assertTrue(unit["same_scope_replacement_allowed"])
        self.assertIn("create fresh owner", unit["next_safe_action"])
        packet = unit["replacement_packet"]
        self.assertEqual(packet["brief"], self.metadata["units"][0]["brief"])
        self.assertEqual(packet["findings"], ["The parser failed on empty input."])
        self.assertEqual(packet["evidence"], ["reports/reproduction.md"])
        self.assertEqual(packet["program"], "recovery-fixture")

    def test_crash_inside_completion_drain_before_reply_preserves_missing_inbox(self):
        pushed = self.call("inbox", "push", "owner-1", "u1", "completed", "--report", "reports/final.md")
        snippet = """import os, pathlib, runpy, sys
module = runpy.run_path(sys.argv[1])
replace = os.replace
def crash_after_move(source, target):
    replace(source, target)
    if pathlib.Path(source).name == 'inbox':
        os._exit(73)
os.replace = crash_after_move
module['main'](['--store', sys.argv[2], 'inbox', 'drain', '--json'])
"""
        result = subprocess.run([sys.executable, "-c", snippet, str(SCRIPT), str(self.store)],
                                env=self.env, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 73)
        self.assertEqual(result.stdout, "")
        self.assertFalse((self.store / "inbox").exists())
        before = self.inventory()
        state = self.host_state()
        pickup = self.call("pickup", "--host-state", state)
        unit = pickup["units"][0]
        self.assertFalse(unit["same_scope_replacement_allowed"])
        self.assertIn("reconcile retained completion", unit["next_safe_action"])
        pointer = unit["replacement_packet"]["retained_completions"][0]
        self.assertEqual(pointer["filename"], pushed["filename"])
        self.assertEqual(pointer["report"], "reports/final.md")
        self.assertEqual(len(pointer["batch"]), 32)
        self.assertIn("inbox", pickup["changes_since_checkpoint"])
        self.assertEqual(self.call("pickup", "--host-state", state), pickup)
        self.assertEqual(self.inventory(), before)

    def test_updates_after_checkpoint_survive_pickup_and_batch_replay(self):
        self.call("inbox", "push", "owner-1", "u1", "completed", "--report", "reports/final.md")
        batch = self.call("inbox", "drain")
        self.call("unit", "set", "u1", "--state", "done")
        self.call("ledger", "record", "10", "a" * 40, "unit-test-verified", "--evidence", "reports/final.md")
        self.assertEqual(self.call("inbox", "drain"), batch)
        result = self.call("pickup", "--host-state", self.host_state())
        self.assertEqual(result["units"][0]["verification"], "unit-test-verified")
        self.assertEqual(result["units"][0]["replacement_packet"]["current_unit"]["state"], "done")
        self.assertEqual(result["current_snapshot"]["inbox"]["inbox-claimed"]["batches"], [batch["batch"]])
        self.assertIn("units", result["changes_since_checkpoint"])
        self.assertIn("ledger", result["changes_since_checkpoint"])

    def test_stale_pending_init_and_unknown_host_never_certify_stopped_writer(self):
        for state, stopped, age in (("pending-init", True, 0), ("failed", False, 0),
                                    ("failed", True, 301), ("failed", True, -60), ("running", True, 0)):
            with self.subTest(state=state, stopped=stopped, age=age):
                unit = self.call("pickup", "--host-state", self.host_state(state, stopped, age))["units"][0]
                self.assertFalse(unit["same_scope_replacement_allowed"])
                self.assertIn("do not duplicate dispatch" if state == "running" else "hold or isolate", unit["next_safe_action"])
        before = self.inventory()
        result = self.call("pickup")
        self.assertEqual(result["units"][0]["owner_classification"], "unknown")
        self.assertIn("no host adapter", result["host_error"])
        self.assertEqual(self.inventory(), before)

    def test_fresh_bounded_explicit_host_adapter_and_invalid_output(self):
        adapter = self.root / "host.py"
        log = self.root / "host-request.json"
        adapter.write_text("import datetime, json, pathlib, sys\n"
                           f"pathlib.Path({str(log)!r}).write_text(sys.stdin.read())\n"
                           "print(json.dumps({'schema_version':1, 'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),"
                           "'owners':[{'id':'owner-1','state':'stopped','writer_stopped':True}]}))\n")
        command = self.root / "host-command.json"
        command.write_text(json.dumps({"read_only": True, "argv": [sys.executable, str(adapter)]}))
        result = self.call("pickup", "--host-command", str(command))
        self.assertTrue(result["units"][0]["same_scope_replacement_allowed"])
        self.assertEqual(json.loads(log.read_text()), {"schema_version": 1, "owner_ids": ["owner-1"]})
        adapter.write_text("print('invalid-json')\n")
        result = self.call("pickup", "--host-command", str(command))
        self.assertEqual(result["units"][0]["owner_classification"], "unknown")
        adapter.write_text("print('x' * (1024 * 1024 + 1))\n")
        result = self.call("pickup", "--host-command", str(command))
        self.assertIn("exceeds 1 MiB", result["host_error"])

    def test_nonreading_host_adapter_times_out_large_request_and_cleans_up(self):
        adapter = self.root / "nonreading-host.py"
        pid_file = self.root / "host.pid"
        adapter.write_text("import os, pathlib, time\n"
                           f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
                           "time.sleep(60)\n")
        command = self.root / "host-command.json"
        command.write_text(json.dumps({"read_only": True, "argv": [sys.executable, str(adapter)]}))
        snippet = """import json, runpy, sys, threading, types
module = runpy.run_path(sys.argv[1])
module['read_host_adapter'].__globals__['HOST_ADAPTER_TIMEOUT'] = 0.5
launched = []
launch = module['subprocess'].Popen
def record_process(*args, **kwargs):
    process = launch(*args, **kwargs)
    launched.append(process)
    return process
module['subprocess'].Popen = record_process
before = set(threading.enumerate())
owners, error = module['host_observation'](
    types.SimpleNamespace(host_state=None, host_command=sys.argv[2]),
    {'owner-' + str(index) + '-' + 'x' * 64 for index in range(50000)}, sys.argv[3])
print(json.dumps({'owners': owners, 'error': error,
                  'reaped': launched[0].poll() is not None,
                  'stdin_closed': launched[0].stdin.closed,
                  'stdout_closed': launched[0].stdout.closed,
                  'threads_cleaned': set(threading.enumerate()) == before}))
"""
        try:
            result = subprocess.run([sys.executable, "-c", snippet, str(SCRIPT), str(command), str(self.root)],
                                    text=True, capture_output=True, timeout=4)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(json.loads(result.stdout), {
                "owners": {}, "error": "host observation unavailable: host adapter exceeded 0.5 second deadline",
                "reaped": True, "stdin_closed": True, "stdout_closed": True, "threads_cleaned": True})
        finally:
            if pid_file.exists():
                try:
                    os.kill(int(pid_file.read_text()), signal.SIGTERM)
                except ProcessLookupError:
                    pass

    def test_changed_or_unknown_published_head_cannot_reuse_saved_verdict(self):
        self.call("ledger", "record", "10", "a" * 40, "unit-test-verified", "--evidence", "reports/old.md")
        self.save_checkpoint()
        self.forge["10"]["headRefOid"] = "b" * 40
        self.forge_file.write_text(json.dumps(self.forge))
        unit = self.call("pickup", "--host-state", self.host_state())["units"][0]
        self.assertTrue(unit["head_changed"])
        self.assertEqual(unit["verification"], "NOT-VERIFIED")
        self.assertEqual(unit["replacement_packet"]["evidence_status"], "stale")
        self.assertIn("verify the current published head", unit["next_safe_action"])
        self.forge_file.write_text("{}")
        unit = self.call("pickup", "--host-state", self.host_state())["units"][0]
        self.assertEqual(unit["verification"], "NOT-VERIFIED")
        self.assertFalse(unit["same_scope_replacement_allowed"])
        self.assertEqual(unit["replacement_packet"]["evidence_status"], "unknown")
        calls = [json.loads(line) for line in self.forge_log.read_text().splitlines()]
        self.assertTrue(all(call[:3] == ["pr", "view", "10"] for call in calls))

    def test_completed_and_merged_units_are_preserved_without_dispatch(self):
        self.call("unit", "set", "u1", "--state", "done")
        unit = self.call("pickup", "--host-state", self.host_state())["units"][0]
        self.assertIn("verify the current published head", unit["next_safe_action"])
        self.assertTrue(unit["same_scope_replacement_allowed"])
        self.assertEqual(unit["replacement_packet"]["current_unit"]["state"], "done")
        self.call("unit", "set", "u1", "--state", "merged")
        self.save_checkpoint()
        self.forge_file.write_text("{}")
        unit = self.call("pickup")["units"][0]
        self.assertTrue(unit["merged"])
        self.assertIn("preserve merged", unit["next_safe_action"])
        self.call("unit", "set", "u1", "--state", "building", "--pr", "11", "--sha", "b" * 40)
        unit = self.call("pickup")["units"][0]
        self.assertFalse(unit["merged"])

    def test_done_open_pr_requires_current_head_behavioral_verification(self):
        self.call("unit", "set", "u1", "--state", "done")
        self.call("ledger", "record", "10", "a" * 40, "unit-test-verified", "--evidence", "old-pass")
        self.save_checkpoint()
        cases = (("verifier-failed", "fix or reconcile", True),
                 ("verifier-blocked", "verification is blocked", False),
                 ("type-check-only", "fresh behavioral evidence", True),
                 ("unit-test-verified", "preserve completed work", False),
                 ("live-ui-verified", "preserve completed work", False))
        for head in ("a" * 40, "b" * 40):
            self.forge["10"]["headRefOid"] = head
            self.forge_file.write_text(json.dumps(self.forge))
            for verdict, expected_action, replacement_allowed in cases:
                with self.subTest(head=head, verdict=verdict):
                    self.call("ledger", "record", "10", head, verdict, "--evidence", "current-verdict")
                    before = self.inventory()
                    unit = self.call("pickup", "--host-state", self.host_state())["units"][0]
                    self.assertEqual(unit["verification"], verdict)
                    self.assertEqual(unit["head_changed"], head == "b" * 40)
                    self.assertIn(expected_action, unit["next_safe_action"])
                    self.assertEqual(unit["same_scope_replacement_allowed"], replacement_allowed)
                    self.assertEqual(unit["replacement_packet"]["current_unit"]["state"], "done")
                    self.assertEqual(unit["replacement_packet"]["current_head_ledger"]["evidence"], "current-verdict")
                    self.assertEqual(before, self.inventory())

    def test_done_changed_head_missing_verdict_and_unknown_forge_hold_completion(self):
        self.call("unit", "set", "u1", "--state", "done")
        self.call("ledger", "record", "10", "a" * 40, "unit-test-verified", "--evidence", "old-pass")
        self.save_checkpoint()
        self.forge["10"]["headRefOid"] = "b" * 40
        self.forge_file.write_text(json.dumps(self.forge))
        before = self.inventory()
        unit = self.call("pickup", "--host-state", self.host_state())["units"][0]
        self.assertEqual(unit["verification"], "NOT-VERIFIED")
        self.assertIn("fresh behavioral evidence", unit["next_safe_action"])
        self.assertTrue(unit["same_scope_replacement_allowed"])
        self.assertEqual(unit["replacement_packet"]["evidence_status"], "stale")
        self.forge_file.write_text("{}")
        unit = self.call("pickup", "--host-state", self.host_state())["units"][0]
        self.assertEqual(unit["next_safe_action"], "hold; published PR state is unknown")
        self.assertFalse(unit["same_scope_replacement_allowed"])
        self.assertEqual(unit["replacement_packet"]["current_unit"]["state"], "done")
        self.assertEqual(before, self.inventory())

    def test_completed_external_receipt_cannot_override_nonpassing_open_pr(self):
        actions = self.metadata["units"][0]["next_actions"]
        actions[0].update(status="completed", receipt="local-receipt")
        actions.append({"id": "external-publish", "kind": "external", "status": "completed", "receipt": "receipt-1"})
        self.save_checkpoint()
        cases = (("verifier-failed", "fix or reconcile", True),
                 ("verifier-blocked", "verification is blocked", False),
                 ("type-check-only", "fresh behavioral evidence", True),
                 (None, "fresh behavioral evidence", True))
        for verdict, expected_action, replacement_allowed in cases:
            with self.subTest(verdict=verdict):
                head = "b" * 40 if verdict is None else "a" * 40
                self.forge["10"]["headRefOid"] = head
                self.forge_file.write_text(json.dumps(self.forge))
                if verdict:
                    self.call("ledger", "record", "10", head, verdict, "--evidence", "nonpass")
                before = self.inventory()
                unit = self.call("pickup", "--host-state", self.host_state())["units"][0]
                self.assertIn(expected_action, unit["next_safe_action"])
                self.assertEqual(unit["same_scope_replacement_allowed"], replacement_allowed)
                self.assertEqual(unit["replacement_packet"]["completed_action_receipts"], actions)
                self.assertEqual(before, self.inventory())

    def test_failed_done_unit_still_requires_safe_writer_ownership(self):
        self.call("unit", "set", "u1", "--state", "done")
        self.call("ledger", "record", "10", "a" * 40, "verifier-failed", "--evidence", "failure")
        self.save_checkpoint()
        for state, stopped, expected in (("running", False, "observe existing owner"),
                                         ("unknown", False, "previous writer is not confirmed stopped"),
                                         ("failed", False, "previous writer is not confirmed stopped")):
            with self.subTest(state=state):
                before = self.inventory()
                unit = self.call("pickup", "--host-state", self.host_state(state, stopped))["units"][0]
                self.assertFalse(unit["same_scope_replacement_allowed"])
                self.assertIn(expected, unit["next_safe_action"])
                self.assertEqual(unit["verification"], "verifier-failed")
                self.assertEqual(before, self.inventory())

    def test_done_local_unit_without_pr_preserves_historical_completion(self):
        self.call("unit", "add", "local-unit", "--track", "build")
        self.call("unit", "set", "local-unit", "--state", "done")
        self.metadata["units"].append(self.unit("local-unit", "local-owner", "local-scope"))
        self.save_checkpoint()
        before = self.inventory()
        unit = self.call("pickup")["units"][1]
        self.assertIn("preserve completed work", unit["next_safe_action"])
        self.assertFalse(unit["same_scope_replacement_allowed"])
        self.assertEqual(unit["replacement_packet"]["current_unit"]["state"], "done")
        self.assertEqual(before, self.inventory())

    def test_action_receipts_cannot_regress_or_disappear_and_findings_are_retained(self):
        action = self.metadata["units"][0]["next_actions"][0]
        action.update(status="pending")
        self.save_checkpoint()
        self.metadata["units"][0]["next_actions"] = []
        checkpoint = self.save_checkpoint()
        self.assertEqual(checkpoint["units"][0]["next_actions"][0]["status"], "pending")
        unit = self.call("pickup", "--host-state", self.host_state())["units"][0]
        self.assertFalse(unit["same_scope_replacement_allowed"])
        self.assertIn("reconcile pending action receipts", unit["next_safe_action"])
        action.update(status="completed", receipt="https://fixture.invalid/action/1")
        self.metadata["units"][0]["next_actions"] = [action]
        self.save_checkpoint()
        self.metadata["units"][0]["findings"] = ["The correction also needs UTF-8 input."]
        self.metadata["units"][0]["evidence"] = []
        self.metadata["units"][0]["next_actions"] = []
        checkpoint = self.save_checkpoint()
        self.assertEqual(checkpoint["units"][0]["next_actions"], [action])
        self.assertEqual(len(checkpoint["units"][0]["findings"]), 2)
        self.assertEqual(checkpoint["units"][0]["evidence"], ["reports/reproduction.md"])
        self.metadata["units"][0]["next_actions"] = [{**action, "status": "planned", "receipt": None}]
        before = (self.store / "checkpoint.json").read_bytes()
        self.assertIn("regress a completed", self.save_checkpoint(code=1))
        self.assertEqual((self.store / "checkpoint.json").read_bytes(), before)

    def test_overlapping_active_or_unknown_writer_forces_hold(self):
        self.call("unit", "add", "u2", "--track", "build")
        self.metadata["units"].append(self.unit("u2", "owner-2", "worktree-A"))
        self.save_checkpoint()
        owners = [{"id": "owner-1", "state": "stopped", "writer_stopped": True},
                  {"id": "owner-2", "state": "running", "writer_stopped": False}]
        for observation in (owners, owners[:1]):
            unit = self.call("pickup", "--host-state", self.host_state(owners=observation))["units"][0]
            self.assertFalse(unit["same_scope_replacement_allowed"])
            self.assertEqual(unit["overlapping_unconfirmed_owners"], ["owner-2"])
            self.assertIn("overlapping owners", unit["next_safe_action"])

    def test_resolved_findings_stay_resolved_on_stale_checkpoint_refresh(self):
        finding = self.metadata["units"][0]["findings"][0]
        self.metadata["units"][0]["findings"] = []
        self.metadata["units"][0]["resolved_findings"] = [finding]
        checkpoint = self.save_checkpoint()
        self.assertEqual(checkpoint["units"][0]["findings"], [])
        self.assertEqual(checkpoint["units"][0]["resolved_findings"], [finding])
        self.metadata["units"][0]["findings"] = [finding]
        del self.metadata["units"][0]["resolved_findings"]
        checkpoint = self.save_checkpoint()
        self.assertEqual(checkpoint["units"][0]["findings"], [])
        self.assertEqual(checkpoint["units"][0]["resolved_findings"], [finding])

    def test_schema_and_corruption_errors_are_actionable(self):
        self.metadata["units"][0]["work_scope"] = []
        self.assertIn("nonempty string list", self.save_checkpoint(code=1))
        checkpoint_path = self.store / "checkpoint.json"
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoint["snapshot"]["inbox"]["inbox"]["pointers"] = [{"broken": True}]
        checkpoint_path.write_text(json.dumps(checkpoint))
        self.assertIn("checkpoint inbox pointer", self.call("pickup", code=1))

    def test_pickup_does_not_create_a_lock_and_works_while_writer_lock_is_held(self):
        (self.store / ".orch.lock").unlink()
        state = self.host_state()
        before = self.inventory()
        first = self.call("pickup", "--host-state", state)
        self.assertEqual(first, self.call("pickup", "--host-state", state))
        self.assertEqual(self.inventory(), before)
        self.assertFalse((self.store / ".orch.lock").exists())
        if os.name != "nt":
            import fcntl
            with (self.store / ".orch.lock").open("w") as stream:
                fcntl.flock(stream, fcntl.LOCK_EX)
                self.call("pickup", "--host-state", state)


if __name__ == "__main__":
    unittest.main()
