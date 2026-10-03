# Maintenance index

`registry/skills.json` is the source of truth for maintenance data. Its top-level `schema_version` is `1`; `skills` is an object keyed by the runtime skill directory name. An empty object is valid before any skills are added.

Each skill entry contains:

| Field | Meaning |
| --- | --- |
| `maintenance_notes` | What you authored or customized and why |
| `reviewed_on` | Last maintenance review date, in YYYY-MM-DD format |
| `sources` | Zero or more upstream sources; empty for independent work |

Each source contains:

| Field | Meaning |
| --- | --- |
| `id` | Stable lowercase kebab-case identifier, unique within the skill |
| `relationship` | `adapted` for copied or modified material; `inspired` for ideas |
| `repository` | Public HTTP(S) Git repository URL |
| `ref` | Branch or ref to check for future updates |
| `paths` | Repository-relative files or directories to watch, including supporting files; use `.` to watch the whole repository |
| `baseline_revision` | Full immutable Git commit identifying the original reference |
| `last_reviewed_revision` | Full commit whose relevant changes have been considered, including rejected changes |
| `last_incorporated_revision` | Full commit most recently used for incorporation; may be null for inspiration with no incorporated material |

For a new adaptation, initialize all three revisions to the source commit. For inspiration, initialize baseline and last reviewed to the reference commit and last incorporated to null. Use full 40- or 64-character hexadecimal Git object IDs, not moving branches or release names, in revision fields.

## Review decisions

Maintenance notes and reviews describe final behavior, source differences, reasons, and validation. Use Git history for editing chronology.

Use optional `reviews/<skill-name>/` records for consequential upstream adoption decisions. Include the source ID, previous and reviewed commits, decision (`adopt`, `partial`, or `keep`), selected changes, and reasoning. Source IDs let one skill track several independent references.

After review, update the index and any decision record together in one Git change. Keeping a customization still advances `last_reviewed_revision`; otherwise a monitor would repeatedly report the same rejected changes. `last_incorporated_revision` is provenance, not a claim that the local skill equals upstream. The checker validates registry records; it does not yet validate or reconcile review-history files.

## Future monitoring contract

A monitor should read this index, resolve each source ref, and compare only its watched paths since `last_reviewed_revision`. It should include additions, modifications, deletions, and moved files. A change outside watched paths need not create a review. A missing path, unavailable repository, or rewritten history should be reported for investigation.

When relevant changes appear, produce a review proposal with an upstream diff and a comparison against the customized skill. Detection alone must not advance review revisions or modify skills. A human and an agent choose what to incorporate and record their decision. No monitor, schedule, or remote access is configured by this scaffold.

## Context boundary

Agents doing project work need `skills/<name>/SKILL.md` and runtime resources. Registry entries and review history are for agents maintaining the harness. Installers should package only runtime content, never the maintenance index or harness-level `AGENTS.md`.

Keeping a file next to a skill does not by itself prove it will be loaded into context; tools differ. This layout makes the intended distribution boundary explicit and independent of those discovery rules.
