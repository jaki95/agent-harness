# agent-harness

A portable home for skills, scripts, and conventions that I own and maintain across projects.

Public skills are reference material for deliberate adaptation, with sources and revisions tracked separately. This repository is the source of truth; project-specific instructions stay in their projects.

## Layout

```text
skills/                 Runtime instructions and supporting files only
registry/skills.json     Maintenance index: sources and upstream revision tracking
reviews/                Optional consequential upstream adoption decisions
scripts/                Portable maintenance utilities and their tests
templates/              Runtime and maintenance templates
docs/                   Adaptation, registry, and portability conventions
package.json            Pinned Skills CLI for compatibility testing
AGENTS.md               Instructions for agents maintaining this repository
```

## Check the harness

Requires Python 3.10 or newer, with no third-party dependencies:

```sh
python3 scripts/check.py
python3 -m unittest discover -s scripts/tests
```

Run these from the repository root. The checker also works from another directory when invoked by its full path. GitHub Actions runs both commands on pushes and pull requests.

To check Skills CLI compatibility, use Node 22.20 or newer:

```sh
npm ci --ignore-scripts
npm run test:skills
```

The pinned CLI test creates temporary Git tags and project-local installations. It verifies release pinning, explicit upgrades, runtime resources, and exclusion of maintenance records. It does not import public skills or install globally.

## Available skills

