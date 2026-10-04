# Check owner readiness before full review

Run the disposable owner workflow from the repository root. It uses temporary Git projects and never installs skills.

```sh
python3 -m unittest scripts.tests.test_acceptance.AcceptanceTests.test_owner_workflow_red_red_green_before_review
python3 -m unittest scripts.tests.test_acceptance
```

Set `TMPDIR` to an existing task-owned temporary directory when the host's default temporary storage is constrained. Set `HARNESS_ACCEPTANCE_TRANSCRIPT` to an external file path to retain the owner workflow's actual CLI transcript.

1. Declare an outcome with its adjacent identity scenario omitted. Declaration must exit with code `2` and name the missing scenario.
2. Add that scenario and declare the committed manifest. Run with a probe reporting a preview source against a canonical requirement. Readiness must exit with code `1` and name the environment contradiction.
3. Correct the measurement setup and commit it. Run and recheck at actual HEAD. Both must exit with code `0` and report `ready` as `true`.
4. Start full independent review only after that owner loop passes. Its verdict, live proof, and current-head CI remain separate merge requirements.

The broader suite exercises configurable changed-file limits, canonical requirement contradictions, missing and failed tools, stale heads, changed evidence, per-command dirty mutations, incomplete and interrupted runs, full finding history, and shared repeated-premise investigation. It also covers duplicate JSON keys, justified applicability, empty and repeated command arguments, evidence-name collisions, artifact bytes, literal predicates, symlink working directories, and invalid setup that prevents measurement execution.

For a review-fix evaluation, retain a failing run, append its actual head and repro run ID to one finding, and declare again. Record a second failed fix under the same premise and gate. A changed current premise must not avoid Attack the Premise. Removed history must fail declaration. Append an investigation and preserve passing current-head focused and affected-case gates before the next full review round.

The checker cannot discover undeclared cases or authenticate a misleading project probe. Independent reviewers must inspect those claims.
