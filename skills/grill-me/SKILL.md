---
name: grill-me
description: "Stress-test a plan, decision, or idea through a focused interview. Use when the user invokes grill-me, asks to be grilled, or explicitly wants their thinking challenged."
---

# Grill Me

Interview the user until the important decisions and assumptions are understood together. Organize the discussion as a decision tree: some choices can be made now; others depend on answers still missing.

## Work in rounds

Identify the current frontier: unresolved decisions whose prerequisites are settled. Ask all independently answerable questions in that frontier together, numbered, with a short title and your recommended answer plus its reasoning. Include options when they help the user choose.

Wait for the user's answers before advancing. Update the tree after each round. Defer any question that depends on an unanswered question, even when both concern the same topic. Do not silently treat a recommendation as an accepted decision.

If an answer leaves a material ambiguity, resolve it before asking the questions that depend on it. Challenge weak assumptions directly and constructively; investigate consequential branches without inventing irrelevant decisions.

## Find facts; ask for decisions

Inspect available project files, documentation, and tools to establish facts before asking the user. Ask the user to make choices, not to retrieve information you can access yourself. Explain what remains unknown when a fact cannot be verified.

Use a subagent for independent fact-finding when delegation is available and permitted. Otherwise investigate directly. Pending research leaves its dependent branch unresolved; continue asking independently answerable questions while it runs. Do not choose a user preference merely because research is unfinished.

## Finish with shared understanding

When no material branch remains unresolved, briefly summarize the agreed decisions, constraints, and any explicitly deferred issues. Ask the user to confirm that this captures their intent before starting implementation or other follow-on work. If they correct the summary, revisit the affected branches.
