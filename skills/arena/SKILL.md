---
name: arena
description: "Spawn N parallel candidates at the same task, pick a base, graft the strongest parts of the losers into it. Use for /arena, 'arena this', 'throw it in the arena', or when one attempt at a non-trivial artifact would lock in the wrong shape."
disable-model-invocation: true
---

# Arena

Use the host's subagent tools and existing role-model configuration; inherit the parent model when no role model is configured. Schedule all required agents within the host's concurrency limits. Delegation tools are required. Report unavailable tools or denied access, and do not claim the affected steps ran. Resolve named skills through the host's available skill catalog and read their instructions. Report unavailable skills by name, continue with this skill's own rules, and do not claim the missing skill was applied.

If the host provides a todo-list tool, open a list with one entry per phase (Frame, Fan out, Cross-judge, Pick, Graft, Verify) before starting. Without that tool, follow the phases directly.

## Phase A: Frame

Every candidate gets the same prompt, so the prompt is the contract.

1. State the artifact each candidate is producing.
2. Derive the rubric, 3-6 concrete gradeable criteria for what success looks like on *this* task. It is the picker's tool in Phase D. Candidates only see the task.
3. Pick the runners. Use the host's configured **arena runners** roster. If no roster is configured, default to three independent candidates inheriting the parent model. An `auto` or `inherit-parent` entry means the parent model, so omit a model override for it. If a configured model is unavailable, inherit the parent model for that seat and record the substitution. Model diversity is optional. Spawn more runners when the arena covers multiple design directions. Use configured role settings for reasoning and speed where supported; otherwise inherit the host defaults.
4. Give each candidate its own output location (a git worktree where possible, otherwise an explicitly assigned per-candidate directory in the host's temporary workspace), per the **principle-separate-before-serializing-shared-state** principle skill.

## Phase B: Fan out

Launch all N subagents through the host's delegation tools within its concurrency limits, each with the task, the path to the shared grounding, its own output path, and instructions to produce the artifact and a short rationale naming the alternatives it considered and what it rejected.

If a candidate fails to produce output, proceed with N-1 and note the dropout in the synthesis record.

## Phase C: Cross-judge

After all Phase B candidates complete, spawn one independent read-only judge using the host's configured **arena cross-judge pool**, or inherit the parent model. A separate same-model judge is valid; model diversity is optional and follows the user's model and cost preferences. If a configured model is unavailable, inherit the parent model and report the substitution. The judge sees the rubric and the candidates by path label, scores each criterion, and recommends a base with rationale. It runs in parallel with the parent's reading in Phase D. Don't spawn it while candidates are still writing. If delegation is unavailable, report the review gap; the parent's reading does not replace independent review.

## Phase D: Pick a base

Read every candidate end to end before picking. Score each against the rubric criterion by criterion, not on holistic feel, and compare with the cross-judge when one ran. Agreement on the base confirms the pick. Disagreement means one of you is biased or the rubric was ambiguous. Read both rationales before deciding.

Pick the base a future maintainer can extend most easily without breaking invariants. When two feel tied, prefer the cleaner boundary or smaller API, per the Laziness Protocol.

## Phase E: Graft

Walk each losing candidate once more for what is worth porting into the base, usually one or two things per candidate, not most of it. Fold each graft in by hand, per the **principle-redesign-from-first-principles** principle skill, so the result stays coherent under one mental model. Don't paste mechanically.

If the candidates converge on one shape, that is strong agreement. Note it and ship the consensus shape. No graft is needed. If they wildly diverge, Phase A was under-specified. Reframe and re-run rather than averaging the divergence.

## Phase F: Verify

Verify the synthesized artifact like any other output, per the **principle-prove-it-works** principle skill. If verification finds a problem the arena missed, either Phase A was wrong (re-frame and re-run) or a candidate caught it and you missed the graft (go back to Phase E). Don't paper over it.

## Outputs

One synthesized artifact, with a short synthesis note alongside naming the base and why, the cross-judge's verdict or the review gap, each graft with its source candidate, what was rejected and why, any convergence or dropouts, and the verification result.
