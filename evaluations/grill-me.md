# Grill Me evaluations

Reviewed against the restored upstream baseline on 2026-10-03. These are manual behavioral cases, separate from runtime instructions. Initial instruction walkthroughs are recorded below; live multi-turn agent evaluation remains to be done during first use. Repository and CLI checks verify packaging and structure, not interview quality.

## Independent decisions in the same round

- Input: "Grill me about a weekend reading club. We need to decide who it serves and whether meetings are online or in person."
- Expected: Ask the independently answerable audience and meeting-format questions together, number them, and recommend an answer for each. Wait for replies.
- Walkthrough: Both questions have settled prerequisites in this scenario; the round includes both. No implementation or meeting invitations are authorized.
- Live outcome: Not yet run.

## A dependent question waits

- Input: "Grill me about this event. We haven't chosen online versus in person, and we're also considering a room capacity."
- Expected: Ask about the event format first. Room capacity belongs to a later branch if in person is selected; do not assume that choice.
- Walkthrough: Capacity depends on meeting format, so it is excluded from the initial frontier. This remains true even if the agent recommends an in-person event.
- Live outcome: Not yet run.

## Delegate fact-finding as upstream specifies

- Fixture: A disposable project with `README.md` saying "The app uses SQLite and has no hosted database." The user asks: "Grill me about deploying this app."
- Expected: Dispatch a subagent to inspect the supplied project context before posing decisions that depend on it. Do not ask the user which database the README already identifies. Ask other independently answerable decisions while that research is running.
- Walkthrough: The database is a fact for delegated research; selecting deployment requirements is a user decision. Dependent questions wait for the research result, while independent questions can proceed.
- Live outcome: Not yet run.

## Completion requires confirmation

- Input: All branches of the event's decision tree have been explored and settled.
- Expected: End the interview only when the frontier is empty and no branch is silently assumed. Wait for the user's confirmation of shared understanding before acting on the plan.
- Walkthrough: Completion and acting on the plan are separate. The original upstream confirmation requirement is preserved.
- Live outcome: Not yet run.

## Outside scope

- Input: "Rename the button from Start to Continue."
- Expected: Handle the requested edit using the relevant workflow; do not activate an unsolicited grilling interview.
- Walkthrough: The description targets stress-testing or grill trigger phrases; an ordinary button edit contains neither.
- Live outcome: Not yet run.

## Prerequisite note

The restored upstream instructions require a subagent for environment fact-finding. They provide no direct-inspection fallback; that earlier local behavior was removed. Behavior in an environment without delegation is not specified by this baseline and should not be invented as an evaluation expectation.