| Skill | Purpose |
| --- | --- |
| [grill-me](skills/grill-me/SKILL.md) | Stress-test a plan, decision, or idea in rounds of questions |
| [harness](skills/harness/SKILL.md) | Working mode with selective explanations, milestone updates, and routed principles and playbooks |
| [unslop](skills/unslop/SKILL.md) | Remove AI writing patterns while preserving meaning |
| [technical-writing](skills/technical-writing/SKILL.md) | Write docs, PR descriptions, and commit messages with the original writing guidance |
| [deslop](skills/deslop/SKILL.md) | Remove unnecessary code patterns and match local style with minimal edits |
| [interrogate](skills/interrogate/SKILL.md) | Challenge changes with independent reviewers and a pragmatic lead verdict, without automatic edits |
| [show-me-your-work](skills/show-me-your-work/SKILL.md) | Keep and audit a decision trail with evidence, separate review, and explicit limitations |
| [benchmark-checklist](skills/benchmark-checklist/SKILL.md) | Vet performance measurements and report repeatable, correct, relevant results |
| [figure-it-out](skills/figure-it-out/SKILL.md) | Design and execute a task-specific workflow with measured experiments and a decision trail |
| [no-comments](skills/no-comments/SKILL.md) | Review scoped comments and suppressions, preserve unresolved rationale, and fix accepted findings |
| [control-ui](skills/control-ui/SKILL.md) | Drive and inspect browser or Electron UIs with local automation and captured evidence |
| [control-cli](skills/control-cli/SKILL.md) | Exercise interactive CLIs and TUIs with repeatable terminal input and transcripts |
| [how](skills/how/SKILL.md) | Explain architecture and runtime flow through delegated exploration and explanation |
| [why](skills/why/SKILL.md) | Investigate historical rationale across available evidence sources with calibrated confidence |
| [architect](skills/architect/SKILL.md) | Ground, compare, and synthesize designs before implementation, with an opt-in checkpoint |
| [swarm](skills/swarm/SKILL.md) | Run independent coverage or race workers and consolidate evidence with explicit gaps |
| [arena](skills/arena/SKILL.md) | Compare independent candidates with a cross-judge, synthesize one artifact, and verify it |
| [principle-laziness-protocol](skills/principle-laziness-protocol/SKILL.md) | Simplify code and unnecessary indirection without a fixed layer limit |
| [principle-foundational-thinking](skills/principle-foundational-thinking/SKILL.md) | Choose data structures before logic and make necessary shared-state ownership explicit |
| [principle-redesign-from-first-principles](skills/principle-redesign-from-first-principles/SKILL.md) | Integrate requirements as foundational design decisions and deliver the redesign incrementally |
| [principle-attack-the-premise](skills/principle-attack-the-premise/SKILL.md) | Test assumptions shared by failed fixes with evidence suited to the symptom |
| [principle-subtract-before-you-add](skills/principle-subtract-before-you-add/SKILL.md) | Remove unnecessary complexity before building on the simpler base |
| [principle-minimize-reader-load](skills/principle-minimize-reader-load/SKILL.md) | Reduce layers and hidden state so readers can trace code quickly |
| [principle-outcome-oriented-execution](skills/principle-outcome-oriented-execution/SKILL.md) | Converge planned migrations on the target architecture with explicit verification boundaries |
| [principle-experience-first](skills/principle-experience-first/SKILL.md) | Prioritize a polished core experience for consumers and maintainers |
| [principle-exhaust-the-design-space](skills/principle-exhaust-the-design-space/SKILL.md) | Compare distinct prototypes before committing to an uncertain design |
| [principle-build-the-lever](skills/principle-build-the-lever/SKILL.md) | Build the smallest rerunnable tool that performs or proves non-trivial work |
| [principle-model-the-domain](skills/principle-model-the-domain/SKILL.md) | Encode domain rules in structures that reduce scattered conditions and invalid states |
| [principle-boundary-discipline](skills/principle-boundary-discipline/SKILL.md) | Validate at system boundaries and keep business logic pure |
| [principle-type-system-discipline](skills/principle-type-system-discipline/SKILL.md) | Use types to prevent invalid states, mismatched values, and unhandled variants |
| [principle-make-operations-idempotent](skills/principle-make-operations-idempotent/SKILL.md) | Make retries and partial failures converge to the intended state |
| [principle-migrate-callers-then-delete-legacy-apis](skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md) | Migrate internal callers and remove legacy APIs in the same refactor |
| [principle-separate-before-serializing-shared-state](skills/principle-separate-before-serializing-shared-state/SKILL.md) | Separate independent write targets before serializing necessary shared state |
| [principle-prove-it-works](skills/principle-prove-it-works/SKILL.md) | Verify real outputs with direct observation and repeatable evidence |
| [principle-fix-root-causes](skills/principle-fix-root-causes/SKILL.md) | Reproduce and fix the mechanism while retaining corrective boundary validation |
| [principle-sequence-verifiable-units](skills/principle-sequence-verifiable-units/SKILL.md) | Verify each small unit and order delivery so the sequence demonstrates correctness |
| [principle-test-behavior-not-implementation](skills/principle-test-behavior-not-implementation/SKILL.md) | Assert observable behavior and scrutinize tests against plausible defects |
| [principle-explain-the-number](skills/principle-explain-the-number/SKILL.md) | Establish measurement limiters, eliminate misleading results, and retain evidence |
| [principle-guard-the-context-window](skills/principle-guard-the-context-window/SKILL.md) | Keep bulky material out of the parent context with bounded scope and host-aware delegation |
| [principle-never-block-on-the-human](skills/principle-never-block-on-the-human/SKILL.md) | Proceed on authorized reversible work while retaining human product direction |
| [principle-encode-lessons-in-structure](skills/principle-encode-lessons-in-structure/SKILL.md) | Turn recurring corrections into enforceable mechanisms and authorized task notes |

