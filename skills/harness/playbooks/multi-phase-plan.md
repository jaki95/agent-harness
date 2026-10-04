### Multi-phase or multi-PR plan

**You own the plan, not the code. The plan is a checklist an owner runs box by box and the operator audits from the evidence.** The plan is the deliverable. Do not implement.

Use available host filesystem, Git, execution, delegation, and matching verification tools within task authorization and host permissions. Resolve named skills through Harness's catalog rules and bundled resources from its installed package. Report unavailable tools, records, controls, or access without claiming an affected step completed. The bundled plan checker requires Node 22.20+ and no third-party dependencies; the Markdown command validates structure. Its acceptance commands declare scenarios, capture project gates, and check current-head evidence per `../references/acceptance-record.md`. Missing delegation or checker access is reported without a completed-check claim.

1. When the change is one or two files with an obvious approach, skip the plan. Say so and stop.
2. Settle open questions by prototype before you write. Run `prototype.md` for each. Keep the branch, the SHA, and the screenshots for Appendix A. Ask the operator only about a product or preference call that no run can settle. Give options (the **principle-never-block-on-the-human** principle skill).
3. Explore through supported host delegation, with configured role models or parent inheritance and host concurrency limits, per Harness's Subagents section (the **principle-guard-the-context-window** principle skill). Each returns file pointers, conventions, test commands, and entry points. No inlined dumps.
4. Copy the skeleton below into the plan file and fill every placeholder. Unless the operator names a path, write the file under `docs/` in an authorized task or project location. Keep every heading and every sub-block in the order shown. One section per PR. One PR is one change with its own evidence (the **principle-sequence-verifiable-units** principle skill). Each PR names one committed acceptance manifest. Its owner declares every scoped outcome, scenario, pass predicate, project gate, required environment, and concrete nonapplicability before implementation or measurement. Put project-specific size and canonical-source rules in that manifest. Name the execution playbook in **How to read this**. Pick between `autopilot-full.md` and `autopilot-stack.md` per the rule at the end of `autopilot-stack.md`. A standing program takes `orchestrate.md`.
5. Read and apply **technical-writing** in full, then **unslop**. The body is one Diátaxis mode, how-to. Appendices hold explanation and reference. Each heading states the task or the finding. No long dashes. No mid-sentence colons.
6. Run `node <Harness-package>/scripts/check-plan.mjs <plan.md>` and fix every line it prints (the **principle-encode-lessons-in-structure** principle skill).
7. Hand back. Post the plan path and the script's output, then stop. Execution starts on the operator's explicit go, under the execution playbook the plan names.

**Verification.** Tests alone are not sufficient verification. A PR is verified only when its applicable unit, live, and perf checks have evidence, with a reason for each nonapplicable check. (the **principle-prove-it-works** skill). That sentence is the verification rule. Every verification block opens with it. Retain unit, live, and perf sections. A nonapplicable block states `N/A. <concrete reason>` after the rule and has no boxes; unavailable tools, unfinished work, or inconclusive results are not reasons to call a required check nonapplicable. Runnable behavior changes require live proof on the matching surface. Size live lanes around distinct scenarios and risks; state the positive lane count, the actual configured or inherited model, and why the coverage is sufficient. Each lane is one box with a concrete scenario, the artifact it saves, and its pass predicate. Use screenshots for visual observations and transcripts, logs, or other actual outputs for nonvisual surfaces. One lane is the **Regression lane against trunk.** It runs the same load-bearing scenario on trunk and head. If trunk does not have the feature, the lane records that fact and gates the behavior the diff adds plus the end state the user waits for instead of inventing a trunk result. When perf applies, comparable trunk and head scenarios must both produce the named metric. If trunk lacks the feature, isolate the work the diff adds and set an absolute budget for that work plus the end-to-end state the user waits for. Do not claim a ratio between unlike scenarios. The perf block names the metric, the interleaved probe, the trunk baseline measured first, and the rule with the number that fails. A PR that changes an interaction is review-gated. The operator reviews it in chat with screenshots and a video before merge. A PR that changes no interaction writes `**Review gate.** None. <PR id> is not review-gated.` and no boxes under it.

**Control skill.** Pick it by surface. Browser, Electron, and web UIs use **control-ui**. CLIs and TUIs use **control-cli**. Native mobile uses whatever simulator-driving skill the repo has. A PR that touches two surfaces gets lanes on both. A surface with no control skill is a risk in Appendix C, and its live block still names how each lane drives it.

````markdown
# <Program> plan

<Under ten lines. What changes, for whom, the rule the program enforces, and the PR ids in order.>

## How to read this

