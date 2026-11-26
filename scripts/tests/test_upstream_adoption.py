import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor_upstream as monitor
import review_upstream as review
import upstream_adoption as adoption
from test_adoption_execution import BASE, NEW, OLD, Forge
from test_review_upstream import CHANGE


class IssueClient:
    base = "repos/fixture/repo/issues"

    def __init__(self):
        self.notes = []
        self.issue = {"number": 4, "state": "open", "user": {"login": monitor.ACTIONS_LOGIN}}
        self.source = {"key": "first/upstream", "repository": "https://example.org/repo", "ref": "main",
                       "reviewed": OLD, "observed_revision": NEW, "status": "pending", "changes": [monitor.asdict(CHANGE)],
                       "paths": ["watched/"], "error": "", "missing_paths": []}
        self.snapshot([self.source])
        self.head = BASE

    def snapshot(self, items):
        snap = {"errors": [], "sources": items}
        self.issue["body"] = monitor.issue_body(snap, monitor.fingerprint(snap), 1)

    def request(self, method, endpoint, payload=None):
        if method == "GET" and endpoint.endswith("/issues/4"):
            return self.issue.copy()
        if method == "GET" and endpoint.endswith("/git/ref/heads/main"):
            return {"object": {"sha": self.head}}
        raise AssertionError((method, endpoint))

    def issues(self):
        return [self.issue.copy()]

    def comments(self, number):
        assert number == 4
        return copy.deepcopy(self.notes)

    def add(self, author, body):
        c = {"id": len(self.notes) + 100, "created_at": "now", "updated_at": "now",
             "user": {"login": author, "type": "Bot" if author.endswith("[bot]") else "User"}, "body": body}
        self.notes.append(c)
        return c

    def comment(self, number, body):
        return self.add("adopter[bot]", body)

    def edit(self, number, **fields):
        self.issue.update(fields)


class AdoptionFlowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.client = IssueClient()
        self.src = {"key": "first/upstream", "repository": self.client.source["repository"],
                    "observed_revision": NEW, "changed_files": [monitor.asdict(CHANGE)], "reviewed_revision": OLD,
                    "local_files": {"skills/first/SKILL.md": "old instructions"}, "maintenance_notes": "Keep existing API"}
        self.answer = {"decision": "keep", "behavior": "Retain local behavior", "preserve": "Entry point",
                       "verify": "Compare runtime bytes", "why": "Established local preference", "depends": []}
        self.questions = []
        self.worker = adoption.Worker("fixture/repo", "Maintainer", "adopter[bot]", self.client, self.directory,
                                      self.ask, gather=self.gather)
        record = {"maintenance_notes": "Keep existing API", "reviewed_on": "2025-01-01", "sources": [{
            "id": "upstream", "relationship": "adapted", "repository": self.src["repository"],
            "ref": "main", "paths": ["watched/"], "baseline_revision": OLD, "last_reviewed_revision": OLD,
            "last_incorporated_revision": OLD}]}
        self.git = Forge({"schema_version": 1, "skills": {"first": record}})
        mock = patch.object(adoption.execution, "AdoptionGit", return_value=self.git)
        mock.start()
        self.addCleanup(mock.stop)

    def gather(self, repo, queue, scratch):
        return review.Evidence(self.client.head, (dict(self.src),))

    def ask(self, role, payload, schema):
        self.questions.append(role)
        if role == adoption.DISCUSS:
            return {"answer": "This keeps the local entry point.", "revisions": []}
        return self.answer

    def test_issue_approval_exact_head_merge_and_clean_closeout(self):
        self.worker.reconcile()
        self.assertIn("Proposal P1", self.client.notes[0]["body"])
        self.client.add("Maintainer", "Why keep this?")
        self.client.add("bystander", "approve P1")
        self.worker.reconcile(4)
        self.assertFalse(self.git.opened)
        self.assertIn("local entry point", self.client.notes[-1]["body"])
        self.client.add("Maintainer", "approve P1 item 1")
        self.worker.reconcile(4)
        self.assertEqual(len(self.git.opened), 1)
        self.assertIn("https://github.com/fixture/repo/pull/3", self.client.notes[-1]["body"])
        self.worker.reconcile(4)
        self.assertEqual([self.git.branch], self.git.merges)
        self.assertIn("Host update pending", self.client.notes[-1]["body"])
        self.assertIn("1 · first/upstream (keep)", self.client.notes[-1]["body"])
        self.client.snapshot([])
        self.worker.reconcile()
        self.assertEqual(self.client.issue["state"], "closed")
        notes_before = list(self.client.notes)
        self.worker.reconcile()
        self.assertEqual(self.client.notes, notes_before)
        self.assertEqual(self.questions, [adoption.PROPOSE, adoption.DISCUSS])

    def test_offline_approval_and_later_hold_never_publish(self):
        self.worker.reconcile()
        self.client.add("Maintainer", "approve P1")
        self.client.add("Maintainer", "hold P1 item 1")
        self.worker.reconcile()
        self.assertFalse(self.git.opened)
        self.assertFalse(self.git.merges)

    def test_discussion_revises_proposal_and_old_approval_cannot_execute(self):
        self.worker.reconcile()
        self.client.add("Maintainer", "Please adapt instead")
        self.client.add("Maintainer", "approve P1")
        self.worker.ask = lambda *args: {"answer": "I revised the proposal.", "revisions": [
            {**self.answer, "key": self.src["key"], "decision": "adapt", "behavior": "Adopt the requested improvement"}]}
        self.worker.reconcile()
        self.assertTrue(any("Proposal P2" in c["body"] for c in self.client.notes))
        self.assertFalse(self.git.opened)

    def test_unrelated_ref_advance_keeps_proposal(self):
        self.worker.reconcile()
        self.client.source["observed_revision"] = self.src["observed_revision"] = "f" * 40
        self.client.snapshot([self.client.source])
        self.client.add("Maintainer", "approve P1")
        self.worker.reconcile(4)
        self.assertEqual(self.questions, [adoption.PROPOSE])
        self.assertEqual(len(self.git.opened), 1)
        updated = json.loads(self.git.tree["registry/skills.json"][1])
        self.assertEqual(NEW, updated["skills"]["first"]["sources"][0]["last_reviewed_revision"])

    def test_changed_published_proposal_blocks_approval(self):
        self.worker.reconcile()
        self.client.notes[0]["body"] = "Changed proposal."
        self.client.add("Maintainer", "approve P1")
        with self.assertRaisesRegex(monitor.MonitorError, "receipt changed"):
            self.worker.reconcile(4)
        self.assertFalse(self.git.opened)

    def test_lost_publication_response_recovers_original_then_shows_changed_proposal(self):
        send = self.client.comment

        def drop_response(number, body):
            send(number, body)
            raise OSError("lost response")

        with patch.object(self.client, "comment", side_effect=drop_response):
            with self.assertRaises(OSError):
                self.worker.reconcile(4)
        self.src["maintenance_notes"] = "Evidence changed while offline"
        self.worker.reconcile(4)
        proposals = [n["body"].splitlines()[0] for n in self.client.notes if n["body"].startswith("## Proposal")]
        self.assertEqual(proposals, ["## Proposal P1 · 1 decisions", "## Proposal P2 · 1 decisions"])

    def test_review_failure_can_recover_with_same_source(self):
        with patch.object(self.worker, "ask", side_effect=monitor.MonitorError("analysis-timeout", "private detail")):
            self.worker.reconcile(4)
        self.assertIn("blocked", self.client.notes[0]["body"])
        self.assertNotIn("private detail", self.client.notes[0]["body"])
        self.client.add("Maintainer", "approve P1")
        self.worker.reconcile(4)
        self.assertTrue(any("Proposal P2" in c["body"] for c in self.client.notes))
        self.assertFalse(self.git.opened)

    def test_final_head_settles_without_another_external_event(self):
        with patch.object(self.worker, "run", side_effect=["settling", "changed", "merged"]) as reconcile:
            with patch.object(adoption.time, "sleep"):
                self.assertEqual(self.worker.settle(4), "merged")
        self.assertEqual(reconcile.call_count, 3)

    def test_unreadable_old_batch_does_not_starve_current_issue(self):
        old = adoption.Journal(self.directory / "3")
        old.save()
        seen = []

        def run(number):
            seen.append(number)
            if number == 3:
                raise monitor.MonitorError("missing-receipt", "old receipt missing")
            return "reviewed"

        with patch.object(self.worker, "run_checked", side_effect=run):
            with self.assertRaisesRegex(monitor.MonitorError, "old receipt missing"):
                self.worker.reconcile()
        self.assertEqual(seen, [3, 4])

    def test_edited_within_creation_second_is_ineligible(self):
        comment = self.client.add("Maintainer", "approve P1")
        comment["node_id"] = "IC_safe"
        client = adoption.IssueGitHub("fixture/repo")
        node = {"id": "IC_safe", "body": comment["body"], "lastEditedAt": None, "includesCreatedEdit": True}
        with patch.object(client, "request", return_value={"data": {"nodes": [node]}}):
            originals = adoption.Journal(self.directory).originals([comment], "maintainer", client)
        self.assertFalse(originals)

    def test_unreadable_completed_snapshot_does_not_block_discovery(self):
        closed = {"number": 3, "state": "closed", "user": {"login": monitor.ACTIONS_LOGIN},
                  "body": monitor.MARKER + "\nmalformed historical snapshot"}
        with patch.object(self.client, "issues", return_value=[closed, self.client.issue.copy()]):
            self.worker.reconcile()
        self.assertIn("Proposal P1", self.client.notes[0]["body"])

    def test_warning_after_journal_loss_does_not_restore_authority(self):
        self.worker.reconcile(4)
        self.client.add("Maintainer", "approve P1")
        self.worker.directory = self.directory / "fresh"
        for _ in range(2):
            with self.assertRaisesRegex(monitor.MonitorError, "unrecorded adoption receipt"):
                self.worker.reconcile(4)
        self.assertFalse(self.git.opened)

    def test_withdrawn_group_does_not_hold_open_a_clean_merged_batch(self):
        pull = self.git.pull
        self.git.pull = lambda branch, known=None: pull(branch, known) if branch in self.git.opened else None
        self.worker.reconcile(4)
        self.client.add("Maintainer", "approve P1")
        self.client.add("Maintainer", "hold P1 item 1")
        self.worker.reconcile(4)
        self.assertFalse(self.git.opened)
        self.client.add("Maintainer", "approve P1 item 1")
        self.worker.reconcile(4)
        self.worker.reconcile(4)
        self.assertEqual(len(self.git.merges), 1)
        self.client.snapshot([])
        self.worker.reconcile(4)
        self.assertEqual(self.client.issue["state"], "closed")
