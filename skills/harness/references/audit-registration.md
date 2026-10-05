# Hourly audit registration

`audit.py` records verified host registration separately from completed coordinator work. It uses Python 3.10 or later and the existing `orch.py` lock and atomic writes. It does not start a daemon, dispatch owners, resolve gates, or recover forge state.

## Commands

All commands require `--store <program-store>`. They print one JSON result. `--now <ISO-8601-time>` provides an explicit timezone-aware clock for deterministic replay. Normal runs use the current UTC time.

```sh
python3 <harness-package>/scripts/audit.py --store <program-store> ensure --checkpoint <checkpoint.json> --adapter <adapter.json>
python3 <harness-package>/scripts/audit.py --store <program-store> pickup
python3 <harness-package>/scripts/audit.py --store <program-store> status
python3 <harness-package>/scripts/audit.py --store <program-store> complete --delivery-id <host-delivery-id> --due-at <next-expected-audit> --evidence <audit-evidence.txt> --report <audit-report.json>
python3 <harness-package>/scripts/audit.py --store <program-store> stop
```

`ensure` freezes a complete checkpoint before any host mutation. Its first hourly obligation is one hour after setup. Repeated setup preserves that obligation and reconciles the stable registration. The program key hashes the program name, repository, and canonical store path. A changed program, repository, or adapter fails without a host mutation. An explicit repeat can refresh operational checkpoint fields. It cannot replace the original authorization, unresolved gates, or saved gate contents.

`pickup` returns the saved checkpoint and current queue files. It observes registration without creating or enabling a schedule. A disabled registration returns `suspended`. Only an explicit `ensure` can enable it. A stopped program stays stopped on every subsequent command. A newly authorized program uses a separate store.

`status` reads local files only. It does not call the host or change the receipt. Its registration status is the last verified observation, with `registration_observed_at` as its age. A current `armed` observation proves registration, not delivered wakeups or completed work.

`complete` requires a nonempty UTF-8 evidence file of at most 65,536 bytes. It captures its contents and SHA-256 hash. The report requires `progress`, `failures`, and `required_actions` lists. The supplied occurrence must match `next_expected_audit` and be due. A late completion advances one nominal hourly occurrence. Registration readbacks and pickup never advance a missed occurrence. Replaying the same delivery with the same occurrence, report, and evidence does not record a second completion. Conflicting replay fails. A stopped program cannot record a new completion.

`stop` persists stopped intent before discovery or cancellation. It refreshes exact ownership readback before cancelling the owned identifier. An absent or disabled readback confirms `stopped`. A timeout, ambiguity, changed owner, or unavailable readback retains `cancellation-unconfirmed` and the identifier. Pickup retries reconciliation and cancellation without enabling a schedule. Unrelated registrations remain outside the cancellation scope.

A command exits with `0` for a recorded result, including an explicit unsupported host. Host uncertainty exits with `1` and a saved JSON result. Invalid inputs exit with `2` and an error on stderr.

## Checkpoint

The checkpoint JSON requires `schema_version` equal to `1`. These fields capture the full program recovery context.

| Field | Shape and contents |
| --- | --- |
| `program` | Nonempty stable program name. |
| `repo` | Nonempty repository path for the coordinator. |
| `authorization` | Nonempty text containing the actual task grant and its limits. A link alone does not preserve authority. |
| `resume` | Nonempty instructions for the first action after suspension. |
| `units` | List of scoped units and their known state. |
| `owners` | List of objects with a nonempty `id` and a `scope` list of writable paths or resources. Preserve branches, worktrees, and liveness evidence when known. |
| `published_heads` | List of repository, branch or PR identities and published head SHAs. |
| `findings` | List of unresolved findings and their scope. |
| `evidence` | List of evidence paths and retained observations needed for pickup. |
| `next_actions` | List of pending actions and their prerequisites. |
| `unresolved_gates` | List of unresolved human gates with their actual question, authority boundary, and state. |

Empty lists are valid. Missing lists fail. The helper checks the outer shapes and owner scopes. The coordinator remains responsible for the meaning and completeness of each entry.

