# Unslop source adoption

- Skill. `unslop`.
- Source ID. `cursor-pstack`.
- Review date. 2026-10-03.
- Reviewed commit. `23e4138daa01c42d4969f7a5465f82704e64f798`.
- Decision. Adopt the upstream instruction body unchanged.

Unslop edits prose to remove AI writing patterns while preserving meaning and tone.
Its headings, stable rule identifiers, patterns, and examples match the pinned upstream source.
The quoted description has the original value.
The skill includes `disable-model-invocation: true` and Codex's explicit-only invocation policy.
Provenance and evaluation cases live outside the runtime package.
Source-body comparisons and temporary installation checks validate content and packaging.
Independent behavioral evaluation is pending.
