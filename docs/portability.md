# Portability conventions

## Shared and local boundaries

Shared assets describe reusable behavior. Project repositories provide their own domain terminology, build commands, code standards, environment configuration, and permission rules.

For example, a shared review skill can describe a review process; a project's instructions identify its test command and coding conventions. Do not hard-code those project details into the shared skill.

Local scratch files can live in ignored `local/` or `work/` directories. Credentials belong in the environment or an appropriate credential store. Git ignore rules are convenience filters, not a secret scanner.

## Tool adapters

The initial scaffold contains no installation adapter. When adding one:

- Make its target tool, destination, and scope explicit.
- Prefer project-local installation for the first integration.
- Support inspecting proposed changes before writing and preserve existing destination files.
- Track what was installed so updates and removal affect only harness-managed files.
- Keep tool-specific paths and configuration in the adapter, leaving skill content portable.
- Verify the target tool's current discovery and instruction rules before implementing an adapter.

Until an adapter exists, the harness is maintained and validated here but is not automatically discovered by tools running in other projects.

## Version selection

Use Git commits to identify exact harness versions. When connecting a project, record the selected commit and any locally chosen skills in that project. Promote updates after reviewing the diff and trying the relevant evaluation cases. Add release tags when there is a useful first version to distribute.

Personal and work clones may use different selections. Shared assets should not depend on employer-private content; work-only instructions should remain in an approved work repository.
