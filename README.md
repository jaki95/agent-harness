# agent-harness

A portable home for skills, scripts, and conventions that I own and maintain across projects.

Skills start empty. Public skills are reference material for deliberate adaptation, with attribution and licensing preserved. This repository is the source of truth; project-specific instructions stay in their projects.

## Layout

```text
skills/                 Owned skills, one directory per skill
scripts/                Portable maintenance utilities and their tests
templates/skill/        Starting files for a new or adapted skill
docs/adapting-skills.md  Adaptation and maintenance workflow
docs/portability.md      Boundaries between shared and project-specific behavior
AGENTS.md               Instructions for agents working on this repository
```

## Check the harness

Requires Python 3.10 or newer, with no third-party dependencies:

```sh
python3 scripts/check.py
python3 -m unittest discover -s scripts/tests
```

Run these from the repository root. The checker also works from another directory when invoked by its full path. GitHub Actions runs both commands on pushes and pull requests once the repository is hosted on GitHub.

## Add the first skill

Follow [the adaptation workflow](docs/adapting-skills.md). Each skill contains instructions, a provenance record, and concrete evaluation cases. Templates are inactive until you create a skill directory and customize them.

## Portability

Keep reusable behavior here and project context in project repositories. See [portability conventions](docs/portability.md) before connecting the harness to an agent tool. Tool-specific installation adapters will be added when there is a concrete target and scope.

## Licensing

No repository-wide license has been selected yet. Each adapted skill must record its upstream license and retain required notices. Customization does not remove upstream license obligations.
