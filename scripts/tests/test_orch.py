"""Exercise durable bookkeeping and GitHub frontier discovery in temporary stores."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "skills/harness/scripts/orch.py"
orch = types.ModuleType("harness_orch")
exec(compile(SCRIPT.read_text(), str(SCRIPT), "exec"), orch.__dict__)


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = self.root / "program"
        self.call("init")

    def call(self, *arguments, code=0):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = orch.main(["--store", str(self.store), *arguments, "--json"])
        self.assertEqual(result, code, stderr.getvalue())
        return json.loads(stdout.getvalue()) if stdout.getvalue() else stderr.getvalue()

    def add_unit(self):
        return self.call("unit", "add", "u1", "--track", "build", "--brief", "briefs/u1.md")

    def pr(self, number, branch, base="main", state="OPEN", sha=None, fork=False):
        return {"number": number, "headRefName": branch, "baseRefName": base,
                "headRefOid": sha or str(number % 10) * 40, "state": state,
                "isCrossRepository": fork}

    def fake_gh(self, rows):
        def read(arguments, repo):
            if arguments[0] == "repo":
                return {"nameWithOwner": "fixture/repo", "defaultBranchRef": {"name": "main"}}
            return rows[int(arguments[2])].copy()
        return read

    def discover(self, rows, order, code=0):
        with patch.object(orch, "gh_json", side_effect=self.fake_gh(rows)):
            return self.call("frontier", "set", "--repo", str(self.root), "--prs", order, code=code)

    def test_init_preserves_existing_records_and_unit_updates(self):
        self.add_unit()
        self.call("unit", "set", "u1", "--state", "done", "--branch", "work/u1", "--pr", "10", "--sha", "a" * 40)
        self.call("init")
        row = self.call("unit", "get", "u1")
        self.assertEqual((row["state"], row["pr"], row["sha"]), ("done", "10", "a" * 40))
        self.assertEqual(self.call("unit", "counts"), {"done": 1})
        self.assertEqual(self.call("unit", "list", "--track", "build", "--state", "done"), [row])
        self.call("unit", "add", "u1", "--track", "build", code=1)

    def test_ledger_never_reuses_verdict_for_a_different_head(self):
        self.call("ledger", "record", "10", "a" * 40, "unit-test-verified", "--evidence", "reports/a.md")
        missing = self.call("ledger", "check", "10", "b" * 40, code=2)
        self.assertEqual(missing["verdict"], "NOT-VERIFIED")
        self.call("ledger", "record", "10", "a" * 40, "verifier-failed", "--evidence", "reports/failure.md", "--verifier", "reviewer")
        self.assertEqual(self.call("ledger", "check", "10", "a" * 40)["verdict"], "verifier-failed")
        self.assertEqual(self.call("ledger", "summary"), {"verifier-failed": 1})

    def test_drain_replays_unacknowledged_batch_and_keeps_later_arrivals(self):
        self.add_unit()
        self.call("inbox", "push", "worker-1", "u1", "done", "--report", "reports/u1.md")
        batch = self.call("inbox", "drain")
        self.call("unit", "set", "u1", "--state", "needs-verify")
        self.call("inbox", "push", "worker-2", "u2", "done")
        self.assertEqual(self.call("inbox", "drain"), batch)
        self.assertEqual(self.call("inbox", "count"), 2)
        self.call("inbox", "ack", batch["batch"])
        self.call("inbox", "ack", batch["batch"])
        next_batch = self.call("inbox", "drain")
        self.assertEqual([row["unit"] for row in next_batch["pointers"]], ["u2"])
        self.assertNotEqual(next_batch["batch"], batch["batch"])

    def test_interruption_after_claim_is_recovered_on_next_invocation(self):
        self.call("inbox", "push", "worker", "u1", "done")
        original = Path.mkdir

        def interrupt(path, *args, **kwargs):
            if path == self.store / "inbox" and not path.exists():
                raise OSError("simulated interruption after claiming the batch")
            return original(path, *args, **kwargs)

        with patch.object(Path, "mkdir", interrupt):
            self.call("inbox", "drain", code=1)
        batch = self.call("inbox", "drain")
        self.assertEqual([row["unit"] for row in batch["pointers"]], ["u1"])
        self.assertTrue((self.store / "inbox").is_dir())
        self.call("inbox", "ack", batch["batch"])
        self.assertEqual(self.call("inbox", "count"), 0)

    def test_peek_does_not_claim_and_invalid_ack_cannot_escape_store(self):
        self.call("inbox", "push", "worker", "u1", "done")
        self.assertEqual(len(self.call("inbox", "drain", "--peek")), 1)
        self.assertEqual(list((self.store / "inbox-claimed").iterdir()), [])
        self.call("inbox", "ack", "../../outside", code=1)
        self.assertEqual(self.call("inbox", "count"), 1)

    def test_unreadable_pointer_is_not_deleted(self):
        (self.store / "inbox/broken.tsv").write_text("broken\trow\n")
        self.call("inbox", "drain", code=1)
        self.assertTrue((self.store / "inbox/broken.tsv").exists())

    def test_frontier_uses_published_heads_and_declared_linear_order(self):
        rows = {10: self.pr(10, "work/base", sha="a" * 40),
                11: self.pr(11, "work/child", "work/base", sha="b" * 40)}
        value = self.discover(rows, "10,11")
        self.assertEqual([row["sha"] for row in value["prs"]], ["a" * 40, "b" * 40])
        self.assertEqual(value["lowestUnmerged"], 10)
        before = (self.store / "frontier.json").read_text()
        self.discover(rows, "11,10", code=1)
        self.assertEqual((self.store / "frontier.json").read_text(), before)

    def test_merged_prefix_survives_github_retargeting(self):
        rows = {10: self.pr(10, "work/base", state="MERGED"),
                11: self.pr(11, "work/child")}
        self.assertEqual(self.discover(rows, "10,11")["lowestUnmerged"], 11)
        rows[11]["state"] = "MERGED"
        self.assertIsNone(self.discover(rows, "10,11")["lowestUnmerged"])

    def test_rejects_ambiguous_disconnected_forked_or_closed_chains(self):
        invalid = [
            {10: self.pr(10, "a"), 11: self.pr(11, "b")},
            {10: self.pr(10, "a", "b"), 11: self.pr(11, "b", "a")},
            {10: self.pr(10, "a"), 11: self.pr(11, "b", "a"), 12: self.pr(12, "c", "a")},
            {10: self.pr(10, "a", "outside")},
            {10: self.pr(10, "a", fork=True)},
            {10: self.pr(10, "a", state="CLOSED")},
            {10: self.pr(10, "a"), 11: self.pr(11, "b", "a", state="MERGED")},
        ]
        for rows in invalid:
            with self.subTest(rows=rows):
                self.discover(rows, ",".join(map(str, rows)), code=1)
        self.assertEqual(orch.frontier(self.store)["generation"], 0)

    def test_discovery_drift_preserves_previous_frontier(self):
        rows = {10: self.pr(10, "work/base")}
        self.discover(rows, "10")
        before = (self.store / "frontier.json").read_text()
        normal = self.fake_gh(rows)
        calls = 0

        def moving(arguments, repo):
            nonlocal calls
            row = normal(arguments, repo)
            if arguments[0] == "pr":
                calls += 1
                if calls == 2:
                    row["headRefOid"] = "f" * 40
            return row

        with patch.object(orch, "gh_json", side_effect=moving):
            self.call("frontier", "set", "--repo", str(self.root), code=1)
        self.assertEqual((self.store / "frontier.json").read_text(), before)

    def test_frontier_cannot_refresh_from_another_repository(self):
        rows = {10: self.pr(10, "work/base")}
        self.discover(rows, "10")
        before = (self.store / "frontier.json").read_text()
        normal = self.fake_gh(rows)

        def wrong_repository(arguments, repo):
            value = normal(arguments, repo)
            if arguments[0] == "repo":
                value["nameWithOwner"] = "other/repo"
            return value

        with patch.object(orch, "gh_json", side_effect=wrong_repository):
            self.call("frontier", "set", "--repo", str(self.root), code=1)
        self.assertEqual((self.store / "frontier.json").read_text(), before)

    def test_gh_failure_or_invalid_sha_cannot_seed_a_frontier(self):
        with patch.object(orch.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "denied")):
            self.call("frontier", "set", "--repo", str(self.root), "--prs", "10", code=1)
        self.discover({10: self.pr(10, "a", sha="unknown")}, "10", code=1)
        self.assertEqual(orch.frontier(self.store)["generation"], 0)

    def test_gates_require_explicit_resolution_and_status_is_derived(self):
        self.add_unit()
        self.call("standing", "add", "Only the authorized stacker changes bases.")
        self.call("gate", "park", "release", "--question", "Ship now?", "--options", "ship,wait", "--default", "wait")
        first = self.call("status")
        self.assertEqual(first["summary"]["openGateIds"], ["release"])
        self.assertEqual(self.call("status")["changed"], "no derived changes")
        self.assertEqual(self.call("gate", "list")[0]["Status"], "open")
        self.call("gate", "resolve", "release", "--answer", "ship")
        self.assertEqual(self.call("status")["summary"]["openGateIds"], [])
        self.assertIn("| release | resolved | Ship now? |", (self.store / "status.md").read_text())
        self.assertEqual(self.call("standing", "show")[0]["number"], 1)

    def test_table_sanitization_and_corruption_rejection(self):
        row = self.call("unit", "add", "=SUM(A1)", "--track", "+build\tunsafe\nline")
        self.assertEqual(row["id"], "'=SUM(A1)")
        self.assertEqual(row["track"], "'+build unsafe line")
        self.assertEqual(self.call("unit", "get", "=SUM(A1)"), row)
        (self.store / "units.tsv").write_text("id\ttrack\tstate\tbranch\tpr\tsha\tbrief\nshort\trow\n")
        self.call("unit", "counts", code=1)

    def test_active_lock_blocks_another_process_and_exit_releases_it(self):
        snippet = ("import runpy,sys; from pathlib import Path; "
                   "m=runpy.run_path(sys.argv[1]); "
                   "lock=m['locked'](Path(sys.argv[2])); lock.__enter__(); "
                   "print('locked',flush=True); sys.stdin.read()")
        child = subprocess.Popen([sys.executable, "-c", snippet, str(SCRIPT), str(self.store)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            self.call("unit", "add", "u1", "--track", "build", code=1)
            child.terminate()
            child.wait(timeout=10)
            self.add_unit()
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)

    def test_cli_runs_from_unrelated_working_directory_and_env_store(self):
        environment = {**os.environ, "ORCH_STORE": str(self.store), "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([sys.executable, str(SCRIPT), "unit", "get", "missing", "--json"],
                                cwd=self.root, env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unit missing not found", result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPT), "unit", "add", "cli", "--track", "build", "--json"],
                                cwd=self.root, env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["id"], "cli")


if __name__ == "__main__":
    unittest.main()
