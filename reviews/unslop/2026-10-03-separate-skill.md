# Restore separate Unslop skill

- Source ID. `cursor-pstack`.
- Reviewed commit. `23e4138daa01c42d4969f7a5465f82704e64f798`.
- Decision. Adopt the upstream instruction body unchanged.

The user requested Unslop as a separate skill in its original format.
Restore every upstream heading, rule identifier, pattern, and example.
Normalize the description to a quoted scalar without changing its value.
Retain `disable-model-invocation: true` and add Codex's explicit-only invocation policy.
Track provenance and evaluation cases outside the runtime package.
Source-body parity and temporary installation checks validate content and packaging.
Independent behavioral evaluation remains pending.
