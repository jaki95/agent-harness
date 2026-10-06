# Recover an interrupted queue

Use the installed Harness `scripts/orch.py` with an explicit project-local
`--store` directory. The helper requires Python 3.10+.
Forge reads require authenticated `gh` and the scoped repository checkout.
The coordinator owns the store. Workers return reports.

## Save a checkpoint

Initialize the existing store and record its units through the commands in
the orchestration store reference (`orchestration-store.md`). Then save all
current owner metadata through one command:

```sh
orch checkpoint --input <checkpoint-input.json>
```

The input is a complete declaration of the current program. Use this shape:

```json
{
  "schema_version": 1,
  "program": "Disposable queue",
  "repository": {"name": "fixture/repo", "path": "<repository-dir>"},
  "authorization": "Implement the declared units. Hold merges for the operator.",
  "units": [
    {
      "id": "u1",
      "owner_id": "owner-1",
      "work_scope": ["<owner-worktree>"],
      "brief": "Complete the current unit. Preserve its confirmed results.",
      "findings": ["Resolve the outstanding review finding in the report."],
      "evidence": ["reports/u1.md"],
      "next_actions": [
        {"id": "verify-u1", "kind": "local", "status": "planned", "receipt": null}
      ]
    }
  ]
}
```

Declare every current unit exactly once. Use stable owner and action identifiers.
`brief` contains the consolidated current instructions, including later changes.
`findings` retains every unresolved finding. `evidence` contains report pointers.
To close a finding, include its exact identifier in optional `resolved_findings`.
Checkpoint retains prior findings until explicit resolution and preserves evidence.
An old input cannot reopen a resolved finding or discard a completed action receipt.
`repository.path` is an absolute path to the scoped checkout.
`work_scope` identifies writable checkouts, branches, or other owned resources.
Use the same canonical identifier wherever two units share a resource.
Keep project paths and private task content in the project store.

An action has kind `dispatch`, `local`, or `external` and status `planned`,
`pending`, or `completed`. Before an external operation or dispatch, checkpoint
its pending intent. After confirmed completion, checkpoint its receipt.
A pending intent means the operation may already have happened.
Reconcile current host or forge state before changing that intent or retrying.
A completed action requires a receipt and never becomes a retry instruction.

Checkpoint writes `checkpoint.json` atomically under the existing process lock.
It captures the unit table, exact-head verification ledger, frontier, gates,
standing orders, and pending and retained completion pointers alongside the
declaration. Existing store files and command contracts remain compatible.
Record published heads through `orch unit set` and refresh the frontier when
applicable. A saved head is historical information until a fresh forge read.

Checkpoint after owner assignment, a published head or finding change, an
external action receipt, and a classified completion drain. Persist the unit
and ledger changes before the checkpoint, then acknowledge the retained batch.
On replay, read current facts before updating the checkpoint. Preserve receipts,
confirmed completed work, and unresolved findings.

## Inspect the next safe action

```sh
orch pickup --json
orch pickup --host-state <fresh-host-state.json> --json
orch pickup --host-command <host-read-adapter.json> --json
```

Pickup reads the checkpoint and current store, then reads scoped PRs from `gh`.
It handles independent PRs as well as stacks. It never dispatches, merges,
acknowledges a batch, creates a lock, or repairs missing store directories.
Repeated pickup leaves the durable store unchanged.

The host observation format is:

```json
{
  "schema_version": 1,
  "observed_at": "<current-UTC-time>",
  "owners": [{"id": "owner-1", "state": "stopped", "writer_stopped": true}]
}
```

Use observations from the current host query, no older than 300 seconds.
Active states are `running`, `waiting`, and `needs-input`.
Terminal states are `completed`, `failed`, `cancelled`, and `stopped`.
Missing, stale, inaccessible, or `pending-init` status remains unknown.
An old checkpoint's owner state is never proof of a stopped writer.
A terminal owner with unconfirmed writer termination cannot release its scope.

For a host adapter, supply a JSON file with `read_only: true` and an `argv` array.
The helper runs that explicitly supplied read command without a shell and with
a bounded timeout. Its stdin requests the scoped owner identifiers.
Its stdout must return the host observation format above.
Choose an actual read-only host operation. The declaration does not sandbox
arbitrary commands or grant new access.

The report includes current store differences, retained completion batches,
current forge observations, owner classifications, evidence applicability,
and a consolidated replacement packet with the next safe action.
Units added after the checkpoint require owner reconciliation before dispatch.
Missing host access remains unknown. A merged PR preserves completed external
work even when its owner's host is inaccessible.
An inaccessible forge cannot certify a saved head or old verdict.
A changed published head invalidates affected verification under the existing
exact-head ledger rules. Keep historical evidence for the replacement owner.

For a confirmed active owner, continue observation instead of dispatching a
second writer. For a confirmed stopped writer, the coordinator may reuse its
scope within the saved authorization. For an unknown writer, use a new isolated
writable scope or visibly hold the unit. Deliver the entire replacement packet
and all retained findings to a fresh owner. Confirm no external action is pending
before dispatch. Pickup grants no new authorization.

Hourly audit registration recovery remains separate. Use `audit.py pickup`
per the audit registration reference (`audit-registration.md`) for registration
intent, missed ticks, and host wake receipts.