Harness uses Poteto Mode's section layout and routes to separate skills by name through the host's skill catalog. Its communication, Investigation, Bug fix, Feature, Refactoring, Perf issue, Hillclimb, Runtime forensics, Trace forensics, Prototype, Visual parity, Babysit, Shipping, Autonomous run, Orchestrate, both Autopilots, Multi-phase or multi-PR plan, Session pickup, Pause safely, Worktree and simulator cleanup, and Opening a PR playbooks are bundled inside its package. Unslop preserves its pinned upstream instruction body. Technical writing adds named Unslop discovery and a missing-skill fallback. Invoke Harness with `/harness` on hosts that expose skills as slash commands, or `$harness` in Codex. Install the writing, code cleanup, review, control, investigation, design, and engineering skills listed above for the full workflow. A standalone Harness install uses its own communication rules and reports unavailable routed skills. PRs opened under Harness are ready for review. Execution follows host and task rules. How, Why, Architect, and Arena preserve Poteto's delegation workflows using host tools and existing model configuration. Every feature begins with How over the affected subsystem, followed by Architect and a four-item throughput checkpoint before delegated implementation. Implementation uses a scoped delegate, or Arena when multiple implementation shapes are valid. Feature verification runs on the matching surface and reports inconclusive or wrong-surface results. Each small unit is built, verified, and committed before the next; delivery uses ordered commits and stacked follow-ups. Contested feature designs go through Interrogate before shipping, and authorized PR work follows Opening a PR. One owner handles each coupled feature or migration and delegates internally after blockers. Parent-level fan-out is for independent artifacts; checkpoints are rewritten at phase boundaries and fresh owners take new work.

The bundled Refactoring playbook preserves behavior through a recorded baseline, named target structure, subtraction-first changes, scoped mechanical delegation, equivalence checks, and ordered verified commits. API reshapes migrate every caller and delete the old API in one wave. Refactors must reduce reader load. Large or cross-cutting structural work routes to Figure It Out.

Figure It Out designs and executes workflows for large migrations, ambitious multi-part changes, work reviewed after stepping away, unmatched tasks, and explicit requests. It reads Harness Principles, frames completion and rigor, designs independently-landable units, runs measured experiments, logs through Show Me Your Work, and verifies the final product. Host todo tooling is optional; unavailable skills and capabilities are reported.

Show Me Your Work owns decision-trail formatting and auditing. Its template and Bash helper preserve the pinned source. Logs stay local unless reviewers need a committed trail. Audits use host-provided access to the current run, and separate reviewers inspect the trail and transcript. Missing tools or transcripts leave review incomplete; unavailable model diversity is reported. Attention replies name the actual reviewer and any flags or limitations.

Performance work owns the measurement story and ties every fix to measured evidence. Benchmark Checklist vets numbers before reporting or acting on them, using host-appropriate measurement tools, repeatability checks, and explicit verdicts. Its Explain the Number dependency is included as a separate skill and resolves by installed name. The bundled Perf issue playbook grounds trace-supported hypotheses, delegates a scoped fix using host model configuration, verifies each attempt, compares actual artifacts, and reports baseline, result, delta, and artifact path. Its eight strategy families guide hypotheses only when the trace supports them. The bundled Hillclimb playbook sustains improvement of one metric using an agreed target and attempt floor, a sensitivity-proven frozen harness, isolated delegated attempts, measured keep-or-revert decisions, and a Show Me Your Work trail. Unattended work uses only supported host wake mechanisms; missing capability is reported.

Runtime forensics diagnoses live symptoms using captured artifacts, host-appropriate instrumentation, and source attribution. Trace forensics analyzes an existing capture in a queryable form, resolves source symbols, and reports hypotheses when paired-capture confirmation is unavailable. SQLite is optional. Both deliver cited diagnoses; fixes require a request and use Bug fix or Perf issue. Missing tools and evidence are reported.

Prototype answers a concrete design or behavioral decision using an isolated disposable artifact. It explores labeled alternatives, observes them on the matching surface, and presents evidence, tradeoffs, and a recommendation. The chosen direction goes to Feature or Architect for production implementation.

Visual parity captures a baseline before migration, keeps it and its harness fixed, and verifies each component through matching-surface image comparison. Every nonzero pixel difference fails. Shared primitives migrate first; isolated component owners iterate until zero difference or a reported blocker. Baseline concerns stop for clarification. PR delivery follows task authorization.

