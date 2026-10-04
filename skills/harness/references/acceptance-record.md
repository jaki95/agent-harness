# Acceptance record reference

The acceptance checker captures an owner's project gates before a full independent review starts. It requires Node 22.20+, Git, and the declared tools. It has no third-party dependencies.

## Commands

The existing Markdown command remains a structural check. Acceptance commands use a committed JSON manifest.

```sh
node <Harness-package>/scripts/check-plan.mjs <plan.md>
node <Harness-package>/scripts/check-plan.mjs acceptance declare acceptance.json
node <Harness-package>/scripts/check-plan.mjs acceptance run acceptance.json
node <Harness-package>/scripts/check-plan.mjs acceptance check acceptance.json
```

`declare` validates the manifest and snapshots its actual clean committed head. It does not assert readiness. Declaration precedes implementation or measurement. Git history proves commit ancestry, not when a person first experimented.

`run` executes every declared gate and returns a readiness report. `check` validates the latest run without executing gates. Both resolve the actual current Git head. A report has `ready`, `head`, `problems`, `runId`, and `store` fields.

An exit code of `0` means declaration succeeded or readiness passed. An exit code of `1` means readiness failed. Invalid arguments, unreadable inputs, invalid declarations, and an occupied owner lock exit with code `2`. Errors have no stack trace.

## Manifest

One committed manifest contains every scoped outcome, scenario, gate, and accumulated finding. `repoRoot` explicitly identifies the actual Git repository root. Relative `repoRoot` paths resolve against the manifest's directory. The manifest must be a tracked file within that root. Unknown fields, duplicate JSON keys, duplicate IDs, and dangling references fail validation.

This example declares an owner check and the adjacent identity case.

```json
{
	"version": 1,
	"repoRoot": ".",
	"outcomes": [
		{"id": "identities", "description": "Retain both owner identities", "scenarioIds": ["owner", "adjacent"]}
	],
	"scenarios": [
		{"id": "owner", "setup": "Open an owner's retained item", "pass": "The item retains its owner", "verification": {"gateIds": ["focus"]}},
		{"id": "adjacent", "setup": "Open an adjacent item with a different identity", "pass": "The second item retains its own identity", "verification": {"gateIds": ["edge"]}}
	],
	"gates": [
		{"id": "focus", "argv": ["node", "checks/owner.mjs"], "timeoutMs": 30000, "predicate": {"exitCode": 0}, "artifacts": []},
		{"id": "edge", "argv": ["node", "checks/adjacent.mjs"], "timeoutMs": 30000, "predicate": {"exitCode": 0, "jsonEquals": {"retained": true}}, "artifacts": []}
	],
	"findings": []
}
```

IDs use lowercase letters, digits, and hyphens. Outcomes require a description and at least one `scenarioIds` reference. Every scenario requires concrete `setup` and `pass` prose. Its `verification` contains either a nonempty `gateIds` array or `nonapplicable`.

A nonapplicability reason has at least four words that explain why the scenario needs no executable check. Reasons that claim missing or unavailable tools, unfinished work, or inconclusive results fail validation. Reviewers still judge applicability and scenario completeness.

Every declared gate is required, even when no scenario references it. Gates contain an `argv` command array, `timeoutMs`, `predicate`, and `artifacts`. `cwd` optionally names a directory within the repository. Symlinks resolve to their actual directory. The executable name is nonempty. Remaining arguments preserve their exact strings, including repeated and empty values. Commands use no implicit shell. A project can explicitly name a shell in `argv`.

`timeoutMs` is an integer from `1` through `3600000`. A command timeout, nonzero exit, unavailable tool, output above the runner's 8 MiB capture limit, or missing artifact fails readiness. `predicate.exitCode` must be `0`. Optional `predicate.jsonEquals` compares each named top-level stdout JSON property against a literal value. Objects and arrays compare by value. Extra stdout properties are allowed.

`artifacts` lists file paths relative to `repoRoot` or absolute paths. `{run}` expands to the current receipt directory in command arguments and artifact paths. The runner also exposes `HARNESS_ACCEPTANCE_RUN_DIR` and `HARNESS_ACCEPTANCE_REPO_ROOT` to each command. Gate outputs belong in the receipt directory or project-ignored proof paths. Untracked source files and tracked changes fail readiness.

## Environment and project rules

