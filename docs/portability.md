# Portability conventions

## Shared and local boundaries

Shared assets describe reusable behavior. Project repositories provide their own domain terminology, build commands, code standards, environment configuration, and permission rules.

For example, a shared review skill can describe a review process; a project's instructions identify its test command and coding conventions. Do not hard-code those project details into the shared skill.

Local scratch files can live in ignored `local/` or `work/` directories. Credentials belong in the environment or an appropriate credential store. Git ignore rules are convenience filters, not a secret scanner.

## Distribution

The Skills CLI handles agent-specific installation paths. Install only selected skills from this repository, using the commands in [installation.md](installation.md). It copies each discovered skill directory to its installed location; maintenance directories remain in the source repository. The harness's top-level scripts are maintenance tools and are not distributed through skill installation. Runtime scripts required by a skill belong inside that skill directory.

If a future tool needs a custom adapter:

- Make its target tool, destination, and scope explicit.
- Prefer project-local installation for the first integration.
- Support inspecting proposed changes before writing and preserve existing destination files.
- Track what was installed so updates and removal affect only harness-managed files.
- Keep tool-specific paths and configuration in the adapter, leaving skill content portable.
- Package only `skills/<name>/`. Exclude `registry/`, `evaluations/`, `reviews/`, and the harness's own `AGENTS.md` from project installations.
- Verify the target tool's current discovery and instruction rules before implementing an adapter.

Work on customized skills in this source repository. Installed copies are updated through the CLI and should not be treated as the source of truth.

## Version selection

Use `main` for personally selected current skills and immutable release tags for reproducible project installations. Commit the CLI-generated `skills-lock.json` and installed project skill files with the consuming project. Follow [versioning.md](versioning.md) for release and update decisions.

Personal and work clones may use different selections. Shared assets should not depend on employer-private content; work-only instructions should remain in an approved work repository.
