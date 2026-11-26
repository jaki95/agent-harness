# Install and update skills

Use Node 22.20 or newer, npm/npx, and Git. The examples use Skills CLI 1.7.0 and Codex. Choose a skill from the [catalog](skills.md) or list the current collection:

```sh
npx skills@1.7.0 add jaki95/agent-harness --list
```

## Pin a release in a project

Run inside the consuming project. This example installs `grill-me` from the [published v0.1.0 release](https://github.com/jaki95/agent-harness/releases/tag/v0.1.0).

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#v0.1.0' --skill grill-me --agent codex --copy
```

Commit the installed files and `skills-lock.json`. The CLI uses symlinks by default. Use `--copy` for independent project files.

**Upgrade or roll back.** Select a [published tag](https://github.com/jaki95/agent-harness/releases), substitute it for `v0.1.0` in the same command, and review the project diff. A project update preserves the installed tag:

```sh
npx skills@1.7.0 update grill-me --project
```

## Follow main

For a personal install that follows reviewed changes, run:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill grill-me --agent codex --global
npx skills@1.7.0 update grill-me --global
```

For a project install, omit `--global` on `add` and use `--project` on `update`. Edit skills in the source repository. An update can replace edits made to installed copies.

## Install Harness

To get the bundled playbooks and scripts, select `harness` alone. Invoke it with `$harness` in Codex.

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill harness --agent codex --global
```

Harness looks up companion skills by name in the host catalog and reports any missing skill. For its full selection from this collection, use the same names for installation and updates. Run in Bash or Zsh:

```bash
harness_skills=(
  harness unslop technical-writing
  deslop no-comments interrogate
  show-me-your-work figure-it-out benchmark-checklist
  how why architect
  arena swarm control-ui
  control-cli principle-laziness-protocol principle-foundational-thinking
  principle-redesign-from-first-principles principle-attack-the-premise principle-subtract-before-you-add
  principle-minimize-reader-load principle-outcome-oriented-execution principle-experience-first
  principle-exhaust-the-design-space principle-build-the-lever principle-model-the-domain
  principle-boundary-discipline principle-type-system-discipline principle-make-operations-idempotent
  principle-migrate-callers-then-delete-legacy-apis principle-separate-before-serializing-shared-state principle-prove-it-works
  principle-fix-root-causes principle-sequence-verifiable-units principle-test-behavior-not-implementation
  principle-explain-the-number principle-guard-the-context-window principle-never-block-on-the-human
  principle-encode-lessons-in-structure
)
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill "${harness_skills[@]}" --agent codex --global
npx skills@1.7.0 update "${harness_skills[@]}" --global
```

The [Harness playbook index](../skills/harness/SKILL.md) links to the instructions for each task. Codex requires explicit invocation for Harness and permits implicit invocation for its routed skills. On other hosts, upstream `disable-model-invocation` settings can require explicit selection.

## Check prerequisites for the work you want to do

Installation supplies runtime instructions and bundled helpers. The project and host supply tools, permissions, and accounts.

| Workflow | What to have available |
| --- | --- |
| [Feature](../skills/harness/playbooks/feature.md), [review](../skills/interrogate/SKILL.md), and [investigation](../skills/how/SKILL.md) | Host delegation for independent work. UI and CLI verification need a running project and its browser or terminal driver. Historical investigations use Git and authenticated `gh`. The [Bug fix playbook](../skills/harness/playbooks/bug-fix.md) can use a separately installed `tdd` skill. |
| [Plan and acceptance checks](../skills/harness/references/acceptance-record.md) | Node 22.20+, Git, and the project's declared verification commands. [Isolated verification lanes](../skills/harness/references/isolated-lanes.md) require Linux and Python 3.10+. |
| [Queue recovery](../skills/harness/references/queue-recovery.md) and [unattended audits](../skills/harness/references/audit-registration.md) | Git, Python 3.10+, and authenticated `gh` for PR state. Unattended audits require a supported host scheduler and adapter. The package includes the manual recovery path. |
| [Wayfinder](../skills/wayfinder/SKILL.md) | A host `Skill` tool, `grilling`, `domain-modeling`, `research`, `prototype`, and a tracker configured for Wayfinding operations. Research tickets also need subagents, Git branches, and push access. |
| [Retro](../skills/retro/SKILL.md) | A host `Skill` tool, the separate `writing-for-agents` skill, and access to session evidence. |
| [Statechart](../skills/statechart/SKILL.md) | A TypeScript-capable runtime, Java, and TLC. Its launcher can obtain tools with mise and network access. Image rendering uses Pele. |
| [Correct](../skills/correct/SKILL.md) and [Blast Radius](../skills/blast-radius/SKILL.md) | Project history, source, and executable checks. Blast Radius uses Arena for wide reviews and Unslop for its report. |
| [Maintain Verification Skill](../skills/maintain-verification-skill/SKILL.md) | A project-local verification skill with a feature map, a runnable app or CLI, and host delegation. The [generator](../skills/create-verification-skill/SKILL.md) writes to `.agents/skills/verify-<slug>/`. |

The CLI distributes each selected skill's directory. Repository maintenance scripts, the upstream registry, Statechart's test corpus, and review records stay with the source checkout. See the [Skills CLI documentation](https://github.com/vercel-labs/skills/blob/v1.7.0/README.md) for other agent selections.
