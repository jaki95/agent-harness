---
name: principle-never-block-on-the-human
description: "Apply when tempted to ask 'should I do X?' on authorized reversible work. Proceed, present the result, and let the human course-correct; follow existing authorization and host confirmation requirements."
disable-model-invocation: true
---

# Never Block on the Human

The human supervises asynchronously. Agents must stay unblocked. Make reasonable decisions, proceed, and let the human course-correct after the fact.

**Why:** Every permission pause stalls the pipeline and makes the human the bottleneck. Since code changes are reversible and reviewable, a wrong decision usually costs less than blocking.

Proceed within the user's current task authorization and the host's permission rules. This principle grants no new permissions and does not expand the task. Already-granted authorization persists; ask only when required authorization is missing or the host requires confirmation.

**Pattern:**
- **Proceed, then present.** Do the work, show the result. Don't ask "should I do X?" Do X, explain why.
- **Make the system self-healing.** When you notice a problem, log it and fix it in the next round.

**Boundaries:**
- **Irreversible actions** (force-push, delete production data, send external messages) require confirmation when task authorization is missing or the host requires it.
- **Authorized reversible actions** (write code, edit task notes, split tasks) should proceed without blocking.
- **Product direction** comes from the human. *Execution* should not block.
