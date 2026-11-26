# Upstream skill review, November 26

[Issue #27, generation 2](https://github.com/jaki95/agent-harness/issues/27) reported 27 pending sources and one unresolved Harness comparison. Local detection against all 48 registered sources found the same changed file paths, object IDs, and modes. The queued Cursor revision was `7a583913eb1b8d1a0ee76753d1a2cf072e7b54f9`. The current revision adds no changes to those watched files.

All decisions below refer to source `cursor-pstack` at [b7b93c36be9bcc36a74db438e0fd385d660bc559](https://github.com/cursor/plugins/commit/b7b93c36be9bcc36a74db438e0fd385d660bc559). The previous column identifies the prior reviewed commit in that repository. A keep decision advances only the reviewed revision. The registry records the incorporated revision for full and partial adoptions.

## Decisions

| Skill | Previous | Decision | What changes or stays, and why |
| --- | --- | --- | --- |
| `architect` | `c86f349b` | partial | Compare state ownership, duplicate public operations, and what callers must know. Retain five phases, independent candidate designs, the opt-in human checkpoint, design rationale, and the bundled reviewer references. |
| `arena` | `ae5650fe` | keep | Keep the configured roster, optional model diversity, and independent same-model judge. The upstream roster change would override host choices. |
| `benchmark-checklist` | `c86f349b` | partial | State the one-primary-number rule directly. Keep seven measurement questions, host tools and permissions, and Benchmark Checklist use in the local Perf issue and Hillclimb playbooks. |
| `blast-radius` | `0bb6f379` | partial | Trace the change and its commits directly. Use independent Arena candidates for wide changes under configured runner and judge roles. Keep executable evidence for the safety claim. |
| `figure-it-out` | `ae5650fe` | keep | Keep the configured role, effort and speed choices when available. The upstream model changes do not apply to host-selected roles. |
| `harness` | `ae5650fe` | partial | Give delegates the user goal and existing acceptance criteria. Trace affected code directly for implementation work. Keep cited investigations, independent Architect designs, and isolated worktrees for unrelated changes. Keep the executable orchestration and plan verification, operator authorization, review and publication checks. Retire the deleted upstream orchestration playbook and plan checker watches. Track the upstream worker brief for future changes. |
| `how` | `ae5650fe` | keep | Retain the original wording and both prompt templates. Narrow questions use one explainer. Complex questions use two to four explorers followed by an explainer. |
| `no-comments` | `ae5650fe` | partial | Trace the symbol directly or use Why for history. Keep unproven constraints, permissions for structural replacements, and host-configured reviewer settings. |
| `principle-attack-the-premise` | `ae5650fe` | partial | Use a discriminating observation before the next fix. Distinguish results that support or contradict the premise from inconclusive evidence. Keep the rerunnable check with the diagnosis. |
| `principle-boundary-discipline` | `23e4138d` | partial | Use two questions to locate parsing and pure logic. Keep domain types at public boundaries and framework dependencies in the shell. |
| `principle-build-the-lever` | `c86f349b` | partial | Keep the non-triviality threshold, a hand-checked first unit, rerun safety, one shared delegate contract, and the smallest reproducible tool. Drop repeated explanations. |
| `principle-explain-the-number` | `ae5650fe` | partial | Keep the decision threshold, noise floor, measured limiter, and run evidence. Resolve the performance checklist by installed name. Keep this skill scoped to measurement rather than model evaluation. |
| `principle-fix-root-causes` | `ae5650fe` | partial | Condense reproduction, instrumentation, and pattern-wide repair. Keep legitimate states, corrective boundary validation, and persisted-state inspection after restart. |
| `principle-foundational-thinking` | `23e4138d` | partial | Choose core data structures around access patterns and put shared foundations first. Keep explicit ownership and synchronization when actors must share state. |
| `principle-make-operations-idempotent` | `ae5650fe` | partial | Derive each action from current state and check convergence across repeated and interrupted runs. Scope the temporary-path rename example to file replacement. |
| `principle-minimize-reader-load` | `c86f349b` | partial | Judge layers by what they hide and what callers must remember. Keep the two tracing questions and the 30-second test. |
| `principle-model-the-domain` | `c86f349b` | partial | Select a structure that removes branches or invalid states. Keep one owner for domain knowledge repeated across processing phases and preserve discovery metadata. |
| `principle-prove-it-works` | `23e4138d` | partial | Check the actual output and observation method. Keep scripted evidence visible and route durable decision trails to Show Me Your Work by name. |
| `principle-separate-before-serializing-shared-state` | `23e4138d` | partial | Give independent writers their own records. Serialize structurally only when writers must share one target. |
| `principle-sequence-verifiable-units` | `23e4138d` | partial | Verify each unit, including automated edits. Keep the known-good trunk baseline and order commits to demonstrate the change. |
| `principle-test-behavior-not-implementation` | `ae5650fe` | partial | Use two imagined edits to check observable behavior and independence from internals. Keep useful tests, exact contractual error wording, external effects, and compile-time or cross-table invariants. |
| `principle-type-system-discipline` | `ae5650fe` | partial | Keep semantic types, parsed inputs, and schema-derived types. Use installed, language-neutral principle names for related guidance. |
| `show-me-your-work` | `ae5650fe` | keep | Keep the independent decision-trail reviewer and host-configured effort and speed. Do not require a particular vendor or a second model family. |
| `statechart` | `0bb6f379` | adopt | Adopt the upstream package and MIT notice. Nested diagrams show entry and exit transitions. Preserve SANY diagnostics, CRLF parsing, native Windows launch guidance, and cleanup of the spawned worker and its run directories. Model results still require replay against the application. |
| `swarm` | `ae5650fe` | keep | Keep the host-configured worker roster, optional diversity, and supported effort and speed settings. Report unavailable roles and missing evidence. |
| `technical-writing` | `c86f349b` | partial | Condense the four writing layers. Keep the worked example, Unslop discovery and fallback, and proposals for additions to its vocabulary. Retain invocation metadata. |
| `unslop` | `ae5650fe` | partial | Use one-line editing rules and retain stable rule numbers, gaps, and local discovery metadata. Rule 26 applies to abstract uses and preserves literal technical names. |
| `why` | `ae5650fe` | partial | Shorten the discovery description and open with the evidence requirement. Retain seven evidence categories, confidence tiers, source restrictions, contradiction reporting, and citation checks. |

## Harness source tracking

Upstream [removed the orchestration playbook and plan checker](https://github.com/cursor/plugins/commit/2f87c85) and referred program-scale work to Figure It Out and plan verification to the multi-phase playbook. Harness still provides executable orchestration and plan checks, so the registry retires the two individual file watches and keeps the original baseline. The new `worker.md` watch covers delegated acceptance criteria. Local delegates inherit configured roles and the operator's permissions. The upstream ready-for-review default and restrictions on reporting blockers did not transfer.

Upstream first moved coordination to the Project tracker and store and used host PR and CI events to follow work. The old bookkeeping scripts then had no caller. [PR #1043](https://github.com/cursor/plugins/pull/1043). The later simplification treated some skill instructions as redundant. It reports packaging and script checks but gives no comparative trial of multi-day orchestration. [PR #1249](https://github.com/cursor/plugins/pull/1249).

## Bounded instruction checks

Two fresh agents each received one package, the same three requests, and inherited model settings. They read the assigned Markdown only. On a complex checkout with inaccessible storage, the retained How package produced a plan for three explorers and one explainer. The rejected How candidate produced a plan for one read-only explainer. Both required citations and marked storage internals unverified. This tested dispatch decisions. Neither agent executed the proposed investigation.

Both agents marked an unconfirmed cache-bypass experiment inconclusive and required a traced rerun. Both strengthened a public error test whose callers depend on exact wording, kept the cross-table invariant, and replaced the private-helper call count with an observable assertion. Each package received one trial. These cases give no general estimate of model quality or speed.

## Local verification

- The detector reported all 48 sources unchanged after the registry update. The 23 incorporated revisions correspond to 23 changed runtime packages. Five sources advanced only their reviewed revision.
- The repository checker validated 48 packages. All 255 Python tests passed. The Skills CLI installed the packages into disposable projects and exercised pinned updates and explicit upgrades.
- All 411 Statechart files and modes matched the pinned source, including the license. The real Linux CLI reproduced both the Login Mermaid chart and the report byte for byte. The full Statechart run passed 406 of 407 tests with a Java runtime. The remaining test compiles Java source. It passed all 4,000 generated configurations on a targeted rerun with the matching JDK. Linux signal cleanup, rendering and Windows-format inputs were exercised. Native Windows execution remains unverified.
- The local orchestration CLI passed six disposable recovery scenarios. Repeated pickup after a coordinator crash preserved state. A changed PR head invalidated its prior verdict, and a stale or missing host observation prevented reassignment to the same scope.
