# Technical-writing source adoption

- Skill. `technical-writing`.
- Source ID. `cursor-pstack`.
- Review date. 2026-10-03.
- Reviewed commit. `23e4138daa01c42d4969f7a5465f82704e64f798`.
- Decision. Adopt the upstream instruction body unchanged.

The skill guides documentation, PR descriptions, and commit messages.
Its headings, named standards, rules, amendment-proposal instruction, and worked example match the pinned upstream source.
The skill includes `disable-model-invocation: true` and Codex's explicit-only invocation policy.
It depends on the separate Unslop skill.
Provenance and evaluation cases live outside the runtime package.
Source-body comparisons and temporary installation checks validate content and packaging.
Independent behavioral evaluation is pending.
