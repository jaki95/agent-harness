# Initial upstream adaptation

This records the initial implementation, which included unrequested changes subsequently rejected by the user. It is historical, not the current skill specification. See [the baseline restoration](2026-10-03-restore-upstream-baseline.md).

- Skill: `grill-me`
- Source ID: `matt-pocock-grilling`
- Review date: 2026-10-03
- Previous reviewed commit: none; initial adoption
- New reviewed commit: `d81f3a183412e71a5b1e84ca21bc1a35eea03a60`
- Decision: adopt, with local naming and portability adjustments

## Upstream reviewed

[Pinned skill directory](https://github.com/mattpocock/skills/tree/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/productivity/grilling)

Reviewed `SKILL.md` and `agents/openai.yaml`. The current skill is self-contained. Its core workflow maps decisions and their prerequisites, asks the current frontier in rounds with recommended answers, retrieves facts, and waits for confirmation of shared understanding before acting.

## Initial agent choices, subsequently corrected

- User requested `grill-me` despite the upstream rename to `grilling`; the display name is `Grill Me`.
- Retained rounds of independent questions rather than restoring the older one-question-at-a-time approach.
- Rephrased the instructions and made fact-finding work without mandatory subagent tooling.
- Kept the upstream UI description and default invocation behavior.
- Explicitly represent deferred issues in the closing summary so they are not silently assumed or reopened indefinitely.
- Kept source records, maintenance notes, and evaluation cases outside the runtime package.

## Evaluation status

The instruction walkthroughs are in `evaluations/grill-me.md`. Live multi-turn behavior has not yet been independently evaluated. The harness check and skill-creator validator passed, as did 17 maintenance tests and the Skills CLI integration test. A temporary project installation of the actual `grill-me` directory preserved its instructions and excluded maintenance files. These checks do not establish interview quality.

## Registry initialization

Baseline, last reviewed, and last incorporated revisions are all initialized to the pinned commit above. The watched directory includes both instructions and UI metadata. Automated monitoring is not implemented by this adaptation.
