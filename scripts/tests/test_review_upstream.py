import copy
import json
import os
import shlex
import subprocess
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


def issue(generation=1, head=HEAD, *, number=6, state="open", status="pending"):
    changes = (CHANGE,) if status == "pending" else ()
    snapshot = monitor.compact(monitor.Report((monitor.Result(SOURCE, status, head, changes),)), {})
    return {"number": number, "state": state, "user": {"login": monitor.ACTIONS_LOGIN}, "body": monitor.issue_body(snapshot, monitor.fingerprint(snapshot), generation)}


def evidence():
    return review.Evidence(MAIN, ({"key": SOURCE.key, "observed_revision": HEAD,
        "changed_files": [monitor.asdict(CHANGE)], "maintenance_notes": "Keep customization",
        "local_files": {"skills/sample/SKILL.md": "local"}},))


def advice():
    return {"findings": [{"key": SOURCE.key, "summary": "Changed guidance", "local_impact": "Retain local safeguards",
        "recommendation": "partially-adopt", "next_actions": ["Propose a scoped adoption for approval"],
        "limits": "No tests or adoption performed", "evidence_paths": ["watched/SKILL.md"]}]}


class FakeGitHub:
    def __init__(self):
        self.issue = issue()
        self.history = []
        self.notes = []
        self.fail_after_delivery = False
        self.fail_before_delivery = False

    def viewer_login(self):
        return "reviewer"

    def issues(self):
        return copy.deepcopy([*self.history, self.issue] if self.issue else self.history)

    def comments(self, number):
        return [note.copy() for note in self.notes if note["number"] == number]

    def comment(self, number, body):
        if self.fail_before_delivery and review.ReviewKey(6, 1, "").marker.split(":")[0] in body:
            raise monitor.MonitorError("command-failed", "GitHub unavailable")
        self.notes.append({"number": number, "body": body, "user": {"login": self.viewer_login()}})
        if self.fail_after_delivery and any(marker in body for marker in ("upstream-codex-review:", "upstream-codex-partial:")):
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

    def test_only_reviewers_own_footer_confirms_delivery(self):
        marker = review.find_queue(self.client, {monitor.ACTIONS_LOGIN}).key.marker
        body = "## Codex analysis and suggested next actions\n\nReview advice.\n\n" + marker
        self.client.notes.extend([
            {"number": 6, "body": body, "user": {"login": monitor.ACTIONS_LOGIN}},
            {"number": 6, "body": "Quoted record\n" + body, "user": {"login": "reviewer"}},
            {"number": 6, "body": body + "\nText after marker", "user": {"login": "reviewer"}},
        ])
        self.assertEqual("published", self.run_review().kind)
        self.assertEqual("quiet", self.run_review().kind)
        self.assertEqual(1, self.models)

    def test_multipart_resumes_at_missing_part_after_lost_response(self):
        value = advice()
        finding = value["findings"][0]
        for field in ("summary", "local_impact", "limits"):
            finding[field] = "🎵" * 4000
        finding["next_actions"] = ["🎵" * 1500] * 8
        attempts = []
        def analyze(*args):
            attempts.append(1)
            return value

        original = self.client.comment
        def lose_response(number, body):
            original(number, body)
            if "Review part 1." in body:
                raise monitor.MonitorError("timeout", "Part posted before connection closed")

        with patch.object(self.client, "comment", side_effect=lose_response):
            self.assertEqual("failed", self.run_review(analyze=analyze, now=0).kind)
        self.assertFalse(any(review.find_queue(self.client, {monitor.ACTIONS_LOGIN}).key.marker in note["body"]
                             for note in self.client.notes))
        self.assertEqual("published", self.run_review(analyze=analyze, now=3601).kind)
        self.assertEqual("quiet", self.run_review(analyze=analyze, now=3602).kind)
        parts = [note["body"] for note in self.client.notes if "<!-- upstream-codex-part:" in note["body"]]
        self.assertGreater(len(parts), 1)
        self.assertEqual(len(parts), len(set(parts)))
        self.assertEqual(24000, sum(part.count("🎵") for part in parts))
        self.assertTrue(all(len(note["body"].encode()) <= monitor.ISSUE_LIMIT for note in self.client.notes))
        self.assertEqual(1, len(attempts))

    def test_queue_rotation_between_parts_prevents_final_receipt(self):
        original = self.client.comment
        new_queue = issue(generation=2)
        def rotate(number, body):
            original(number, body)
            self.client.issue = new_queue
        value = advice()
        value["findings"][0]["summary"] = "a" * 1000
        with patch.object(monitor, "ISSUE_LIMIT", 900), patch.object(self.client, "comment", side_effect=rotate):
            self.assertEqual("stale", self.run_review(analyze=lambda *args: value).kind)
        self.assertEqual(1, len(self.client.notes))
        self.assertIn("Review part 1.", self.client.notes[0]["body"])

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

    def test_complete_sources_split_across_bounded_model_inputs(self):
        snapshot = monitor.parse_snapshot(self.client.issue["body"])
        second = {**snapshot["sources"][0], "key": "second/source"}
        snapshot["sources"].append(second)
        self.client.issue["body"] = monitor.issue_body(snapshot, monitor.fingerprint(snapshot), 1)
        first = evidence().sources[0]
        proof = review.Evidence(MAIN, (first, {**first, "key": "second/source"}))
        limit = len(json.dumps(monitor.asdict(review.Evidence(MAIN, (proof.sources[1],)))).encode())
        batches = []

        def analyze(batch, scratch):
            self.assertLessEqual(len(json.dumps(monitor.asdict(batch)).encode()), limit)
            batches.append([s["key"] for s in batch.sources])
            if len(batches) == 2:
                raise monitor.MonitorError("analysis-timeout", "Second request timed out")
            return {"findings": [dict(advice()["findings"][0], key=k) for k in batches[-1]]}

        with patch.object(review, "INPUT_LIMIT", limit):
            self.assertEqual("failed", self.run_review(evidence=lambda *args: proof, analyze=analyze, now=0).kind)
            result = self.run_review(evidence=lambda *args: proof, analyze=analyze, now=3601)
        self.assertEqual("published", result.kind)
        self.assertEqual([["sample/source"], ["second/source"], ["second/source"]], batches)
        self.assertIn("### second/source", self.client.notes[-1]["body"])

    def test_stale_partial_analysis_is_discarded(self):
        snapshot = monitor.parse_snapshot(self.client.issue["body"])
        snapshot["sources"].append({**snapshot["sources"][0], "key": "other/source", "status": "unknown"})
        self.client.issue["body"] = monitor.issue_body(snapshot, monitor.fingerprint(snapshot), 1)
        proof = review.Evidence(MAIN, evidence().sources, (("other/source", "evidence-unknown"),))

        def stale(*args):
            self.client.issue = issue(generation=2)
            return advice()

        self.assertEqual("stale", self.run_review(evidence=lambda *args: proof, analyze=stale).kind)
        self.assertEqual([], self.client.notes)

    def test_queue_changed_while_model_runs_is_not_published(self):
        def stale(proof, scratch):
            self.client.issue = issue(generation=2)
            return advice()
        self.assertEqual("stale", self.run_review(analyze=stale).kind)
        self.assertEqual([], self.client.notes)

    def test_rotation_during_analysis_discards_delivery_even_with_the_same_fingerprint(self):
        def rotate(proof, scratch):
            self.client.history = [issue(state="closed", status="unchanged")]
            self.client.issue = issue(number=7)
            return self.analyze(proof, scratch)

        self.assertEqual("stale", self.run_review(analyze=rotate).kind)
        self.assertEqual([], self.client.notes)
        self.assertEqual("published", self.run_review().kind)
        self.assertEqual(2, self.models)
        self.assertEqual([7], [note["number"] for note in self.client.notes])

    def test_rotated_issue_gets_its_own_analysis_and_completion_record(self):
        self.assertEqual("published", self.run_review().kind)
        previous_note = self.client.notes[0].copy()
        self.client.history = [issue(state="closed", status="unchanged")]
        self.client.issue = issue(number=7)
        self.assertEqual("published", self.run_review().kind)
        self.assertEqual("quiet", self.run_review().kind)
        self.assertEqual((2, 2), (self.models, self.collections))
        self.assertEqual([6, 7], [note["number"] for note in self.client.notes])
        self.assertEqual(previous_note, self.client.notes[0])
        self.assertEqual(["6", "7"], sorted(path.name.split("-")[0] for path in self.root.glob("*.json")))

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

    def test_completed_history_without_an_active_issue_skips_analysis(self):
        self.client.history = [issue(number=4, state="closed", status="unchanged"),
                               issue(number=5, state="closed", status="unchanged")]
        self.client.issue = None
        self.assertEqual("quiet", self.run_review().kind)
        self.assertEqual((0, 0, []), (self.models, self.collections, self.client.notes))

    def test_clean_open_issue_waits_for_monitor_closure(self):
        self.client.history = [issue(number=5, state="closed", status="unchanged")]
        self.client.issue = issue(status="unchanged")
        self.assertEqual("quiet", self.run_review().kind)
        self.assertEqual((0, 0), (self.models, self.collections))

    def test_duplicate_unfinished_issues_fail_before_analysis(self):
        for state, status in (("open", "pending"), ("closed", "pending"),
                              ("closed", "unknown"), ("open", "unchanged")):
            with self.subTest(state=state, status=status):
                self.client.history = [issue(number=5, state=state, status=status)]
                with self.assertRaises(monitor.MonitorError) as raised:
                    self.run_review()
                self.assertEqual("duplicate-issues", raised.exception.code)
        self.assertEqual((0, 0, []), (self.models, self.collections, self.client.notes))

    def test_malformed_closed_history_fails_before_analysis(self):
        clean = monitor.parse_snapshot(issue(status="unchanged")["body"])
        for body in (monitor.MARKER, monitor.issue_body(clean, "0" * 64, 1)):
            with self.subTest(body=body):
                self.client.history = [{"number": 5, "state": "closed", "body": body, "user": {"login": monitor.ACTIONS_LOGIN}}]
                with self.assertRaises(monitor.MonitorError) as raised:
                    self.run_review()
                self.assertEqual("invalid-snapshot", raised.exception.code)
        self.assertEqual((0, 0, []), (self.models, self.collections, self.client.notes))


