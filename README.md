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
| [harness](skills/harness/SKILL.md) | Communication mode with selective explanations, milestone updates, and routed playbooks |
| [unslop](skills/unslop/SKILL.md) | Remove AI writing patterns while preserving meaning |
| [technical-writing](skills/technical-writing/SKILL.md) | Write docs, PR descriptions, and commit messages with the original writing guidance |

Harness uses Poteto Mode's section layout and routes to separate skills by name through the host's skill catalog. Its communication playbooks are bundled inside its package. Unslop preserves its pinned upstream instruction body. Technical writing adds named Unslop discovery and a missing-skill fallback. Invoke Harness with `/harness` on hosts that expose skills as slash commands, or `$harness` in Codex. Install `unslop` and `technical-writing` for the full writing workflow. A standalone Harness install uses its own communication rules and reports unavailable writing skills. Execution and delegation follow the host and task rules.

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
