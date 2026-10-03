"""Exercise the plan checker's public CLI with complete and broken plans."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "skills/harness/scripts/check-plan.mjs"
RULE = "Tests alone are not sufficient verification. A PR is verified only when its applicable unit, live, and perf checks have evidence, with a reason for each nonapplicable check."
PLAN = f"""# Recoverable inbox plan

Keep completion reports until their state updates are recorded.
One PR changes the drain and acknowledgement commands.

## How to read this

One box is one unit of work. Every box names the evidence that checks it.
Check a box only when its evidence exists.
The body is a how-to. The program runs `playbooks/autopilot-stack.md` from the installed Harness package.
The operator lands the verified stack.
{RULE}

## Program checklist

### Arm the program

- [ ] Read the installed Harness package and named skills before work and each tick.
- [ ] On explicit go, arm an hourly audit through a supported host wake mechanism.
- [ ] Post a status message only for newly reported changes and record the tick.

### Spawn owners

- [ ] One owner handles the inbox PR on its own branch.

### PR mechanics, for every PR

- [ ] Use gh and open the PR ready. Run repository checks.

### Verdict and merge, for every PR

- [ ] Gate the exact head through Swarm and return findings to the owner.

### Boot recipe, for every live lane

- [ ] Check out the exact head and use separate temporary stores.

## Retain drained reports (PR 1)

**Depends on.** None.

**Files.**

- [ ] Edit `skills/harness/scripts/orch.py`.

**Build.**

- [ ] Retain a claimed inbox batch until acknowledgement.

**You see.**

- [ ] Repeated drain returns the same unacknowledged batch ID.

**Verify, unit.** {RULE}

- [ ] Add the interrupted-drain case. Run `python3 -m unittest discover -s scripts/tests`.

**Verify, live.** {RULE} 2 lanes on `inherit-parent` at the PR head. Cover replay and later arrivals.

- [ ] Lane 1. Regression lane against trunk. Run the drain command on trunk and head and record the changed persistence contract. Save `drain-comparison.txt`. Pass when the accepted contract holds on head and the trunk difference is recorded.
- [ ] Lane 2. Push a later arrival before acknowledging the first batch. Save `later-arrival.txt`. Pass when the second pointer remains pending.

**Verify, perf.** {RULE}

- [ ] Metric. Median completion-record latency at trunk and head.
- [ ] Probe. Alternate ten identical batches on each side.
- [ ] Baseline. Record the trunk median before the head change.
- [ ] Rule. Head median must be within 10 percent of the trunk median.

**Review gate.** None. PR 1 is not review-gated.

**Merge.**

- [ ] Parent records a clean exact-head verdict and hands the stack to the operator.

## Close the program

- [ ] Every applicable check has evidence and every nonapplicable check has a reason.

## Appendix A. Prototype evidence

A temporary store confirmed that replay preserves the batch ID.

## Appendix B. Alternatives rejected

Deleting pointers before state updates can lose completion reports.

## Appendix C. Risks

Replay must reconcile existing state without repeating external actions.

## Appendix D. Links and reading list

Read Orchestrate, Swarm, and Show Me Your Work through the installed catalog.
"""


@unittest.skipUnless(shutil.which("node"), "Node is required for the bundled plan checker")
class PlanCheckerTests(unittest.TestCase):
    def check(self, plan, code):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan with spaces.md"
            path.write_text(plan)
            result = subprocess.run(["node", str(SCRIPT), str(path)], capture_output=True, text=True,
                                    cwd=directory, timeout=10)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def nonapplicable(self, plan, block, next_block, reason):
        start = plan.index(f"**{block}**")
        end = plan.index(f"**{next_block}**", start)
        return plan[:start] + f"**{block}** {RULE} N/A. {reason}\n\n" + plan[end:]

    def test_accepts_scenario_driven_lanes_and_nonvisual_artifacts(self):
        result = self.check(PLAN, 0)
        self.assertIn("1 PR sections, 0 problems", result.stdout)

    def test_accepts_each_explicit_nonapplicable_block_with_reason(self):
        for block, following in (("Verify, unit.", "Verify, live."),
                                 ("Verify, live.", "Verify, perf."),
                                 ("Verify, perf.", "Review gate.")):
            with self.subTest(block=block):
                plan = self.nonapplicable(PLAN, block, following,
                                         "This documentation-only change has no executable surface for this check.")
                self.check(plan, 0)

    def test_rejects_empty_generic_or_placeholder_nonapplicability(self):
        for reason in ("", "Not applicable.", "<concrete reason>"):
            with self.subTest(reason=reason):
                plan = self.nonapplicable(PLAN, "Verify, perf.", "Review gate.", reason)
                self.assertIn("concrete N/A reason", self.check(plan, 1).stderr)

    def test_nonapplicable_block_cannot_hide_unfinished_boxes(self):
        plan = PLAN.replace(f"**Verify, perf.** {RULE}", f"**Verify, perf.** {RULE} N/A. This change has no performance impact.")
        self.assertIn("says N/A but has boxes", self.check(plan, 1).stderr)

    def test_rejects_wrong_count_duplicate_missing_and_reordered_lanes(self):
        invalid = [PLAN.replace("2 lanes on", "3 lanes on"),
                   PLAN.replace("Lane 2.", "Lane 1."),
                   PLAN.replace("Lane 2.", "Lane 3."),
                   PLAN.replace("Lane 1.", "Lane 3.").replace("Lane 2.", "Lane 1.")]
        for plan in invalid:
            with self.subTest(plan=plan):
                self.assertIn("expected 1 to", self.check(plan, 1).stderr)

    def test_rejects_missing_regression_evidence_and_pass_predicate(self):
        cases = [("Regression lane against trunk", "Compare historical output", "no regression lane"),
                 ("Save `later-arrival.txt`.", "Keep a note.", "no evidence artifact"),
                 ("Pass when the second pointer remains pending.", "Looks good.", "no pass predicate")]
        for old, new, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.check(PLAN.replace(old, new), 1).stderr)

    def test_rejects_missing_perf_baseline_and_subblock_order(self):
        self.assertIn("perf boxes", self.check(PLAN.replace("- [ ] Baseline.", "- [ ] Estimate."), 1).stderr)
        self.assertIn("sub-blocks", self.check(PLAN.replace("**Depends on.** None.\n", ""), 1).stderr)

    def test_review_gate_requires_operator_screenshots_and_video(self):
        plan = PLAN.replace("**Review gate.** None. PR 1 is not review-gated.", "**Review gate.** The operator reviews before merge.\n\n- [ ] Show screenshots to the operator.")
        self.assertIn('lacks "video"', self.check(plan, 1).stderr)

    def test_command_line_reports_missing_file_and_usage(self):
        result = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage", result.stderr)
        result = subprocess.run(["node", str(SCRIPT), "/nonexistent/harness-plan.md"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("harness-plan.md", result.stderr)


if __name__ == "__main__":
    unittest.main()
