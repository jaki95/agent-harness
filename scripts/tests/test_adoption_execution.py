import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adoption_execution as worker
from adoption_git import AdoptionGit, Stopped


BASE = "a" * 40
OLD = "b" * 40
NEW = "c" * 40
REPO = "fixture/repo"


class Forge:
    def __init__(self, registry):
        self.base, self.branch = BASE, None
        self.contents = {worker.REGISTRY: json.dumps(registry), "skills/first/SKILL.md": "old instructions"}
        self.tree, self.number, self.merged = {}, None, False
        self.published, self.opened, self.merges, self.reruns = [], [], [], []
        self.ci = ("passed", [51], "")
        self.lost = False

    def ref(self, branch):
        return self.base if branch == "main" else self.branch

    def entries(self, base, paths):
        return "e" * 40, {p: {"path": p, "mode": "100644"} if p in self.contents else None for p in paths}

    def read_blob(self, entry):
        return self.contents[entry["path"]]

    def commit(self, base, old, tree, updates, message):
        self.tree = updates
        return hashlib.sha1(json.dumps([old, updates]).encode()).hexdigest()

    def publish(self, branch, old, new):
        self.branch = new
        self.published.append(new)
        if self.lost:
            self.lost = False
            raise OSError("lost successful branch update response")

    def pull(self, branch, known=None):
        if self.number is not None:
            return {"pr": self.number, "url": "https://github.com/fixture/repo/pull/3",
                    "head": self.branch, "merged": self.merged, "closed": self.merged}

    def open_pull(self, branch, title, body):
        self.title, self.body = title, body
        self.number = 3
        self.opened.append(branch)
        return self.pull(branch)

    def describe_pull(self, pr, title, body):
        self.title, self.body = title, body

    def checks(self, pr, head, base, workflows):
        return self.ci

    def failure_evidence(self, errors):
        return errors

    def attempt(self, run_id):
        return 1, "completed"

    def rerun(self, run_id):
        self.reruns.append(run_id)

    def merge(self, pr, head):
        assert head == self.branch
        self.merges.append(head)
        self.merged = True
        return {"status": "merged"}


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.items = []
        evidence = {}
        skills = {}
        for i, skill in enumerate(["first", "second"], 1):
            key = skill + "/upstream"
            self.items.append({"key": key, "revision": NEW, "id": i, "decision": "keep",
                               "digest": str(i) * 64, "behavior": "retain", "preserve": "original scope",
                               "verify": "check", "why": "The local skill already covers this behavior."})
            skills[skill] = {"reviewed_on": "2025-01-01", "maintenance_notes": "keep local scheduling",
                "sources": [{"id": "upstream", "relationship": "adapted", "repository": "https://example.org/repo",
                             "ref": "main", "paths": ["watched/"], "baseline_revision": OLD,
                             "last_reviewed_revision": OLD, "last_incorporated_revision": OLD}]}
            evidence[key] = {"key": key, "observed_revision": NEW, "reviewed_revision": OLD,
                             "repository": "https://example.org/repo", "changed_files": [],
                             "local_files": {"skills/first/SKILL.md": "old instructions"} if i == 1 else {}}
        self.forge = Forge({"schema_version": 1, "skills": skills})
        self.responses = []
        self.calls = []
        def ask(role, payload, schema):
            self.calls.append((role, payload))
            return self.responses.pop(0)
        self.ctx = worker.Execution(REPO, 7, Path(directory.name), None, evidence, ask)
        adapter = patch.object(worker, "AdoptionGit", return_value=self.forge)
        adapter.start()
        self.addCleanup(adapter.stop)

    def run_group(self, items=None, recheck=None):
        items = self.items if items is None else items
        return worker.execute_group(self.ctx, 13, items, recheck or (lambda: items))

    def replacement(self, text="new instructions", authority=False):
        return {"in_scope": True, "authority": authority, "reason": "allowed",
                "edits": [{"path": "skills/first/SKILL.md", "text": text, "delete": False}]}

    def test_registry_only_real_diff_and_idempotent_merge(self):
        published = self.run_group()
        self.assertEqual(published["status"], "published")
        self.assertEqual(list(self.forge.tree), [worker.REGISTRY])
        self.assertIn("2 sources", self.forge.title)
        self.assertIn("The local skill already covers this behavior.", self.forge.body)
        self.assertIn("issues/7#issuecomment-13", self.forge.body)
        self.assertIn(NEW, self.forge.body)
        record = json.loads(self.forge.tree[worker.REGISTRY][1])["skills"]["first"]["sources"][0]
        self.assertEqual(record["last_reviewed_revision"], NEW)
        self.assertEqual(record["last_incorporated_revision"], OLD)
        self.assertEqual(self.run_group()["status"], "merged")
        repeat = self.run_group([])
        self.assertEqual(repeat["digests"], [x["digest"] for x in self.items])
        self.assertEqual(len(self.forge.merges), 1)
        self.assertEqual(len(self.forge.opened), 1)

    def test_hold_after_verdict_stops_submission_and_splits_out_held_item(self):
        self.run_group()
        reads = iter([self.items, self.items[:1]])
        self.assertEqual(self.run_group(recheck=lambda: next(reads))["status"], "changed")
        self.assertEqual(self.forge.merges, [])
        self.assertEqual(self.run_group(self.items[:1])["status"], "published")
        records = json.loads(self.forge.tree[worker.REGISTRY][1])["skills"]
        self.assertEqual(records["second"]["sources"][0]["last_reviewed_revision"], OLD)
        self.assertEqual(self.run_group(self.items[:1])["status"], "merged")
        self.assertIn("Keep local behavior for first/upstream", self.forge.title)
        self.assertNotIn("second/upstream", self.forge.body)
        self.assertEqual(len(self.forge.published), 2)
        self.assertEqual(len(self.forge.opened), 1)

    def test_independent_runs_inspect_actual_answer_and_exact_patch(self):
        self.items[0]["decision"] = "adapt"
        self.responses = [self.replacement(), {"needs_tools": False, "task": "Demonstrate the new behavior"},
                          {"answer": "I retained ownership while applying the new instructions"},
                          {"passed": True, "authority": False, "reason": "correct response", "witness": ""}]
        self.run_group()
        self.assertEqual(self.run_group()["status"], "merged")
        self.assertEqual(self.calls[2][1]["instructions"]["skills/first/SKILL.md"], "new instructions")
        self.assertEqual(self.calls[3][1]["observed_answer"], "I retained ownership while applying the new instructions")

    def test_out_of_scope_write_cannot_create_branch(self):
        self.items[0]["decision"] = "adapt"
        answer = self.replacement()
        answer["edits"][0]["path"] = ".github/workflows/check.yml"
        self.responses.append(answer)
        self.assertEqual(self.run_group()["status"], "blocked")
        self.assertFalse(self.forge.published)

    def test_authority_guard_distinguishes_docs_edits_from_rule_changes(self):
        path = "skills/harness/playbooks/shipping.md"
        self.assertFalse(worker.authority_change(path, "Post receipt", "Post the receipt"))
        self.assertTrue(worker.authority_change(path, "Require owner approval", "Merge immediately"))

    def test_successful_ci_still_needs_named_representative_behavior(self):
        self.items[0]["decision"] = "adapt"
        self.responses = [self.replacement(), {"needs_tools": True, "task": "Exercise real scheduler"},
                          {"passed": True, "authority": False, "reason": "works", "witness": "untested"}]
        self.run_group()
        with patch.object(self.forge, "witnesses", return_value=["run 51: scheduling"], create=True):
            self.assertEqual(self.run_group()["status"], "blocked")
        self.assertFalse(self.forge.merges)

    def test_manual_authority_pr_never_requests_merge(self):
        self.items[0]["decision"] = "adopt"
        self.responses.append(self.replacement(authority=True))
        self.run_group()
        self.assertEqual(self.run_group()["status"], "manual")
        self.assertFalse(self.forge.merges)

    def test_crash_after_ref_update_recovers_owned_commit(self):
        self.forge.lost = True
        with self.assertRaises(OSError):
            self.run_group()
        self.assertEqual(self.run_group()["status"], "published")
        self.assertEqual(self.run_group()["status"], "merged")
        self.assertEqual(len(self.forge.published), 1)

    def test_lost_pr_creation_response_binds_actual_pr_before_merge(self):
        create = self.forge.open_pull
        def lost(*args):
            create(*args)
            raise OSError("response lost")
        with patch.object(self.forge, "open_pull", side_effect=lost):
            with self.assertRaises(OSError):
                self.run_group()
        self.assertEqual(self.run_group()["status"], "merged")
        self.assertEqual(self.run_group([])["digests"], [x["digest"] for x in self.items])
        self.assertEqual(len(self.forge.opened), 1)

    def test_partial_rerun_response_reconciles_each_run_separately(self):
        self.run_group()
        failures = [{"workflow": "check.yml", "id": n, "conclusion": "timed_out", "attempt": 1}
                    for n in [41, 42]]
        self.forge.ci = ("failed", failures, "")
        def submit(run_id):
            self.forge.reruns.append(run_id)
            if run_id == 41:
                raise OSError("lost response")
        with patch.object(self.forge, "rerun", side_effect=submit):
            self.assertEqual(self.run_group()["status"], "blocked")
        self.assertEqual(self.forge.reruns, [41, 42])
        with patch.object(self.forge, "attempt", return_value=(2, "in_progress")):
            self.assertEqual(self.run_group()["status"], "waiting")
        self.assertEqual(self.forge.reruns, [41, 42])

    def test_rejected_async_request_stops_without_a_second_mutation(self):
        self.run_group()
        with patch.object(self.forge, "merge", return_value={"status": "pending", "uuid": "id"}) as submit:
            self.assertEqual(self.run_group()["status"], "waiting")
            with patch.object(self.forge, "merge_status", return_value="failed", create=True) as read:
                self.assertEqual(self.run_group()["status"], "blocked")
                read.assert_called_once_with(3, self.forge.branch, {"status": "pending", "uuid": "id"})
            self.assertEqual(submit.call_count, 1)

    def test_ref_moved_outside_worker_fails_closed(self):
        self.run_group()
        self.forge.branch = "d" * 40
        self.assertEqual(self.run_group()["status"], "blocked")
        self.assertFalse(self.forge.merges)

    def test_code_repair_limit_across_invocations(self):
        self.items[0]["decision"] = "adapt"
        self.responses = [self.replacement(str(i)) for i in range(3)]
        self.run_group()
        self.forge.ci = ("failed", [{"workflow": "check.yml", "id": 41, "conclusion": "failure", "attempt": 1}], "")
        self.assertEqual(self.run_group()["status"], "published")
        self.assertEqual(self.run_group()["status"], "published")
        self.assertIn("Two code repairs", self.run_group()["message"])
        self.assertEqual(len(self.forge.opened), 1)

    def test_only_one_infrastructure_rerun(self):
        self.run_group()
        self.forge.ci = ("failed", [{"workflow": "check.yml", "id": 41, "conclusion": "timed_out", "attempt": 1}], "")
        self.assertEqual(self.run_group()["status"], "waiting")
        self.run_group()
        self.assertEqual(self.forge.reruns, [41])


