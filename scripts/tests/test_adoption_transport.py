import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import Mock

import test_monitor_upstream as fixtures


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import monitor_upstream as monitor
from route_adoption_event import adoption_issue
from wake_upstream_operator import dispatch


class AdoptionTransportTests(unittest.TestCase):
    repository = "example/harness"
    owner = "maintainer"
    branch = "adoption/issue-17-approval-1234"

    def route(self, event, payload):
        return adoption_issue(event, {"repository": {"full_name": self.repository}, **payload},
                              self.repository, self.owner)

    def test_only_the_owners_fresh_queue_issue_comment_wakes_work(self):
        event = {
            "action": "created",
            "issue": {"number": 17, "state": "open", "user": {"login": monitor.ACTIONS_LOGIN},
                      "body": monitor.MARKER + "\nBatch"},
            "comment": {"user": {"login": self.owner}, "created_at": "2026-03-01T00:00:00Z",
                        "updated_at": "2026-03-01T00:00:00Z", "body": "Discussions are wake hints too"},
        }
        self.assertEqual(17, self.route("issue_comment", event))
        for key, value in (("issue", {"pull_request": {}}), ("issue", {"body": "User " + monitor.MARKER}),
                           ("issue", {"user": {"login": self.owner}}), ("issue", {"state": "closed"}),
                           ("comment", {"user": {"login": "another"}}), ("comment", {"updated_at": "later"})):
            with self.subTest(key=key, value=value):
                altered = copy.deepcopy(event)
                altered[key].update(value)
                self.assertIsNone(self.route("issue_comment", altered))
        self.assertIsNone(self.route("issue_comment", dict(event, action="edited")))

    def test_ci_and_pr_closure_resume_the_issue_without_running_branch_code(self):
        run = {"name": "Check harness", "head_repository": {"full_name": self.repository}, "head_branch": self.branch}
        event = {"action": "completed", "workflow_run": run}
        self.assertEqual(17, self.route("workflow_run", event))
        for key, value in (("head_repository", {"full_name": "fork/harness"}), ("head_branch", "feature"),
                           ("name", "Another workflow"), ("head_branch", self.branch + "-other")):
            self.assertIsNone(self.route("workflow_run", dict(event, workflow_run=dict(run, **{key: value}))))
        pr = {"base": {"ref": "main"}, "head": {"repo": {"full_name": self.repository}, "ref": self.branch}}
        self.assertEqual(17, self.route("pull_request_target", {"action": "closed", "pull_request": pr}))
        pr["head"]["repo"] = None
        self.assertIsNone(self.route("pull_request_target", {"action": "closed", "pull_request": pr}))

    def test_public_entry_point_only_emits_an_issue_number(self):
        event = {"repository": {"full_name": self.repository}, "action": "completed", "workflow_run": {
            "name": "Check harness", "head_repository": {"full_name": self.repository}, "head_branch": self.branch}}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "event").write_text(json.dumps(event))
            subprocess.run([sys.executable, str(ROOT / "scripts/route_adoption_event.py")], check=True,
                           env={**os.environ, "GITHUB_EVENT_NAME": "workflow_run", "GITHUB_REPOSITORY": self.repository,
                                "GITHUB_EVENT_PATH": str(path / "event"), "GITHUB_OUTPUT": str(path / "output"),
                                "ADOPTION_OWNER": self.owner})
            self.assertEqual("issue=17\n", (path / "output").read_text())

    def test_startup_dispatch_verifies_private_target_and_revokes_ephemeral_token(self):
        client = Mock(side_effect=[{"id": 7}, {"token": "temporary"},
                                   {"private": True, "full_name": "org/operator", "default_branch": "stable"}, {}, {}])
        dispatch("org/operator", "app-identity", client)
        self.assertEqual(("POST", "app/installations/7/access_tokens", "app-identity",
                          {"repositories": ["operator"], "permissions": {"actions": "write"}}),
                         client.call_args_list[1].args)
        self.assertEqual(("POST", "repos/org/operator/actions/workflows/upstream-adoption.yml/dispatches", "temporary",
                          {"ref": "stable"}), client.call_args_list[3].args)
        self.assertEqual(("DELETE", "installation/token", "temporary"), client.call_args_list[-1].args)
        client = Mock(side_effect=[{"id": 7}, {"token": "temp"}, {"private": False}, {}])
        with self.assertRaises(ValueError):
            dispatch("org/operator", "app-identity", client)
        self.assertEqual(("DELETE", "installation/token", "temp"), client.call_args_list[-1].args)

    def test_private_workflow_runs_the_installed_worker_by_path_and_forwards_only_hint(self):
        yaml = (ROOT / "templates/upstream-operator/upstream-adoption.yml").read_text()
        command = textwrap.dedent(yaml.split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            script = directory / "installed worker.py"
            script.write_text("import json, sys; print(json.dumps(sys.argv[1:]))")
            env = dict(os.environ, WORKER=str(script), SOURCE=self.repository, OWNER=self.owner,
                       STATE=str(directory / "private state"), BOT="harness[bot]", MODEL="", EFFORT="")
            required = ["--repo", self.repository, "--owner", self.owner, "--bot", "harness[bot]",
                        "--state-dir", str(directory / "private state")]
            for hint, expected in [("", required), ("17", [*required, "--issue", "17"])]:
                job = subprocess.run(["bash", "-e", "-c", command], env=dict(env, ISSUE=hint),
                                     cwd=directory, check=True, capture_output=True, text=True)
                self.assertEqual(expected, json.loads(job.stdout))
            invalid = subprocess.run(["bash", "-e", "-c", command], env=dict(env, ISSUE="17 --other"),
                                     cwd=directory, capture_output=True)
            self.assertNotEqual(0, invalid.returncode)
            self.assertEqual(b"", invalid.stdout)

    def test_network_restoration_requests_catchup_with_no_periodic_job(self):
        hook = ROOT / "templates/upstream-operator/90-upstream-adoption-reconnect"
        with tempfile.TemporaryDirectory() as tmp:
            systemctl = Path(tmp) / "systemctl"
            systemctl.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
            systemctl.chmod(0o755)
            for reason, state, expected in (("down", "NONE", False), ("connectivity-change", "LIMITED", False),
                                            ("connectivity-change", "FULL", True), ("up", "", True)):
                wake = subprocess.run([hook, "fixture", reason], check=True, capture_output=True, text=True,
                                      env={**os.environ, "PATH": tmp, "CONNECTIVITY_STATE": state})
                self.assertEqual(["--no-block", "start", "upstream-adoption-reconnect.service"] if expected else [],
                                 wake.stdout.splitlines())

    def test_monitor_hands_clean_batch_to_worker_until_final_receipt(self):
        client = fixtures.FakeIssues()
        fixture = fixtures.PublisherTests()
        fixture.setUp()
        def reconcile(report):
            return monitor.reconcile_batch(report, self.repository, issues=client, adoption=True)
        self.assertEqual(("quiet", None), reconcile(fixture.clean_report()))
        action, number = reconcile(fixture.pending)
        self.assertEqual(("created", 1), (action, number))
        self.assertEqual(("quiet", number), reconcile(fixture.pending))
        self.assertEqual(("awaiting-adoption", number), reconcile(fixture.clean_report()))
        self.assertEqual(("awaiting-adoption", number), reconcile(fixture.clean_report()))
        self.assertEqual("open", client.records[0]["state"])
        client.edit(number, state="closed")
        self.assertEqual(("quiet", None), reconcile(fixture.clean_report()))
        self.assertEqual(("created", number + 1), reconcile(fixture.pending))


if __name__ == "__main__":
    unittest.main()
