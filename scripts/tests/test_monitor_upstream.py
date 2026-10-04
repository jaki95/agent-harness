import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import monitor_upstream as monitor


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


class RepositoryFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="monitor-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        git(self.upstream, "init", "-b", "main")
        git(self.upstream, "config", "user.email", "test@example.invalid")
        git(self.upstream, "config", "user.name", "Fixture")
        self.write("watched/SKILL.md", "upstream skill\n")
        self.write("watched/helper.txt", "helper\n")
        self.write("outside.txt", "outside\n")
        self.before = self.commit()
        self.harness = self.root / "harness"
        (self.harness / "skills" / "sample").mkdir(parents=True)
        (self.harness / "skills" / "sample" / "SKILL.md").write_text("customized skill\n")
        (self.harness / "registry").mkdir()
        self.source = {"id": "source", "relationship": "adapted", "repository": "https://example.invalid/upstream",
                       "ref": "main", "paths": ["watched/"], "baseline_revision": self.before,
                       "last_reviewed_revision": self.before, "last_incorporated_revision": self.before}
        self.write_registry()
        fixture = self

        class FixtureGit(monitor.Git):
            fetches = []

            def fetch(self, repository, ref):
                self.fetches.append((repository, ref))
                self.command("-c", "protocol.file.allow=always", "fetch", "--no-tags", "--", str(fixture.upstream), ref)
                return self.command("rev-parse", "FETCH_HEAD^{commit}").decode().strip()

        self.transport = FixtureGit

    def write_registry(self, source=None):
        record = {"maintenance_notes": "Keep local customizations.", "reviewed_on": "2020-01-01",
                  "sources": [source or self.source]}
        self.index = {"schema_version": 1, "skills": {"sample": record}}
        self.save_registry()

    def save_registry(self):
        (self.harness / "registry" / "skills.json").write_text(json.dumps(self.index))

    def write(self, path, text):
        target = self.upstream / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self):
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-m", "fixture", "--allow-empty")
        return git(self.upstream, "rev-parse", "HEAD")

    def collect(self):
        before = (self.harness / "registry" / "skills.json").read_bytes()
        report = monitor.collect(self.harness, git_factory=self.transport)
        self.assertEqual(before, (self.harness / "registry" / "skills.json").read_bytes())
        return report