class CheckReadbackTests(unittest.TestCase):
    def setUp(self):
        self.git = AdoptionGit(REPO, object())
        self.receipt = {"capture_status": "complete", "review_threads": [], "current_checks": [],
            "after": {"head_sha": NEW, "base_sha": BASE, "state": "OPEN", "review_decision": None,
                      "merge_state": "CLEAN", "mergeable": "MERGEABLE"}}
        self.run = {"workflow_runs": [{"head_sha": NEW, "event": "pull_request", "path": ".github/workflows/check.yml",
            "head_repository": {"full_name": REPO}, "id": 44, "run_attempt": 1,
            "status": "completed", "conclusion": "success"}]}

    def checks(self):
        with patch.object(self.git, "api", return_value=self.run), patch.object(self.git, "helper", return_value=self.receipt):
            return self.git.checks(2, NEW, BASE, ["check.yml"])

    def test_named_workflow_must_pass_on_current_head(self):
        self.assertEqual(self.checks()[:2], ("passed", [44]))
        self.run["workflow_runs"][0]["head_sha"] = OLD
        self.assertEqual(self.checks()[0], "waiting")
        self.run["workflow_runs"][0]["head_sha"] = NEW
        self.run["workflow_runs"][0]["head_repository"] = {"full_name": "stranger/fork"}
        self.assertEqual(self.checks()[0], "waiting")

    def test_threads_and_rules_block_merge(self):
        self.receipt["review_threads"] = [{"resolved": False}]
        self.assertEqual(self.checks()[0], "blocked")
        self.receipt["review_threads"] = []
        self.receipt["after"]["merge_state"] = "BLOCKED"
        self.assertEqual(self.checks()[0], "blocked")
        self.receipt["after"]["merge_state"] = "CLEAN"
        self.receipt["current_checks"] = [{"observed_state": "fail"}]
        self.assertEqual(self.checks()[0], "blocked")

    def test_tree_walk_rejects_link_or_truncation(self):
        def api(method, endpoint):
            if endpoint.startswith("git/commits/"):
                return {"tree": {"sha": OLD}}
            return {"truncated": False, "tree": [{"path": "skills", "mode": "120000", "type": "blob", "sha": NEW}]}
        with patch.object(self.git, "api", side_effect=api):
            with self.assertRaisesRegex(Stopped, "non-directory"):
                self.git.entries(BASE, ["skills/test/entry"])
