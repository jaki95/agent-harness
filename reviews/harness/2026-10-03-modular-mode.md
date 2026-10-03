# Modular Harness mode adaptation

- Skill. `harness`.
- Source ID. `cursor-pstack`.
- Review date. 2026-10-03.
- Previous and reviewed upstream commit. `23e4138daa01c42d4969f7a5465f82704e64f798`.
- Decision. Partial adoption.

## User direction

The user requested a Poteto-style mode skill named Harness, invoked as `/harness` where supported.
The mode must use the upstream rule format, separate Unslop and technical-writing skills, and separate playbooks.
Selective explanations and milestone updates remain the selected customizations.
The user deferred engineering, verification workflows, subagents, and autonomy to later discussion.

## Structure and retained content

The mode preserves Poteto's section order.
The reply and comment sections are unchanged from the pinned source.
The separate writing skills retain their full upstream instruction bodies, including stable Unslop rule identifiers, examples, named technical-writing standards, and exact sentence guidance.
Their bodies are no longer paraphrased or bundled references.
The metadata retains explicit-only invocation and the mode's icon, color, and reminder fields.
Quoted scalar representation follows the portable harness checker convention.
Codex's explicit-only policy is also supplied in `agents/openai.yaml` for all three skills.
Host support determines whether `/harness`, native mode features, and reminders are available. Codex uses `$harness`.

## Deliberate customization

The mode name, description, and reminder identify Harness.
The mandatory principle inventory becomes selective explanation.
The milestone policy is explicit.
The progress-update, handoff, and technical-writing playbooks are newly authored communication workflows in the upstream numbered-step and reply format.
The authoring-a-skill playbook is adapted from the pinned upstream playbook.
It uses host authoring guidance and ends with a handoff instead of automatically opening a PR.
No additional upstream principles, implementation workflows, model routing, or external-action permissions are adopted at this stage.
Autonomy and subagent sections retain host and user boundaries without choosing future policy.
Skill and playbook pointers use relative installed paths.
Missing dependencies must be reported.

## Superseded draft

The composite `agent-communication` runtime package and active registry entry were removed.
Its earlier adaptation review remains as maintenance history and describes a superseded draft.
The old manual sample walkthroughs do not establish behavior for this new collection.
New evaluation cases explicitly mark independent behavioral runs as pending.

## Validation

Compare the two writing instruction bodies and the mode's reply and comment sections against the pinned references.
Validate mode section order and all relative skill and playbook routes.
Run the harness checker and Python test suite.
Run the pinned Skills CLI test in temporary fixtures, including an actual install of all three current skill directories.
The checks establish content and packaging properties. They do not establish native mode behavior or independent agent adherence.

On 2026-10-03, the source parity and route checks passed.
`python3 scripts/check.py` validated all three skills.
`python3 -m unittest discover -s scripts/tests` passed all 19 tests.
`npm ci --ignore-scripts` completed with the pinned dependency set.
`npm run test:skills` passed, including the temporary three-skill installation and its routed files and policy metadata.
Independent behavioral evaluation remains pending.

Before PR publication, rebase onto current main preserved the existing `grill-me` skill and plain-text description support.
The checker validated all four owned skills, all 21 Python tests passed, and the CLI test installed all four into a temporary project with Harness routes and policies intact.
Pinned writing-body and mode-section comparisons passed again.