class DetectorTests(RepositoryFixture):
    def test_unrelated_head_does_not_change_identity(self):
        first = self.collect()
        self.write("outside.txt", "unrelated\n")
        self.commit()
        second = self.collect()
        self.assertEqual("unchanged", second.results[0].status)
        self.assertNotEqual(first.results[0].head, second.results[0].head)
        self.assertEqual(monitor.fingerprint(monitor.compact(first, {})), monitor.fingerprint(monitor.compact(second, {})))

    def test_change_and_entrypoint_customization_are_reported(self):
        self.write("watched/SKILL.md", "new upstream skill\n")
        self.commit()
        result = self.collect().results[0]
        self.assertEqual("pending", result.status)
        self.assertEqual(["watched/SKILL.md"], [c.new_path for c in result.changes])
        self.assertIn("+new upstream skill", result.upstream_patch)
        self.assertIn("+customized skill", result.customization_patch)
        self.assertIn("Supporting files have no declared local mapping", result.comparison_note)

    def test_literal_file_path_does_not_match_other_files(self):
        self.write("watched/[a].txt", "before\n")
        self.write("watched/a.txt", "before\n")
        self.source["last_reviewed_revision"] = self.commit()
        self.source["paths"] = ["watched/[a].txt"]
        self.write_registry()
        self.write("watched/a.txt", "unrelated\n")
        self.commit()
        self.assertEqual("unchanged", self.collect().results[0].status)
        self.write("watched/[a].txt", "after\n")
        self.commit()
        result = self.collect().results[0]
        self.assertEqual(["watched/[a].txt"], [c.new_path for c in result.changes])
        self.assertIn("+after", result.upstream_patch)
        self.assertNotIn("+unrelated", result.upstream_patch)

    def test_directory_replaced_with_file_is_missing(self):
        shutil.rmtree(self.upstream / "watched")
        self.write("watched", "replacement file\n")
        self.commit()
        result = self.collect().results[0]
        self.assertEqual("missing-path", result.error)
        self.assertEqual(("watched/",), result.missing_paths)
        self.assertFalse(any(c.new_path == "watched" for c in result.changes))

    def test_mode_change_changes_notification_identity(self):
        first = self.collect()
        (self.upstream / "watched" / "helper.txt").chmod(0o755)
        self.commit()
        result = self.collect().results[0]
        self.assertEqual("pending", result.status)
        self.assertEqual("100644", result.changes[0].old_mode)
        self.assertEqual("100755", result.changes[0].new_mode)
        self.assertEqual(result.changes[0].old_object, result.changes[0].new_object)
        self.assertNotEqual(monitor.fingerprint(monitor.compact(first, {})),
                            monitor.fingerprint(monitor.compact(monitor.Report((result,)), {})))

    def test_addition_and_deletion(self):
        self.write("watched/new.txt", "added\n")
        (self.upstream / "watched" / "helper.txt").unlink()
        self.commit()
        result = self.collect().results[0]
        self.assertEqual({"A", "D"}, {c.kind for c in result.changes})
        self.assertIn("+added", result.upstream_patch)
        self.assertIn("-helper", result.upstream_patch)

    def test_renames_across_both_watched_boundaries(self):
        (self.upstream / "watched" / "helper.txt").rename(self.upstream / "helper.txt")
        (self.upstream / "outside.txt").rename(self.upstream / "watched" / "outside.txt")
        self.commit()
        changes = self.collect().results[0].changes
        self.assertEqual({("watched/helper.txt", "helper.txt"), ("outside.txt", "watched/outside.txt")},
                         {(c.old_path, c.new_path) for c in changes})
        self.assertEqual({"R"}, {c.kind for c in changes})

    def test_absent_path_is_unknown_and_keeps_deletion_evidence(self):
        self.source["paths"] = ["watched/helper.txt"]
        self.write_registry()
        (self.upstream / "watched" / "helper.txt").unlink()
        self.commit()
        report = self.collect()
        self.assertTrue(report.failed)
        result = report.results[0]
        self.assertEqual("missing-path", result.error)
        self.assertEqual(("watched/helper.txt",), result.missing_paths)
        self.assertEqual("D", result.changes[0].kind)
        self.assertIn("-helper", result.upstream_patch)

    def test_absent_at_both_revisions_is_unknown(self):
        self.source["paths"] = ["absent"]
        self.write_registry()
        self.assertEqual("missing-path", self.collect().results[0].error)

    def test_whole_repository_path(self):
        self.source["paths"] = ["."]
        self.write_registry()
        self.write("outside.txt", "changed\n")
        self.commit()
        self.assertEqual("pending", self.collect().results[0].status)

    def test_fetch_is_shared_by_repository_and_ref(self):
        self.index["skills"]["other"] = copy.deepcopy(self.index["skills"]["sample"])
        self.save_registry()
        self.collect()
        self.assertEqual([("https://example.invalid/upstream", "main")], self.transport.fetches)

    def test_missing_ref_is_unknown(self):
        self.source["ref"] = "missing"
        self.write_registry()
        report = self.collect()
        self.assertTrue(report.failed)
        self.assertEqual("command-failed", report.results[0].error)

    def test_missing_reviewed_commit(self):
        self.source["last_reviewed_revision"] = "a" * 40
        self.write_registry()
        self.assertEqual("missing-commit", self.collect().results[0].error)

    def test_rewritten_history(self):
        git(self.upstream, "checkout", "--orphan", "replacement")
        self.write("watched/SKILL.md", "rewritten\n")
        self.commit()
        git(self.upstream, "branch", "-f", "main", "replacement")
        git(self.upstream, "tag", "old-history", self.before)
        original = self.transport.fetch

        def retaining_old_commit(transport, repository, ref):
            head = original(transport, repository, ref)
            transport.command("-c", "protocol.file.allow=always", "fetch", str(self.upstream), "old-history")
            return head

        with patch.object(self.transport, "fetch", retaining_old_commit):
            self.assertEqual("history-rewritten", self.collect().results[0].error)

    def test_fetch_failure_does_not_claim_clean(self):
        with patch.object(self.transport, "fetch", side_effect=monitor.MonitorError("timeout", "offline")):
            report = self.collect()
        self.assertEqual("unknown", report.results[0].status)
        self.assertTrue(report.failed)

    def test_patch_limit_is_unknown(self):
        self.write("watched/SKILL.md", "changed\n")
        self.commit()
        original = self.transport.command

        def limited(transport, *args):
            if "--binary" in args:
                raise monitor.MonitorError("output-limit", "Too much patch")
            return original(transport, *args)

        with patch.object(self.transport, "command", limited):
            result = self.collect().results[0]
        self.assertEqual("unknown", result.status)
        self.assertEqual("output-limit", result.error)

    def test_missing_local_entrypoint_is_unknown(self):
        self.write("watched/SKILL.md", "changed\n")
        self.commit()
        (self.harness / "skills" / "sample" / "SKILL.md").unlink()
        self.assertEqual("comparison-unavailable", self.collect().results[0].error)

    def test_ambiguous_entrypoint_reports_mapping_limit(self):
        self.write("watched/another/SKILL.md", "another\n")
        incorporated = self.commit()
        self.source["last_incorporated_revision"] = incorporated
        self.write_registry()
        self.write("watched/SKILL.md", "changed\n")
        self.commit()
        result = self.collect().results[0]
        self.assertEqual("pending", result.status)
        self.assertIn("explicit mapping", result.comparison_note)

    def test_registry_validation_runs_before_fetch(self):
        self.source["paths"] = ["../unsafe"]
        self.write_registry()
        report = self.collect()
        self.assertTrue(report.errors)
        self.assertEqual([], self.transport.fetches)


