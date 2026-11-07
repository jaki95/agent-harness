---
name: principle-attack-the-premise
description: "Apply when two or more fixes that share one premise have failed the same gate. Write the premise down and test it directly before you write another fix that assumes it."
disable-model-invocation: true
---

# Attack the Premise

When two or more fixes that share one premise have failed the same gate, investigate the premise before trying another fix that assumes it.

**Why:** Repeated failures are evidence about the shared premise, but do not by themselves prove it false.

**Pattern:**
- **Write the premise down.** The premise is the one sentence that every failed fix assumed.
- **Test the premise before the next fix.** Find an observation that would come out differently if the premise were false, and make it. Look at how the failures are distributed, not only at how large they are. Make the check rerunnable per **Build the Lever**.
- **Follow the evidence.** If it contradicts the premise, revise the explanation and look for what the failures have in common that the premise did not predict. If it supports the premise, ask the next "why" per **Fix Root Causes**. The earlier fixes may have treated a consequence instead of the cause. If the observation cannot distinguish the explanations, label it inconclusive and choose a better observation.
- **Remove the condition instead of compensating for it**, per the **Laziness Protocol**. If the evidence shows that one part always lands on the losing side, change what puts it there. A mechanism that cleans up after it leaves the cause in place and adds work on every run.

**Stop:** Do not start the next fix before the premise is written down and tested. Keep the evidence and its limitations with the resulting diagnosis.

This principle is distinct from **Redesign from First Principles**, which rebuilds a design around a new requirement. It questions a fact the current design assumes.
