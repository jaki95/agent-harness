import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import monitor_upstream as monitor
import review_upstream as review
import install_upstream_reviewer as installer


OLD = "1" * 40
HEAD = "2" * 40
MAIN = "3" * 40
CHANGE = monitor.Change("M", "watched/SKILL.md", "watched/SKILL.md", "a" * 40, "b" * 40, "100644", "100644")
SOURCE = monitor.Source("sample", "source", "https://github.com/fixture/upstream", "main", ("watched/",), OLD, OLD, "Keep customization")


def issue(generation=1, head=HEAD):
    snapshot = monitor.compact(monitor.Report((monitor.Result(SOURCE, "pending", head, (CHANGE,)),)), {})
    return {"number": 6, "state": "open", "body": monitor.issue_body(snapshot, monitor.fingerprint(snapshot), generation)}


def evidence():
    return review.Evidence(MAIN, ({"key": SOURCE.key, "observed_revision": HEAD,
        "changed_files": [monitor.asdict(CHANGE)], "local_files": {"skills/sample/SKILL.md": "local"}},))


def advice():
    return {"findings": [{"key": SOURCE.key, "summary": "Changed guidance", "local_impact": "Retain local safeguards",
        "recommendation": "partially-adopt", "next_actions": ["Propose a scoped adoption for approval"],
        "limits": "No tests or adoption performed", "evidence_paths": ["watched/SKILL.md"]}]}


class FakeGitHub:
    def __init__(self):
        self.issue = issue()
        self.notes = []
        self.fail_after_delivery = False
        self.fail_before_delivery = False

    def issues(self):
        return [copy.deepcopy(self.issue)]

    def comments(self, number):
        return self.notes.copy()

    def comment(self, number, body):
        if self.fail_before_delivery and review.ReviewKey(6, 1, "").marker.split(":")[0] in body:
            raise monitor.MonitorError("command-failed", "GitHub unavailable")
        self.notes.append({"body": body})
        if self.fail_after_delivery and "upstream-codex-review:" in body:
            raise monitor.MonitorError("timeout", "Delivery response lost")


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client = FakeGitHub()
        self.models = 0
        self.collections = 0

    def collect(self, repository, queue, scratch):
        self.collections += 1
        return evidence()

    def analyze(self, proof, scratch):
        self.models += 1
        return advice()

    def run_review(self, **kwargs):
        return review.review_queue("fixture/harness", self.root, github=self.client,
            evidence=kwargs.pop("evidence", self.collect), analyze=kwargs.pop("analyze", self.analyze), **kwargs)

    def test_completed_generation_remains_quiet_without_model_or_fetch(self):
        self.assertEqual("published", self.run_review().kind)
        self.assertEqual("quiet", self.run_review().kind)
        self.assertEqual((1, 1, 1), (self.models, self.collections, len(self.client.notes)))
        self.assertIn("suggested next actions", self.client.notes[0]["body"])
        self.assertIn("Propose a scoped adoption", self.client.notes[0]["body"])

    def test_crash_after_remote_commit_is_recovered_without_second_review(self):
        self.client.fail_after_delivery = True
        self.assertEqual("published", self.run_review(now=0).kind)
        self.assertEqual(1, len(self.client.notes))
        self.client.fail_after_delivery = False
        self.assertEqual("quiet", self.run_review(now=1).kind)
        self.assertEqual(1, self.models)
        self.assertEqual(1, sum("upstream-codex-review:" in n["body"] for n in self.client.notes))

    def test_cache_before_delivery_reuses_model_after_backoff(self):
        self.client.fail_before_delivery = True
        self.assertEqual("failed", self.run_review(now=0).kind)
        self.client.fail_before_delivery = False
        self.assertEqual("quiet", self.run_review(now=10).kind)
        self.assertEqual("published", self.run_review(now=3601).kind)
        self.assertEqual(1, self.models)
        self.assertEqual(2, self.collections)

    def test_queue_changed_while_model_runs_is_not_published(self):
        def stale(proof, scratch):
            self.client.issue = issue(generation=2)
            return advice()
        self.assertEqual("stale", self.run_review(analyze=stale).kind)
        self.assertEqual([], self.client.notes)

    def test_new_generation_with_same_fingerprint_gets_new_analysis(self):
        self.run_review()
        self.client.issue = issue(generation=3)
        self.assertEqual("published", self.run_review().kind)
        self.assertEqual(2, self.models)

    def test_failure_is_visible_once_retries_after_one_hour(self):
        def broken(proof, scratch):
            raise monitor.MonitorError("analysis-timeout", "Timed out")
        self.assertEqual("failed", self.run_review(analyze=broken, now=0).kind)
        self.assertEqual("quiet", self.run_review(analyze=broken, now=20).kind)
        self.assertEqual("failed", self.run_review(analyze=broken, now=3601).kind)
        self.assertEqual(1, len(self.client.notes))
        self.assertNotIn("upstream-codex-review:", self.client.notes[0]["body"])

    def test_invalid_partial_model_output_is_failure(self):
        self.assertEqual("failed", self.run_review(analyze=lambda e, s: {"findings": []}).kind)
        self.assertIn("invalid-analysis", self.client.notes[0]["body"])

    def test_lock_returns_quiet(self):
        with (self.root / "review.lock").open("a") as held:
            review.fcntl.flock(held, review.fcntl.LOCK_EX | review.fcntl.LOCK_NB)
            self.assertEqual("quiet", self.run_review().kind)
        self.assertEqual(0, self.models)

    def test_no_issue_or_closed_issue_skips_analysis(self):
        self.client.issue["state"] = "closed"
        self.assertEqual("quiet", self.run_review().kind)
        self.assertEqual(0, self.models)