class FakeIssues:
    def __init__(self):
        self.records = []
        self.notes = []
        self.calls = []
        self.fail_comment = False
        self.fail_after = ""

    def issues(self):
        return copy.deepcopy(self.records)

    def comments(self, number):
        return copy.deepcopy(self.notes)

    def create(self, body):
        self.calls.append("create")
        self.records.append({"number": 1, "body": body, "state": "open"})
        self.after("create")
        return self.records[0]

    def edit(self, number, **fields):
        self.calls.append(tuple(fields))
        self.records[0].update(fields)
        self.after("body" if "body" in fields else "state")
        return self.records[0]

    def comment(self, number, body):
        if self.fail_comment:
            self.fail_comment = False
            raise monitor.MonitorError("command-failed", "Comment API failed")
        self.calls.append("comment")
        self.notes.append({"body": body})
        self.after("comment")
        return self.notes[-1]

    def after(self, operation):
        if operation == self.fail_after:
            self.fail_after = ""
            raise monitor.MonitorError("command-failed", "Response lost after remote mutation")


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeIssues()
        self.source = monitor.Source("sample", "source", "https://github.com/example/upstream", "main",
                                     ("watched/",), "a" * 40, "a" * 40, "Keep customizations.")
        self.change = monitor.Change("M", "watched/SKILL.md", "watched/SKILL.md", "1" * 40, "2" * 40, "100644", "100644")
        self.pending = self.report()

    def report(self, new_object="2" * 40):
        change = monitor.Change("M", "watched/SKILL.md", "watched/SKILL.md", "1" * 40, new_object, "100644", "100644")
        return monitor.Report((monitor.Result(self.source, "pending", "b" * 40, (change,)),))

    def publish(self, report=None):
        return monitor.reconcile_issue(report or self.pending, "example/harness", issues=self.client)

    def snapshot(self):
        return json.loads(monitor.SNAPSHOT.search(self.client.records[0]["body"])[1])

    def test_initial_creation_notifies_without_extra_comment(self):
        self.assertEqual("created", self.publish())
        self.assertEqual("quiet", self.publish())
        self.assertEqual(["create"], self.client.calls)
        self.assertEqual([], self.client.notes)
        self.assertEqual(1, self.snapshot()["generation"])

    def test_generation_supports_a_b_a(self):
        self.publish()
        self.publish(self.report("3" * 40))
        self.publish()
        self.assertEqual(3, self.snapshot()["generation"])
        self.assertEqual(2, len(self.client.notes))
        self.assertIn("upstream-notification:2:", self.client.notes[0]["body"])
        self.assertIn("upstream-notification:3:", self.client.notes[1]["body"])
        self.publish()
        self.assertEqual(2, len(self.client.notes))

    def test_comment_failure_retries_after_body_edit(self):
        self.publish()
        self.client.fail_comment = True
        with self.assertRaises(monitor.MonitorError):
            self.publish(self.report("3" * 40))
        self.assertEqual(2, self.snapshot()["generation"])
        self.publish(self.report("3" * 40))
        self.publish(self.report("3" * 40))
        self.assertEqual(1, len(self.client.notes))

    def test_lost_responses_after_each_remote_mutation_converge(self):
        for operation in ("create", "body", "comment", "close", "reopen"):
            with self.subTest(operation=operation):
                self.setUp()
                target = self.pending
                expected_generation = 1
                expected_notes = 0
                expected_state = "open"
                if operation != "create":
                    self.publish()
                if operation in ("body", "comment"):
                    target = self.report("3" * 40)
                    expected_generation = 2
                    expected_notes = 1
                if operation == "close":
                    target = monitor.Report((monitor.Result(self.source, "unchanged", "b" * 40),))
                    expected_generation = 2
                    expected_state = "closed"
                if operation == "reopen":
                    self.publish(monitor.Report((monitor.Result(self.source, "unchanged", "b" * 40),)))
                    expected_generation = 3
                    expected_notes = 1
                self.client.fail_after = "state" if operation in ("close", "reopen") else operation
                with self.assertRaisesRegex(monitor.MonitorError, "Response lost"):
                    self.publish(target)
                self.publish(target)
                self.publish(target)
                self.assertEqual(1, len(self.client.records))
                self.assertEqual(expected_generation, self.snapshot()["generation"])
                self.assertEqual(expected_notes, len(self.client.notes))
                self.assertEqual(expected_state, self.client.records[0]["state"])
                self.assertEqual(1, self.client.calls.count("create"))

    def test_manual_closed_pending_issue_reopens_without_repeat_comment(self):
        self.publish()
        self.client.records[0]["state"] = "closed"
        self.assertEqual("reopened", self.publish())
        self.assertEqual("open", self.client.records[0]["state"])
        self.assertEqual([], self.client.notes)

    def test_clean_closes_and_recurrence_reopens_with_notification(self):
        self.publish()
        clean = monitor.Report((monitor.Result(self.source, "unchanged", "b" * 40),))
        self.publish(clean)
        self.assertEqual("closed", self.client.records[0]["state"])
        self.assertEqual([], self.client.notes)
        self.publish()
        self.assertEqual("open", self.client.records[0]["state"])
        self.assertEqual(3, self.snapshot()["generation"])
        self.assertEqual(1, len(self.client.notes))

    def test_outage_preserves_pending_and_repeat_is_quiet(self):
        self.publish()
        offline = monitor.Report((monitor.Result(self.source, "unknown", error="timeout", detail="raw error A"),))
        self.publish(offline)
        self.assertEqual([monitor.asdict(self.change)], self.snapshot()["sources"][0]["changes"])
        self.assertIn("Previous pending changes remain unresolved", self.client.records[0]["body"])
        calls = list(self.client.calls)
        noisy = monitor.Report((monitor.Result(self.source, "unknown", error="timeout", detail="raw error B"),))
        self.publish(noisy)
        self.assertEqual(calls, self.client.calls)
        self.assertEqual("open", self.client.records[0]["state"])

    def test_new_watermark_drops_old_proposals_during_outage(self):
        self.publish()
        source = monitor.Source("sample", "source", self.source.repository, "main", ("watched/",), "c" * 40, "a" * 40, "Notes.")
        self.publish(monitor.Report((monitor.Result(source, "unknown", error="timeout"),)))
        self.assertEqual([], self.snapshot()["sources"][0]["changes"])

    def test_ref_change_drops_old_proposals_during_outage(self):
        self.publish()
        source = monitor.Source("sample", "source", self.source.repository, "other", ("watched/",),
                                self.source.reviewed, self.source.incorporated, "Notes.")
        self.publish(monitor.Report((monitor.Result(source, "unknown", error="timeout"),)))
        self.assertEqual([], self.snapshot()["sources"][0]["changes"])

    def test_invalid_registry_preserves_previous_proposals(self):
        self.publish()
        self.publish(monitor.Report((), ("Registry unavailable",)))
        source = self.snapshot()["sources"][0]
        self.assertEqual([monitor.asdict(self.change)], source["changes"])
        self.assertEqual("registry-invalid", source["error"])
        self.assertEqual("open", self.client.records[0]["state"])

    def test_registry_removal_drops_old_proposals(self):
        self.publish()
        self.publish(monitor.Report(()))
        self.assertEqual([], self.snapshot()["sources"])
        self.assertEqual("closed", self.client.records[0]["state"])

    def test_unknown_without_pending_never_closes(self):
        self.publish(monitor.Report((monitor.Result(self.source, "unknown", error="timeout"),)))
        self.assertEqual("open", self.client.records[0]["state"])

    def test_duplicate_marked_issues_fail(self):
        self.publish()
        self.client.records.append(dict(self.client.records[0], number=2))
        with self.assertRaisesRegex(monitor.MonitorError, "Multiple marked issues"):
            self.publish()

    def test_invalid_snapshot_fails(self):
        self.client.records = [{"number": 1, "state": "open", "body": monitor.MARKER}]
        with self.assertRaisesRegex(monitor.MonitorError, "invalid snapshot"):
            self.publish()

    def test_malformed_nested_snapshot_fails_without_key_error(self):
        self.publish()
        snapshot = self.snapshot()
        snapshot["sources"] = [{}]
        self.client.records[0]["body"] = monitor.MARKER + "\n<!-- upstream-snapshot:" + json.dumps(snapshot) + " -->"
        with self.assertRaisesRegex(monitor.MonitorError, "invalid snapshot"):
            self.publish()

    def test_issue_size_limit_is_explicit(self):
        self.publish()
        with patch.object(monitor, "ISSUE_LIMIT", 10):
            with self.assertRaisesRegex(monitor.MonitorError, "body limit"):
                self.publish(self.report("3" * 40))
        self.assertEqual(1, self.snapshot()["generation"])

    def test_unrelated_head_is_quiet(self):
        self.publish()
        result = self.pending.results[0]
        moved = monitor.Report((monitor.Result(result.source, "pending", "c" * 40, result.changes),))
        self.assertEqual("quiet", self.publish(moved))
        self.assertEqual(["create"], self.client.calls)

    def test_api_errors_propagate(self):
        with patch.object(self.client, "issues", side_effect=monitor.MonitorError("command-failed", "API unavailable")):
            with self.assertRaisesRegex(monitor.MonitorError, "API unavailable"):
                self.publish()

    def test_pagination_includes_closed_issues_and_comments(self):
        api = monitor.GitHub("example/harness")
        with patch.object(api, "request", side_effect=[[{"number": n} for n in range(100)], [{"number": 101}]]) as request:
            self.assertEqual(101, len(api.issues()))
            self.assertIn("state=all", request.call_args_list[0].args[1])
            self.assertIn("page=2", request.call_args_list[1].args[1])
        with patch.object(api, "request", return_value={"unexpected": True}):
            with self.assertRaises(monitor.MonitorError):
                api.comments(1)


