# Changelog

## Unreleased

- Registry validation rejects duplicate JSON object keys before parsing can discard provenance records.
- Add multi-phase planning, session pickup, explicit pause, and scoped cleanup, with an adaptive plan checker and portable read-only worktree audit.

- Add Orchestrate, both Autopilots, and Swarm with host delegation, gh, scoped verification, and a portable helper with recoverable inbox batches.

- Add Autonomous run with explicit predicates, supported host wake mechanisms, scoped mid-run fixes, per-iteration evidence, and Hillclimb wake-only composition.

- Add Babysit, Shipping, and review-triage guidance with gh-only monitoring, independent host verification, evidence-based CI classification, authorized review actions, and one-at-a-time stack landing.

- Add core Autonomy rules for authorized execution, persistent prior authorization, bounded long-run persistence, explicit blockers, and unchanged candid judgment.

- Add the delegation and meta principles and host-bound subagent rules, with configured role models, fresh-agent defaults, explicit capability gaps, authorized execution, and task/project note routing.

- Add five separately routed verification principles, with corrective boundary validation, plausible-defect test review, installed dependency names, and agent-evaluation scope excluded.

- Add the bundled Visual parity playbook with fixed pre-change baselines, zero-pixel-difference verification, isolated component owners, evidence-driven iteration, and authorized PR delivery.

- Add the bundled Prototype playbook for decision-first disposable experiments, labeled alternatives, matching-surface observations, and Feature or Architect handoff.

- Add bundled Runtime forensics and Trace forensics playbooks, with host-appropriate instrumentation, optional SQLite shaping, source attribution, explicit confidence, and diagnosis-only delivery.

- Add the bundled Hillclimb playbook and Perf issue route, with agreed targets, a frozen measurement harness, delegated keep-or-revert attempts, canonical Show Me Your Work logging, and authorized PR delivery.

- Add the bundled Perf issue playbook with vetted baseline and post-fix measurements, trace-supported strategy families, host model configuration, artifact comparison, and authorized PR delivery.

- Add the separate Benchmark Checklist skill with pinned measurement and reporting rules, host-appropriate monitoring and profiling tools, named dependency routing, and Codex discovery enabled.

- Harness owns the performance measurement story and ties every performance fix to measured evidence.

- Add the separate Figure It Out skill and bundled Refactoring playbook, with named routing, host tools and model configuration, optional todo tooling, and authorized PR delivery.

- Figure It Out verifies the whole result on the real product and encodes recurring corrections in gates, lint rules, checks, or scripts.

- Figure It Out routes its audit trail through Show Me Your Work and usually commits substantial-work trails for review alongside the diff.

- Add the separate Show Me Your Work skill with its pinned TSV template and Bash helper, host transcript access, separate-review fallbacks, and explicit Attention outcomes.

- Figure It Out uses VERIFIED, NOT VERIFIED, and INCONCLUSIVE verdicts, rejects inconclusive passes, and reports negative results.

- Figure It Out pairs delegated work with a judge, strengthens gamed contracts, and fixes faulty verification gates in separate changes.

- Figure It Out verifies artifacts instead of accepting self-reports and questions observation methods when checks pass too easily.

- Figure It Out treats each unit as a measured experiment, keeps advances, reverts failures, and verifies each unit before the next.

- Figure It Out executes concrete planned items under its loop rules and records decisions as each step lands, with a task-plan fallback for hosts without todo tooling.

- Figure It Out writes down its designed phase list as the workflow the human reviews.

- Figure It Out parallelizes across independent boundaries, isolates workers in separate worktrees or branches, and limits fan-out.

- Figure It Out explores irreversible designs through Architect and Arena, skips mechanical work with concrete structure, and avoids repeating Arena over settled designs.

- Figure It Out builds its verification harness before the work and captures the pre-change baseline for old-versus-new checks.

- Figure It Out designs atomic independently-landable units, addresses the riskiest unknown first, and puts scaffolding and verification before features.

- Figure It Out presents framing before long runs, continues authorized reversible work, and provides one checkpoint for runs lasting several hours.

- Figure It Out framing establishes a testable definition of done, quantified scope and blockers, and consequence-scaled rigor before starting the run.

- Figure It Out startup reads Harness Principles before its workflow phases and uses a task plan when the host has no todo-list tool.

- Harness routes large migrations, ambitious multi-part changes, work reviewed after stepping away, unmatched tasks, and explicit requests to the named Figure It Out skill.

- Harness refactoring replies include changed structure, the preserved behavior baseline, equivalence proof, reader-load changes, and shipped or reverted work, with no new behavior.

- Harness orders small refactoring commits as subtraction, reshape, and follow-on cleanup, with passing slices and the authorized Opening a PR workflow.

- Harness keeps refactors only when they reduce reader load somewhere and reverts those that do not.

- Harness proves unchanged refactoring behavior on the actual artifact, with output comparisons, baseline replay, or matching-surface smoke checks for larger reshapes.

- Harness refactors in small behavior-preserving steps, migrates all API callers before deleting old APIs in one wave, checks textual rename references, and delegates mechanical edits using host model configuration.

- Harness subtracts dead code and redundant structure before refactoring, ships the smallest change that reaches the target shape, and reverts speculative cleanup.

- Harness names the target module layout, types, and call graph before refactoring, with Architect exploration for targets crossing a function boundary.

- Harness names the missing domain structure before refactoring, retains clear local code, and requires fewer branches or invalid states rather than more indirection.

- Harness captures the current behavior contract with How and a test, snapshot, or equivalence harness before refactoring structure.

- Harness keeps refactoring behavior-preserving, splits discovered bugs and features into separate work, and routes named redesigns to Feature.

