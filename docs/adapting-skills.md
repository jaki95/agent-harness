# Adapting and maintaining skills

## Create deliberately

1. Define the recurring task, where the skill should trigger, and a concrete outcome that would make it useful.
2. Choose a public reference, inspect its instructions, and record its URL and exact commit or release. Check its license before adapting it.
3. Create `skills/<lowercase-kebab-name>/`. Copy the three files in `templates/skill/`, removing their `.tmpl` suffixes.
4. Write instructions for your own workflow. Remove assumptions about other people's directories, tools, organizations, permissions, and preferences. Include explicit tool prerequisites and boundaries.
5. Fill in `provenance.json`. For an adaptation, use `origin: "adapted"` and add an upstream entry for every source. Record `url`, `revision`, `license`, and `license_file`, where `license_file` points to a retained notice inside the skill directory. Use `origin: "original"` and an empty upstream list only for independently authored work.
6. Write evaluation cases covering normal use, a case that must not trigger, and a relevant failure or permission boundary. Try them in a disposable project. Record outcomes and the review date.
7. Run the checks and review the diff before committing.

## Metadata convention

The initial checker accepts a deliberately small frontmatter format: exactly two fields, `name` followed by `description`. The name must match its directory. The description must be a nonempty, single-line JSON-quoted string, which is also valid YAML. The template shows this format. Normalize upstream metadata to this format when adapting; extend the checker explicitly if more metadata becomes useful.

Each active skill must contain nonempty `SKILL.md`, `provenance.json`, and `evaluations.md` files. The checker validates structure and provenance fields; it does not assess instruction quality, decide license compatibility, or execute evaluation cases.

## Maintain intentionally

- Review upstream changes when they address a real need. Compare against the pinned revision; do not replace customized instructions wholesale.
- Update the revision and adaptation summary whenever upstream material changes.
- Rerun relevant evaluation cases after instruction or prerequisite changes.
- Keep attribution and required license notices with the adapted files.
- Review the recorded `reviewed_on` date when revisiting a skill. No automatic review cadence is enforced yet.
- Retire unused skills through a reviewed Git change; history preserves the previous implementation.