class CliTests(RepositoryFixture):
    def cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(SCRIPTS / "monitor_upstream.py"), *args],
                              cwd=self.root, env=env, text=True, capture_output=True)

    def test_required_output_and_help_are_clear(self):
        result = self.cli("--help")
        self.assertEqual(0, result.returncode)
        self.assertIn("--issue-repo", result.stdout)
        result = self.cli()
        self.assertEqual(2, result.returncode)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_registry_still_produces_reports(self):
        (self.harness / "registry" / "skills.json").write_text("invalid")
        output = self.root / "reports"
        result = self.cli("--root", str(self.harness), "--output-dir", str(output))
        self.assertEqual(1, result.returncode)
        self.assertTrue(json.loads((output / "report.json").read_text())["errors"])
        self.assertTrue((output / "report.md").exists())
        self.assertNotIn("Traceback", result.stderr)

    def test_subprocess_reads_git_and_writes_read_only_report_from_other_cwd(self):
        self.write("watched/SKILL.md", "changed\n")
        self.commit()
        scripts = self.harness / "scripts"
        scripts.mkdir()
        shutil.copy(SCRIPTS / "monitor_upstream.py", scripts)
        shutil.copy(SCRIPTS / "check.py", scripts)
        tools = self.root / "bin"
        tools.mkdir()
        real_git = shutil.which("git")
        wrapper = tools / "git"
        wrapper.write_text("#!/usr/bin/env python3\nimport os, sys\na=sys.argv[1:]\n"
                           f"a=[{str(self.upstream)!r} if x=='https://example.invalid/upstream' else x for x in a]\n"
                           "if 'fetch' in a:\n i=a.index('fetch'); a[i:i]=['-c','protocol.file.allow=always']\n"
                           f"os.execv({real_git!r}, [{real_git!r}]+a)\n")
        wrapper.chmod(0o755)
        env = dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}")
        before = (self.harness / "registry" / "skills.json").read_bytes()
        output = self.root / "reports"
        result = subprocess.run([sys.executable, str(scripts / "monitor_upstream.py"), "--output-dir", str(output)],
                                cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        data = json.loads((output / "report.json").read_text())
        self.assertEqual("pending", data["results"][0]["status"])
        self.assertIn("+changed", (output / "report.md").read_text())
        self.assertEqual(before, (self.harness / "registry" / "skills.json").read_bytes())
        self.assertNotIn("Issue reconciliation", result.stdout)

    def test_protected_output_path_is_rejected(self):
        result = self.cli("--root", str(self.harness), "--output-dir", str(self.harness / "registry"))
        self.assertEqual(1, result.returncode)
        self.assertIn("Reports must be outside", result.stderr)
        self.assertFalse((self.harness / "registry" / "report.json").exists())
        self.assertNotIn("Traceback", result.stderr)

    def test_fake_gh_publishes_errors_with_full_newlines_and_keeps_failure(self):
        (self.harness / "registry" / "skills.json").write_text("invalid")
        tools = self.root / "bin"
        tools.mkdir()
        capture = self.root / "api-payload.json"
        wrapper = tools / "gh"
        wrapper.write_text("#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n"
                           "a=sys.argv[1:]\n"
                           "if a[a.index('--method')+1]=='GET': print('[]')\n"
                           "else:\n payload=json.loads(Path(a[a.index('--input')+1]).read_text())\n"
                           f" Path({str(capture)!r}).write_text(json.dumps(payload))\n"
                           " print(json.dumps(dict(payload,number=1,state='open')))\n")
        wrapper.chmod(0o755)
        result = self.cli("--root", str(self.harness), "--output-dir", str(self.root / "report"),
                          "--issue-repo", "example/harness", env=dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}"))
        self.assertEqual(1, result.returncode)
        self.assertIn("Issue reconciliation created", result.stdout)
        body = json.loads(capture.read_text())["body"]
        self.assertIn("\n# External skill updates\n", body)
        self.assertIn("Registry error", body)
        self.assertIn(monitor.MARKER, body)
        self.assertTrue((self.root / "report" / "report.json").exists())
        self.assertNotIn("Traceback", result.stderr)

    def test_fake_gh_failure_retains_report_and_fails_without_traceback(self):
        self.source["paths"] = ["../unsafe"]
        self.write_registry()
        tools = self.root / "bin"
        tools.mkdir()
        wrapper = tools / "gh"
        wrapper.write_text("#!/bin/sh\nprintf 'API unavailable' >&2\nexit 1\n")
        wrapper.chmod(0o755)
        result = self.cli("--root", str(self.harness), "--output-dir", str(self.root / "report"),
                          "--issue-repo", "example/harness", env=dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}"))
        self.assertEqual(1, result.returncode)
        self.assertIn("API unavailable", result.stderr)
        self.assertTrue((self.root / "report" / "report.json").exists())
        self.assertNotIn("Traceback", result.stderr)


class CommandTests(unittest.TestCase):
    def test_stderr_diagnostic_is_retained(self):
        with self.assertRaisesRegex(monitor.MonitorError, "fixture transport failure"):
            monitor.run([sys.executable, "-c", "import sys; sys.stderr.write('fixture transport failure'); sys.exit(1)"])

    def test_limits_and_timeout(self):
        with self.assertRaisesRegex(monitor.MonitorError, "evidence limit"):
            monitor.run([sys.executable, "-c", "print('x'*1000)"], limit=10)
        with self.assertRaisesRegex(monitor.MonitorError, "time limit"):
            monitor.run([sys.executable, "-c", "import time; time.sleep(2)"], timeout=0.1)


if __name__ == "__main__":
    unittest.main()
