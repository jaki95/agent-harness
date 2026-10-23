import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/harness/scripts/pr_publish.py"
FIXTURE = Path(__file__).parent / "fixtures/pr_publish_gh.py"
REQUEST_ID = "630b9d5e-3f2a-4f7e-8b0c-2d5f9a8c1e42"


class PrPublishTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.remote = self.root / "fork.git"
        self.base_remote = self.root / "base.git"
        self.work = self.root / "work"
        self.work.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        executable = self.bin / "gh"
        shutil.copyfile(FIXTURE, executable)
        executable.chmod(0o755)
        self.scenario_path = self.root / "scenario.json"
        self.log = self.root / "calls.jsonl"
        self.env = {**os.environ, "PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
                    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_ALLOW_PROTOCOL": "file",
                    "PUBLISH_SCENARIO": str(self.scenario_path), "PUBLISH_LOG": str(self.log)}
        self.git("init", "--bare", str(self.remote))
        self.git("init", "--bare", str(self.base_remote))
        self.git("init", "-b", "guessed-topic")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        self.git("config", f"url.{self.remote}.insteadOf", "git@github.com:contributor/fork.git")
        self.git("remote", "add", "origin", str(self.base_remote))
        self.head = self.commit("initial")
        self.git("push", str(self.remote), "HEAD:refs/heads/actual-topic")
        self.new_head = self.commit("fixed")
        self.git("push", str(self.remote), "HEAD:refs/testing/prepared")
        self.git("--git-dir", str(self.remote), "update-ref", "-d", "refs/testing/prepared")
        self.snapshot = {
            "id": "PR_fixture", "number": 12, "url": "https://github.com/fixture/project/pull/12",
            "headRefOid": self.head, "headRefName": "actual-topic",
            "headRepository": {"nameWithOwner": "contributor/fork",
                               "url": "https://github.com/contributor/fork",
                               "sshUrl": "git@github.com:contributor/fork.git"},
            "baseRefOid": self.head, "baseRefName": "main", "state": "OPEN", "isDraft": False,
            "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN", "reviewDecision": "APPROVED",
            "mergedAt": None, "autoMergeRequest": None,
        }
        self.scenario = {"snapshots": [self.snapshot], "remote": str(self.remote),
                         "head_from_remote": True}

    def git(self, *arguments, check=True):
        return subprocess.run(["git", *arguments], cwd=self.work, env=self.env,
                              text=True, capture_output=True, check=check, timeout=10)

    def commit(self, content):
        (self.work / "content").write_text(content)
        self.git("add", "content")
        self.git("commit", "-m", content)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def run_cli(self, action="push", *arguments):
        self.scenario_path.write_text(json.dumps(self.scenario))
        self.log.unlink(missing_ok=True)
        return subprocess.run([sys.executable, str(SCRIPT), action, "--repo", "fixture/project",
                               "12", "--expected-head", self.head, *arguments], cwd=self.work,
                              env=self.env, capture_output=True, text=True, timeout=10)

    def refs(self, repository):
        result = self.git("--git-dir", str(repository), "for-each-ref", "--format=%(refname) %(objectname)")
        return dict(line.split() for line in result.stdout.splitlines())

    def mutations(self):
        calls = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return [call for call in calls if "PUT" in call["arguments"]]

    def test_push_updates_exact_existing_fork_ref_not_local_or_origin_branch(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.refs(self.remote), {"refs/heads/actual-topic": self.new_head})
        self.assertEqual(self.refs(self.base_remote), {})
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["head_repository"], "contributor/fork")
        self.assertEqual(receipt["head_ref"], "actual-topic")
        self.assertEqual(receipt["status"], "published")

    def test_missing_branch_is_not_created(self):
        self.git("--git-dir", str(self.remote), "update-ref", "-d", "refs/heads/actual-topic")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("does not exist", result.stderr)
        self.assertEqual(self.refs(self.remote), {})

    def test_https_transport_uses_github_target_and_confirms_published_head(self):
        self.git("config", f"url.{self.remote}.insteadOf", "https://github.com/contributor/fork.git")
        result = self.run_cli("push", "--transport", "https")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.refs(self.remote), {"refs/heads/actual-topic": self.new_head})

    def test_unconfirmed_push_reports_failure_without_retrying_or_creating_refs(self):
        self.scenario["head_from_remote"] = False
        result = self.run_cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("publication not confirmed", result.stderr)
        self.assertEqual(self.refs(self.remote), {"refs/heads/actual-topic": self.new_head})
        self.assertEqual(self.refs(self.base_remote), {})

    def test_missing_head_repository_cannot_publish(self):
        self.snapshot["headRepository"] = None
        result = self.run_cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("head repository", result.stderr)
        self.assertEqual(self.refs(self.remote), {"refs/heads/actual-topic": self.head})

    def test_stale_expected_head_and_remote_movement_cannot_overwrite_changes(self):
        for github_matches in (True, False):
            with self.subTest(github_matches=github_matches):
                self.scenario["head_from_remote"] = github_matches
                self.git("--git-dir", str(self.remote), "update-ref", "refs/heads/actual-topic", self.new_head)
                result = self.run_cli()
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("head", result.stderr)
                self.assertEqual(self.refs(self.remote), {"refs/heads/actual-topic": self.new_head})

    def test_deleted_or_moved_branch_between_read_and_push_is_not_recreated_or_overwritten(self):
        for replacement in (None, self.new_head):
            with self.subTest(replacement=replacement):
                self.git("--git-dir", str(self.remote), "update-ref", "refs/heads/actual-topic", self.head)
                hook = self.work / ".git/hooks/pre-push"
                command = ["git", "--git-dir", str(self.remote), "update-ref"]
                command += ["refs/heads/actual-topic", replacement] if replacement else ["-d", "refs/heads/actual-topic"]
                hook.write_text("#!/bin/sh\n" + shlex.join(command) + "\n")
                hook.chmod(0o755)
                result = self.run_cli()
                self.assertEqual(result.returncode, 2, result.stderr)
                expected = {"refs/heads/actual-topic": replacement} if replacement else {}
                self.assertEqual(self.refs(self.remote), expected)

    def test_rewrite_requires_explicit_flag_and_still_uses_expected_head(self):
        self.git("checkout", "--orphan", "rewrite")
        rewritten = self.commit("rewrite")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.refs(self.remote), {"refs/heads/actual-topic": self.head})
        result = self.run_cli("push", "--allow-rewrite")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.refs(self.remote), {"refs/heads/actual-topic": rewritten})

    def stack(self, predecessor_merged=False):
        return [{"number": 5, "pull_requests": [
            {"number": 11, "state": "closed" if predecessor_merged else "open",
             "merged_at": "2026-10-23T01:00:00Z" if predecessor_merged else None,
             "head": {"sha": self.head}},
            {"number": 12, "state": "open", "merged_at": None, "head": {"sha": self.head}},
            {"number": 13, "state": "open", "merged_at": None, "head": {"sha": self.new_head}},
        ]}]

    def prepare_merge(self, response):
        self.scenario["head_from_remote"] = False
        self.scenario["merge_response"] = response
        merged = {**self.snapshot, "state": "MERGED", "mergedAt": "2026-10-23T01:00:00Z"}
        self.scenario["snapshots"] = [self.snapshot, self.snapshot, merged]

    def test_native_stack_refuses_unmerged_predecessor_without_mutation(self):
        self.scenario["stacks"] = self.stack()
        for state in ("open", "closed"):
            with self.subTest(state=state):
                self.scenario["stacks"][0]["pull_requests"][0]["state"] = state
                result = self.run_cli("merge")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("predecessor #11", result.stderr)
                self.assertEqual(self.mutations(), [])

    def test_native_stack_lands_only_next_pr_with_head_guard_and_no_rule_bypass(self):
        self.scenario["stacks"] = self.stack(predecessor_merged=True)
        self.prepare_merge({"status": "pending", "details": {"uuid": REQUEST_ID,
                            "expected_head_sha": self.head, "merge_method": "squash",
                            "merge_action": "default", "bypass_rules": False}})
        self.scenario["poll_response"] = {"status": "merged", "details": {"sha": self.new_head}}
        result = self.run_cli("merge")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "merged")
        self.assertEqual([call["payload"] for call in self.mutations()], [{
            "sha": self.head, "merge_method": "squash", "merge_action": "default", "bypass_rules": False}])
        self.assertEqual(self.mutations()[0]["arguments"][1], "repos/fixture/project/pulls/12/merge-async")

    def test_standalone_merge_uses_same_guarded_api(self):
        self.prepare_merge({"status": "merged", "details": {"sha": self.new_head}})
        result = self.run_cli("merge")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.mutations()), 1)
        self.assertEqual(self.mutations()[0]["payload"]["sha"], self.head)

    def test_changed_head_or_target_before_merge_prevents_mutation(self):
        for change in ({"headRefOid": self.new_head}, {"headRefName": "renamed"}, {"baseRefName": "release"}):
            with self.subTest(change=change):
                self.scenario["head_from_remote"] = False
                self.scenario["snapshots"] = [self.snapshot, {**self.snapshot, **change}]
                result = self.run_cli("merge")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(self.mutations(), [])

    def test_pending_queue_and_failure_are_not_reported_merged_or_retried(self):
        for response in ({"status": "enqueued", "details": {}},
                         {"status": "failed", "details": {"message": "Required check failed"}},
                         {"status": "pending", "details": {"uuid": REQUEST_ID,
                          "expected_head_sha": self.head, "merge_method": "squash",
                          "merge_action": "default", "bypass_rules": False}}):
            with self.subTest(status=response["status"]):
                self.prepare_merge(response)
                self.scenario["poll_response"] = response
                result = self.run_cli("merge", "--wait", "0")
                self.assertEqual(result.returncode, 2 if response["status"] == "failed" else 3, result.stderr)
                self.assertEqual(len(self.mutations()), 1)
                if response["status"] != "failed":
                    self.assertEqual(json.loads(result.stdout)["status"], response["status"])

    def test_async_merged_response_requires_pr_state_confirmation(self):
        self.prepare_merge({"status": "merged", "details": {"sha": self.new_head}})
        self.scenario["snapshots"] = [self.snapshot]
        result = self.run_cli("merge")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("not confirmed", result.stderr)

    def test_ambiguous_stack_or_pending_request_does_not_fall_back_to_legacy_merge(self):
        self.scenario["stacks"] = self.stack(True) * 2
        result = self.run_cli("merge")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.mutations(), [])
        self.scenario["stacks"] = []
        self.scenario["merge_error"] = "HTTP 409: another merge request is pending"
        result = self.run_cli("merge")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(len(self.mutations()), 1)
        self.assertIn("another merge request is pending", result.stderr)


if __name__ == "__main__":
    unittest.main()