- Harness bundles the complete Feature workflow with a single owner for coupled work, phase-boundary checkpoints, and fresh owners for subsequent work.

- Harness requires Interrogate before shipping contested feature designs and uses the Opening a PR playbook for task-authorized PR work.

- Harness builds, verifies, and commits each small feature unit before the next, then organizes small ordered commits and stacked follow-up PRs.

- Harness keeps the Feature verification rule unchanged, requiring the matching surface and explicitly flagging inconclusive or wrong-surface results.

- Harness requires scoped delegation for feature implementation and Arena for multiple valid shapes, retaining the child-agent no-spawn exception and using host model configuration.

- Harness records all four Feature throughput-checkpoint items before delegation, with nonapplicable dimensions explained and a task-plan fallback when no todo-list tool exists.

- Harness begins every feature with How over the affected subsystem and Architect for parallel design exploration before implementation.

- Harness routes bug fixes through matching-surface reproduction, delegated investigation and implementation, runtime evidence, and its Opening a PR playbook. Investigation loops and model selection use host capabilities.

- Harness routes UI and CLI verification to separate Control UI and Control CLI skills with unchanged pinned upstream instructions and Codex discovery enabled.

- Harness bundles its PR policies in the Opening a PR playbook. PR creation reports the URL and continues the build; separate monitoring waits for a user request after the stack exists.

- Harness keeps narrow PRs and dependent base-branch stacks, with `gh` for creation, retargeting, readiness, and status checks.

- Harness uses `gh` for all PR operations and registers or attaches PR URLs with host tracking when supported or required.

- Harness uses GitHub CLI (`gh`) for forge operations throughout the PR workflow.

- Harness uses the upstream PR description format unchanged, with ordered headings, mandatory Scope, concise verification outcomes, and linked supporting evidence.

- Harness uses the upstream PR title rule unchanged, with Conventional Commit types and scopes, short imperative subjects, and no trailing period.

- Harness applies every technical-writing layer except Diátaxis, followed by Unslop, to PR titles, descriptions, and commit bodies.

- Harness uses the upstream PR commit policy unchanged, with frequent commits and small, ordered, independently landable commits before PR creation.

- Harness uses the upstream PR worktree rule unchanged, including isolated delegate worktrees and reset-based recovery.

- Interrogate provides read-only independent adversarial reviews and a lead verdict. Harness routes subagents preparing to open a PR through it. Unsupported models and reduced diversity are reported without opening a maintenance PR.

- Harness routes code through No-comments before submitting it for PR review. Its bundled reviewer and parent workflow retain unresolved comments and keep constraint comments until an approved replacement is verified.

- Harness routes code changes through Deslop before committing them for a PR; its pinned upstream SKILL.md is unchanged.

- Harness opens PRs ready for review, disables draft defaults, and verifies readiness before reporting it.

- Architect and Arena retain the upstream design and candidate-comparison workflows with host tools, optional todo lists, existing model configuration, full skill names, and the agreed Laziness rule.

- Harness includes the upstream Investigation playbook and separate How and Why skills, preserving their delegation patterns and evidence guidance with host tool bindings and existing model configuration.

- Harness routes to Separate Before Serializing Shared State with its pinned upstream SKILL.md unchanged.

- Harness routes to Migrate Callers Then Delete Legacy APIs with its pinned upstream SKILL.md unchanged.

- Harness routes to Make Operations Idempotent with its pinned upstream SKILL.md unchanged.

- Harness routes to Type System Discipline with its upstream rules unchanged and full names for its principle skill references.

- Harness routes to Boundary Discipline with its pinned upstream SKILL.md unchanged.

- Harness routes to Model the Domain under Architecture with its pinned upstream SKILL.md unchanged.

- Harness routes to Build the Lever with its upstream rules unchanged; cross-skill references use names.

- Harness routes to Exhaust the Design Space with its pinned upstream SKILL.md unchanged.

- Harness routes to Experience First with its pinned upstream SKILL.md unchanged.

- Harness routes to Outcome-Oriented Execution with its pinned upstream SKILL.md unchanged.

- Harness routes to Minimize Reader Load with its upstream rules and 30-second test unchanged; cross-skill references use names.

- Harness routes to Subtract Before You Add with its pinned upstream SKILL.md unchanged.
- Attack the Premise tests shared assumptions with diagnostic evidence suited to the symptom, retaining actor imbalance as an example rather than a mandatory census.
- Harness routes to Redesign From First Principles with its pinned upstream SKILL.md unchanged.
- Harness routes to the separate Foundational Thinking engineering skill, preferring isolated state and requiring explicit ownership and synchronization for necessary sharing.
- Harness routes to the separate Laziness Protocol engineering skill, with indirection judged by comprehension rather than a fixed three-file-or-layer limit.
- Codex can discover the routed Unslop and technical-writing skills through implicit invocation; Harness remains explicitly activated.
- Harness playbooks work without a todo-list tool; direct technical-writing calls discover and read Unslop by name with a missing-skill fallback.
- Removed evaluation records and their mandatory checker requirement; upstream review records are optional for consequential adoption decisions.

- Harness communication mode with separate Unslop and technical-writing skills and routed communication playbooks.
- Mode and explicit-only invocation metadata validation, with Codex invocation policy files.
- Temporary collection and standalone Harness installation checks for bundled playbooks and named writing dependencies.
- Added Matt Pocock's current `grilling` skill as `grill-me`, preserving its instructions and description verbatim with independent source tracking.
- Removed unrequested instruction rewrites; only the skill name and UI display name differ from the pinned upstream.
- Portable runtime skill structure and separate source-maintenance registry.
- Adaptation and optional upstream review templates.
- Pinned Skills CLI installation compatibility checks.
- Manual release workflow with version validation and release tags.

No versioned releases have been published yet.
