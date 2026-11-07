# Skill update probes

Date: 2026-11-07. This is a bounded check of selected instruction changes, not a general model benchmark.

## Setup

Two fresh delegates inherited the parent session model and settings without overrides. Each received the same eight independent requests in the same order. Package A contained the existing skills from harness `8d9533240857f6a9fc6cf37e6bf36f2073caa3e0`. Package B contained the proposed updates. The prompts did not identify which package was newer. Both included relevant Interrogate and Why references when those references existed. Delegates could read only their assigned package and could not use network, delegate, modify repository code, or claim unavailable actions.

The host delegation tool does not expose the exact inherited model identifier in its result. These observations apply to this session, not every model in a configurable roster. Common host instructions remained present in both conditions. There was one response per package, with eight tasks sharing a context. The follow-up C used a fresh context and only the migration case. This does not establish a causal effect, noninferiority, a success rate, or a token/latency improvement.

## Observed migration failure and correction

Both initial responses migrated direct imports, qualified calls, dynamic registration, workers, and tests. A preserved the existing tuple return. B invented a return change and rewrote the tests to accept Event objects:

```python
# Package A
def publish(event: Event) -> tuple[str, dict[str, object]]:
    return event.topic, event.payload

# Package B
def publish(event: Event) -> Event:
    return event
```

The task requested a new input/API shape, not different return values. Four independent contract checks executed the proposed transport, api, jobs, and registry modules in disposable directories. They check the literal results of save, ready, and dispatch, plus retirement of the old API. A passed all four; B failed all three result checks and passed API retirement. Its own rewritten tests would not expose that scope expansion.

The final migration skill adds one sentence:

> Preserve behavior outside the requested API change, including return values, side effects, and errors.

Fresh probe C returned `event.topic, event.payload` and passed all four independent checks. The shorter body remains; the other deleted reminders were not restored. One failure is enough to retain this targeted instruction, but the rerun does not prove it prevents every similar failure.

## Other observed outcomes

| Case | A and B observations |
| --- | --- |
| Type design | Both used a discriminated union, exhaustive rendering, distinct ID types, and boundary parsing. |
| Root cause | Both accepted a guard for legitimate loading null and fixed invalid restored ready state at the producer. Cache deletion was evidence, not proof of the repair. |
| Test review | Both retained external no-send assertions and exact contractual errors, replaced private-helper coupling, and checked actual email payloads and counts. |
| Static review | Both blocked a traced cross-tenant disclosure despite the unavailable runtime, and disclosed absent independent/runtime verification. |
| Investigation | Both separated the trace-supported deadline from unknown intent, kept contradictory config evidence visible, and rejected a population-rate claim from changed sampled groups. |
| Recovery | Both reused stable idempotency keys, reconciled completed external registration, preserved state, and rejected PID existence as sufficient ownership proof. |
| Measurement | Both specified the decision before running and rejected a warm tiny-fixture mean as evidence for cold 100k-record p95 and correctness. |

These are response-level observations. The migration snippets were executed; the other generated implementations and plans were not run against real applications or services. No full autonomous shipping workflow or every skill was behaviorally evaluated.

## Exact task requests

### migration

Skill: `principle-migrate-callers-then-delete-legacy-apis`.

Implement this internal Python API change. Return the replacement files and explain the scope. transport.py currently defines send_event(topic, payload), returning (topic, payload). New API is publish(Event(topic, payload)) using a frozen dataclass. callers: api.py imports send_event and calls send_event('saved', {'id': item}); jobs.py imports transport and calls transport.send_event('ready', {'id': item}); registry.py has HANDLERS = {'emit': getattr(transport, 'send_event')}, used by workers as HANDLERS['emit'](topic, payload). All callers are inside this repo; there are no external API consumers. tests assert exact tuples from api.save('x'), jobs.ready('x'), and registry.HANDLERS['emit']('tick', {'id':'x'}). What should the final code and tests look like?

### types

Skill: `principle-type-system-discipline`.

Design a TypeScript model and render function for a request. Current type is {status: 'loading'|'success'|'error'; data?: string; error?: Error}; render uses non-null assertions. A successful request must carry data and an error must carry an Error. The server will add a cancelled state next month. UserId and InvoiceId both arrive as strings; charge(userId, invoiceId) has suffered swapped-argument bugs. Give concrete types, render, and the boundary flow. We have no schema generator installed.

### debugging

Skill: `principle-fix-root-causes`.

