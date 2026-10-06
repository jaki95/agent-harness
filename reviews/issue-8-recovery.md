# Queue recovery verification

Issue #8 adds durable queue checkpoints and a read-only pickup report.
The completion condition is a merged change whose disposable CLI demonstration
recovers an interrupted drain without lost findings or repeated dispatch.

## Workflow

1. Trace the existing store and capture its passing regression baseline.
2. Add checkpoint metadata beside the existing store records.
3. Exercise interrupted drain recovery and conservative owner reconciliation.
4. Update the runtime instructions and verify project-local installation.
5. Run an independent CLI verification and review the actual diff.
6. Open a PR, confirm current-head checks, and squash-merge the verified change.

## Work allocation

- Blocking first steps are repository identity, issue scope, current main, and store grounding.
- Independent workstreams are runtime implementation with its tests, and documentation.
- Shared mutable state stays with one runtime writer and one documentation writer.
- The smallest safe decomposition is one runtime owner because checkpoint and pickup share the store contract.

The design extends the existing plain-file store rather than adding an event
engine or scheduler. Pickup observes state and returns a next action.
The coordinator retains responsibility for authorization and external actions.

## Baseline

The existing orchestration suite passes all 16 tests on the pre-change main.
It covers retained drains, interrupted claims, process locks, and exact-head
ledger lookup. The baseline has no queue checkpoint or pickup command.

## Verification evidence

The disposable demonstration is rerunnable from the repository root:

```sh
python3 scripts/demo_queue_recovery.py --output local/queue-recovery-demo.json
```

The output records actual fixture forge calls, the host adapter request, and
six pickup scenarios. The coordinator exits inside the inbox rename before
the drain response. Recovery retains the claimed report, recommends completion
reconciliation, and leaves the missing pending directory unchanged.
Repeated pickup returns the same report and preserves every store byte.

The demonstration also checks confirmed stopped ownership, pending-init,
stale host observations, missing host access, and changed-head evidence.
Forge and host reads in the demonstration use disposable executable fixtures.
They do not prove delivery from an external agent host.

The project-local Skills CLI check invokes the installed checkpoint and pickup
commands from an unrelated directory. It compares the installed resources with
the runtime package and confirms maintenance records are excluded.
