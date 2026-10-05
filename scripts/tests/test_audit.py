import hashlib
import json
import time
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/harness/scripts/audit.py"
HOST = ROOT / "scripts/tests/fixtures/audit_host.py"
START = "2026-10-05T00:00:00Z"
DUE = "2026-10-05T01:00:00Z"


class AuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = self.root / "store"
        subprocess.run([sys.executable, str(SCRIPT.with_name("orch.py")), "--store", str(self.store), "init"],
                       check=True, capture_output=True)
        self.queue = {path.name: path.read_bytes() for path in self.store.iterdir() if path.is_file()}
        self.checkpoint = self.root / "checkpoint.json"
        self.metadata = {"schema_version": 1, "program": "fixture/program", "repo": str(self.root),
                         "authorization": "Implement scoped queue. Hold merge until operator approves.",
                         "resume": "Read checkpoint and gates before assigning a writer.",
                         "units": [{"id": "u1", "state": "needs-review"}],
                         "owners": [{"id": "owner-1", "scope": ["src/module.py"]}],
                         "published_heads": [{"pr": 4, "sha": "a" * 40}],
                         "findings": ["Review still required"], "evidence": [],
                         "next_actions": ["Inspect owner"], "unresolved_gates": ["operator-merge"]}
        self.checkpoint.write_text(json.dumps(self.metadata))
        self.state = self.root / "host.json"
        self.state.write_text(json.dumps({"registrations": [], "calls": [], "mode": "normal"}))
        self.adapter = self.root / "adapter.json"
        self.adapter.write_text(json.dumps({"schema_version": 1, "argv": [sys.executable, str(HOST), str(self.state)],
                                            "timeout_seconds": 1}))
        self.evidence = self.root / "audit.txt"
        self.evidence.write_text("Confirmed owner liveness and current unresolved operator gate.\n")
        self.report = self.root / "report.json"
        self.report.write_text(json.dumps({"progress": [], "failures": [], "required_actions": []}))

    def call(self, *args, now=START, code=0):
        result = subprocess.run([sys.executable, str(SCRIPT), "--store", str(self.store), "--now", now, *args],
                                text=True, capture_output=True, timeout=8)
        self.assertEqual(result.returncode, code, result.stderr + result.stdout)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def ensure(self, **kwargs):
        return self.call("ensure", "--checkpoint", str(self.checkpoint), "--adapter", str(self.adapter), **kwargs)

    def receipt(self):
        return json.loads((self.store / "audit-registration.json").read_text())

    def host(self, **changes):
        state = json.loads(self.state.read_text())
        state.update(changes)
        self.state.write_text(json.dumps(state))
        return state

    def assert_queue_preserved(self):
        for name, data in self.queue.items():
            self.assertEqual((self.store / name).read_bytes(), data, name)

    def test_registration_suspension_missed_pickup_completion_and_owned_stop(self):
        first = self.ensure()
        self.assertEqual(first["registration_status"], "armed")
        self.assertTrue(first["notify"])
        self.assertEqual(first["next_expected_audit"], DUE)
        self.assertFalse(self.ensure(now="2026-10-05T00:30:00Z")["notify"])
        host = self.host()
        self.assertEqual(host["calls"].count("ensure"), 1)
        host["registrations"].append({"registration_id": "unrelated", "program_key": "other", "status": "enabled"})
        self.host(registrations=host["registrations"])
        pickup = self.call("pickup", now="2026-10-05T04:00:00Z")
        self.assertEqual((pickup["next_expected_audit"], pickup["overdue_seconds"]), (DUE, 10800))
        self.assertTrue(pickup["notify"])
        self.assertFalse(self.call("pickup", now="2026-10-05T05:00:00Z")["notify"])
        self.assertEqual(pickup["checkpoint"]["metadata"], self.metadata)
        self.assertIn("gates.md", pickup["checkpoint"]["queue_files"])
        args = ("complete", "--delivery-id", "delivery-1", "--due-at", DUE,
                "--evidence", str(self.evidence), "--report", str(self.report))
        completed = self.call(*args, now="2026-10-05T04:00:00Z")
        self.assertFalse(completed["notify"])
        self.assertEqual(completed["last_completed_audit"]["evidence"]["sha256"],
                         hashlib.sha256(self.evidence.read_bytes()).hexdigest())
        self.assertEqual(completed["next_expected_audit"], "2026-10-05T02:00:00Z")
        self.assertFalse(self.call(*args, now="2026-10-05T05:00:00Z")["notify"])
        self.assertEqual(len(list((self.store / "audit-completions").glob("*.json"))), 1)
        stopped = self.call("stop")
        self.assertEqual((stopped["desired"], stopped["registration_status"]), ("stopped", "stopped"))
        self.assertEqual(self.host()["registrations"][1]["status"], "enabled")
        self.call("pickup")
        self.ensure()
        self.assertEqual(self.host()["calls"].count("ensure"), 1)
        self.assert_queue_preserved()

    def test_lost_creation_response_reconciles_without_duplicate(self):
        self.host(mode="lost-create")
        first = self.ensure(code=1)
        self.assertEqual(first["registration_status"], "unconfirmed")
        self.assertEqual(first["pending"]["operation"], "ensure")
        self.assertEqual(len(self.host()["registrations"]), 1)
        self.host(mode="normal")
        self.assertEqual(self.call("pickup")["registration_status"], "armed")
        self.assertEqual(self.host()["calls"].count("ensure"), 1)

    def test_cancellation_timeout_preserves_stopped_and_retries_without_rearming(self):
        self.ensure()
        self.host(mode="cancel-timeout")
        stopped = self.call("stop", code=1)
        self.assertEqual((stopped["desired"], stopped["registration_status"]), ("stopped", "cancellation-unconfirmed"))
        operation_id = stopped["pending"]["operation_id"]
        self.host(mode="normal")
        picked = self.call("pickup")
        self.assertEqual(picked["registration_status"], "stopped")
        cancels = [row for row in self.receipt()["host_responses"] if row["operation"] == "cancel"]
        self.assertEqual([row["operation_id"] for row in cancels], [operation_id, operation_id])
        self.assertEqual(self.host()["calls"].count("ensure"), 1)

    def test_fresh_readback_prevents_cancelling_changed_ownership(self):
        self.ensure()
        self.host(mode="wrong-owner")
        stopped = self.call("stop", code=1)
        self.assertEqual(stopped["registration_status"], "cancellation-unconfirmed")
        self.assertNotIn("cancel", self.host()["calls"])

    def test_bad_observations_fail_without_external_mutation(self):
        self.ensure()
        for mode in ("malformed", "duplicate", "oversized", "hang"):
            with self.subTest(mode=mode):
                before = self.host()["calls"].count("ensure")
                self.host(mode=mode)
                self.assertEqual(self.call("pickup", code=1)["registration_status"], "unconfirmed")
                self.assertEqual(self.host()["calls"].count("ensure"), before)
        self.assert_queue_preserved()

    def test_unsupported_host_keeps_complete_checkpoint_and_status_is_read_only(self):
        result = self.call("ensure", "--checkpoint", str(self.checkpoint))
        self.assertEqual(result["registration_status"], "unavailable")
        self.assertEqual(result["checkpoint"]["metadata"], self.metadata)
        self.assertIsNone(result["registration_id"])
        before = (self.store / "audit-registration.json").read_bytes()
        self.call("status", now="2026-10-05T04:00:00Z")
        self.assertEqual((self.store / "audit-registration.json").read_bytes(), before)
        self.assertEqual(self.host()["calls"], [])
        self.assert_queue_preserved()

    def test_unsupported_adapter_records_no_armed_claim(self):
        self.host(mode="unsupported")
        self.assertEqual(self.ensure()["registration_status"], "unavailable")
        self.assertEqual(self.host()["calls"], ["discover"])

    def test_changed_identity_adapter_and_missing_checkpoint_fields_fail_closed(self):
        self.ensure()
        for field in ("program", "repo"):
            changed = dict(self.metadata, **{field: "changed"})
            self.checkpoint.write_text(json.dumps(changed))
            self.ensure(code=2)
        self.checkpoint.write_text(json.dumps(self.metadata))
        command = json.loads(self.adapter.read_text())
        command["timeout_seconds"] = 2
        self.adapter.write_text(json.dumps(command))
        self.ensure(code=2)
        for field in ("authorization", "owners", "published_heads", "unresolved_gates"):
            incomplete = dict(self.metadata)
            del incomplete[field]
            self.checkpoint.write_text(json.dumps(incomplete))
            self.ensure(code=2)
        self.assertEqual(self.host()["calls"].count("ensure"), 1)

    def test_checkpoint_refresh_preserves_registration_and_overdue_obligation(self):
        self.ensure()
        changed = dict(self.metadata, next_actions=["Reconcile owner report"])
        self.checkpoint.write_text(json.dumps(changed))
        result = self.ensure(now="2026-10-05T04:00:00Z")
        self.assertEqual(result["checkpoint"]["metadata"], changed)
        self.assertEqual(result["next_expected_audit"], DUE)
        self.assertEqual(self.host()["calls"].count("ensure"), 1)

    def test_completed_audit_requires_evidence_matching_due_and_immutable_delivery(self):
        self.ensure()
        args = ("complete", "--delivery-id", "d1", "--due-at", DUE,
                "--evidence", str(self.evidence), "--report", str(self.report))
        self.call(*args, code=2)
        self.evidence.write_text("")
        self.call(*args, now=DUE, code=2)
        self.evidence.write_text("Owner report captured.\n")
        self.report.write_text(json.dumps({"progress": ["u1 pushed"], "failures": [], "required_actions": []}))
        self.assertTrue(self.call(*args, now=DUE)["notify"])
        self.evidence.write_text("Changed replay evidence.\n")
        self.call(*args, now=DUE, code=2)
        self.assertEqual(len(list((self.store / "audit-completions").glob("*.json"))), 1)

    def test_adapter_limits_validate_before_registration(self):
        for timeout in (0, 31, True, "1"):
            command = json.loads(self.adapter.read_text())
            command["timeout_seconds"] = timeout
            self.adapter.write_text(json.dumps(command))
            self.ensure(code=2)
        self.assertFalse((self.store / "audit-registration.json").exists())
        self.assertEqual(self.host()["calls"], [])

    def test_disabled_pickup_is_visible_and_only_explicit_ensure_rearms(self):
        self.ensure()
        host = self.host()
        host["registrations"][0]["status"] = "disabled"
        self.host(registrations=host["registrations"])
        pickup = self.call("pickup", now="2026-10-05T04:00:00Z")
        self.assertEqual(pickup["registration_status"], "suspended")
        self.assertEqual(pickup["next_expected_audit"], DUE)
        self.assertTrue(pickup["notify"])
        self.assertFalse(self.call("pickup", now="2026-10-05T05:00:00Z")["notify"])
        self.assertEqual(self.host()["calls"].count("ensure"), 1)
        self.assertEqual(self.ensure()["registration_status"], "armed")
        self.assertEqual(self.host()["calls"].count("ensure"), 2)

    def test_retained_batch_and_large_checkpoint_remain_readable(self):
        subprocess.run([sys.executable, str(SCRIPT.with_name("orch.py")), "--store", str(self.store),
                        "inbox", "push", "owner", "u1", "done", "--report", "reports/u1.md"],
                       check=True, capture_output=True)
        subprocess.run([sys.executable, str(SCRIPT.with_name("orch.py")), "--store", str(self.store),
                        "inbox", "drain"], check=True, capture_output=True)
        (self.store / "standing-orders.md").write_text("x" * 40000)
        (self.store / "preferences.md").write_text("y" * 40000)
        before = {str(path.relative_to(self.store)): path.read_bytes()
                  for path in self.store.rglob("*") if path.is_file()}
        result = self.ensure()
        files = result["checkpoint"]["queue_files"]
        self.assertTrue(any(name.startswith("inbox-claimed/") for name in files))
        self.assertGreater((self.store / "audit-registration.json").stat().st_size, 65536)
        self.assertEqual(self.call("status")["registration_status"], "armed")
        self.assertEqual(self.call("pickup")["registration_status"], "armed")
        for name, contents in before.items():
            self.assertEqual((self.store / name).read_bytes(), contents)
        for response in self.receipt()["host_responses"]:
            self.assertIn("stdout", json.loads(Path(response["path"]).read_text()))
            self.assertEqual(response["sha256"], hashlib.sha256(Path(response["path"]).read_bytes()).hexdigest())

    def test_pickup_exposes_changed_gates_without_granting_authority(self):
        self.metadata["unresolved_gates"] = []
        self.checkpoint.write_text(json.dumps(self.metadata))
        self.assertFalse(self.ensure()["recovery_hold"])
        (self.store / "gates.md").write_text("# Gates\n\nOperator approval pending.\n")
        result = self.call("pickup")
        self.assertTrue(result["recovery_hold"])
        self.assertTrue(result["notify"])
        self.assertFalse(self.call("pickup")["notify"])
        self.assertNotEqual(result["current_queue_files"]["gates.md"], result["checkpoint"]["queue_files"]["gates.md"])
        self.assertEqual(result["checkpoint"]["metadata"]["authorization"], self.metadata["authorization"])

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux process-group liveness proof")
    def test_inherited_pipe_holder_is_bounded_and_killed(self):
        self.host(mode="pipe-holder")
        result = self.ensure(code=1)
        self.assertIn("pipes", result["error"])
        pid = self.host()["child_pid"]
        for _ in range(20):
            proc = Path(f"/proc/{pid}/stat")
            if not proc.exists() or proc.read_text().split()[2] == "Z":
                break
            time.sleep(0.02)
        else:
            self.fail("adapter pipe holder survived its bounded operation")
        self.assertEqual(self.host()["calls"], ["discover"])

    def test_checkpoint_refresh_cannot_replace_frozen_authorization_or_gates(self):
        self.ensure()
        for field in ("authorization", "unresolved_gates"):
            changed = dict(self.metadata)
            changed[field] = "New grant" if field == "authorization" else []
            self.checkpoint.write_text(json.dumps(changed))
            self.ensure(code=2)
            self.assertEqual(self.call("pickup")["checkpoint"]["metadata"], self.metadata)
