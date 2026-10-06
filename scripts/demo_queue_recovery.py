"""Run queue recovery through disposable real CLI fixtures and save a transcript."""

import argparse
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("queue_demo_fixture", args.repo / "scripts/tests/test_recovery.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixture = module.RecoveryTests()
    fixture.setUp()
    cases = []

    def observe(label, arguments, classification, replacement_allowed):
        result = fixture.call("pickup", *arguments)
        unit = result["units"][0]
        assert unit["owner_classification"] == classification
        assert unit["same_scope_replacement_allowed"] is replacement_allowed
        cases.append({"scenario": label, "command": ["orch", "pickup", *arguments, "--json"],
                      "report": unit, "host_error": result["host_error"]})
        return unit

    try:
        observe("confirmed-stopped-writer", ["--host-state", fixture.host_state()], "terminal", True)
        observe("pending-init-is-unknown", ["--host-state", fixture.host_state("pending-init", True)], "unknown", False)
        observe("stale-host-is-unknown", ["--host-state", fixture.host_state(age=601)], "unknown", False)
        observe("missing-host-is-unknown", [], "unknown", False)
        fixture.call("ledger", "record", "10", "a" * 40, "unit-test-verified", "--evidence", "reports/old.md")
        fixture.save_checkpoint()
        fixture.forge["10"]["headRefOid"] = "b" * 40
        fixture.forge_file.write_text(json.dumps(fixture.forge))
        changed = observe("changed-head-invalidates-verdict", ["--host-state", fixture.host_state()], "terminal", True)
        assert changed["head_changed"]
        assert changed["verification"] == "NOT-VERIFIED"
        assert changed["replacement_packet"]["evidence_status"] == "stale"
        fixture.test_fresh_bounded_explicit_host_adapter_and_invalid_output()
        fixture.test_crash_inside_completion_drain_before_reply_preserves_missing_inbox()
        state = fixture.host_state()
        before = fixture.inventory()
        recovered = fixture.call("pickup", "--host-state", state)
        replay = fixture.call("pickup", "--host-state", state)
        assert before == fixture.inventory()
        assert recovered == replay
        assert not (fixture.store / "inbox").exists()
        cases.append({"scenario": "crash-after-claim-before-reply",
                      "command": ["orch", "pickup", "--host-state", state, "--json"],
                      "report": recovered["units"][0], "store_unchanged": True,
                      "repeated_pickup_identical": True, "missing_inbox_not_recreated": True})
        transcript = {"schema_version": 1, "scenarios": cases,
                      "forge_calls": [json.loads(line) for line in fixture.forge_log.read_text().splitlines()],
                      "host_adapter_request": json.loads((fixture.root / "host-request.json").read_text())}
        args.output.write_text(json.dumps(transcript, indent=2) + "\n")
        print(json.dumps({"artifact": str(args.output.resolve()), "scenarios": len(cases),
                          "verified": ["real-gh-fixture", "real-host-argv-adapter", "crash-before-drain-response",
                                       "retained-report", "read-only-repeated-pickup", "stopped-owner",
                                       "pending-init", "stale-host", "missing-host", "changed-published-head"]}))
    finally:
        fixture.doCleanups()


if __name__ == "__main__":
    main()
