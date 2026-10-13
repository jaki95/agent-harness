# Selected upstream behavior updates

The approved change applies the five additions recommended by the upstream assessment. It retains the preceding [selective prose compression](2026-10-13-upstream-prose-compression.md).

## Sources and decisions

Review date: 2026-10-13.

| Skill | Source ID | Decision | Previous reviewed commit | New reviewed and incorporated commit |
| --- | --- | --- | --- | --- |
| `harness` | `cursor-pstack` | partial | `23e4138daa01c42d4969f7a5465f82704e64f798` | `c86f349b102feb91f1966f8a6a60882a4e601b50` |
| `principle-fix-root-causes` | `cursor-pstack` | adopt | `23e4138daa01c42d4969f7a5465f82704e64f798` | `c86f349b102feb91f1966f8a6a60882a4e601b50` |
| `architect` | `cursor-pstack` | partial | `23e4138daa01c42d4969f7a5465f82704e64f798` | `c86f349b102feb91f1966f8a6a60882a4e601b50` |
| `arena` | `cursor-pstack` | partial | `23e4138daa01c42d4969f7a5465f82704e64f798` | `c86f349b102feb91f1966f8a6a60882a4e601b50` |
| `grill-me` | `matt-pocock-grilling` | adopt | `d81f3a183412e71a5b1e84ca21bc1a35eea03a60` | `49dd158d1076134a641b33efb035946536778336` |

The immutable evidence is in the [Cursor comparison](https://github.com/cursor/plugins/compare/23e4138daa01c42d4969f7a5465f82704e64f798...c86f349b102feb91f1966f8a6a60882a4e601b50) and the [Matt Pocock comparison](https://github.com/mattpocock/skills/compare/d81f3a183412e71a5b1e84ca21bc1a35eea03a60...49dd158d1076134a641b33efb035946536778336).

## Selected changes

- Harness incorporates the fence-state fix from `pstack/skills/poteto-mode/scripts/check-plan.mjs` into its bundled `scripts/check-plan.mjs`. It recognizes backtick and tilde fences with up to three leading spaces. A closing line must use the same marker, have sufficient length, and contain only trailing whitespace. Backticks in a backtick opening info string prevent it from starting a fence. The local acceptance CLI dispatch and structural requirements remain intact.
- Fix Root Causes adds the instruction to propose a cheap, always-on signal when the deciding fact required a deep investigation. The existing clarification about correct boundary validation remains. The instruction proposes a signal rather than authorizing unrelated instrumentation.
- Grill Me adds the upstream rule that "yes" accepts the recommended answer. Its rounds, design tree, user-owned decisions, and naming adaptations remain.
- Architect adds the limited-context contributor perspective to its entrypoint and appends four sections from upstream `references/design-red-flags.md` to the corresponding local reference. The sections cover split ownership, duplicate task paths, importable internals, and hand-synchronized lists. The original four sections remain intact. Per-actor state still gives each state object one owner. The rationale template, candidate replacement rule, configured models, and independent-candidate runner prompt remain.
- Arena adopts the upstream final output paragraph, making the selection reason, judge verdict, graft sources, rejection reasons, convergence, dropouts, and verification result explicit. It preserves the local three-candidate default, isolation, host concurrency limits, configured models or parent inheritance, and judging after candidate completion.

Other Harness updates remain unadopted, including performance-ordering and stopping changes, Cursor-specific routing, mode metadata removal, and the shell worktree audit. The local performance strategy families, Python audit, PR workflow, merge authorization, and model policies remain. Architect and Arena do not adopt the upstream model-default or candidate-count changes.

## Registry result

The five sources advance both `last_reviewed_revision` and `last_incorporated_revision` to the exact commits above. Baseline revisions, source identities, watched paths, and unrelated entries remain. Maintenance notes record the selected additions and retained customizations. Partial incorporation does not claim whole-package equivalence.

## Verification

Four new public-CLI test methods exercise valid fences, false closing lines, prose after closing, and invalid opening info strings. They produced 10 failing subcases before the fix. All 13 plan-checker tests pass after the fix. These checks include tilde fences, indentation, longer matching closers, shorter and mismatched markers, closing-line suffixes, and literal headings and checkboxes inside examples.

`python3 scripts/check.py` passed for all 41 skills and the registry. `python3 -m unittest discover -s scripts/tests` passed all 225 tests outside the known sandbox restriction on Node spawning Git. `npm ci --ignore-scripts` and `npm run test:skills` passed with temporary fixtures and project-local installs. The integration check covered tagged installation, pinned updates, explicit upgrades, bundled resources, invocation policies, and maintenance-record exclusion. `git diff --check` passed.

Direct comparisons verify unchanged frontmatter, Codex invocation policies, source baselines, original architecture checks, rationale resources, and the previous compression results. The compression record's reproducible count is scoped to its original 10 entrypoints so subsequent adoptions do not change that measurement.

No agent-behavior evaluation, user-wide installation, release, or publication is performed.