One box is one unit of work. Every box names the evidence that checks it. A nested box is a sub-step of the box above it. Check a box only when its evidence exists, a file, a log line, a screenshot, a test run, or a SHA. The body is a how-to. The appendices explain and record.

The program runs the selected playbook from the installed Harness package, `playbooks/<execution playbook>.md`. <Who merges, and which PR ids are the operator's items that stop at merge-ready.>

Tests alone are not sufficient verification. A PR is verified only when its applicable unit, live, and perf checks have evidence, with a reason for each nonapplicable check.

## Program checklist

### Arm the program

- [ ] State the protocol and this plan to the operator, then stop. Start execution only on the operator's explicit go.
- [ ] Read these from the installed Harness package or the host skill catalog at program start. Re-read them at every tick.
  - [ ] The selected execution playbook in the installed Harness package.
  - [ ] The installed **swarm** skill.
  - [ ] The installed matching control skill or named repository driver.
  - [ ] **Opening a PR** in the installed Harness package.
  - [ ] Each other named leaf skill the program uses, resolved through the host catalog.
- [ ] On the operator's go, arm an hourly audit tick with a supported host watch or wake mechanism and the tick prompt below. Never leave the cadence to memory. Disclose unavailable unattended execution without claiming an active hourly audit.
- [ ] Use this tick prompt, verbatim. "Re-read the execution playbook from its installed Harness package. Audit the operation against it and fix drift in this tick. Probe every active lane and inspect host status and the current operation when side effects are missing. Missing visible side effects alone does not prove a stall. Replace a confirmed failed or stuck lane promptly; confirm the old writer stopped before reusing its scope, or isolate the replacement. Then post a short status message to the operator in chat only when the audit found a tracked change that no earlier status message reported, such as a PR opened, a code-ready head, a round launched or closed, a verdict, a merge, a stuck agent and the action taken, a blocker added or cleared, or a decision only the operator can make. Name every such change and nothing else. Do not repeat a table, the merged list, or an unchanged blocker. If the audit found none, end the turn with no reply text. Either way, log this tick's row in your decision trail. The row names the items reported, or none."
- [ ] On the operator's hold or stand-down, send every owner a zero-writes order at once, request supported cancellation or interruption, and report unconfirmed stops.

### Spawn owners

- [ ] Spawn one owner per PR with the full lifecycle the execution playbook names.
- [ ] Follow this dependency graph. Start dependent work only after its parent merges, or base it on the parent branch when the execution playbook stacks.
  - [ ] <PR id> and <PR id> are independent and first. Both branch from `main`.
  - [ ] <PR id> after <PR id>.
- [ ] Hold the file boundaries. <PR id or class> touches only `<glob>`.
- [ ] Hold the review gate. <PR ids> change an interaction. They wait for the operator's review in chat with screenshots and a video before merge.

### PR mechanics, for every PR

- [ ] Use `gh` for every PR operation. Do not require Origin or Graphite.
- [ ] Open the PR ready, never draft, per **Opening a PR**. Use `gh pr create --base <base-branch>` and register or attach its URL through host tracking when supported or required. A stack child targets its parent branch.
- [ ] Before implementation or measurement, commit each PR's acceptance manifest and run `node <Harness-package>/scripts/check-plan.mjs acceptance declare <manifest.json>` per `references/acceptance-record.md` in the installed Harness package.
- [ ] Run the repo's required pre-review checks for the touched paths before the PR-facing push, including lint and typecheck when provided. Push with hooks on.
- [ ] Before each code-ready report, run `acceptance run <manifest.json>` at the clean committed head. Return its head, run ID, and receipt store.
- [ ] Read and apply **deslop** before each commit and **no-comments** before review.
- [ ] Triage every Bugbot and security-reviewer comment per the Bugbot triage reference in the installed Harness package (`../references/bugbot-triage.md`).
- [ ] Rebase onto current trunk before the code-ready report and babysit. Keep that merge base in fix rounds. Rebase again only at merge prep, on a `git merge-tree` conflict with trunk, or on a CI failure that comes from a change on trunk.

### Verdict and merge, for every PR