class ValidationTests(unittest.TestCase):
    def test_source_coverage_duplicate_unknown_paths_and_empty_actions_rejected(self):
        samples = []
        duplicate = advice(); duplicate["findings"] *= 2; samples.append(duplicate)
        wrong = advice(); wrong["findings"][0]["evidence_paths"] = ["absent/path"]; samples.append(wrong)
        empty = advice(); empty["findings"][0]["next_actions"] = []; samples.append(empty)
        for value in samples:
            with self.subTest(value=value), self.assertRaises(monitor.MonitorError):
                review.validate_advice(value, evidence())

    def test_supplied_registry_notes_are_valid_evidence(self):
        value = advice()
        value["findings"][0]["evidence_paths"] = ["registry/skills.json"]
        self.assertEqual(value, review.validate_advice(value, evidence()))

    def test_schema_binds_each_source_to_its_evidence_and_declares_bounds(self):
        first = evidence().sources[0]
        second = {**first, "key": "other/source", "local_files": {"skills/other/SKILL.md": "other"},
                  "changed_files": [{**monitor.asdict(CHANGE), "old_path": "other/SKILL.md",
                                     "new_path": "other/SKILL.md"}]}
        proof = review.Evidence(MAIN, (first, second))
        schema = review.output_schema(proof)
        self.assertEqual("object", schema["type"])
        findings = schema["properties"]["findings"]
        self.assertEqual((2, 2), (findings["minItems"], findings["maxItems"]))
        variants = findings["items"]["anyOf"]
        self.assertEqual(2, len(variants))
        for variant, key, paths in zip(variants, ("sample/source", "other/source"), (
                ["registry/skills.json", "skills/sample/SKILL.md", "watched/SKILL.md"],
                ["other/SKILL.md", "registry/skills.json", "skills/other/SKILL.md"])):
            with self.subTest(key=key):
                self.assertFalse(variant["additionalProperties"])
                self.assertEqual(["key", "summary", "local_impact", "recommendation", "next_actions", "limits", "evidence_paths"],
                                 variant["required"])
                properties = variant["properties"]
                self.assertEqual({"type": "string", "enum": [key]}, properties["key"])
                self.assertEqual({"type": "array", "minItems": 1, "maxItems": 30,
                                  "items": {"type": "string", "enum": paths}}, properties["evidence_paths"])
                self.assertEqual({"type": "array", "minItems": 1, "maxItems": 8,
                                  "items": {"type": "string", "minLength": 1, "maxLength": 1500,
                                            "pattern": r"\S"}}, properties["next_actions"])
                for field in ("summary", "local_impact", "limits"):
                    self.assertEqual({"type": "string", "minLength": 1, "maxLength": 4000,
                                      "pattern": r"\S"}, properties[field])
        value = advice()
        value["findings"][0]["evidence_paths"] = ["skills/other/SKILL.md"]
        with self.assertRaisesRegex(monitor.MonitorError, r"sample/source\.evidence_paths\[0\]"):
            review.validate_advice(value, proof)

    def test_invalid_evidence_diagnostic_does_not_echo_model_path(self):
        value = advice()
        value["findings"][0]["evidence_paths"] = ["model-private-content:42"]
        with self.assertRaises(monitor.MonitorError) as failure:
            review.validate_advice(value, evidence())
        self.assertEqual("Codex sample/source.evidence_paths[0] is not a supplied evidence path", str(failure.exception))
        self.assertNotIn("model-private-content", str(failure.exception))

    def test_advice_bounds_and_whitespace_are_rejected_with_field_diagnostics(self):
        cases = (("summary", " " * 2), ("local_impact", "x" * 4001),
                 ("next_actions", [" " ]), ("next_actions", ["x" * 1501]),
                 ("next_actions", ["action"] * 9), ("evidence_paths", ["watched/SKILL.md"] * 31))
        for field, invalid in cases:
            value = advice()
            value["findings"][0][field] = invalid
            with self.subTest(field=field), self.assertRaisesRegex(monitor.MonitorError, "sample/source." + field):
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

    def test_disabled_code_mode_startup_notice_allows_completed_analysis(self):
        notice = {"type": "item.completed", "item": {"id": "item_0", "type": "error",
            "message": "Code Mode is unavailable because code-mode host is disabled. "
                       "Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`."}}
        trace = json.dumps(notice).encode() + b'\n{"type":"turn.completed"}'
        review.validate_trace(trace)
        notice["item"]["message"] = "A different error occurred"
        with self.assertRaises(monitor.MonitorError):
            review.validate_trace(json.dumps(notice).encode() + b'\n{"type":"turn.completed"}')

    def test_codex_flags_schema_and_stdin_are_enforced(self):
        with tempfile.TemporaryDirectory() as temp:
            def fake_run(args, **kwargs):
                self.assertIn("--ignore-user-config", args)
                self.assertIn("--ignore-rules", args)
                self.assertIn("--json", args)
                self.assertIn("read-only", args)
                self.assertEqual("-", args[-1])
                self.assertIn(b"UNTRUSTED DATA", kwargs["input"])
                self.assertIn(b"without line numbers or fragments", kwargs["input"])
                self.assertIn(b"Registry maintenance_notes are excerpts from registry/skills.json", kwargs["input"])
                self.assertEqual(600, kwargs["timeout"])
                Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps(advice()))
                return b'{"type":"turn.completed"}'
            with patch.object(monitor, "run", side_effect=fake_run):
                self.assertEqual(advice(), review.codex_review(evidence(), Path(temp), model="gpt-6.1-sol"))

    def test_valid_model_output_can_exceed_one_comment(self):
        value = advice()
        value["findings"][0]["next_actions"] = ["🎵" * 1500] * 8
        output = json.dumps(value)
        self.assertGreater(len(output), monitor.ISSUE_LIMIT)
        def fake_run(args, **kwargs):
            Path(args[args.index("--output-last-message") + 1]).write_text(output)
            return b'{"type":"turn.completed"}'
        with tempfile.TemporaryDirectory() as temp, patch.object(monitor, "run", side_effect=fake_run):
            self.assertEqual(value, review.codex_review(evidence(), Path(temp)))

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

    def test_staged_worker_runs_the_selected_gh_when_another_is_first_on_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tools = root / "codex-bin"
            tools.mkdir()
            codex = tools / "codex"
            decoy = tools / "gh"
            selected = root / "selected gh wrapper"
            codex.write_text("#!/bin/sh\nexit 25\n")
            decoy.write_text("#!/bin/sh\nexit 26\n")
            selected.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CALL_LOG"\necho "[]"\n')
            for exe in (codex, decoy, selected):
                exe.chmod(0o755)
            installer.stage(root / "runtime", root / "state", root / "units", codex,
                            Path(sys.executable), selected, repository="fixture/harness")
            service = (root / "units" / (installer.UNIT + ".service")).read_text().splitlines()
            command = shlex.split(next(line.removeprefix("ExecStart=") for line in service if line.startswith("ExecStart=")))
            installed_path = shlex.split(next(line.removeprefix("Environment=") for line in service
                                               if line.startswith('Environment="PATH=')))[0].removeprefix("PATH=")
            log = root / "invocation"
            result = subprocess.run(command, capture_output=True, text=True,
                                    env={**os.environ, "PATH": installed_path, "CALL_LOG": str(log)})
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("No actionable queue", result.stdout)
            self.assertIn("repos/fixture/harness/issues?", log.read_text())

    def test_staging_copies_only_maintenance_scripts_and_enables_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = Path(sys.executable).resolve()
            installer.stage(root / "runtime", root / "state", root / "units", executable, executable,
                executable, repository="fixture/harness")
            self.assertEqual(set(installer.BUNDLE), {p.name for p in (root / "runtime").iterdir()})
            self.assertEqual(2, len(list((root / "units").iterdir())))
            self.assertTrue((root / "state/scratch").is_dir())