class ValidationTests(unittest.TestCase):
    def test_source_coverage_duplicate_unknown_paths_and_empty_actions_rejected(self):
        samples = []
        duplicate = advice(); duplicate["findings"] *= 2; samples.append(duplicate)
        wrong = advice(); wrong["findings"][0]["evidence_paths"] = ["absent/path"]; samples.append(wrong)
        empty = advice(); empty["findings"][0]["next_actions"] = []; samples.append(empty)
        for value in samples:
            with self.subTest(value=value), self.assertRaises(monitor.MonitorError):
                review.validate_advice(value, evidence())

    def test_legacy_github_link_pins_exact_revision(self):
        item = monitor.parse_snapshot(issue()["body"])["sources"][0]
        item.pop("observed_revision")
        self.assertEqual(HEAD, review.observed_revision(item))
        item["link"] = f"https://evil.invalid/fixture/upstream/compare/{OLD}...{HEAD}"
        with self.assertRaises(monitor.MonitorError):
            review.observed_revision(item)

    def test_trace_rejects_tool_calls_and_incomplete_turns(self):
        review.validate_trace(b'{"type":"item.completed","item":{"type":"agent_message","text":"ok"}}\n{"type":"turn.completed"}')
        for trace in (b'{"type":"item.started","item":{"type":"mcp_tool_call"}}', b'{"type":"turn.failed"}', b'{}'):
            with self.assertRaises(monitor.MonitorError):
                review.validate_trace(trace)

    def test_codex_flags_schema_and_stdin_are_enforced(self):
        with tempfile.TemporaryDirectory() as temp:
            def fake_run(args, **kwargs):
                self.assertIn("--ignore-user-config", args)
                self.assertIn("--ignore-rules", args)
                self.assertIn("--json", args)
                self.assertIn("read-only", args)
                self.assertEqual("-", args[-1])
                self.assertIn(b"UNTRUSTED DATA", kwargs["input"])
                self.assertEqual(600, kwargs["timeout"])
                Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps(advice()))
                return b'{"type":"turn.completed"}'
            with patch.object(monitor, "run", side_effect=fake_run):
                self.assertEqual(advice(), review.codex_review(evidence(), Path(temp), model="gpt-6.1-sol"))

    def test_metadata_does_not_change_semantic_digest_and_outage_preserves_revision(self):
        snapshot = monitor.parse_snapshot(issue()["body"])
        legacy = copy.deepcopy(snapshot); legacy["sources"][0].pop("observed_revision")
        self.assertEqual(monitor.fingerprint(snapshot), monitor.fingerprint(legacy))
        outage = monitor.compact(monitor.Report((monitor.Result(SOURCE, "unknown", error="timeout"),)), snapshot)
        self.assertEqual(HEAD, outage["sources"][0]["observed_revision"])
        self.assertIn('watched/SKILL.md', issue()["body"])

    def test_legacy_outage_does_not_attach_new_head_to_old_change_objects(self):
        legacy = monitor.parse_snapshot(issue()["body"])
        legacy["sources"][0].pop("observed_revision")
        outage = monitor.compact(monitor.Report((monitor.Result(SOURCE, "unknown", "9" * 40, error="timeout"),)), legacy)
        self.assertNotIn("observed_revision", outage["sources"][0])
        self.assertEqual(HEAD, review.observed_revision(outage["sources"][0]))

    def test_invalid_observed_revision_rejected(self):
        snapshot = monitor.parse_snapshot(issue()["body"])
        snapshot["sources"][0]["observed_revision"] = "main"
        with self.assertRaises(monitor.MonitorError):
            monitor.parse_snapshot(monitor.issue_body(snapshot, snapshot["fingerprint"], 1))


