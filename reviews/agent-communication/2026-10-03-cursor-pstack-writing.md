# Initial communication adaptation

This record describes the superseded composite draft. See [the modular Harness adaptation](../harness/2026-10-03-modular-mode.md) for the replacement. The former runtime skill and active registry entry were removed.

- Skill. `agent-communication`.
- Source ID. `cursor-pstack-writing`.
- Review date. 2026-10-03.
- Previous reviewed commit. None. This is the initial adaptation.
- Reviewed commit. `23e4138daa01c42d4969f7a5465f82704e64f798`.
- Decision. Partial adoption.

## Accepted choices

The user selected explanations for consequential decisions and milestone updates.
The user selected Poteto Mode's exact writing style.
This stage implements communication only.

## Reference material

The source repository is [cursor/plugins](https://github.com/cursor/plugins).
The following files were read at the immutable reviewed commit.

- [Poteto Mode](https://github.com/cursor/plugins/blob/23e4138daa01c42d4969f7a5465f82704e64f798/pstack/skills/poteto-mode/SKILL.md) supplies reply and comment rules.
- [Unslop](https://github.com/cursor/plugins/blob/23e4138daa01c42d4969f7a5465f82704e64f798/pstack/skills/unslop/SKILL.md) supplies the prose pattern catalog.
- [Technical writing](https://github.com/cursor/plugins/blob/23e4138daa01c42d4969f7a5465f82704e64f798/pstack/skills/technical-writing/SKILL.md) supplies document purposes and sentence guidance.

## Adoption and changes

The runtime instructions restate the writing behavior in a self-contained skill.
The prose reference retains the upstream catalog, including punctuation restrictions, concrete language, complete sentences, and formatting rules.
The technical-writing reference retains the document categories and guidance for clear instructions and unambiguous language.
The entrypoint retains consumer impact, maintainer context, evidence labels, inspected links, and comments that explain a non-obvious reason.

Selective explanations replace the mandatory principle inventory in every reply.
Milestone updates express the user's chosen progress policy.
Host-required status updates and user-requested detail remain supported.
Exact quotations, machine formats, URLs, symbols, and code retain their literal syntax.
Tab indentation applies to illustrative snippets. Runnable and copied code follows the project's syntax and conventions.
Unavailable facts remain explicit, including in reference documents.
The skill uses the harness's two-field metadata convention.
It does not depend on Cursor-specific commands, agent types, plugins, or named models.
New jargon does not automatically trigger an upstream skill-change proposal.

## Deferred scope

Engineering, verification workflows, subagent policy, and autonomy remain undecided.
This skill reports verification evidence but does not prescribe a testing workflow.
Long-run decision logs and independent trail reviews remain separate decisions.
No upstream skill was installed. No user-wide agent directory was modified.

## Validation

Six cases were walked through using temporary local fixtures and same-agent sample responses.
The cases cover selective explanations, milestones, prose rules, technical writing, exact formats, and missing evidence or authorization.
These walkthroughs are not independent behavioral evaluations.
An independent session evaluation remains pending.
The runtime reference checks passed.
`python3 scripts/check.py` validated one skill and the maintenance index.
`python3 -m unittest discover -s scripts/tests` passed all 17 tests.

## Registry update

Baseline, last reviewed, and last incorporated revisions are all `23e4138daa01c42d4969f7a5465f82704e64f798`.
The recorded incorporation means partial adoption, not equivalence to the complete upstream mode.
