# Harness source adoption

- Skill. `harness`.
- Source ID. `cursor-pstack`.
- Review date. 2026-10-03.
- Reviewed upstream commit. `23e4138daa01c42d4969f7a5465f82704e64f798`.
- Decision. Partial adoption.

## Scope

Harness is a communication mode with selective explanations and milestone updates.
It routes to the separate Unslop and technical-writing skills and four communication playbooks.
Execution permissions and delegation follow the host and task rules.

## Upstream content

The source is [Poteto Mode](https://github.com/cursor/plugins/blob/23e4138daa01c42d4969f7a5465f82704e64f798/pstack/skills/poteto-mode/SKILL.md).
Harness uses its section order and unchanged reply and comment sections.
The mode metadata includes explicit-only invocation, an icon, a color, and a reminder.
Quoted scalars follow the harness checker convention.
All three communication skills include Codex's explicit-only policy in `agents/openai.yaml`.
Host support determines whether `/harness`, native mode features, and reminders are available. Codex uses `$harness`.

## Adaptations

The name, description, and reminder identify Harness.
Explanations focus on consequential choices, with principle names included when useful.
Progress updates report meaningful findings, decisions, obstacles, and substantial completed steps.
The progress-update, handoff, and technical-writing playbooks are original communication workflows with numbered steps and a reply specification.
The authoring-a-skill playbook is adapted from [the upstream authoring playbook](https://github.com/cursor/plugins/blob/23e4138daa01c42d4969f7a5465f82704e64f798/pstack/skills/poteto-mode/playbooks/authoring-a-skill.md).
It uses host authoring guidance and ends with a handoff. Creating a PR requires task authorization.
Relative file paths connect installed skills and playbooks.
The mode reports missing dependencies.

## Validation

On 2026-10-03, pinned-source comparisons confirmed the mode's section order and unchanged reply and comment sections.
The writing-skill instruction bodies match their pinned sources.
`python3 scripts/check.py` validated all four owned skills.
`python3 -m unittest discover -s scripts/tests` passed all 21 tests.
`npm ci --ignore-scripts` and `npm run test:skills` passed.
The CLI check installed all four skills into a temporary project and verified Harness's routes and invocation policy files.
These checks establish content and packaging properties.
Native mode behavior and independent agent adherence are unverified.
