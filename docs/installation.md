# Installation and upgrades

## Requirements and current status

Use Node 22.20 or newer, npm/npx, Git, and access to the private `jaki95/agent-harness` GitHub repository. The tested Skills CLI version is `1.7.0`; commands below pin the installer independently of the harness version. Existing Git credentials, an authenticated GitHub CLI, or SSH can provide repository access. No public directory listing is required.

The collection includes `grill-me`, `harness`, `unslop`, `technical-writing`, `deslop`, `no-comments`, `interrogate`, `show-me-your-work`, `figure-it-out`, `benchmark-checklist`, `how`, `why`, `architect`, `arena`, `swarm`, `control-ui`, `control-cli`, `principle-laziness-protocol`, `principle-foundational-thinking`, `principle-redesign-from-first-principles`, `principle-attack-the-premise`, `principle-subtract-before-you-add`, `principle-minimize-reader-load`, `principle-outcome-oriented-execution`, `principle-experience-first`, `principle-exhaust-the-design-space`, `principle-build-the-lever`, `principle-model-the-domain`, `principle-boundary-discipline`, `principle-type-system-discipline`, `principle-make-operations-idempotent`, `principle-migrate-callers-then-delete-legacy-apis`, `principle-separate-before-serializing-shared-state`, `principle-prove-it-works`, `principle-fix-root-causes`, `principle-sequence-verifiable-units`, `principle-test-behavior-not-implementation`, `principle-explain-the-number`, `principle-guard-the-context-window`, `principle-never-block-on-the-human`, and `principle-encode-lessons-in-structure`. The following command lists skills at the remote revision, so unmerged local changes are not available through `main` yet:

```sh
npx skills@1.7.0 add jaki95/agent-harness --list
```

The `grill-me` examples on `main` are available now. Release-tag examples remain illustrative until those versions are published.

## Personal installation: follow approved changes on main

Install globally for your personal Codex setup:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill grill-me --agent codex --global
npx skills@1.7.0 update grill-me --global
```

For Harness's full workflow, select the mode, both writing skills, Deslop, No-comments, Interrogate, Show Me Your Work, Figure It Out, Benchmark Checklist, How, Why, Architect, Arena, Swarm, Control UI, Control CLI, and its engineering, verification, delegation, and meta principles. The CLI does not install other skills automatically.

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill harness unslop technical-writing deslop no-comments interrogate show-me-your-work figure-it-out benchmark-checklist how why architect arena swarm control-ui control-cli principle-laziness-protocol principle-foundational-thinking principle-redesign-from-first-principles principle-attack-the-premise principle-subtract-before-you-add principle-minimize-reader-load principle-outcome-oriented-execution principle-experience-first principle-exhaust-the-design-space principle-build-the-lever principle-model-the-domain principle-boundary-discipline principle-type-system-discipline principle-make-operations-idempotent principle-migrate-callers-then-delete-legacy-apis principle-separate-before-serializing-shared-state principle-prove-it-works principle-fix-root-causes principle-sequence-verifiable-units principle-test-behavior-not-implementation principle-explain-the-number principle-guard-the-context-window principle-never-block-on-the-human principle-encode-lessons-in-structure --agent codex --global
npx skills@1.7.0 update harness --global
npx skills@1.7.0 update unslop --global
npx skills@1.7.0 update technical-writing --global
npx skills@1.7.0 update deslop --global
npx skills@1.7.0 update no-comments --global
npx skills@1.7.0 update interrogate --global
npx skills@1.7.0 update show-me-your-work --global
npx skills@1.7.0 update figure-it-out --global
npx skills@1.7.0 update benchmark-checklist --global
npx skills@1.7.0 update how --global
npx skills@1.7.0 update why --global
npx skills@1.7.0 update architect --global
npx skills@1.7.0 update arena --global
npx skills@1.7.0 update swarm --global
npx skills@1.7.0 update control-ui --global
npx skills@1.7.0 update control-cli --global
npx skills@1.7.0 update principle-laziness-protocol --global
npx skills@1.7.0 update principle-foundational-thinking --global
npx skills@1.7.0 update principle-redesign-from-first-principles --global
npx skills@1.7.0 update principle-attack-the-premise --global
npx skills@1.7.0 update principle-subtract-before-you-add --global
npx skills@1.7.0 update principle-minimize-reader-load --global
npx skills@1.7.0 update principle-outcome-oriented-execution --global
npx skills@1.7.0 update principle-experience-first --global
npx skills@1.7.0 update principle-exhaust-the-design-space --global
npx skills@1.7.0 update principle-build-the-lever --global
npx skills@1.7.0 update principle-model-the-domain --global
npx skills@1.7.0 update principle-boundary-discipline --global
npx skills@1.7.0 update principle-type-system-discipline --global
npx skills@1.7.0 update principle-make-operations-idempotent --global
npx skills@1.7.0 update principle-migrate-callers-then-delete-legacy-apis --global
npx skills@1.7.0 update principle-separate-before-serializing-shared-state --global
npx skills@1.7.0 update principle-prove-it-works --global
npx skills@1.7.0 update principle-fix-root-causes --global
npx skills@1.7.0 update principle-sequence-verifiable-units --global
npx skills@1.7.0 update principle-test-behavior-not-implementation --global
npx skills@1.7.0 update principle-explain-the-number --global
npx skills@1.7.0 update principle-guard-the-context-window --global
npx skills@1.7.0 update principle-never-block-on-the-human --global
npx skills@1.7.0 update principle-encode-lessons-in-structure --global
```