- [ ] Root runs `acceptance check <manifest.json>` at actual code-ready HEAD in the same store before the full independent round. Missing scenarios, failed or absent gates, stale evidence, and contradictory measurement setup block dispatch.
- [ ] After review findings, append the consolidated record and preserve each failed head, premise, repro run, and investigation. Declare amendments before the next fix or measurement. Require current-head focused and every known affected-case check. Two failed fixes sharing a premise and gate require Attack the Premise evidence before another ready report.
- [ ] Keep the independent verdict, applicable live proof, and current-head CI at merge. Passing owner preflight replaces none of them.
- [ ] At the code-ready head SHA and at each later push that changes the patch, run the **swarm** skill. One gates lane. The declared live lanes from the PR's **Verify, live** block and the perf lane from its **Verify, perf** block when applicable. Honor concrete nonapplicability reasons; missing capability is still incomplete. Two or more audit lanes, each with its own focus, that read the diff and the receipts and distrust the PR body. The root audits the receipts in the merge-ready report before the verdict.
- [ ] Clean only when every lane is `PASS`. Findings go back to the owner, including a defect that a lane filed as a note. A new head gets a fresh swarm and a fresh verdict, except for results that stay valid under the patch-id rule in `shipping.md`.
- [ ] <The merge or append rule from the execution playbook, with the patch-id rule from `shipping.md`.>

### Boot recipe, for every live lane

Each live lane runs in an isolated supported host execution environment at the exact PR head. Drive through **control-ui**, **control-cli**, or the named matching repository driver.

- [ ] `git fetch origin <head-branch> && git checkout <head SHA>`.
- [ ] <Start the backend and the surface. Wait for ready.>
- [ ] <Deliver input only through the control skill's commands. Name the read-only diagnostics.>
- [ ] Save every evidence artifact to `<authorized evidence dir>/worker-<n>/<slug>.<ext>` and return the paths with the report.

## <Task as a verb phrase> (<PR id>)

**Depends on.** <PR id, or None.>

**Files.**

- [ ] Edit `<path>`.
- [ ] Create `<path>`.
- [ ] Delete `<path>`.

**Build.**

- [ ] Commit `<manifest.json>` with the scoped outcomes, scenarios, concrete predicates, project commands, required environment, and justified nonapplicability. Declare it before implementation or measurement.
- [ ] <One change. Name the symbol and the file.>

**You see.**

- [ ] <One observable result, with the exact log line or screen state.>

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its applicable unit, live, and perf checks have evidence, with a reason for each nonapplicable check.

- [ ] <Test file and the case it gains.> Run `<command>`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its applicable unit, live, and perf checks have evidence, with a reason for each nonapplicable check. <N> lanes on `<configured or inherited workers model>` at the PR head, per the boot recipe. Coverage follows <distinct scenarios and risks; why these lanes suffice>.

- [ ] Lane 1. Regression lane against trunk. Run <the same load-bearing scenario> at trunk and head. If trunk lacks the feature, record that and gate <the behavior the diff adds plus the end state the user waits for>. Save `<evidence artifact>`. Pass when <predicate>.
- [ ] Lane 2. <Distinct scenario or risk.> Save `<evidence artifact>`. Pass when <predicate>.
- [ ] <Continue through the declared N, with one distinct scenario, evidence artifact, and pass predicate per lane. Remove excess lane examples.>

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its applicable unit, live, and perf checks have evidence, with a reason for each nonapplicable check.

- [ ] Metric. <What is measured at both trunk and head. If trunk lacks the feature, also name the diff-added work and the end-to-end state the user waits for.>
- [ ] Probe. <The command or procedure, run at trunk and at the head, interleaved. Both sides must produce the metric.>
- [ ] Baseline. Record the trunk <value> first.
- [ ] Rule. <Head against trunk, with the number that fails. If the scenarios differ, add absolute budgets for the diff-added work and the user-visible end state instead of an invalid ratio.>

**Review gate.** The operator reviews before merge.

- [ ] Copy lane <n> screenshots into `<media path>/<pr-id>-review-<slug>.png`.
- [ ] Record a 30 to 60 second video of the change in the lane's supported environment. Save it as `<media path>/<pr-id>-review.mp4`.
- [ ] Post the screenshots and the video in chat. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Bugbot triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] <The owner squash-merges its own PR, or the root appends it to the base-branch stack and the operator lands it bottom-up.>

## Close the program

- [ ] Every box above is checked with its evidence.
- [ ] Reply to the operator with the report the execution playbook names.

## Appendix A. Prototype evidence

<Each open question a prototype answered, with the branch, the SHA, and the artifact links. Each question that stays unproven.>

## Appendix B. Alternatives rejected

<Each approach weighed and why it lost.>

## Appendix C. Risks

<Each risk with the PR it lands in and what the owner watches.>

## Appendix D. Links and reading list

<Docs to read before editing. Which PRs use the installed **how** and **interrogate** skills. The trail follows the installed **show-me-your-work** skill.>
````

**Reply:** the plan path, the PR ids with their dependencies and the review-gated set, what the prototypes proved and what stays unproven, and the check script's output.
