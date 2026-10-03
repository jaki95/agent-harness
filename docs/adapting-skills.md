# Adapting and maintaining skills

## Create deliberately

1. Define the recurring task, its triggers, and an outcome that would make the skill useful.
2. Choose public references and record their repositories, relevant paths, and exact commits.
3. For an upstream import, copy the selected canonical skill and its runtime resources into `skills/<lowercase-kebab-name>/`, applying only requested naming changes. For independently authored skills, start from `templates/skill/SKILL.md.tmpl`. Only runtime instructions and supporting files belong in that directory.
4. Preserve the imported baseline. Propose further customizations separately, including any tool or environment assumptions that need changing. Apply instruction or behavior changes only after agreeing them with the user; a goal of eventually owning customized skills does not authorize immediate rewrites.
5. Add an entry keyed by the skill name to `registry/skills.json`, using `templates/registry-entry.json.tmpl`. Record each source as `adapted` or `inspired`, using `templates/source.json.tmpl` and the conventions in [registry.md](registry.md). Independently authored work can have an empty sources list.
6. Create `evaluations/<skill-name>.md` from `templates/evaluations.md.tmpl`. Cover normal use, a case that must not trigger, and a relevant failure or permission boundary. Try the cases in a disposable project and record outcomes.
7. Run the checks and review the diff before committing.

## Metadata convention

The checker accepts a deliberately small runtime frontmatter format: exactly two fields, `name` followed by `description`. The name must match its directory. Descriptions may be single-line plain YAML text or nonempty JSON-quoted strings. Plain text must start with a letter and avoid reserved boolean/null values, YAML comment markers, and colon-space sequences. Preserve supported upstream formatting; extend the checker explicitly if an import requires additional metadata instead of rewriting instructions to fit the scaffold.

Each active skill must have a nonempty `SKILL.md`, a matching registry entry, and a nonempty evaluation file outside its runtime directory. The checker validates these boundaries, source fields, and revision formats. It does not verify that commits exist remotely, assess instruction quality, or execute evaluation cases.

## Maintain intentionally

Review upstream changes against the source's `last_reviewed_revision`. Compare useful changes with your current customized skill. Record the decision in `reviews/<skill-name>/` using `templates/review.md.tmpl`, then advance the last reviewed revision even when keeping your skill unchanged. Advance the last incorporated revision only when incorporating changes from that commit; partial adoption does not imply that your skill matches upstream.

Update maintenance notes and the review date, and rerun relevant evaluation cases after changes. Do not replace customized instructions wholesale. Retire unused skills through a reviewed Git change that also removes their registry entries and evaluation files. History preserves previous versions and review decisions.
