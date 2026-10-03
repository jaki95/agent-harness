# agent-harness

A portable home for skills, scripts, and conventions that I own and maintain across projects.

Skills start empty. Public skills are reference material for deliberate adaptation, with sources and revisions tracked separately. This repository is the source of truth; project-specific instructions stay in their projects.

## Layout

```text
skills/                 Runtime instructions and supporting files only
registry/skills.json     Maintenance index: sources and upstream revision tracking
evaluations/            Manual evaluation cases, one file per skill
reviews/                Upstream update decisions and reasoning
scripts/                Portable maintenance utilities and their tests
templates/              Runtime and maintenance templates
docs/                   Adaptation, registry, and portability conventions
AGENTS.md               Instructions for agents maintaining this repository
```

## Check the harness

Requires Python 3.10 or newer, with no third-party dependencies:

```sh
python3 scripts/check.py
python3 -m unittest discover -s scripts/tests
```

Run these from the repository root. The checker also works from another directory when invoked by its full path. GitHub Actions runs both commands on pushes and pull requests once the repository is hosted on GitHub.

## Add the first skill

Follow [the adaptation workflow](docs/adapting-skills.md). Each skill has runtime instructions, a separate registry entry, and separate evaluation cases. Templates are inactive until you customize and place them in their intended locations.

## Track upstream sources

[The maintenance index](registry/skills.json) records both adaptations and inspirations, with multiple sources supported per skill. Each source tracks its baseline, last reviewed commit, and last incorporated commit. [Registry conventions](docs/registry.md) describe these fields and the update review process. The index starts empty; automated monitoring is not implemented yet.

## Portability

Keep reusable behavior here and project context in project repositories. See [portability conventions](docs/portability.md) before connecting the harness to an agent tool. Tool-specific installation adapters will be added when there is a concrete target and scope.
