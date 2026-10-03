# Unslop evaluation cases

This skill retains the instruction body from its pinned upstream source.
The rule identifiers and examples remain intact.

## Normal use

- Input. Ask Unslop to edit a paragraph containing a vague attribution, ornate vocabulary, praise, dash separators, curly quotes, and a compressed fragment.
- Expected result. Read the separate Unslop skill. Rewrite in plain, complete sentences while preserving meaning and intended tone. Retain the stable rule identifiers in the skill itself.
- Observed outcome. Independent behavioral execution is pending. The local source comparison verifies the complete instruction body is unchanged.

## Outside scope

- Input. Return supplied JSON exactly without requesting a prose edit or invoking the mode.
- Expected behavior. Preserve the requested literal output. Do not rewrite machine syntax as prose.
- Observed outcome. Independent behavioral execution is pending. Explicit-only metadata is present.

## Failure boundary

- Input. Rewrite a paragraph whose claimed performance improvement has no source or measurement.
- Expected result. Remove unsupported content or name its missing support. Do not invent a source or measurement.
- Observed outcome. Independent behavioral execution is pending. The source catalog still includes its vague-attribution and concrete-language rules.
