# Orchestration store

Read this contract before using the helper for Orchestrate. It requires Python 3.10+; frontier discovery also requires authenticated `gh` access from an existing repository checkout. Use an authorized store directory on a local filesystem supporting process locks. The store belongs to the coordinator; workers return reports instead of concurrently editing its tables.

Resolve the installed Harness package through the host catalog. Invoke its bundled helper by that package path, with an explicit store path:

```sh
python3 <Harness-package>/scripts/orch.py --store <store-dir> init
```

The playbook abbreviates this command prefix as `orch`. `ORCH_STORE` may supply the store path and `ORCH_REPO` may supply a repository directory. Paths supplied to the helper resolve against the current working directory. `--json` returns complete records and can appear before or after the subcommand. Ordinary output is compact; `status` prints three summary lines. Exit codes are `0` for success, `1` for invalid input or failed operations, and `2` for a missing unit, gate, or exact-head verdict. A missing verdict prints `NOT-VERIFIED`.

## Records

The helper maintains these readable files:

| File | Contract |
| --- | --- |
| `units.tsv` | `id`, `track`, `state`, `branch`, `pr`, `sha`, `brief`; one row per unit. |
| `ledger.tsv` | `pr`, `sha`, `verdict`, `evidence`, `verifier`, `ts`; one current verdict per PR/head pair. |
| `frontier.json` | Repository identity, trunk, generation, ordered scoped PRs with published heads and bases, and lowest unmerged PR. |
| `preferences.md` | Consecutively numbered standing orders. |
| `gates.md` | Open and explicitly resolved human gates, including questions, options, defaults, and answers. |
| `inbox/` | One completion pointer per file: timestamp, agent, unit, status, report path. |
| `inbox-claimed/` | Unacknowledged drained batches, retained for recovery. |
| `checkpoint.json` | Optional versioned queue declaration with authorization, owners, scopes, findings, action receipts, and a snapshot of the existing records. |
| `status.md` | Derived unit, ledger, frontier, and gate tables; regenerate instead of editing. |

`overview.md`, briefs, evidence reports, and the Show Me Your Work trail are maintained by their designated owners. Initialization preserves existing records. TSV cells flatten tabs and newlines and escape leading spreadsheet formulas. Invalid headers, row widths, duplicate keys, verdicts, or frontier data fail visibly.

For interrupted Autopilot or Orchestrate queues, use `orch checkpoint --input <json>`
and read-only `orch pickup`. Read the queue recovery contract (`queue-recovery.md`)
before recording owner metadata or reconciling replacement work.

## Unit and verification commands

```sh
orch unit add <id> --track <track> --brief <path>
orch unit set <id> --state <state> --branch <branch> --pr <number> --sha <sha>
orch unit get <id>
orch unit list --state <state> --track <track>
orch unit counts
orch ledger record <pr> <exact-head-sha> <verdict> --evidence <path> --verifier <name>
orch ledger check <pr> <exact-head-sha>
orch ledger summary
```

Only `--state` is required for `unit set`; omitted fields retain their values. Duplicate `unit add` fails. Ledger verdicts are `live-ui-verified`, `unit-test-verified`, `type-check-only`, `verifier-blocked`, and `verifier-failed`. A changed head has no verdict until recorded. The helper stores receipts; it does not run verification, inspect evidence, or decide whether a result satisfies acceptance. The coordinator records independent verdicts in preference to worker self-reports and checks the current published head before using them.

## Recoverable drains

```sh
orch inbox push <agent> <unit> <status> --report <path>
orch inbox peek --json
orch inbox count
orch inbox drain --json
orch inbox ack <batch-id>
```

`inbox drain --peek` is also read-only. A drain returns `{"batch": "<id>", "pointers": [...]}` and moves the pending inbox into that retained batch. An empty inbox returns a null batch. New arrivals go to a new pending inbox. Until acknowledgement, subsequent drains return the same batch, including after an interrupted command. A missing pending directory after interruption is recreated on the next inbox operation.

Classify each pointer, persist its unit and ledger changes, regenerate status, then acknowledge the batch. Reconcile persisted facts on replay: check a unit before adding it, update its existing row, and check actual PR state before repeating an external action. Acknowledgement is idempotent. Pending arrivals are claimed only after the retained batch is acknowledged. A malformed batch is reported and retained.

## Frontier discovery

```sh
orch frontier set --repo <repository-dir> --prs <bottom-up-pr-list>
orch frontier show --json
```

Declare one same-repository linear chain in bottom-up order. After initialization, omitting `--prs` refreshes the saved scope. The helper queries repository identity and default branch through gh, reads every scoped PR's published head, base, and state twice, and rejects metadata that changes during discovery. Open PRs must form one linear chain rooted at trunk or a declared merged predecessor; cycles, forks, disconnected roots, branching, duplicate heads, or an incorrect order fail. Merged PRs may remain as a historical prefix after GitHub retargets surviving PRs to trunk. A PR closed without merging requires scope reconciliation and does not advance the frontier.

Refreshing from a different repository fails. Failed discovery preserves the last snapshot; that saved snapshot is not fresh evidence. Recompute after merges or topology changes and confirm actual state before acting. For multiple stacks, initialize a separate frontier store for each and record its path in the program overview. Never combine independent stacks by inventing an order.

## Standing orders, gates, and status

```sh
orch standing add <instruction>
orch standing show --json
orch gate park <id> --question <question> --options <options> --default <continuation>
orch gate list --json
orch gate resolve <id> --answer <answer>
orch status
```

A gate's default is recorded, never automatically accepted. Missing authorization requires an actual answer or an existing grant; elapsed time supplies neither. Continue independent authorized work around a parked gate.

Store operations take a nonblocking process lock. A competing writer gets an error and retries only after the holder exits. Process termination releases the lock; the persistent `.orch.lock` file is not evidence of a live writer and must not be deleted to bypass an active lock. Table updates use temporary files and atomic replacement. The lock coordinates one local store, not writers on different machines. Agent replacement still requires a confirmed stop or an isolated writable scope.