Verification routes to five separate principles: direct proof on the real artifact, reproduction and root-cause fixes, checked incremental units, behavior-focused tests, and explained measurements. Correct boundary validation is retained; tests are judged against plausible defects rather than an undefined-return heuristic. Agent-evaluation instructions are excluded.

Delegation uses host tools, asynchronous execution when supported, file pointers, configured role models and difficulty tiers, and parent inheritance when no role is configured. The parent reviews actual work and owns the result. Fresh delegates receive consolidated scope; reuse is reserved for costly live state. Missing capabilities and model diversity are disclosed. Guard the Context Window, Never Block on the Human, and Encode Lessons in Structure are separate skills. Execution remains authorized, and task/project notes follow host rules.

Autonomy proceeds on authorized work without routine permission pauses. Existing authorization persists; consequential actions ask when authorization is missing or the host requires approval. Explicit persistence requests continue until completion, explicit pause, or a concrete blocker requiring input. Product scope and permissions remain bounded, and recommendations retain candid judgment. Autonomous run uses supported host wake mechanisms; installation does not provide scheduling infrastructure.

Babysit starts on request and works the lowest unmerged PR until merge-ready, using explicit status, review-only, background, or drive modes. Its triage reference tests findings against current evidence; replies and resolutions follow task authorization. Shipping independently verifies each PR against its parent, rechecks patch identity, and lands only the uninterrupted passing run, one bottom PR at a time. Both use gh and host watch/wake capabilities; missing continuous monitoring is disclosed.

Autonomous run drives one explicitly requested task toward a checkable predicate with measured iterations and a decision trail. Host event watches or heartbeats provide supported wakeups; unavailable unattended execution is disclosed. Related fixes stay authorized, independent fixes use authorized PRs, and unrelated discoveries become follow-ups. Explicit pause or genuine blockers stop the run without weakening the predicate.

Orchestrate coordinates standing programs with scoped agents, recoverable completion batches, exact-commit verification, and computed PR frontiers. Its bundled Python helper maintains portable state without installing dependencies. Autopilot-full gives each independent PR an owner through authorized merge; Autopilot-stack delivers a verified chain for operator landing. Both use the separate Swarm skill and supported host audits, with missing capabilities disclosed.

Multi-phase plans retain per-PR evidence checklists with scenario-driven applicable verification and explicit operator gates. The bundled Node checker validates their structure. Session pickup preserves completed work while reconciling current state; explicit pauses checkpoint task-owned changes, while compaction keeps execution active. Cleanup uses a bundled read-only Python audit and confirms ownership, inactivity, merge or abandonment, and file preservation before removing exact candidates.

## Add a skill

Follow [the adaptation workflow](docs/adapting-skills.md). Each skill has runtime instructions and a separate registry entry. Review records are optional for consequential upstream adoption decisions. Templates are inactive until you customize and place them in their intended locations.

## Track upstream sources

[The maintenance index](registry/skills.json) records both adaptations and inspirations, with multiple sources supported per skill. Each source tracks its baseline, last reviewed commit, and last incorporated commit. [Registry conventions](docs/registry.md) describe these fields and the update review process. Automated monitoring is not implemented yet.

## Installation and releases

Use the Skills CLI directly against this private repository; no separate skills.sh publication or custom installer is required. [Installation instructions](docs/installation.md) cover project and global scopes, updates, release pins, and rollback.

```sh
npx skills@1.7.0 add jaki95/agent-harness --list
```

Install the available skill from approved changes on `main`, running inside your target project:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill grill-me --agent codex
```

Follow [the release workflow](docs/versioning.md) to publish a validated collection. Repository checks verify structure and packaging, not agent behavior. Releases are manually triggered, validated, and tagged; the workflow rejects empty collections and existing tags.

Keep reusable behavior here and project context in project repositories. See [portability conventions](docs/portability.md) for the distribution boundary.
