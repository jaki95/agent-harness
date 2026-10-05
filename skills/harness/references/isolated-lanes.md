# Run an isolated verification lane

Use the bundled `scripts/run_lane.py` launcher when a project command needs private environment state, a local deadline, and a process-cleanup receipt. The first supported backend requires Linux, readable process inventory, Python 3.10 or later, and Git. Other platforms return `unsupported` before project execution.

## Launch a project command

Start from a clean checkout. Create a caller-owned temporary root outside the source tree or under a project-ignored directory. Pass the full expected commit ID.

```sh
mkdir -p local/verification-runs
python3 <Harness-package>/scripts/run_lane.py \
  --checkout "$PWD" --head "$(git rev-parse HEAD)" \
  --temp-root "$PWD/local/verification-runs" --deadline 60 \
  -- python -m unittest discover -s tests
```

Replace `<Harness-package>` with the installed Harness directory. The project supplies its command. The launcher uses argv directly, without an implicit shell. Commands named `python`, `python3`, or a versioned Python name resolve through the private environment. Matching interpreter names outside that environment are rejected. Renamed interpreters and wrappers must honor the supplied environment and cache paths.

Each invocation creates a unique private directory containing a Python venv without pip, home, temporary files, caches, output files, hooks, and a receipt. It clears inherited environment configuration. The child receives private `HOME`, `TMPDIR`, `XDG_CACHE_HOME`, Python bytecode and pip-cache paths. Its `PATH` starts with the private venv and then the platform default tool path. Python packages installed by the command belong in that venv. Project dependencies remain project-owned inputs.

Use `--env <file.json>` for an explicit JSON mapping of additional environment variables. Private directory variables and interpreter, loader, Git, and cache overrides are reserved. The launcher does not copy those supplied values into receipts. Use `--secret-env KEY` to pass a selected credential from the caller's environment. This option can repeat. Known credential values are rejected in command arguments and excluded from hook evidence and receipts. Command arguments and input paths must be public. Arbitrary hidden credentials cannot be identified reliably.

The selected checkout must be the actual Git root at the expected head. Source checks reject tracked changes and untracked source files before and after execution. Put generated files in the lane directory or project-ignored paths. The launcher preserves existing files in the caller's temporary root and retains its own run directories for inspection.

## Read the result

The CLI prints a JSON result with an outcome, cleanup state, command return code, and receipt path. A fixed reason code identifies failures, including a temporary-root failure that prevents receipt creation. Exit zero requires `passed` and `complete` cleanup. Any other run result exits nonzero. Invalid CLI or environment input exits with code 2.

The receipt records the resolved public command, expected and observed source head, private directory paths, configured deadline, setup and execution durations, command return code, and cleanup evidence. `commands` records each owned validation, setup, and execution process group. Signal attempts, residual zombies, and observed escaped children remain visible. Outcomes distinguish `command_failed`, `environment_failed`, `timed_out`, `cancelled`, and `unsupported`. Cleanup independently reports `complete`, `incomplete`, or `not_started`.

`--receipt <path>` exports the receipt to a caller-selected artifact location. The parent directory must already exist. Existing files and symlinks are rejected. The run directory retains the authoritative receipt. A failed export prevents a passing result. No shared latest-run file is updated.

Raw command output remains in private `.stdout` and `.stderr` files. These files can contain credentials printed by project commands. Restrict access to the temporary root and remove retained run directories through the project's scoped cleanup policy. The launcher does not delete caller files or impose a storage quota.

## Add child evidence

A project driver can append JSON lines to the path in `HARNESS_LANE_HOOKS`. Two event shapes are accepted.

```python
import json
import os
from pathlib import Path
import time
import your_project

started = time.monotonic()
with Path(os.environ["HARNESS_LANE_HOOKS"]).open("a") as hooks:
    hooks.write(json.dumps({"kind": "import", "module": "your_project",
                           "file": str(Path(your_project.__file__).resolve())}) + "\n")
    hooks.write(json.dumps({"kind": "ready", "id": "driver-ready",
                           "elapsed_seconds": time.monotonic() - started}) + "\n")
```

Import records require a module name and an existing absolute resolved file path. Readiness records require an identifier and a finite nonnegative elapsed time within execution. Unknown fields, malformed records, known secrets, and oversized hook input are excluded and counted in `rejected_hooks`. Hooks record child observations. Independent review still checks whether the import and readiness evidence describes the real driver.

## Integrate an acceptance gate

Commit a project wrapper such as `scripts/verify-lane.sh`. This example uses a project-local Codex skill installation. Adapt the installed package path and project command to the target host.

```sh
#!/bin/sh
set -eu
exec python3 .agents/skills/harness/scripts/run_lane.py \
  --checkout "$HARNESS_ACCEPTANCE_REPO_ROOT" \
  --head "$(git rev-parse HEAD)" \
  --temp-root "$HARNESS_ACCEPTANCE_RUN_DIR" \
  --deadline 10 \
  --receipt "$HARNESS_ACCEPTANCE_RUN_DIR/lifecycle.json" \
  -- python -m unittest discover -s tests
```

Declare the wrapper and its exported receipt using the existing acceptance manifest format.

```json
{
  "id": "isolated-project-check",
  "argv": ["sh", "scripts/verify-lane.sh"],
  "timeoutMs": 30000,
  "predicate": {"exitCode": 0},
  "artifacts": ["{run}/lifecycle.json"]
}
```

Give each gate a distinct receipt filename. The acceptance driver's outer timeout must allow launcher startup, the local deadline, cleanup allowances, and receipt export. An outer hard kill can prevent the launcher from cleaning up or writing its receipt. Acceptance still requires its own current-head readiness evidence and an independent review verdict.

## Understand the deadline and ownership limits

A monotonic deadline covers local validation subprocesses, venv setup, and project execution. Cleanup gets a separately recorded bounded allowance after that deadline. Each external command starts its own session and process group. The launcher observes its direct child without reaping it until group signals finish. It sends `SIGTERM`, escalates to `SIGKILL` when necessary, and checks for surviving live group members before reporting complete cleanup.

The guarantee covers cooperative commands in the owned process group. Observed children that leave the group make cleanup incomplete. A child that creates another session can escape observation. Complete group cleanup does not prove containment of every possible descendant. Residual zombies are recorded separately because they are no longer executing and the launcher cannot reap children owned by another process.

Private environments prevent accidental sharing of package and cache writes. They are not a filesystem sandbox. A command can deliberately access another lane or modify the checkout. Use stronger host isolation when that behavior must be prevented.

A local subprocess deadline cannot bound a host approval queue, tool transport, blocked kernel filesystem operations, or a host crash. `SIGKILL` of the launcher prevents its cleanup handler and final receipt. Missing cleanup access or unreliable inventory produces an incomplete result rather than proof of cleanup.
