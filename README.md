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

## Add the first skill

Follow [the adaptation workflow](docs/adapting-skills.md). Each skill has runtime instructions, a separate registry entry, and separate evaluation cases. Templates are inactive until you customize and place them in their intended locations.

## Track upstream sources

[The maintenance index](registry/skills.json) records both adaptations and inspirations, with multiple sources supported per skill. Each source tracks its baseline, last reviewed commit, and last incorporated commit. [Registry conventions](docs/registry.md) describe these fields and the update review process. The index starts empty; automated monitoring is not implemented yet.

## Installation and releases

Use the Skills CLI directly against this private repository; no separate skills.sh publication or custom installer is required. [Installation instructions](docs/installation.md) cover project and global scopes, updates, release pins, and rollback.

```sh
npx skills@1.7.0 add jaki95/agent-harness --list
```

The collection is currently empty, so listing reports no skills. Follow [the release workflow](docs/versioning.md) to publish the first version after adding and evaluating an owned skill. Releases are manually triggered, validated, and tagged; the workflow rejects empty collections and existing tags.

Keep reusable behavior here and project context in project repositories. See [portability conventions](docs/portability.md) for the distribution boundary.