A gate's optional `environment` contains `probeArgv` and a nonempty `required` JSON object. The probe must exit with code `0` and emit a JSON object. Every required property compares literally. The probe runs before the gate. A contradictory setup prevents the gate from starting.

Measurement gates set `measurement` to `true` and require an environment probe. The runner probes before and after each measurement. Both observations must match. Every command, including each probe, requires the same clean actual head before and after execution.

The optional `projectRules` object has no default rules. A project can provide either or both of these inputs.

```json
{
	"changedFileLimit": {"base": "origin/main", "maximum": 5},
	"canonicalSource": {"gateIds": ["measurement"], "properties": {"source": "https://example.invalid/canonical", "mode": "production"}}
}
```

The changed-file rule resolves `base` to a commit at declaration. Each run computes its merge base with actual HEAD and counts NUL-delimited changed paths. The example's `5` is a project choice. A changed base reference invalidates evidence and requires a fresh declaration and run.

The canonical rule adds required environment properties for its named measurement gates. Those gates need `measurement` and an environment probe. Contradictions between canonical properties and `environment.required` fail declaration. No URL, revision, execution mode, or size limit is universal Harness policy.

Project probes report the measurement source. Harness captures their execution and values. It cannot authenticate that a project probe describes the real system. Independent review must verify consequential source claims.

## Finding history

Each review finding extends the same `findings` array. A finding contains these fields.

| Field | Meaning |
| --- | --- |
| `id` | Stable finding ID. |
| `class` | Shared defect class. |
| `premise` | Current proposed explanation. |
| `focusedScenarioId` | Current executable focused check. |
| `affectedScenarioIds` | Every known affected case, checked at current HEAD. |
| `coverageReason` | Why the affected inventory covers the class. |
| `failedAttempts` | Append-only records with `head`, `premise`, `gateId`, and `reproRunId`. |
| `investigations` | Append-only records with `premise`, `gateId`, `evidenceScenarioIds`, and `conclusion`. |

A `reproRunId` refers to a retained run from this repository and manifest. The failed attempt's head must match that run. The named gate must have executed and failed. Its command identity, declaration binding, stdout, stderr, and captured artifacts are rechecked. A prose claim or missing-tool failure does not establish historical repro evidence.

The next declaration compares the full prior declaration chain. It rejects removed findings, changed defect classes, removed affected cases, rewritten failed attempts, and removed or rewritten investigations. Changing the top-level premise preserves the premises stored in old attempts.

Two distinct failed heads under the same recorded premise and gate require Attack the Premise evidence before readiness can pass. The count spans all findings in the consolidated manifest. Repeated references to one failed head count once. An investigation names that premise and gate, executable evidence scenarios, and a conclusion. All its evidence scenarios and each finding's focused and affected cases require passing current-head gates.

The checker requires the evidence and preserves its history. Reviewers judge whether the defect inventory, investigation, and conclusion are adequate.

## Store and freshness

The default store is under the actual worktree's Git metadata directory. `--store <directory>` selects an explicit external directory. Source-tree stores fail, including ignored directories and symlinks into the source tree. Each store has a namespace derived from the real repository root and manifest path. One owner writes a namespace at a time.

The store contains immutable full declaration snapshots, per-run evidence directories, and pointers to the active declaration and latest run. Declaration snapshot IDs are SHA-256 digests. Receipts and captured evidence have SHA-256 digests. Declared artifact files are copied into the run; current readiness also rechecks their original bytes. Historical repro checks use the retained copies.

Declarations bind a Git ancestor containing the exact manifest bytes. Receipts bind that declaration, manifest digest, actual HEAD, exact commands, captured outputs, artifact paths, and observed environment. A rebase or amend requires a new run. Changed declaration or evidence bytes invalidate readiness.

The runner publishes the latest-run pointer before any commands. A failed or interrupted new run cannot reuse an earlier pass. A complete run publishes its receipt and digest last. Readiness never combines gates from separate runs. An interrupted writer may leave `owner.lock`. Removal requires confirmation that its recorded process has stopped. The checker does not steal a live owner's lock.

The store is owner-controlled evidence, not adversarial attestation. Deleting the whole store loses its history. Preserve the store and use one owner for the acceptance record.

Passing preflight permits a full independent review to start. It never replaces the independent verdict, applicable live proof, or current-head CI required for merge.