from test_monitor_upstream import FakeIssues, RepositoryFixture, git


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

    def test_large_queue_reaches_review_after_interrupted_upload_and_validates_the_parts(self):
        for index in range(320):
            self.write(f"watched/entry-{index:04}.md", f"Entry {index}\n")
        head = self.commit()
        report = self.collect()
        client = FakeIssues()
        publishers = {monitor.ACTIONS_LOGIN}
        repository = "fixture/harness"
        client.fail_after = "comment"
        with self.assertRaisesRegex(monitor.MonitorError, "Response lost"):
            monitor.reconcile_issue(report, repository, issues=client)
        self.assertIsNone(review.find_queue(client, publishers))
        monitor.reconcile_issue(report, repository, issues=client)
        self.assertEqual(1, len(client.records))
        self.assertGreater(len(client.notes), 1)
        bodies = [note["body"] for note in client.notes]
        self.assertEqual(len(bodies), len(set(bodies)))
        self.assertTrue(all(len(body.encode()) <= monitor.ISSUE_LIMIT for body in [*bodies, client.records[0]["body"]]))
        queue = review.find_queue(client, publishers)
        self.assertEqual(head, queue.snapshot["sources"][0]["observed_revision"])
        first = client.notes[0]
        with patch.dict(first["user"], login="unrelated"):
            with self.assertRaisesRegex(monitor.MonitorError, "Missing upstream snapshot parts"):
                review.find_queue(client, publishers)
        with patch.dict(first, body=first["body"].replace("entry-0000", "entry-1111")):
            with self.assertRaisesRegex(monitor.MonitorError, "digest"):
                review.find_queue(client, publishers)
        client.viewer_login = lambda: "reviewer"
        with patch.object(review, "codex_review", return_value=advice()) as analyze:
            def run():
                return review.review_queue(repository, self.root / "state", github=client,
                    evidence=lambda repo, queue, path: review.gather_evidence(repo, queue, path, git_factory=self.evidence_transport))
            self.assertEqual("published", run().kind)
            self.assertEqual("quiet", run().kind)
            self.assertEqual(1, analyze.call_count)
            self.assertEqual(321, len(analyze.call_args.args[0].sources[0]["changed_files"]))

    def test_relocated_test_and_split_package_manifest_are_selected_individually(self):
        testdir = self.harness / "tests/sample"
        (testdir / "test").mkdir(parents=True)
        (testdir / "test/spec.ts").write_text("local test")
        (testdir / "test/unrelated.json").write_text("unrelated")
        (testdir / "package.json").write_text("maintainer dependencies")
        scripts = self.harness / "skills/sample/scripts"
        scripts.mkdir()
        (scripts / "package.json").write_text("runtime manifest")
        self.write("watched/scripts/test/spec.ts", "upstream test")
        self.write("watched/scripts/package.json", "upstream manifest")
        self.commit()
        self.queue = review.Queue(self.queue.key, monitor.compact(self.collect(), {}))
        self.commit_harness()
        source = self.gather().sources[0]
        self.assertEqual({"skills/sample/SKILL.md", "skills/sample/scripts/package.json",
                          "tests/sample/test/spec.ts", "tests/sample/package.json"}, set(source["local_files"]))
        self.assertEqual([], source["unmatched_upstream_paths"])
        self.assertEqual(0, source["omitted_local_files"])

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
        entrypoint = self.harness / "skills/sample/SKILL.md"
        entrypoint.unlink()
        entrypoint.symlink_to("/example/unreadable")
        self.commit_harness()
        with self.assertRaises(monitor.MonitorError) as raised:
            self.gather()
        self.assertEqual("unsafe-evidence", raised.exception.code)

    def test_changed_object_identity_mismatch_is_rejected(self):
        self.queue.snapshot["sources"][0]["changes"][0]["new_object"] = "f" * 40
        with self.assertRaises(monitor.MonitorError) as raised:
            self.gather()
        self.assertEqual("evidence-mismatch", raised.exception.code)


    def test_reads_changed_counterparts_and_skips_large_unrelated_files(self):
        package = self.harness / "skills/sample"
        (package / "helper.txt").write_text("custom helper")
        (package / "large-test-corpus").write_bytes(b"x" * (review.INPUT_LIMIT + 1))
        self.write("watched/helper.txt", "new helper")
        self.write("watched/new-file.md", "upstream only")
        self.commit()
        self.queue = review.Queue(self.queue.key, monitor.compact(self.collect(), {}))
        self.commit_harness()
        source = self.gather().sources[0]
        self.assertEqual({"skills/sample/SKILL.md": "customized skill\n", "skills/sample/helper.txt": "custom helper"},
                         source["local_files"])
        self.assertEqual(1, source["omitted_local_files"])
        self.assertEqual(["watched/new-file.md"], source["unmatched_upstream_paths"])

    def test_directory_watch_without_trailing_slash_matches_local_descendants(self):
        self.source["paths"] = ["watched"]
        self.write_registry()
        (self.harness / "skills/sample/helper.txt").write_text("local helper")
        self.write("watched/helper.txt", "changed upstream helper")
        self.commit()
        self.queue = review.Queue(self.queue.key, monitor.compact(self.collect(), {}))
        self.commit_harness()
        source = self.gather().sources[0]
        self.assertEqual("local helper", source["local_files"]["skills/sample/helper.txt"])
        self.assertEqual([], source["unmatched_upstream_paths"])

    def test_oversized_source_leaves_other_review_publishable_and_retries_without_duplication(self):
        self.index["skills"]["large"] = copy.deepcopy(self.index["skills"]["sample"])
        (self.harness / "skills/large").mkdir()
        (self.harness / "skills/large/SKILL.md").write_text("x" * (review.INPUT_LIMIT + 1))
        self.save_registry()
        self.commit_harness()
        snapshot = monitor.compact(self.collect(), {})
        client = FakeGitHub()
        client.issue["body"] = monitor.issue_body(snapshot, monitor.fingerprint(snapshot), 1)
        analyses = []

        def analyze(proof, scratch):
            keys = [s["key"] for s in proof.sources]
            analyses.append(keys)
            return {"findings": [dict(advice()["findings"][0], key=k) for k in keys]}

        def run(now):
            return review.review_queue("fixture/harness", self.root / "state", github=client, now=now,
                evidence=lambda repo, queue, path: review.gather_evidence(repo, queue, path, git_factory=self.evidence_transport),
                analyze=analyze)

        client.fail_after_delivery = True
        self.assertEqual("failed", run(0).kind)
        client.fail_after_delivery = False
        self.assertEqual([["sample/source"]], analyses)
        self.assertIn("Suggested decision", client.notes[0]["body"])
        self.assertIn("large/source", client.notes[0]["body"])
        self.assertIn("evidence-limit", client.notes[0]["body"])
        self.assertNotIn("upstream-codex-review:", client.notes[0]["body"])
        self.assertEqual("quiet", run(5).kind)
        self.assertEqual("failed", run(3601).kind)
        self.assertEqual((1, 1), (len(client.notes), len(analyses)))
        (self.harness / "skills/large/SKILL.md").write_text("small enough")
        self.commit_harness()
        self.assertEqual("published", run(7202).kind)
        self.assertIn("upstream-codex-review:", client.notes[-1]["body"])
        self.assertEqual("quiet", run(7203).kind)
