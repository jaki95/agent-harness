import copy
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "skills/harness/scripts/check-plan.mjs"
NODE = shutil.which("node")


@unittest.skipUnless(NODE and shutil.which("git"), "Node and Git are required")
class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Acceptance fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.manifest = {
            "version": 1,
            "repoRoot": ".",
            "outcomes": [{"id": "ownership", "description": "Preserve both owner identities",
                          "scenarioIds": ["owner", "adjacent"]}],
            "scenarios": [self.scenario("owner", "focus"), self.scenario("adjacent", "edge")],
            "gates": [self.gate("focus", "pass"), self.gate("edge", "pass")],
            "findings": [],
        }
        (self.root / "probe.mjs").write_text("""import fs from 'node:fs';
const mode = process.argv[2];
if (mode === 'fail') { console.error('adjacent identity was lost'); process.exit(1); }
if (mode === 'dirty') fs.writeFileSync('tracked.txt', 'changed');
if (mode === 'restore') fs.writeFileSync('tracked.txt', 'original');
if (mode === 'environment') console.log(fs.readFileSync('source.json', 'utf8'));
else if (mode === 'mutate-environment') {
  fs.writeFileSync('proof/source.json', JSON.stringify({source: 'preview'}));
  console.log(JSON.stringify({ok: true}));
} else if (mode === 'proof-environment') console.log(fs.readFileSync('proof/source.json', 'utf8'));
else if (mode === 'wait') setTimeout(() => console.log('{"ok":true}'), 3000);
else console.log(JSON.stringify({ok: true}));
""")
        (self.root / "tracked.txt").write_text("original")
        (self.root / ".gitignore").write_text("proof/\n")
        (self.root / "source.json").write_text('{"source":"canonical"}')
        self.save()
        self.commit("Declare owner outcomes")
        self.transcript = []

    @staticmethod
    def scenario(name, gate):
        return {"id": name, "setup": f"Open {name} identity beside its owner",
                "pass": "Both identities retain their own state", "verification": {"gateIds": [gate]}}

    @staticmethod
    def gate(name, mode):
        return {"id": name, "argv": [NODE, "probe.mjs", mode], "timeoutMs": 5000,
                "predicate": {"exitCode": 0, "jsonEquals": {"ok": True}}, "artifacts": []}

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def save(self):
        (self.root / "acceptance.json").write_text(json.dumps(self.manifest, indent=2) + "\n")

    def commit(self, message="Update fixture"):
        self.git("add", ".")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def cli(self, action, code=0, *extra):
        result = subprocess.run([NODE, str(SCRIPT), "acceptance", action,
                                 str(self.root / "acceptance.json"), *extra],
                                capture_output=True, text=True)
        self.transcript.append(f"$ node check-plan.mjs acceptance {action} acceptance.json\n"
                               f"{result.stdout}{result.stderr}exit {result.returncode}\n")
        self.assertEqual(code, result.returncode, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def declare(self):
        return self.cli("declare")

    def ready(self):
        self.declare()
        report = self.cli("run")
        self.assertTrue(report["ready"])
        self.assertEqual(self.git("rev-parse", "HEAD"), report["head"])
        return report

    def test_owner_workflow_red_red_green_before_review(self):
        adjacent = self.manifest["scenarios"].pop()
        self.save()
        self.commit()
        self.assertIn("adjacent", self.cli("declare", 2))
        self.manifest["scenarios"].append(adjacent)
        self.manifest["gates"][1]["measurement"] = True
        self.manifest["gates"][1]["environment"] = {
            "probeArgv": [NODE, "probe.mjs", "environment"], "required": {"source": "canonical"}}
        self.manifest["projectRules"] = {"canonicalSource": {
            "gateIds": ["edge"], "properties": {"source": "canonical"}}}
        (self.root / "source.json").write_text('{"source":"preview"}')
        self.save()
        self.commit()
        self.declare()
        self.assertIn("environment", " ".join(self.cli("run", 1)["problems"]))
        (self.root / "source.json").write_text('{"source":"canonical"}')
        self.commit("Correct canonical measurement setup")
        report = self.cli("run")
        self.assertTrue(report["ready"])
        self.assertTrue(self.cli("check")["ready"])
        self.transcript.append("Full independent review may now start. Its verdict remains required.\n")
        target = os.environ.get("HARNESS_ACCEPTANCE_TRANSCRIPT")
        if target:
            Path(target).write_text("\n".join(self.transcript))

    def test_absent_receipt_and_stale_actual_head(self):
        self.declare()
        self.assertIn("run", " ".join(self.cli("check", 1)["problems"]))
        self.cli("run")
        (self.root / "tracked.txt").write_text("next head")
        self.commit()
        self.assertIn("HEAD", " ".join(self.cli("check", 1)["problems"]))
        self.cli("run")

    def test_failed_and_unavailable_gates_invalidate_prior_pass(self):
        self.ready()
        for mode in ("fail", "unavailable"):
            with self.subTest(mode=mode):
                self.manifest["gates"][1]["argv"] = ([NODE, "probe.mjs", "fail"] if mode == "fail"
                                                    else ["missing-acceptance-tool"])
                self.save()
                self.commit()
                self.declare()
                report = self.cli("run", 1)
                self.assertFalse(report["ready"])
                self.assertFalse(self.cli("check", 1)["ready"])

    def test_dirty_command_cannot_be_repaired_by_later_command(self):
        self.manifest["gates"][0]["argv"][2] = "dirty"
        self.manifest["gates"][1]["argv"][2] = "restore"
        self.save()
        self.commit()
        self.declare()
        self.assertIn("dirty", " ".join(self.cli("run", 1)["problems"]))

    def test_changed_evidence_and_changed_declaration(self):
        report = self.ready()
        receipt = Path(report["store"]) / "runs" / report["runId"] / "receipt.json"
        data = json.loads(receipt.read_text())
        Path(data["gates"][0]["stdout"]["path"]).write_text('{"ok":false}')
        self.assertIn("hash", " ".join(self.cli("check", 1)["problems"]))
        self.cli("run")
        declaration = Path(report["store"]) / "declarations" / (data["declarationId"] + ".json")
        declaration.write_text(declaration.read_text() + " ")
        self.assertIn("hash", " ".join(self.cli("check", 1)["problems"]))

    def test_changed_file_limit_and_base_drift(self):
        base = self.git("rev-parse", "HEAD")
        self.git("branch", "rule-base", base)
        self.manifest["projectRules"] = {"changedFileLimit": {"base": "rule-base", "maximum": 1}}
        self.save()
        self.commit()
        self.ready()
        (self.root / "second\npath.txt").write_text("another path")
        self.commit()
        self.assertIn("changed-file", " ".join(self.cli("run", 1)["problems"]))
        self.git("branch", "-f", "rule-base", "HEAD")
        self.assertIn("base", " ".join(self.cli("check", 1)["problems"]))

    def test_measurement_environment_rechecked_after_gate(self):
        proof = self.root / "proof"
        proof.mkdir()
        (proof / "source.json").write_text('{"source":"canonical"}')
        gate = self.manifest["gates"][1]
        gate["argv"][2] = "mutate-environment"
        gate["measurement"] = True
        gate["environment"] = {"probeArgv": [NODE, "probe.mjs", "proof-environment"],
                               "required": {"source": "canonical"}}
        self.save()
        self.commit()
        self.declare()
        self.assertIn("environment", " ".join(self.cli("run", 1)["problems"]))

    def test_history_survives_premise_change_and_requires_investigation(self):
        gate = self.manifest["gates"][0]
        gate["argv"][2] = "fail"
        self.save()
        head = self.commit()
        self.declare()
        first = self.cli("run", 1)
        finding = {"id": "lost-owner", "class": "owner identity", "premise": "One shared key is safe",
                   "focusedScenarioId": "owner", "affectedScenarioIds": ["adjacent"],
                   "coverageReason": "Both owner and neighboring identity use the shared key",
                   "failedAttempts": [{"head": head, "premise": "One shared key is safe",
                                       "gateId": "focus", "reproRunId": first["runId"]}],
                   "investigations": []}
        self.manifest["findings"].append(finding)
        self.save()
        second_head = self.commit()
        self.declare()
        second = self.cli("run", 1)
        finding["failedAttempts"].append({"head": second_head, "premise": "One shared key is safe",
                                          "gateId": "focus", "reproRunId": second["runId"]})
        finding["premise"] = "Separate keys are needed"
        gate["argv"][2] = "pass"
        self.save()
        self.commit()
        self.declare()
        self.assertIn("Attack the Premise", " ".join(self.cli("run", 1)["problems"]))
        preserved = copy.deepcopy(finding)
        for change in ("finding", "attempt"):
            with self.subTest(change=change):
                self.manifest["findings"] = [] if change == "finding" else [copy.deepcopy(preserved)]
                if change == "attempt":
                    self.manifest["findings"][0]["failedAttempts"].pop(0)
                self.save()
                self.commit()
                self.assertIn("history", self.cli("declare", 2))
        self.manifest["findings"] = [preserved]
        preserved["investigations"].append({"premise": "One shared key is safe", "gateId": "focus",
                                            "evidenceScenarioIds": ["owner", "adjacent"],
                                            "conclusion": "Two separate keys retain both identities"})
        self.save()
        self.commit()
        self.declare()
        self.assertTrue(self.cli("run")["ready"])
        Path(first["store"], "runs", first["runId"], "focus", "command-stdout.txt").unlink()
        self.assertIn("evidence", " ".join(self.cli("check", 1)["problems"]))

    def test_timeout_and_partial_run_do_not_reuse_pass(self):
        report = self.ready()
        gate = self.manifest["gates"][1]
        gate["argv"][2] = "wait"
        gate["timeoutMs"] = 20
        self.save()
        self.commit()
        self.declare()
        failed = self.cli("run", 1)
        self.assertIn("command", " ".join(failed["problems"]))
        Path(failed["store"], "runs", failed["runId"], "receipt.json").unlink()
        self.assertIn("run", " ".join(self.cli("check", 1)["problems"]))

    def test_explicit_store_is_isolated_and_source_store_rejected(self):
        store = Path(self.temp.name) / "receipts"
        declared = self.cli("declare", 0, "--store", str(store))
        self.assertTrue(self.cli("run", 0, "--store", str(store))["ready"])
        self.assertEqual("", self.git("status", "--porcelain"))
        self.assertTrue(Path(declared["store"]).is_relative_to(store))
        self.assertIn("outside", self.cli("declare", 2, "--store", str(self.root / "proof")))

    def test_duplicate_json_keys_and_malformed_input_are_rejected(self):
        for content in ('{"version":1,"version":1}', '{"version":'):
            with self.subTest(content=content):
                (self.root / "acceptance.json").write_text(content)
                result = self.cli("declare", 2)
                self.assertNotIn("Traceback", result)
                self.assertNotIn("at acceptanceCLI", result)
        self.assertIn("duplicate JSON key", self.transcript[0])

    def test_nonapplicability_never_excuses_unavailable_checks(self):
        for reason in ("The required browser tool is unavailable here",
                       "This verification remains unfinished until later",
                       "The check result is inconclusive on this host"):
            with self.subTest(reason=reason):
                self.manifest["scenarios"][1]["verification"] = {"nonapplicable": reason}
                self.save()
                self.commit()
                self.assertIn("nonapplicability", self.cli("declare", 2))
        self.manifest["scenarios"][1]["verification"] = {
            "nonapplicable": "This change only edits documentation and adds no executable behavior"}
        self.save()
        self.commit()
        self.assertTrue(self.ready()["ready"])

    def test_repeated_arguments_and_gate_names_do_not_collide(self):
        gate = self.manifest["gates"][0]
        gate["argv"] = [NODE, "probe.mjs", "pass", "pass"]
        gate["measurement"] = True
        gate["environment"] = {"probeArgv": [NODE, "probe.mjs", "environment", "environment"],
                               "required": {"source": "canonical"}}
        adjacent = self.manifest["gates"][1]
        adjacent["id"] = "focus-before"
        self.manifest["scenarios"][1]["verification"]["gateIds"] = ["focus-before"]
        self.save()
        self.commit()
        report = self.ready()
        self.assertTrue(self.cli("check")["ready"])
        run = Path(report["store"], "runs", report["runId"])
        self.assertEqual('{"source":"canonical"}\n', (run / "focus/before-stdout.txt").read_text())
        self.assertEqual('{"ok":true}\n', (run / "focus-before/command-stdout.txt").read_text())

    def test_empty_command_and_probe_arguments_are_preserved(self):
        gate = self.manifest["gates"][0]
        gate["argv"] = [NODE, "-e", "console.log(JSON.stringify({ok: process.argv[1] === ''}))", ""]
        gate["measurement"] = True
        gate["environment"] = {
            "probeArgv": [NODE, "-e", "console.log(JSON.stringify({source: process.argv[1] === '' ? 'canonical' : 'wrong'}))", ""],
            "required": {"source": "canonical"}}
        self.save()
        self.commit()
        self.assertTrue(self.ready()["ready"])
        self.assertTrue(self.cli("check")["ready"])

    def test_artifact_bytes_and_command_predicate_are_checked(self):
        gate = self.manifest["gates"][0]
        gate["argv"] = [NODE, "-e", "require('fs').writeFileSync(process.argv[1], 'proof'); console.log('{\"ok\":true}')", "{run}/proof.txt"]
        gate["artifacts"] = ["{run}/proof.txt"]
        self.save()
        self.commit()
        report = self.ready()
        Path(report["store"], "runs", report["runId"], "proof.txt").write_text("changed proof")
        self.assertIn("artifact hash", " ".join(self.cli("check", 1)["problems"]))
        gate["predicate"]["jsonEquals"]["ok"] = False
        self.save()
        self.commit()
        self.declare()
        self.assertIn("predicate", " ".join(self.cli("run", 1)["problems"]))

    def test_wrong_environment_skips_measurement(self):
        proof = self.root / "proof"
        proof.mkdir()
        gate = self.manifest["gates"][1]
        gate["argv"] = [NODE, "-e", "require('fs').writeFileSync('proof/measurement-started', 'yes')"]
        gate["measurement"] = True
        gate["environment"] = {"probeArgv": [NODE, "probe.mjs", "environment"],
                               "required": {"source": "canonical"}}
        (self.root / "source.json").write_text('{"source":"preview"}')
        self.save()
        self.commit()
        self.declare()
        self.assertIn("skipped", " ".join(self.cli("run", 1)["problems"]))
        self.assertFalse((proof / "measurement-started").exists())

    def test_canonical_requirement_cannot_override_declared_environment(self):
        gate = self.manifest["gates"][1]
        gate["measurement"] = True
        gate["environment"] = {"probeArgv": [NODE, "probe.mjs", "environment"],
                               "required": {"source": "preview"}}
        self.manifest["projectRules"] = {"canonicalSource": {
            "gateIds": ["edge"], "properties": {"source": "canonical"}}}
        self.save()
        self.commit()
        self.assertIn("contradicts", self.cli("declare", 2))

    def test_valid_symlink_working_directory(self):
        actual = self.root / "actual"
        actual.mkdir()
        (self.root / "linked").symlink_to("actual", target_is_directory=True)
        gate = self.manifest["gates"][0]
        gate["cwd"] = "linked"
        gate["argv"][1] = "../probe.mjs"
        (actual / "retained.txt").write_text("fixture")
        self.save()
        self.commit()
        self.assertTrue(self.ready()["ready"])

    def test_interrupt_never_reuses_successful_run(self):
        report = self.ready()
        gate = self.manifest["gates"][1]
        gate["argv"] = [NODE, "-e", "require('fs').writeFileSync('proof/started', 'yes'); setTimeout(() => {}, 3000)"]
        (self.root / "proof").mkdir()
        self.save()
        self.commit()
        self.declare()
        process = subprocess.Popen([NODE, str(SCRIPT), "acceptance", "run",
                                    str(self.root / "acceptance.json")],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while not (self.root / "proof/started").exists() and process.poll() is None:
                self.assertLess(time.monotonic(), deadline, "gate did not start")
                time.sleep(0.01)
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=5)
            self.assertNotEqual(0, process.returncode)
            self.assertFalse(self.cli("check", 1)["ready"])
            current = json.loads(Path(report["store"], "run.json").read_text())
            self.assertNotEqual(report["runId"], current["id"])
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_shared_premise_failures_accumulate_across_findings(self):
        self.manifest["gates"][0]["argv"][2] = "fail"
        self.save()
        first_head = self.commit()
        self.declare()
        first = self.cli("run", 1)
        (self.root / "tracked.txt").write_text("second attempted fix")
        second_head = self.commit()
        second = self.cli("run", 1)
        attempts = [(first_head, first["runId"]), (second_head, second["runId"])]
        for index, (head, run_id) in enumerate(attempts):
            self.manifest["findings"].append({
                "id": f"identity-{index}", "class": "owner identity", "premise": "A different new premise",
                "focusedScenarioId": "owner", "affectedScenarioIds": ["adjacent"],
                "coverageReason": "Both classes of ownership share the same key",
                "failedAttempts": [{"head": head, "premise": "Shared key is safe",
                                    "gateId": "focus", "reproRunId": run_id}], "investigations": []})
        self.manifest["gates"][0]["argv"][2] = "pass"
        self.save()
        self.commit()
        self.declare()
        self.assertIn("Attack the Premise", " ".join(self.cli("run", 1)["problems"]))
        self.manifest["findings"][0]["investigations"].append({
            "premise": "Shared key is safe", "gateId": "focus", "evidenceScenarioIds": ["owner", "adjacent"],
            "conclusion": "Separate identities need separate keys throughout"})
        self.save()
        self.commit()
        self.declare()
        self.assertTrue(self.cli("run")["ready"])

    def test_historical_repro_survives_removed_working_directory(self):
        old = self.root / "old-checks"
        old.mkdir()
        (old / "retain.txt").write_text("fixture")
        gate = self.manifest["gates"][0]
        gate["cwd"] = "old-checks"
        gate["argv"] = [NODE, "../probe.mjs", "fail"]
        self.save()
        failed_head = self.commit()
        self.declare()
        failed = self.cli("run", 1)
        (old / "retain.txt").unlink()
        old.rmdir()
        gate.pop("cwd")
        gate["argv"] = [NODE, "probe.mjs", "pass"]
        self.manifest["findings"] = [{
            "id": "owner-fix", "class": "owner identity", "premise": "Use separate identities",
            "focusedScenarioId": "owner", "affectedScenarioIds": ["adjacent"],
            "coverageReason": "Both owner and adjacent identities need independent state",
            "failedAttempts": [{"head": failed_head, "premise": "One shared identity is enough",
                                "gateId": "focus", "reproRunId": failed["runId"]}], "investigations": []}]
        self.save()
        self.commit()
        self.declare()
        self.assertTrue(self.cli("run")["ready"])
        self.assertTrue(self.cli("check")["ready"])


if __name__ == "__main__":
    unittest.main()
