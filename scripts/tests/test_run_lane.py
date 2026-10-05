import importlib.util
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "skills/harness/scripts/run_lane.py"
MODULE_SPEC = importlib.util.spec_from_file_location("harness_run_lane", LAUNCHER)
lane = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = lane
PREVIOUS_BYTECODE = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    MODULE_SPEC.loader.exec_module(lane)
finally:
    sys.dont_write_bytecode = PREVIOUS_BYTECODE


def alive(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


@unittest.skipUnless(sys.platform.startswith("linux"), "verified process inventory requires Linux")
class RunLaneTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="run-lane-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.temp = self.root / "runs"
        self.temp.mkdir()
        self.git("init", "-q")
        (self.repo / "source.txt").write_text("committed\n")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
        self.head = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True)

    def spec(self, code, **kwargs):
        values = dict(checkout=self.repo, expected_head=self.head, temp_root=self.temp,
                      argv=("python", "-c", code), deadline_seconds=5)
        values.update(kwargs)
        return lane.LaneSpec(**values)

    def run_code(self, code, **kwargs):
        result = lane.run_lane(self.spec(code, **kwargs))
        self.assertIsNotNone(result.receipt_path)
        receipt = json.loads(result.receipt_path.read_text())
        return result, receipt

    def command(self, code, environment=None, deadline=5, **flags):
        args = [sys.executable, str(LAUNCHER), "--checkout", str(self.repo), "--head", self.head,
                "--temp-root", str(self.temp), "--deadline", str(deadline)]
        if environment is not None:
            path = self.root / ("environment-" + str(time.monotonic_ns()) + ".json")
            path.write_text(json.dumps(environment))
            args += ["--env", str(path)]
        for name, value in flags.items():
            args += ["--" + name.replace("_", "-"), str(value)]
        return args + ["--", "python", "-c", code]

    def await_file(self, path, child):
        end = time.monotonic() + 5
        while time.monotonic() < end:
            if path.exists() and path.read_text():
                return path.read_text()
            if child.poll() is not None:
                self.fail("launcher exited before its execution readiness marker")
            time.sleep(0.02)
        self.fail("execution readiness marker did not appear")

    def test_success_and_nonzero_have_distinct_receipts(self):
        result, receipt = self.run_code("import os; print(os.environ['OUTPUT'])", public_env={"OUTPUT": "receipt must not copy stdout"})
        self.assertEqual((result.outcome, result.cleanup, result.returncode), ("passed", "complete", 0))
        self.assertEqual(receipt["source"]["source_after"], self.head)
        self.assertEqual(Path(receipt["command"][0]).parent, result.receipt_path.parent / "venv/bin")
        self.assertNotIn("receipt must not copy stdout", result.receipt_path.read_text())
        result, receipt = self.run_code("raise SystemExit(7)")
        self.assertEqual((result.outcome, result.returncode, receipt["cleanup"]), ("command_failed", 7, "complete"))

    def test_concurrent_interpreters_packages_and_caches_are_private(self):
        code = """import json, os, pathlib, sys, sysconfig, time
site = pathlib.Path(sysconfig.get_path('purelib'))
(site / 'lane_package.py').write_text('value = ' + repr(os.environ['VALUE']))
cache = pathlib.Path(os.environ['XDG_CACHE_HOME']) / 'value'
cache.write_text(os.environ['VALUE'])
time.sleep(.2)
import lane_package
print(json.dumps({'package': lane_package.value, 'cache': cache.read_text(), 'prefix': sys.prefix}))
"""
        children = [subprocess.Popen(self.command(code, {"VALUE": value}), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for value in ("private-value-alpha", "private-value-beta")]
        receipts = []
        for child, expected in zip(children, ("private-value-alpha", "private-value-beta")):
            output, error = child.communicate(timeout=10)
            self.assertEqual(child.returncode, 0, error + output)
            receipt = json.loads(Path(json.loads(output)["receipt"]).read_text())
            receipts.append(receipt)
            stdout = Path(receipt["run_directory"]) / "execution.stdout"
            observed = json.loads(stdout.read_text())
            self.assertEqual(observed, {"package": expected, "cache": expected, "prefix": receipt["environment_paths"]["VIRTUAL_ENV"]})
            self.assertNotIn(expected, json.dumps(receipt))
        self.assertNotEqual(receipts[0]["run_directory"], receipts[1]["run_directory"])

    def test_missing_temp_root_has_no_fallback_and_preserves_control(self):
        marker = self.temp / "unrelated"
        marker.write_text("retain")
        result = lane.run_lane(self.spec("raise RuntimeError", temp_root=self.root / "missing"))
        self.assertEqual((result.outcome, result.receipt_path, result.cleanup), ("environment_failed", None, "not_started"))
        self.assertEqual(marker.read_text(), "retain")
        self.assertEqual(list(self.temp.iterdir()), [marker])

    def test_source_mismatch_and_dirty_source_never_execute(self):
        marker = self.root / "executed"
        code = f"from pathlib import Path; Path({str(marker)!r}).touch()"
        result, receipt = self.run_code(code, expected_head="0" * 40)
        self.assertEqual((result.outcome, receipt["reason"]), ("environment_failed", "source_identity_changed"))
        self.assertFalse(marker.exists())
        (self.repo / "source.txt").write_text("changed")
        result, receipt = self.run_code(code)
        self.assertEqual(receipt["reason"], "source_not_clean")
        self.assertFalse(marker.exists())

    def test_head_mutation_after_success_is_environment_failure(self):
        code = "import subprocess; subprocess.check_call(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-qm','changed'])"
        result, receipt = self.run_code(code)
        self.assertEqual((result.outcome, result.returncode, receipt["reason"]), ("environment_failed", 0, "source_identity_changed"))

    def lifecycle(self, signum=None, early_exit=False):
        marker = self.root / "descendant.pid"
        descendant = "import os,signal,time,pathlib; signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path(os.environ['PID_FILE']).write_text(str(os.getpid()) + ' ' + pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]); time.sleep(30)"
        code = f"import os,subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{descendant!r}]); p=os.environ['PID_FILE'];\nwhile not os.path.exists(p): time.sleep(.01)\n"
        if not early_exit:
            code += "time.sleep(30)\n"
        control = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
        self.addCleanup(lambda: control.poll() is None and control.kill())
        child = subprocess.Popen(self.command(code, {"PID_FILE": str(marker)}, deadline=2 if signum is None and not early_exit else 5), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            identity = self.await_file(marker, child).split()
            pid, started = map(int, identity)
            if signum:
                child.send_signal(signum)
            output, error = child.communicate(timeout=10)
            receipt = json.loads(Path(json.loads(output)["receipt"]).read_text())
            self.assertEqual(receipt["cleanup"], "complete", error + output)
            self.assertFalse(alive(pid), receipt)
            self.assertIsNone(control.poll())
            execution = next(item for item in receipt["commands"] if item["phase"] == "execution")
            self.assertEqual([item["signal"] for item in execution["signals"]], ["SIGTERM", "SIGKILL"])
            return receipt
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            control.terminate()
            control.wait()
            if marker.exists() and marker.read_text():
                pid, started = map(int, marker.read_text().split())
                try:
                    observed = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
                    if int(observed[19]) == started and observed[0] != "Z":
                        os.kill(pid, signal.SIGKILL)
                except FileNotFoundError:
                    pass

    def test_timeout_kills_term_resistant_descendant_and_preserves_control(self):
        receipt = self.lifecycle()
        self.assertEqual(receipt["outcome"], "timed_out")

    def test_sigint_cancellation_cleans_owned_group(self):
        self.assertEqual(self.lifecycle(signal.SIGINT)["outcome"], "cancelled")

    def test_sigterm_cancellation_cleans_owned_group(self):
        self.assertEqual(self.lifecycle(signal.SIGTERM)["outcome"], "cancelled")

    def test_early_exiting_leader_still_cleans_descendant(self):
        self.assertEqual(self.lifecycle(early_exit=True)["outcome"], "passed")

    def test_unsupported_platform_does_not_execute(self):
        marker = self.root / "execution"
        with patch.object(lane.sys, "platform", "darwin"):
            result, receipt = self.run_code(f"from pathlib import Path; Path({str(marker)!r}).touch()")
        self.assertEqual((result.outcome, receipt["cleanup"]), ("unsupported", "not_started"))
        self.assertFalse(marker.exists())

    def test_inventory_failure_never_reports_cleanup_success(self):
        marker = self.root / "execution"
        original = lane.inventory
        def failing_inventory():
            if marker.exists():
                raise lane.LaneFailure("process_inventory_unavailable")
            return original()
        with patch.object(lane, "inventory", failing_inventory):
            result, receipt = self.run_code(f"import pathlib,time; pathlib.Path({str(marker)!r}).touch(); time.sleep(30)")
        self.assertEqual((result.outcome, result.cleanup), ("environment_failed", "incomplete"))
        self.assertEqual(receipt["reason"], "cleanup_incomplete")
        self.assertFalse(alive(next(item["leader"] for item in receipt["commands"] if item["phase"] == "execution")))

    def test_secret_argv_rejected_and_hooks_cannot_copy_secret(self):
        secret = "credential-value-for-test"
        result = lane.run_lane(self.spec(f"print({secret!r})", secret_env={"TOKEN": secret}))
        self.assertEqual((result.outcome, result.receipt_path), ("environment_failed", None))
        code = """import json, os, pathlib, sys
hooks = pathlib.Path(os.environ['HARNESS_LANE_HOOKS'])
events = [
 {'kind':'ready','id':'service','elapsed_seconds':0},
 {'kind':'import','module':'json','file':json.__file__},
 {'kind':'ready','id':os.environ['TOKEN'],'elapsed_seconds':0},
 {'kind':'import','module':'json','file':json.__file__,'extra':os.environ['TOKEN']},
 {'kind':'ready','id':'future','elapsed_seconds':999},
]
hooks.write_text('\\n'.join(json.dumps(event) for event in events))
print(os.environ['TOKEN'])
"""
        result, receipt = self.run_code(code, secret_env={"TOKEN": secret})
        self.assertEqual(result.outcome, "passed")
        self.assertNotIn(secret, result.receipt_path.read_text())
        self.assertEqual(receipt["rejected_hooks"], 3)
        self.assertEqual([event["kind"] for event in receipt["hooks"]], ["ready", "import"])

    def test_reserved_environment_and_external_python_fail_closed(self):
        result, receipt = self.run_code("print('never')", public_env={"PYTHONPATH": str(self.root)})
        self.assertEqual(receipt["reason"], "reserved_environment")
        result, receipt = self.run_code("print('never')", argv=(sys.executable, "-c", "print('never')"))
        self.assertEqual(receipt["reason"], "external_python_interpreter")

    def test_receipt_export_is_exclusive(self):
        export = self.root / "lane.json"
        result, receipt = self.run_code("print('ok')", receipt=export)
        self.assertEqual(result.outcome, "passed")
        self.assertEqual(json.loads(export.read_text()), receipt)
        before = export.read_bytes()
        result, receipt = self.run_code("print('never')", receipt=export)
        self.assertEqual((result.outcome, receipt["reason"]), ("environment_failed", "receipt_exists"))
        self.assertEqual(export.read_bytes(), before)

    def test_export_includes_failure_receipts(self):
        export = self.root / "failure.json"
        result, receipt = self.run_code("print('never')", expected_head="0" * 40, receipt=export)
        self.assertEqual(result.outcome, "environment_failed")
        self.assertEqual(json.loads(export.read_text()), receipt)

    def test_hook_fifo_and_symlink_never_block_or_read_external_values(self):
        for code in (
            "import os; os.mkfifo(os.environ['HARNESS_LANE_HOOKS'])",
            "import os; os.symlink('/dev/zero',os.environ['HARNESS_LANE_HOOKS'])",
        ):
            result, receipt = self.run_code(code)
            self.assertEqual(result.outcome, "passed")
            self.assertEqual((receipt["hooks"], receipt["rejected_hooks"]), ([], 1))

    def test_ignored_sigchld_is_unsupported_before_spawn(self):
        previous = signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        try:
            result, receipt = self.run_code("print('never')")
        finally:
            signal.signal(signal.SIGCHLD, previous)
        self.assertEqual((result.outcome, receipt["reason"]), ("unsupported", "default_sigchld_required"))

    @unittest.skipUnless(shutil.which("node"), "acceptance integration requires Node")
    def test_acceptance_gate_uses_launcher_argv_and_receipt_artifact(self):
        driver = self.repo / "driver.py"
        driver.write_text(
            "import pathlib, subprocess, sys\n"
            "checkout = pathlib.Path.cwd()\n"
            "head = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()\n"
            f"command = [sys.executable, {str(LAUNCHER)!r}, '--checkout', str(checkout), '--head', head, "
            f"'--temp-root', {str(self.temp)!r}, '--deadline', '10', '--receipt', sys.argv[1], "
            "'--', 'python', '-c', 'print(42)']\n"
            "raise SystemExit(subprocess.call(command))\n"
        )
        manifest = {
            "version": 1, "repoRoot": ".",
            "outcomes": [{"id": "lane", "description": "Project verification owns its child group", "scenarioIds": ["run"]}],
            "scenarios": [{"id": "run", "setup": "Run the project gate in its private lane", "pass": "The gate succeeds and retains its lifecycle receipt", "verification": {"gateIds": ["verify"]}}],
            "gates": [{"id": "verify", "argv": [sys.executable, "driver.py", "{run}/lane.json"], "timeoutMs": 20000, "predicate": {"exitCode": 0}, "artifacts": ["{run}/lane.json"]}],
            "findings": [],
        }
        manifest_path = self.repo / "acceptance.json"
        manifest_path.write_text(json.dumps(manifest))
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "driver")
        checker = ROOT / "skills/harness/scripts/check-plan.mjs"
        for action in ("declare", "run", "check"):
            result = subprocess.run([shutil.which("node"), str(checker), "acceptance", action, str(manifest_path)], cwd=self.repo, capture_output=True, text=True, timeout=25)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            if action != "declare":
                self.assertTrue(json.loads(result.stdout)["ready"])
        artifacts = list((self.repo / ".git").rglob("lane.json"))
        self.assertTrue(artifacts)
        receipt = json.loads(artifacts[0].read_text())
        self.assertEqual((receipt["outcome"], receipt["cleanup"]), ("passed", "complete"))
        self.assertEqual(receipt["source"]["source_after"], self.git("rev-parse", "HEAD").strip())

    def test_denied_group_signal_is_incomplete(self):
        with patch.object(lane.os, "killpg", side_effect=PermissionError):
            result, receipt = self.run_code("print('never')")
        self.assertEqual((result.outcome, result.cleanup), ("environment_failed", "incomplete"))
        self.assertEqual(receipt["commands"][0]["signals"][0]["result"], "denied")

    def test_invalid_deadline_never_executes(self):
        for value in (0, -1, float("nan"), float("inf")):
            result = lane.run_lane(self.spec("print('never')", deadline_seconds=value))
            self.assertEqual((result.outcome, result.cleanup), ("environment_failed", "not_started"))


if __name__ == "__main__":
    unittest.main()