Review two proposed null guards. A: selectUser(id) is documented to return null while the first request is loading. Header immediately reads user.name and crashes; proposed patch renders a loading label while user is null. B: cache.restore writes {state:'ready',items:null} after reading an older cache version even though ready requires an array; proposed patch changes every items.map to (items??[]).map. For each, choose a fix and a check. Clearing the cache makes B disappear. Does that prove the corrective mechanism?

### tests

Skill: `principle-test-behavior-not-implementation`.

Review these test changes for a password-reset API whose contract is to send exactly one email with a reset link for known accounts, send no email for unknown accounts, and return the literal public error 'Invalid reset token' for an invalid token. Proposed cleanup deletes the unknown-account no-call assertion because absence is not behavior, changes the invalid-token assertion to merely expect any exception, retains a private formatLink helper call-count test, and adds an email-provider spy asserting the actual recipient and URL. Decide which changes to keep, reject, or replace, and give the expected assertions. The email provider is an external boundary.

### review

Skill: `interrogate`.

Review this proposed authenticated invoice endpoint. No database or deployed service is available, so running the app is impossible here. Authenticated principal is req.user={id,tenantId}; req.params.id is client-controlled. New code: const invoice = await db.invoice.findUnique({where:{id:req.params.id}}); if (!invoice) return res.status(404).end(); return res.json(invoice); Schema: Invoice {id unique, tenantId, amount}. There is no row-level policy, middleware tenant filter, or authorization check beyond authentication. The author says no runnable reproduction means no finding can block. Return your verdict with concrete evidence, needed fix and verification. Do not pretend to spawn reviewers or run the unavailable app.

### investigation

Skill: `why`.

Explain why a request failed using only this supplied evidence; do not fetch sources. [D1 config spec] request timeout is 5 seconds. [D2 current config for cohort beta] timeout_ms=10000. [D3 request trace R] cohort=beta, elapsed_ms=10002, cancelled_by=deadline. [D4 incident note] author suspects an earlier deploy changed timeouts; no commit is linked. [D5 git] release commit was squashed, and path history has no original author rationale. [D6 Sentry] issue marked resolved manually, 20 sampled events, grouping rule changed yesterday; no raw population count. Give the established mechanism, the unresolved intent question, confidence, next useful evidence, and source citations. Is a rise from 10 sampled events yesterday to 20 today evidence failures doubled?

### recovery

Skill: `principle-make-operations-idempotent`.

A command provisions a workspace, registers it in an external service, and then writes a local completion record. It crashed after registration but before the record. A lock file contains PID 720, which now belongs to an unrelated process after PID reuse. The external service supports idempotency keys and lookup by key. Design the retry steps and the cases to verify. Do not delete state merely because the local completion marker is missing.

### measurement

Skill: `principle-explain-the-number`.

We need decide whether a cache change makes first search on a 100k-record library meet a 200ms p95 target without wrong results. A proposed benchmark runs 100 warm identical queries on a 100-record fixture and reports mean time, while swallowing errors. The author calls its 2x speedup sufficient. Before running anything, specify the decision and a useful measurement; then say what the proposed result establishes.

## Local evidence

Raw packages, responses, and contract outputs are retained under ignored `work/skill-update-evidence/probes/`. They are local run artifacts, not installed skill content. The task requests and consequential failure are retained above for future reruns.

| Artifact | SHA-256 |
| --- | --- |
| `A.md` | `2283b17845723cf4c9a40a581c894d3f2a7f2c0836ee1ecabb9f6db39025a175` |
| `B.md` | `c2587d07ad4badbd1b0c00c4c9716e66868f5c10039ebba7032a4dea6aa15831` |
| `C.md` | `b3ba7744757d262b6cac92736a741c7068a0e99ef3a0f30222aab19d6548b6b6` |
| `A-response.json` | `dfc6a2066e4239331e90438aa13b640f3d792acb526ce345959d44dbaa59d384` |
| `B-response.json` | `ff47d136897454942c22db73f06d3c12fcd79be607eca5e1583e788bbef96929` |
| `C-response.json` | `32fcc7a0c25a867f2f34f95a98fcd487dfd461bcc2e0c19d1ef3685874e2a389` |
| `migration-contract-results.json` | `06b8a7af9f0162e0e178f258fbbbee7c840c26d02b120c4f97b2be361367d342` |

An independent reviewer graded A as passing all eight supplied tasks, initial B as passing seven with the migration scope defect, and revised C as passing the migration task. These counts describe this small sample only. The reviewer also confirmed the retired source paths and final provenance records. The independent grading artifact has SHA-256 `37a2decd15fa9c67440c1fce91cacb790fe806227dc04c6212f96ad7a1826bb6`.