class InstallerTests(unittest.TestCase):
    def test_units_quote_paths_with_spaces_and_preserve_dollar_percent(self):
        service, timer = installer.render_units(Path('/opt/bundle with space'), Path('/var/review $%'),
            Path('/opt/bin/codex'), Path('/usr/bin/python3'), Path('/usr/bin/gh'),
            repository="fixture/harness", model="gpt-6.1-sol", path="/usr/bin")
        self.assertIn('"/opt/bundle with space/review_upstream.py"', service)
        self.assertIn('"/var/review $$%%"', service)
        self.assertIn("TMPDIR=/var/review $%%/scratch", service)
        self.assertIn("Persistent=true", timer)
        self.assertIn("OnCalendar=*:0/15", timer)

    def test_staging_copies_only_maintenance_scripts_and_enables_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = Path(sys.executable).resolve()
            installer.stage(root / "runtime", root / "state", root / "units", executable, executable,
                executable, repository="fixture/harness")
            self.assertEqual(set(installer.BUNDLE), {p.name for p in (root / "runtime").iterdir()})
            self.assertEqual(2, len(list((root / "units").iterdir())))
            self.assertTrue((root / "state/scratch").is_dir())

from test_monitor_upstream import RepositoryFixture, git


class EvidenceTests(RepositoryFixture):
    def setUp(self):
        super().setUp()
        self.write("watched/SKILL.md", "queued upstream instruction\n")
        self.queued_head = self.commit()
        self.queue = review.Queue(review.ReviewKey(6, 1, "0" * 64), monitor.compact(self.collect(), {}))
        git(self.harness, "init", "-b", "main")
        git(self.harness, "config", "user.email", "test@example.invalid")
        git(self.harness, "config", "user.name", "Fixture")
        self.commit_harness()
        self.harness_revision = git(self.harness, "rev-parse", "HEAD")
        fixture = self

        class Transport(monitor.Git):
            fetches = []

            def fetch(self, repository, ref):
                self.fetches.append((repository, ref))
                target = fixture.harness if repository == "https://github.com/fixture/harness.git" else fixture.upstream
                self.command("-c", "protocol.file.allow=always", "fetch", "--no-tags", "--", str(target), ref)
                return self.command("rev-parse", "FETCH_HEAD^{commit}").decode().strip()

        self.evidence_transport = Transport
        self.scratch = self.root / "review-evidence"
        self.scratch.mkdir()

    def commit_harness(self):
        git(self.harness, "add", "-A")
        git(self.harness, "commit", "-m", "fixture", "--allow-empty")

    def gather(self):
        return review.gather_evidence("fixture/harness", self.queue, self.scratch, git_factory=self.evidence_transport)

    def test_reconstructs_queued_sha_even_after_upstream_advances(self):
        self.write("watched/SKILL.md", "newer unqueued change\n")
        self.commit()
        (self.harness / "skills/sample/SKILL.md").write_text("dirty working tree must not be read\n")
        proof = self.gather()
        self.assertEqual(self.harness_revision, proof.harness_revision)
        self.assertEqual(self.queued_head, proof.sources[0]["observed_revision"])
        self.assertIn("+queued upstream instruction", proof.sources[0]["upstream_patch"])
        self.assertNotIn("newer unqueued", proof.sources[0]["upstream_patch"])
        self.assertEqual("customized skill\n", proof.sources[0]["local_files"]["skills/sample/SKILL.md"])
        self.assertEqual(self.queued_head, self.evidence_transport.fetches[-1][1])
        self.assertEqual("dirty working tree must not be read\n", (self.harness / "skills/sample/SKILL.md").read_text())

    def test_registry_mismatch_requires_new_detection(self):
        self.index["skills"]["sample"]["sources"][0]["last_reviewed_revision"] = self.queued_head
        self.save_registry()
        self.commit_harness()
        with self.assertRaises(monitor.MonitorError) as raised:
            self.gather()
        self.assertEqual("queue-superseded", raised.exception.code)

    def test_symlink_local_evidence_is_rejected_not_followed(self):
        (self.harness / "skills/sample/external").symlink_to("/etc/passwd")
        self.commit_harness()
        with self.assertRaises(monitor.MonitorError) as raised:
            self.gather()
        self.assertEqual("unsafe-evidence", raised.exception.code)

    def test_changed_object_identity_mismatch_is_rejected(self):
        self.queue.snapshot["sources"][0]["changes"][0]["new_object"] = "f" * 40
        with self.assertRaises(monitor.MonitorError) as raised:
            self.gather()
        self.assertEqual("evidence-mismatch", raised.exception.code)