Harness can also be installed alone:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill harness --agent codex --global
```

Harness resolves `unslop`, `technical-writing`, `deslop`, `no-comments`, `interrogate`, `show-me-your-work`, `figure-it-out`, `benchmark-checklist`, `control-ui`, `control-cli`, `how`, `why`, `architect`, `arena`, `swarm`, `principle-laziness-protocol`, `principle-foundational-thinking`, `principle-redesign-from-first-principles`, `principle-attack-the-premise`, `principle-subtract-before-you-add`, `principle-minimize-reader-load`, `principle-outcome-oriented-execution`, `principle-experience-first`, `principle-exhaust-the-design-space`, `principle-build-the-lever`, `principle-model-the-domain`, `principle-boundary-discipline`, `principle-type-system-discipline`, `principle-make-operations-idempotent`, `principle-migrate-callers-then-delete-legacy-apis`, `principle-separate-before-serializing-shared-state`, `principle-prove-it-works`, `principle-fix-root-causes`, `principle-sequence-verifiable-units`, `principle-test-behavior-not-implementation`, `principle-explain-the-number`, `principle-guard-the-context-window`, `principle-never-block-on-the-human`, and `principle-encode-lessons-in-structure` by name through the host's skill catalog. Their installation directories can differ from Harness's directory. If a routed skill is unavailable, Harness reports its name and continues with its own communication rules. Bundled playbooks remain available. The [source collection](https://github.com/jaki95/agent-harness) identifies where the separate skills can be obtained; it does not load or install them automatically.

How and Why require host subagent tools. How uses one explainer for a narrow question, or two to four explorers followed by an explainer for a complex question. Why defaults to parallel investigators for available evidence categories followed by a synthesizer. It requires local git history and `gh` access for repository discussions; connected MCP sources are optional and missing sources are recorded as coverage gaps. Delegates use existing host role models or inherit the parent model. Host concurrency limits determine scheduling. Missing tools and denied access are reported; skipped steps are not presented as completed. The installer does not provide delegation tools, connect services, or configure models.

The bundled Feature playbook begins with How over the affected subsystem and Architect for parallel design exploration. Before delegating implementation, record all four throughput-checkpoint items in the host todo list or the task plan, keeping nonapplicable dimensions with `n/a` and a reason. Feature implementation is delegated even for small changes, using an existing configured feature model or parent inheritance. The delegate receives file scope, a domain data shape, and success criteria. Multiple valid implementation shapes use Arena. A child agent forbidden to spawn owns its code directly while preserving separate review. Feature verification runs on the matching surface; inconclusive or wrong-surface results are flagged and do not count as a pass. Feature delivery builds, verifies, and commits each small unit before the next, then organizes small ordered commits and stacked follow-ups. Contested feature designs require Interrogate before shipping; task-authorized PR preparation or creation follows the bundled Opening a PR playbook. One owner handles coupled feature or migration work and fans out after the blocking phase. Parent-level fan-out is for independent artifacts. Checkpoints are rewritten at phase boundaries, and new work goes to a fresh owner rather than chained interrupts. Architect and Arena can be invoked directly. They require host delegation tools and use a todo list when the host provides one. Arena defaults to three independent parent-model candidates and an inherited cross-judge; configured host runner and judge models take precedence. Architect uses its own configured roster when available and requires at least two structurally distinct completed designs before synthesis. Separate named skills provide grounding and verification when installed; missing skills are reported without claiming their rules were applied.

Control UI and Control CLI retain their pinned upstream instructions. They reuse repository-native test or demo harnesses first. Control UI needs a running app and available browser automation or a Chromium debugging connection. Control CLI needs terminal access and an available harness such as tmux or a PTY helper. Their packages provide instructions and examples, not browser binaries, automation dependencies, or terminal tools.

No-comments requires host delegation tools. Its Comment Sicko prompt is bundled inside the package; no Cursor custom agent registration is required. The reviewer uses existing host model configuration or inherits the parent model. How, Why, and Architect are resolved by installed skill name when needed. The reviewer and parent retain unresolved comments, and constraint comments remain until an approved replacement is verified.

Interrogate requires host delegation and repository read/search tools. Reviewers are read-only and receive the same prompt and rubric. It uses the host reviewer roster, or three independent parent-model reviewers when none is configured. It reports missing model diversity and rejected-model fallbacks without opening a maintenance PR. The lead produces a verdict; the skill does not apply fixes automatically.

The bundled Bug fix playbook requires host delegation tools and access to the matching control surface. The lead reproduces and verifies the bug while delegating investigation and implementation. The fix agent uses an existing configured bug-fix model or inherits the parent model. Stubborn investigations continue an evidence-driven hypothesis loop until the mechanism is confirmed or a concrete blocker prevents progress. Persistent goal modes are not required. The `tdd` and `principle-sequence-verifiable-units` references resolve by installed skill name. Sequence Work into Verifiable Units is included; `tdd` is not included in this collection. Missing skills are reported without claiming their instructions were applied.

Show Me Your Work can be invoked directly or routed by name. Its log needs filesystem access, and its unchanged bundled helper needs Bash and standard shell utilities. Logs remain local by default and are committed only when a reviewer needs the trail. Auditing requires host-provided access to the current run's transcript; separate trail review also requires delegation. Missing transcript or delegation access leaves review incomplete. A different model family is used when available; an available separate reviewer otherwise reports missing diversity. Attention replies name the actual reviewer and report incomplete review rather than claiming a pass. Unslop and Encode Lessons in Structure are included as separate skills and resolve by installed name; missing skills are reported. The installer supplies the instructions, template, and helper, not host transcripts, delegation tools, or models.

Figure It Out can be invoked directly or routed for large migrations, ambitious multi-part changes, work reviewed after stepping away, unmatched tasks, and explicit requests. It reads the installed Harness Principles by name before framing completion, quantified scope, rigor, and a long-run checkpoint. It designs independent units, captures the original verification baseline, runs per-unit experiments with judging, logs through Show Me Your Work, and verifies the final product. Host todo tooling is optional, with the same ordered items in a task plan otherwise. Filesystem, read/search, measurement, and delegation capabilities are host requirements. Missing tools or named skills are reported without claiming affected steps ran.

Benchmark Checklist can be invoked directly or routed for measured performance numbers. It requires host execution, filesystem, system-monitoring, and profiling capabilities. System load, core counts, and profiling use host-appropriate tools; source commands are examples. Missing tools or access are reported without claiming checks ran, and missing required evidence leaves a comparison inconclusive. The `principle-explain-the-number` dependency is included as a separate skill and resolves by installed name. The installer does not supply measurement tools or named dependencies. Perf issue and Hillclimb are bundled with Harness.

The bundled Perf issue playbook requires host read/search, measurement, profiling, filesystem, and delegation tools and access to the matching control surface. Baseline and subsequent measurements use Benchmark Checklist; How grounds trace-supported hypotheses, and Architect explores fixes crossing a function boundary. Implementation uses the configured host performance model or parent inheritance. Each attempt is verified before the next, artifacts are compared, and missing capabilities or inconclusive results are reported without claiming a pass. PR work follows task authorization and the bundled Opening a PR playbook.

The bundled Hillclimb playbook requires Git and host read/search, filesystem, measurement, and delegation tools. It agrees a reproducing workload, one metric, a target, and a minimum-attempt predicate, then freezes a sensitivity-proven measurement harness and records a baseline and green regression checks. Scoped delegates use the configured host hillclimb model or parent inheritance; independent hypotheses use isolated worktrees. Each attempt is measured, checked, and kept or reverted before proceeding. Show Me Your Work owns the canonical log and commit policy, with linked attempt evidence local and uncommitted by default. PR work follows task authorization. Guard the Context Window is included as a separate skill and resolves by installed name. Missing skills or capabilities are reported without claiming affected steps ran. Unattended runs borrow only the supported host watch/wake mechanism from Autonomous run, keeping Hillclimb's own stopping rule.

The bundled Runtime forensics playbook requires access to the matching live surface and host read/search, filesystem, profiling, live-instrumentation, and delegation tools. CDP is one instrumentation option. Trace forensics requires filesystem, read/search, format-appropriate parsing and query tools, and delegation for large artifacts. Existing captures are analyzed without rerunning the workload; SQLite is optional. Both map findings to source and report evidence gaps without claiming confirmation. They deliver diagnoses, with fixes only when requested. Both use the included Guard the Context Window skill by installed name. The installer supplies the playbooks, not instrumentation or parsing tools.

The bundled Prototype playbook requires host filesystem, execution, reference-search, and matching control tools. It builds a disposable artifact in isolated scratch space, compares labeled alternatives, and observes them on their actual surface. Missing tools or access are reported without claiming observation occurred. Exhaust the Design Space and Architect resolve by installed skill name; Feature is linked inside Harness. The installer provides the playbook, not a browser, dev server, or reference-search service.

The bundled Visual parity playbook requires Git and host filesystem, execution, image-comparison, delegation, and matching control tools. Capture and freeze the baseline harness before migration; missing baselines or comparisons cannot support a parity claim. Shared primitives migrate before isolated component work. Each component must reach zero pixel difference, or report a concrete blocker without claiming a pass. Baseline concerns stop for clarification. Named principles resolve through the host catalog; Opening a PR is bundled and follows task authorization. The installer provides instructions, not rendering or image-comparison tools.

The bundled Refactoring playbook requires Git and host read/search, verification, and delegation tools. It captures current behavior before changing structure, designs a simpler shape, delegates scoped mechanical edits using an existing configured refactoring model or parent inheritance, proves equivalence on the real artifact, and organizes small ordered passing commits. Large or cross-cutting work uses Figure It Out. PR preparation or creation follows task authorization.

The verification principles are included as separate skills and resolve through the host catalog. Their checks need the host or project tools for the actual artifact, test interface, or measurement; installation does not supply those tools. Never Block on the Human and Encode Lessons in Structure are included as separate skills and resolve by installed name. Missing skills are reported without claiming their instructions were applied. The Skills CLI does not install those dependencies automatically.

Harness subagents use host delegation bindings, background or asynchronous execution when supported, file pointers, role-appropriate tool permissions, existing model configuration, and parent inheritance. Configured role overrides and difficulty tiers take precedence over inherited defaults. Routed workflows retain their roles and reviewers. The parent inspects actual work, owns the result, and prefers fresh delegates with consolidated scope; reuse is for costly state or running processes. Missing tools, model fallbacks, and unavailable diversity are reported. The installer does not add a Cursor wrapper, register custom agents, configure models, or provide delegation tools. Never Block on the Human applies only to authorized execution; Encode Lessons in Structure uses authorized task/project notes, with personal-memory updates governed by host and user rules.

Core Harness Autonomy uses available host tools within current task authorization and host permissions. Routine execution proceeds without repeated confirmation; consequential actions require input only when authorization is missing or the host requires approval. Explicit persistence requests continue until completion, explicit pause, or a concrete blocker requiring input. Installation does not grant external-action permissions, enable a native goal mode, or install scheduling infrastructure. Autonomous run uses only supported host watch/wake capabilities.

Babysit and Shipping are bundled with the review-triage reference. They require Git, authenticated gh access, project tests/builds, and host watch or wake capabilities for sustained monitoring. Shipping also requires independent host delegates and matching control tools. Babysit ends at merge-ready; task-authorized Shipping confirms each bottom PR actually merged before advancing. Review replies, resolutions, verifier posts, follow-up PRs, and CI retriggers follow task authorization. Missing delegation leaves verification incomplete; missing sustained monitoring is reported without claiming a live watcher. The installer does not supply a watcher script, Cursor cloud agents, scheduling infrastructure, or GitHub credentials.

The bundled Autonomous run playbook requires the host tools for execution, filesystem access, verification, and any delegation the task needs. Event watches or heartbeats use supported host wake mechanisms within task authorization; missing unattended execution is reported without claiming an active watcher. Sequence Work into Verifiable Units and Show Me Your Work resolve by installed name. The run retains its completion predicate, handles related authorized fixes, records unrelated follow-ups, and stops on explicit pause or genuine blockers. The installer does not supply a scheduler or turn on a native goal mode.

Orchestrate and both Autopilot playbooks require host delegation, Git, authenticated gh, project verification/control tools, and supported wake mechanisms for unattended audits. Swarm is a separately selected dependency; host model configuration or parent inheritance and concurrency limits govern its workers. Missing tools, model diversity, or scheduling are reported as incomplete capability. Orchestrate additionally bundles `scripts/orch.py` inside Harness, requiring Python 3.10+ and a local filesystem with process locking. It installs no packages. Invoke it from its installed package location with an explicit authorized store directory; read the bundled orchestration-store contract before initialization. It maintains plain records, recoverable inbox batches, exact-head verdicts, and gh-derived scoped linear frontiers. Multiple stacks have separate frontier stores. Autopilot-full merges only with task authority and a clean parent verdict; Autopilot-stack leaves landing to the operator. The installer supplies no agent runtime, credentials, or scheduler.

The bundled Multi-phase or multi-PR plan playbook delivers a plan and waits for explicit execution authorization. Its `scripts/check-plan.mjs` checker requires Node 22.20+ and no third-party packages. Verification retains unit, live, and perf sections with scenario-driven lane counts, exact-head evidence, and concrete reasons for nonapplicable checks; missing tools remain incomplete. The checker validates structure and does not prove evidence or applicability. Interaction review retains screenshots and video before operator landing. Named writing, exploration, control, and Swarm skills resolve through the host catalog.

Session pickup needs accessible current-project history, saved task state, and Git; missing history is disclosed. Pause safely needs authorized filesystem/Git access and supported cancellation, stages only task-owned changes, and saves a resume note in an authorized location. It activates only on an explicit pause; compaction alone continues the task.

Worktree and simulator cleanup bundles `scripts/worktree-audit.py` and its runtime contract. The audit requires Python 3.10+, filesystem access, and Git with NUL-delimited porcelain worktree listings. Optional PR reads use authenticated gh; allocated-size scans are opt-in. It fetches and deletes nothing and installs no packages. Supply current-project host ownership and activity evidence by explicit usage-file argument; absent or stale evidence holds candidates. Tracked, untracked, and ignored content require preservation review, closed PRs do not prove merge, and primary/invocation or active worktrees stay held. Deletion, simulator IDs, and cache paths follow the confirmed cleanup scope and task authorization. The installer supplies instructions and a read-only helper, not simulator tools or host history access.

The bundled Opening a PR playbook requires Git and authenticated GitHub CLI (`gh`) access to the target repository. PR creation follows task authorization. The playbook uses `gh` for PR operations and host tracking tools to register or attach PR URLs when supported or required. Opening a PR reports its URL and continues the build; a separate monitoring pass waits for a user request after the whole stack exists. An Autopilot owner's lifecycle brief assigns its own Babysit loop after the code-ready report.

Direct technical-writing calls locate and read the installed Unslop skill by name, without requiring Harness or automatic skill injection. If Unslop cannot be located or read, technical writing reports it as unavailable and uses its own rules. Harness follows bundled playbook steps directly when the host has no todo-list tool.

For other supported tools, change `--agent`. For project-local installation, run inside the project and omit `--global`; use `--project` on the update command. The CLI uses symlinks to a canonical installed copy by default; `--copy` selects independent copies where preferred.

Select skill names explicitly so you control what is installed or updated. Make edits in the harness source repository, then distribute them through the CLI. An update can replace installed files, including edits made directly to those files.

## Work projects: pin a release

After a real `v0.1.0` release exists, run inside the consuming project:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#v0.1.0' --skill grill-me --agent codex --copy
```

