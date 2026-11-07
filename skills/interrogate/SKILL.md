---
name: interrogate
description: "Use for \"interrogate\", \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". Adversaries try to break a change or design and report findings supported by reproducible or static evidence."
disable-model-invocation: true
---

# Interrogate

Adversaries try to break a change or design. Report proven findings. Do not apply fixes.

## Frame

The scope is what the user names. Otherwise it is the branch diff from its merge base with the base branch, through the working tree, including relevant untracked files. State the intent from the user's message, commits, and PR description. Ask when the intent is unclear.

## Fan out

Use the host's configured Interrogate reviewer roster; otherwise launch three independent reviewers inheriting the parent model. `auto` and `inherit-parent` omit the model override. If a configured model is unavailable, inherit the parent model and disclose the substitution. Model diversity is optional; same-model reviewers are independent reviewers, not cross-model consensus. Use configured role settings for reasoning and speed where supported; otherwise inherit the host defaults.

Give each adversary its own worktree or scratch checkout containing the exact scoped changes, including uncommitted work. Schedule through the host's delegation tools within its concurrency limits. Keep the target checkout and external services read-only; repros may write only in assigned isolated locations and within task permissions. Missing delegation or required execution access is a review gap, not a pass.

Give each adversary the same scope, intent, and brief:

> Break this change. Prove each finding against the real code with a failing test, repro script, or command output. Report the exact command, actual output, expected output, and affected location. For a design or plan, use a prototype or probe the current tree. Keep repros in your assigned workspace. When execution is unavailable, unsafe, or cannot establish the defect, a static finding needs exact code or contract references, a reachable input or state, and the traced violation. Distinguish static proof from an observed failure. Leave out style preferences, speculative future risks, and unsupported claims. No findings is valid.

## Verify

Rerun executable findings in isolation. For static findings, independently trace the cited path or contract and check the claimed input is reachable. Retain proven correctness, security, or contract violations even when a runnable reproduction is unavailable. Report a reproduction gap explicitly; unsupported suspicions remain unverified.

Judge findings against the intent, surrounding code, and known project constraints. A successful run alone does not establish relevance; an unmet prerequisite or a deliberate, authorized tradeoff may refute a claim. Keep every established defect, including a lone reviewer's finding, and merge findings with the same root cause. Agreement does not substitute for evidence. Report findings and verification gaps without selecting a winning reviewer or applying fixes.

## Output

- **Intent**: the restatement.
- **Reviewers**: the actual models and any substitutions, dropouts, or access gaps.
- **Findings**: severity, affected location, evidence, how the defect violates the intent or applicable contract, and the adversaries that found it. Include commands and outputs for executed proof, or the independently checked trace for static proof. Say "no verified findings" when none survive.
- **Dropped or unverified**: counts and reasons per adversary, including any verification gaps. An incomplete review does not establish a clean result.
