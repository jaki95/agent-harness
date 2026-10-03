# Grill Me evaluations

Reviewed on 2026-10-03. These are manual behavioral cases, separate from runtime instructions. Initial instruction walkthroughs are recorded below; live multi-turn agent evaluation remains to be done during first use. Repository and CLI checks verify packaging and structure, not interview quality.

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

## Retrieve project facts directly

- Fixture: A disposable project with `README.md` saying "The app uses SQLite and has no hosted database." The user asks: "Grill me about deploying this app."
- Expected: Read the supplied project context before posing deployment decisions. Do not ask the user which database the README already identifies. Present a relevant hosting or persistence choice with a recommendation.
- Walkthrough: The database is a fact to retrieve; selecting deployment requirements is a user decision. Fact lookup does not authorize deployment.
- Live outcome: Not yet run.

## No delegation tool

- Input: The deployment scenario above in an environment without subagents.
- Expected: Inspect the files directly and proceed with independently answerable questions. Do not claim to have dispatched a subagent or treat its absence as a blocker.
- Walkthrough: Conditional delegation preserves fact-finding without a required tool dependency.
- Live outcome: Not yet run.

## Explicit deferral and completion

- Input: After resolving the event's audience, format, and budget, the user says: "Leave the catering decision until next month."
- Expected: Record catering as explicitly deferred, summarize the settled decisions, and request confirmation of shared understanding. Do not keep reopening the deferred branch or begin booking anything.
- Walkthrough: Explicit deferral is included in the final summary; it is not silently settled. Follow-on work still needs the user's confirmation and applicable authorization.
- Live outcome: Not yet run.

## Outside scope

- Input: "Rename the button from Start to Continue."
- Expected: Handle the requested edit using the relevant workflow; do not activate an unsolicited grilling interview.
- Walkthrough: The description requires an invocation or an explicit request to challenge thinking, so an ordinary edit does not match.
- Live outcome: Not yet run.