Commit `skills-lock.json` and the generated project skill files so the project records its selection. Review the consuming project's diff before committing updates. Use `--agent` selections appropriate to that project; avoid a global installation for a project-specific pin.

## Explicit upgrade and rollback

Pinned refs are preserved by the CLI. `skills update` does not select the next release tag. To adopt a newer release, install explicitly from that tag:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#v0.2.0' --skill grill-me --agent codex --copy
```

To roll back, run the same command with the earlier tag and review the resulting files and lockfile. Upgrade commands target this harness repository, not the upstream authors recorded in the maintenance registry.

## Source and installation boundaries

The CLI distributes a skill's directory, including its runtime resources. It does not distribute sibling `registry/` or `reviews/` directories, or this repository's `AGENTS.md`. Top-level maintenance scripts require a repository clone. Keep scripts needed by an installed skill inside `skills/<name>/scripts/`.

Harness uses `policy.allow_implicit_invocation: false` in Codex. Invoke it as `$harness`. The routed writing, code cleanup, review, control, investigation, and engineering skills use `true`, so Codex can discover them when Harness routes to them. They can also be selected for their matching tasks outside Harness. This Codex policy is a deliberate adaptation of the upstream explicit-only settings. See [OpenAI's invocation-policy documentation](https://learn.chatgpt.com/docs/build-skills#optional-metadata).

Imported `disable-model-invocation: true` frontmatter is retained where present. Deslop, Control UI, and Control CLI retain their upstream default invocation metadata. Other hosts that honor it may require explicitly invoking the routed skills alongside Harness. Hosts that expose slash commands can use `/harness`. Cursor's `mode` and `reminder` metadata is retained but does not implement those native features in other hosts.

Our integration test verifies tagged installs and upgrades with disposable Git repositories. It installs all owned skills into one temporary project and Harness alone into another. It checks every installed runtime file against its source and verifies that the standalone package includes its playbooks and invocation policy, that bundled file references stay inside the package, and that separate routed skills are not installed automatically. It does not modify user-wide skill directories or publish local changes.

## References

- [Skills CLI v1.7.0 documentation](https://github.com/vercel-labs/skills/blob/v1.7.0/README.md)
- [Source ref parsing](https://github.com/vercel-labs/skills/blob/v1.7.0/src/source-parser.ts)
- [Update source and ref handling](https://github.com/vercel-labs/skills/blob/v1.7.0/src/update-source.ts)
- [Project lockfile](https://github.com/vercel-labs/skills/blob/v1.7.0/src/local-lock.ts)
