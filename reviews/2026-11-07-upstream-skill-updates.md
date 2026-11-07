# Reviewed upstream skill updates

Review date: 2026-11-07. Based on harness `8d9533240857f6a9fc6cf37e6bf36f2073caa3e0` and issue [#6, generation 5](https://github.com/jaki95/agent-harness/issues/6).

The user authorized the updates after reviewing the rationale for shorter instructions. Generic reminders are candidates for removal, not assumed necessary because they existed. Opus-specific upstream results do not establish behavior for this host. The paired probes described in [the evaluation record](../evaluations/2026-11-07-skill-update-probes.md) check selected risks on the inherited session model; they do not validate every configured model or a complete autonomous run.

Cursor source: `ae5650febf4320793844c12c4adaa937f417f8da`. Matt Pocock source: `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. A fresh Cursor main read resolved `6b0300214a09fd6029cfb7077043125758cd1fd2`; its `pstack/` and `cursor-team-kit/` trees have no changes from the queued Cursor revision. Adoption stays pinned to the issue evidence.

## Decisions

| Skill | Source | Previous reviewed revision | Decision |
| --- | --- | --- | --- |
| `arena` | `cursor-pstack` | `c86f349b102feb91f1966f8a6a60882a4e601b50` | partial |
| `figure-it-out` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |
| `grill-me` | `matt-pocock-grilling` | `49dd158d1076134a641b33efb035946536778336` | adopt |
| `harness` | `cursor-pstack` | `c86f349b102feb91f1966f8a6a60882a4e601b50` | partial |
| `how` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |
| `interrogate` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |
| `no-comments` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |
| `principle-attack-the-premise` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |
| `principle-explain-the-number` | `cursor-pstack` | `c86f349b102feb91f1966f8a6a60882a4e601b50` | partial |
| `principle-fix-root-causes` | `cursor-pstack` | `c86f349b102feb91f1966f8a6a60882a4e601b50` | partial |
| `principle-make-operations-idempotent` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | adopt |
| `principle-migrate-callers-then-delete-legacy-apis` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |
| `principle-test-behavior-not-implementation` | `cursor-pstack` | `c86f349b102feb91f1966f8a6a60882a4e601b50` | partial |
| `principle-type-system-discipline` | `cursor-pstack` | `c86f349b102feb91f1966f8a6a60882a4e601b50` | partial |
| `show-me-your-work` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |
| `swarm` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |
| `unslop` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |
| `why` | `cursor-pstack` | `23e4138daa01c42d4969f7a5465f82704e64f798` | partial |

Every listed source advances both reviewed and incorporated revisions to its source commit above. Partial incorporation records selected material, not whole-package equivalence. Baselines and the other 24 sources are unchanged.

## arena

Adopt current upstream compact six-phase structure, removing repeated setup, rationale, graft, and verification prose. Keep isolated candidates, hidden rubric, independent judging after candidates finish, synthesis, and verification.

Retained differences: Keep existing invocation metadata and Codex policy files. Use configured role models or parent inheritance, optional model diversity, and host concurrency and permission limits. Map upstream reasoning and speed selection to configured role settings or host defaults. Keep three inherited candidates when no roster is configured and replace unavailable models with parent inheritance. Use an independent same-model judge when appropriate rather than requiring a different family or skipping judging for lack of diversity. Missing delegation remains an explicit review gap, not a completed independent review. Use host tools, temporary paths, optional todo tooling, and installed principle names.

## figure-it-out

Adopt compact phase-placement and experiment-loop wording. Route supported reasoning and speed settings through Harness Subagents.

Retained differences: Keep broad discovery triggers, Show Me Your Work dependency, local task-plan fallback, named principle routing, and tool/permission assumptions.

## grill-me

Use a subagent with a fresh context window for environmental fact gathering.

Retained differences: Local name and description. Existing design-tree rounds and user-owned decisions.

## harness

Adopt matching inline-code delimiters in the plan checker while retaining fence parsing and acceptance dispatch. Carry the user goal through initial updates, briefs, PR purpose, and the final result. Align root-cause, testing, and pre-measurement summaries with their updated leaf skills. Centralize supported effort/speed selection under existing configured role and cost preferences. Use the existing expected-head publication helper in Autopilot owner and topology paths. Keep decision trails accessible to the root and replacements. Extend verifier evidence and root countersigns to all gate loosening. Clarify worker topology prohibitions and freeze unrelated writes during landing.

Retained differences: Keep full independent verification rounds and current-head evidence requirements; do not adopt the major-versus-minor swarm relaxation. Retain the Python orchestration, queue recovery, audit registration, acceptance, worktree audit, and guarded publication implementations. Retain gh-only operations, exact published-head checks, explicit task authorization, native-stack handling, stopped-writer isolation, and operator-landing topology. Do not adopt Cursor-specific model names, project stores, mandatory model diversity, or no-script orchestration. Do not adopt only-runnable findings or missing-checks-as-success policies.

## how

Adopt the four-step workflow with simple questions handled by one explainer and complex questions by two to four explorers then an explainer. Adopt the shorter explorer prompt, retaining a single exact-citation instruction. Route supported reasoning and speed settings through Harness Subagents.

Retained differences: Local invocation metadata, read-only work, configured role models or parent inheritance, host concurrency limits, and missing-capability reporting.

## interrogate

Adopt Frame, Fan out, Verify, Output workflow and isolated executable repros with commands and actual versus expected output. Include working-tree changes and relevant untracked files in the default merge-base scope. Rerun findings and deduplicate by root cause; keep all verified findings rather than choose a winning reviewer. Remove all four old reviewer, rubric, code-quality, and lead-judgment reference files; retain needed contextual judgment inline.

Retained differences: Keep existing invocation metadata and Codex policy files. Use configured role models or parent inheritance, optional model diversity, and host concurrency and permission limits. Map upstream reasoning and speed selection to configured role settings or host defaults. Accept independently traced static correctness, security, and contract defects; executable proof is preferred but is not the only admissible evidence. Separate unverified suspicions and reproduction/access gaps from verified findings; no clean-review claim when review is incomplete. Keep contextual lead judgment against actual intent, reachable inputs, surrounding code, and known constraints. Use three configured or inherited independent reviewers rather than fixed external models. Inline concise scope, isolation, and reviewer setup rather than add an Arena or in-your-own-words installation dependency. Keep target checkout and external services read-only; permit repro writes only inside assigned isolated workspaces within task permissions.

## no-comments

Adopt canonical comment-sicko agent name in its prompt metadata and delegation instruction. Use configured role reasoning and speed settings where available.

Retained differences: Keep existing invocation metadata and Codex policy files. Use configured role models or parent inheritance, optional model diversity, and host concurrency and permission limits. Map upstream reasoning and speed selection to configured role settings or host defaults. Keep explicit bundled prompt passing rather than depend on a Cursor subagent type. Preserve unresolved comment rationales and constraint comments until investigation or an approved, verified replacement. Keep existing scope, restoration, and approval rules for comment deletion and structural encoding.

## principle-attack-the-premise

Rerunnable discriminating observations. Follow the next causal question when evidence supports the premise. Remove demonstrated causes rather than compensate. Remove redundant worked examples.

Retained differences: Repeated failed fixes alone do not prove a premise false. Supporting, contradicting, and inconclusive evidence remain distinct. Installed-skill names replace sibling package links.

## principle-explain-the-number

Trigger before measurement. State the decision-changing result and noise floor before the run. Stop when spread exceeds the measured effect. Remove repeated introductory explanation.

Retained differences: Existing exclusion of agent evaluation scope. Installed-skill names replace sibling package links.

## principle-fix-root-causes

Distinguish legitimate states from invalid states produced earlier. Scrutinize retries, swallowed errors, clamping, and discarded state. Investigate persisted state after restart without inferring that clearing it proves a validation fix. Keep instrumentation and pattern-wide fault repair.

Retained differences: Correct boundary validation can fix the root cause. Diagnostic signal remains a proposal.

## principle-make-operations-idempotent

Derive each step from existing state and apply only the difference. Use interruption-safe evidence of staleness. Replace PID-specific lock advice with general recovery reasoning. Retain repeated-run and crash-point questions.

## principle-migrate-callers-then-delete-legacy-apis

Adopt the concise body with the test-contract instruction and applicability conditions. Keep coordinated migration in the description and heading instead of repeating it in the body. Retain one sentence preserving behavior outside the requested API change. The initial shortened-package probe changed tuple results to Event objects without a requested result-contract change; the corrected package preserved the tuples in a fresh probe.

## principle-test-behavior-not-implementation

Check behavior breakage and stability under internal restructuring. Treat external effects and contractually required absence as behavior. Derive expectations from requirements. Keep invariant and compile-time checks. Replace assertion-shape lists with contract-driven judgment.

Retained differences: A missed defect does not establish that a test catches no defects. Strengthen useful tests before deleting them. Exact error wording remains valid when part of the contract.

## principle-type-system-discipline

Adopt the three-rule body for semantic types, boundary parsing, and schema derivation. Remove five generic reminder bullets and the corresponding compiler-bypass description phrase.

Retained differences: Language-neutral scope. Full installed skill names.

## show-me-your-work

Use configured reviewer reasoning and speed settings where available. Name the trail review independent review and allow a separate same-model reviewer under current user model policy.

Retained differences: Keep existing invocation metadata and Codex policy files. Use configured role models or parent inheritance, optional model diversity, and host concurrency and permission limits. Map upstream reasoning and speed selection to configured role settings or host defaults. Keep current-run-only transcript access and prohibit scanning unrelated conversations. Keep independent review, incomplete-review reporting, append-only log history, local-by-default storage, and truthful Attention output. A same-model review is valid and is not described as cross-family review; diversity is optional.

## swarm

Adopt upstream removal of redundant opening, worker-count reminder, and duplicate aggregate/report instructions. Renumber model selection and output isolation steps and update the dispatch reference. Use configured role reasoning and speed settings where available.

Retained differences: Keep existing invocation metadata and Codex policy files. Use configured role models or parent inheritance, optional model diversity, and host concurrency and permission limits. Map upstream reasoning and speed selection to configured role settings or host defaults. Keep portable execution environments, verified checkout SHAs, rolling scheduling within host concurrency, and honest missing-delegation reporting. Keep configured or inherited models. General diversity is optional; missing arms in an explicitly requested model race remain coverage gaps. Keep exact-SHA and measurement-method receipts, one retry for missing metadata, all proven issues, and explicit coverage gaps.

## unslop

Adopt all upstream body compression, preserving stable rule numbers and gaps.

Retained differences: Keep local invocation metadata and the existing always-apply description clause; this update does not change discovery or scope policy.

## why

Adopt the shorter entrypoint, epistemics framework, investigator and synthesizer prompts, and all five changed source references. Retain five confidence tiers, verbatim searches, source boundaries, contradiction reporting, citation spot-checks, and read-only work. Replace Cursor model/tool calls with configured host roles, concurrency limits, connected-tool discovery, and Harness Subagents settings.

Retained differences: Keep a concise squash-history caveat in code archaeology and three Sentry-specific pitfalls: regrouping, manual resolution, and event sampling. Keep invocation metadata and full seven-category coverage with explicit missing-source reporting.

## Supporting-file mappings

Entrypoints map from `pstack/skills/<name>/SKILL.md` to `skills/<name>/SKILL.md`; Harness maps from `poteto-mode`, and Grill Me maps from `skills/productivity/grilling/SKILL.md` in Matt Pocock's repository.

How and Why retain corresponding relative paths for their changed references. The nine changed Why files and both changed How files were compared individually. `pstack/agents/comment-sicko.md` maps to `skills/no-comments/references/comment-sicko.md`. Interrogate removes the same four reference files deleted upstream and moves the retained contextual and static-proof requirements into its entrypoint. Show Me Your Work keeps its existing helper and template.

Harness entrypoint, changed playbooks, and `scripts/check-plan.mjs` map from the same paths under `pstack/skills/poteto-mode/`. The upstream shell worktree audit and TypeScript orchestration files are not interchangeable with our Python helpers. Those local helpers, their recovery contracts, and tests remain. The three deleted TypeScript paths are removed from active watches after reviewing their deletion; their original source commit remains recorded. The surviving Orchestrate playbook remains watched.

## Verification

The parser tests cover single and multiple backtick delimiters, embedded runs, mismatched delimiters, prose after code, and the existing fence rules. Four new subcases failed before the regex change; all 16 plan-checker tests pass afterward. Acceptance dispatch is covered by the full repository suite.

Structural validation passed for all 42 skills. The full suite passed all 243 tests with Node 24.18 available. `npm ci --ignore-scripts` and `npm run test:skills` passed, including all 42 packages and deleted-reference packaging. Fresh upstream monitoring returned 42 unchanged sources, zero pending sources, and no errors. Independent runtime review returned PASS+NOTES; it separately passed all 16 plan-checker tests. The final independent provenance and probe review found no remaining actionable findings. It confirmed the initial migration defect and the corrected follow-up. The model probes and their limits are recorded in the linked evaluation. No user-wide skill installation or release is part of this change.

Before publication, this change was rebased onto `2ad3c605b092352869bcc8bf225e8a39379a1823`, which adds Wayfinder. Structural validation and installation checks passed for the combined 43 skills, and all 243 Python tests passed again. A fresh upstream scan returned the original 42 sources unchanged and one pending Wayfinder source, with no errors. Wayfinder's upstream change requests a fresh context window for research subagents; it is outside this reviewed batch and remains pending. Issue #6 therefore still has outstanding work after this batch is incorporated.
