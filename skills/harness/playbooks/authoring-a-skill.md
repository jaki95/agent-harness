### Authoring or modifying a skill

**You own the skill's voice.**

1. Use the host's available skill-authoring guidance. If none is available, write a self-contained SKILL.md with a clear trigger, required context, actions, and completion criteria.
2. Validate the skill: frontmatter has `name` and `description`, referenced files exist, cross-skill links resolve.
3. Test cases if structural. Skip if subjective. Report which kind of validation actually ran.
4. Run **Handoff** (`handoff.md`). Create or update a PR only when the task authorizes it.

When in doubt, delete. Keep only prose that changes a decision. Tell it to do the thing and skip the reason. Explain only when the rule is confusing without one. Match tone to scope. Point at structural sources such as types, READMEs, and configuration. Delegate to other skills by path. Don't restate.

**Reply:** summary of the skill, key design decisions, validation notes.
