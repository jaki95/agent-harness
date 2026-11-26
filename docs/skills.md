# Skill catalog

Harness is the working mode. Install the dependencies for the Harness workflows you use. Independent skills sit outside the Harness install list. See the [Harness install commands](installation.md#install-harness) and [host requirements](installation.md#check-prerequisites-for-the-work-you-want-to-do).

| Skill | Harness role | Purpose |
| --- | --- | --- |
| [grill-me](../skills/grill-me/SKILL.md) | Independent | Stress-test a plan, decision, or idea in rounds of questions |
| [wayfinder](../skills/wayfinder/SKILL.md) | Independent | Plan large efforts as linked decision tickets; requires companion skills and tracker setup described in the [installation notes](installation.md#check-prerequisites-for-the-work-you-want-to-do) |
| [retro](../skills/retro/SKILL.md) | Independent | Review a coding session and propose environment improvements by severity; see the [host and dependency requirements](installation.md#check-prerequisites-for-the-work-you-want-to-do) |
| [statechart](../skills/statechart/SKILL.md) | Independent | Model and check state transitions, then draw a statechart |
| [correct](../skills/correct/SKILL.md) | Independent | Turn recurring mistakes into enforceable checks |
| [maintain-verification-skill](../skills/maintain-verification-skill/SKILL.md) | Independent | Check a project's verification skill against source and live behavior |
| [blast-radius](../skills/blast-radius/SKILL.md) | Independent | Investigate downstream risks and prove key safety assumptions |
| [harness](../skills/harness/SKILL.md) | Working mode | Working mode with selective explanations, milestone updates, and routed principles and playbooks |
| [unslop](../skills/unslop/SKILL.md) | Dependency | Remove AI writing patterns while preserving meaning |
| [technical-writing](../skills/technical-writing/SKILL.md) | Dependency | Write docs, PR descriptions, and commit messages with the original writing guidance |
| [deslop](../skills/deslop/SKILL.md) | Dependency | Remove unnecessary code patterns and match local style with minimal edits |
| [interrogate](../skills/interrogate/SKILL.md) | Dependency | Challenge changes with independent reviewers, then verify executable repros or static defects without applying fixes |
| [show-me-your-work](../skills/show-me-your-work/SKILL.md) | Dependency | Keep and audit a decision trail with evidence, separate review, and explicit limitations |
| [benchmark-checklist](../skills/benchmark-checklist/SKILL.md) | Dependency | Vet performance measurements and report repeatable, correct, relevant results |
| [figure-it-out](../skills/figure-it-out/SKILL.md) | Dependency | Design and execute a task-specific workflow with measured experiments and a decision trail |
| [no-comments](../skills/no-comments/SKILL.md) | Dependency | Review scoped comments and suppressions, preserve unresolved rationale, and fix accepted findings |
| [control-ui](../skills/control-ui/SKILL.md) | Dependency | Drive and inspect browser or Electron UIs with local automation and captured evidence |
| [control-cli](../skills/control-cli/SKILL.md) | Dependency | Exercise interactive CLIs and TUIs with repeatable terminal input and transcripts |
| [create-verification-skill](../skills/create-verification-skill/SKILL.md) | Independent | Generate a Codex project skill for app verification, with a maintained feature map in `.agents/skills/verify-<slug>/` |
| [how](../skills/how/SKILL.md) | Dependency | Answer narrow code questions directly and trace complex architecture with independent explorers |
| [why](../skills/why/SKILL.md) | Dependency | Investigate historical rationale across available evidence sources with calibrated confidence |
| [architect](../skills/architect/SKILL.md) | Dependency | Ground, compare, and synthesize designs before implementation, with an opt-in checkpoint |
| [swarm](../skills/swarm/SKILL.md) | Dependency | Run independent coverage or race workers and consolidate evidence with explicit gaps |
| [arena](../skills/arena/SKILL.md) | Dependency | Compare independent candidates with a cross-judge, synthesize one artifact, and verify it |
| [principle-laziness-protocol](../skills/principle-laziness-protocol/SKILL.md) | Dependency | Simplify code and unnecessary indirection without a fixed layer limit |
| [principle-foundational-thinking](../skills/principle-foundational-thinking/SKILL.md) | Dependency | Choose data structures before logic and make necessary shared-state ownership explicit |
| [principle-redesign-from-first-principles](../skills/principle-redesign-from-first-principles/SKILL.md) | Dependency | Integrate requirements as foundational design decisions and deliver the redesign incrementally |
| [principle-attack-the-premise](../skills/principle-attack-the-premise/SKILL.md) | Dependency | Test assumptions shared by failed fixes with evidence suited to the symptom |
| [principle-subtract-before-you-add](../skills/principle-subtract-before-you-add/SKILL.md) | Dependency | Remove unnecessary complexity before building on the simpler base |
| [principle-minimize-reader-load](../skills/principle-minimize-reader-load/SKILL.md) | Dependency | Reduce layers and hidden state so readers can trace code quickly |
| [principle-outcome-oriented-execution](../skills/principle-outcome-oriented-execution/SKILL.md) | Dependency | Converge planned migrations on the target architecture with explicit verification boundaries |
| [principle-experience-first](../skills/principle-experience-first/SKILL.md) | Dependency | Prioritize a polished core experience for consumers and maintainers |
| [principle-exhaust-the-design-space](../skills/principle-exhaust-the-design-space/SKILL.md) | Dependency | Compare distinct prototypes before committing to an uncertain design |
| [principle-build-the-lever](../skills/principle-build-the-lever/SKILL.md) | Dependency | Build the smallest rerunnable tool that performs or proves non-trivial work |
| [principle-model-the-domain](../skills/principle-model-the-domain/SKILL.md) | Dependency | Encode domain rules in structures that reduce scattered conditions and invalid states |
| [principle-boundary-discipline](../skills/principle-boundary-discipline/SKILL.md) | Dependency | Validate at system boundaries and keep business logic pure |
| [principle-type-system-discipline](../skills/principle-type-system-discipline/SKILL.md) | Dependency | Use types to prevent invalid states, mismatched values, and unhandled variants |
| [principle-make-operations-idempotent](../skills/principle-make-operations-idempotent/SKILL.md) | Dependency | Make retries and partial failures converge to the intended state |
| [principle-migrate-callers-then-delete-legacy-apis](../skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md) | Dependency | Migrate internal callers and remove legacy APIs in the same refactor |
| [principle-separate-before-serializing-shared-state](../skills/principle-separate-before-serializing-shared-state/SKILL.md) | Dependency | Separate independent write targets before serializing necessary shared state |
| [principle-prove-it-works](../skills/principle-prove-it-works/SKILL.md) | Dependency | Verify real outputs with direct observation and repeatable evidence |
| [principle-fix-root-causes](../skills/principle-fix-root-causes/SKILL.md) | Dependency | Reproduce and fix the mechanism while retaining corrective boundary validation |
| [principle-sequence-verifiable-units](../skills/principle-sequence-verifiable-units/SKILL.md) | Dependency | Verify each small unit and order delivery so the sequence demonstrates correctness |
| [principle-test-behavior-not-implementation](../skills/principle-test-behavior-not-implementation/SKILL.md) | Dependency | Assert observable behavior and scrutinize tests against plausible defects |
| [principle-explain-the-number](../skills/principle-explain-the-number/SKILL.md) | Dependency | Establish measurement limiters, eliminate misleading results, and retain evidence |
| [principle-guard-the-context-window](../skills/principle-guard-the-context-window/SKILL.md) | Dependency | Keep bulky material out of the parent context with bounded scope and host-aware delegation |
| [principle-never-block-on-the-human](../skills/principle-never-block-on-the-human/SKILL.md) | Dependency | Proceed on authorized reversible work while retaining human product direction |
| [principle-encode-lessons-in-structure](../skills/principle-encode-lessons-in-structure/SKILL.md) | Dependency | Turn recurring corrections into enforceable mechanisms and authorized task notes |