The receipt embeds the supplied metadata plus bounded contents and hashes from `standing-orders.md`, `units.tsv`, `ledger.tsv`, `gates.md`, `preferences.md`, `frontier.json`, `inbox`, and retained `inbox-claimed` batches when present. It holds the store lock while reading them. Each queue file is at most 65,536 bytes and their combined size is at most 262,144 bytes. The helper never rewrites queue files or acknowledges an inbox batch.

`recovery_hold` is true when saved unresolved human gates exist or current gate contents differ from the saved gate contents. Pickup exposes both versions. It does not resolve the conflict or grant fresh authority. This packet supports manual pickup. It does not implement issue 8's queue, owner, or forge recovery engine.

## Host command adapter

An adapter descriptor contains `schema_version` equal to `1`, a nonempty `argv` list, and `timeout_seconds` from `1` through `30`. The helper invokes that command without a shell from the program store. No descriptor means `unavailable`, a complete recovery packet, and an explicit unattended continuation limitation. No schedule is created.

Each command receives one JSON object on stdin. It contains `schema_version`, `operation`, `operation_id`, `program_key`, `target`, and `cadence_seconds` equal to `3600`. `target` contains the repository, canonical store path, and durable receipt path in `checkpoint`. Readback and cancellation also receive `registration_id` when known. The host must persist a wake target that resumes this coordinator from that packet and executes its hourly audit tick. The adapter supplies the host-specific prompt and controls.

`discover` must return an authoritative exact-key lookup. Its JSON response contains `supported` equal to `true`, a `capabilities` object, and a `registrations` list. The capabilities `durable`, `exact_lookup`, `idempotent_ensure`, `scoped_cancel`, and `readback` must all equal `true`. A host without those capabilities returns `supported` equal to `false` or fails the check. Capability declarations are an adapter trust boundary. Fixture tests do not certify a real host's promises.

The lookup returns zero or one matching registration. Each row contains a nonempty `registration_id`, the exact `program_key` and `target`, `cadence_seconds` equal to `3600`, and `status` equal to `enabled` or `disabled`. It filters unrelated keys before returning. Duplicate, malformed, mismatched, or changed identifiers fail the whole observation. They do not authorize creation or cancellation.

`ensure` must create or enable the registration atomically and idempotently by stable program key. Its action response is an object. The helper ignores action claims and requires a subsequent authoritative `readback`. Readback has the same registration list format as discovery. The identifier can be unknown after a lost ensure response, so the adapter must also support stable-key readback.

`cancel` acts only on the exact key, target, and identifier. Its action response is an object. Subsequent readback must show absence or disabled state. The helper persists operation intent before `ensure` or `cancel`. A lost response is recoverable through exact-key discovery. Cancellation retries retain their operation ID.

The helper bounds process time and response memory. Combined stdout and stderr are at most 65,536 bytes. POSIX commands run in an owned process group, which the helper kills on a timeout or inherited open pipe. On Windows it terminates the direct process. A Windows adapter must not spawn descendants that retain its pipes. Such descendants cannot be certified by this standard-library helper.

## Receipts and notifications

`audit-registration.json` stores the canonical registration state and checkpoint. `audit-host-responses` stores immutable per-call JSON receipts with the complete request, raw stdout, raw stderr, exit code, and error. The canonical receipt keeps the latest 20 path and file-hash pointers. Older response files remain available. `audit-completions` stores immutable completion receipts keyed by the delivery ID's hash, with captured audit evidence and report. The canonical receipt points to its latest completed occurrence. A crash after the completion file write can reconcile on delivery replay.

JSON results include `registration_status`, `last_completed_audit`, `next_expected_audit`, and `overdue_seconds`. Neither host `next_run` claims nor changing wall-clock time can hide a missed audit. Completed work and delivered host wakeups are separate facts. This helper records completed work only after the coordinator supplies its audit evidence.

`notify` is a structured change signal, not stdout suppression. A coordinator sends a user notification only when it is true and the change requires attention. Mutating operations consume the signal. The first overdue transition, suspension, new host failure, changed current gates, or changed progress report sets it. Repeated unchanged pickup and increasing overdue seconds do not. Read-only status always returns `notify` equal to `false`. Empty unchanged audit reports stay quiet.

No live host registration or coordinator delivery has been demonstrated by the bundled fixture. A host integration needs its own actual registration readback and delivered audit proof before claiming unattended continuation.
