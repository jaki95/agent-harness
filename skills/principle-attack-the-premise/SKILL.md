---
name: principle-attack-the-premise
description: "Apply when two or more fixes that share one premise have failed the same gate. State the premise and gather evidence that can support or contradict it before trying another fix."
disable-model-invocation: true
---

# Attack the Premise

When two or more fixes that share one premise have failed the same gate, investigate the premise before trying another fix that assumes it.

**Why:** Repeated failures are evidence about the shared premise, but do not by themselves prove it false.

**Pattern:**
- **Write the premise down.** State the assumption every failed fix relied on in one sentence.
- **Choose a discriminating observation.** Identify a result that would support or contradict the premise. Choose diagnostic evidence suited to the symptom.
- **Gather the evidence before the next fix.** Use relevant measurements, traces, logs, or a controlled comparison to test the premise.
- **Revise the premise when contradicted.** Use the result to change the explanation and the next fix, rather than producing another compensation based on the same assumption.
- **Bound the conclusion.** State only what the evidence establishes. If the observation cannot distinguish the explanations, label the result inconclusive and choose a better observation.

**Examples:**
- For suspected workload imbalance, measure work per actor and test whether assignment causes the skew.
- For a missing imported item, trace it through import, storage, and retrieval to test the assumption that it was saved.
- A balanced actor census is evidence against the tested imbalance hypothesis. It does not establish that other premises are correct; all actors could share the same faulty configuration.

**Stop:**
- Do not start the next fix before the shared premise is written down and relevant evidence has been gathered.
- Keep the evidence and its limitations with the resulting diagnosis.

This principle is distinct from **Redesign from First Principles**, which rebuilds a design around a new requirement. It questions a fact the current design assumes.
