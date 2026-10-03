---
name: no-comments
description: "Spawn Comment Sicko, fix accepted findings, and offer encodings for claimed constraints."
disable-model-invocation: true
---

# No comments

Spawn Comment Sicko. Act on accepted findings.

Defer to Comment Sicko's fresh perspective.

Use the host's subagent tools. Delegation tools are required. Use the host's configured Comment Sicko model when available; otherwise inherit the parent model. Report unavailable tools or denied access, and do not claim the affected steps ran. Resolve named skills through the host's available skill catalog and read their instructions. Report unavailable skills by name, continue with this skill's own rules, and do not claim the missing skill was applied.

## Scope

Use the caller's files or diff. Otherwise use the current diff against the base branch, default `main`, including the working tree.

## Steps

1. Spawn one Comment Sicko subagent through the host's delegation tools. Pass the full prompt in `references/comment-sicko.md` and the scope. The reviewer may edit comments and suppressions within that scope and identify refactor targets, but must not edit application code. Do not restate its rules.
2. Inspect its report and diff. Reject application-code edits, scope escapes, exception-protected or unresolved-rationale deletions, constraint-comment deletions without an approved and verified replacement, misstated `MUST KILL` reasons, and flags that treat kept intentional code as guilty. Reshape flags on our-code surprises stay actionable. Delete those comments only when their purpose is established or a tested structural replacement makes them unnecessary. Otherwise preserve or restore them and report the rationale unresolved. A confirmed keep needs proof it is about something we cannot change. Preserve unresolved comments pending investigation or a tested replacement; do not present an unverified constraint as established fact. Audit missed scoped lint and TypeScript suppressions. Correctness or safety suppressions stay actionable `MUST KILL`s. Restore deletions with exact exceptions and scoped proof, or when the rationale remains unresolved. Before accepting thin `IMPORTANT` or `do not remove` kills or keeps, run **how** or **why** on their symbol. If a proposed deletion is ambiguous, preserve or restore the comment and report its purpose unresolved. If evidence refutes a keep, delete it. If ambiguity remains, retain it. Revert and rerun one rejected report with the failure named. Reject a second, report it open, and fail `/no-comments`.
3. Fix trivial accepted flags directly by deleting a dead path, dropping a parameter, or using the real API. If any fix needs a shape, run **architect** once for the accepted set and surrounding code. Stop at the sketch. Architect shapes. Step 4 implements.
4. Implement the smallest root-cause fix in scope. Remove every named workaround. If the root cause is out of scope, land the smallest in-scope fix and report the rest open. The **principle-fix-root-causes** and **principle-redesign-from-first-principles** skills guide intent only. Neither authorizes widening the fence nor fixing instances outside it. Never bolt on symptom guards.
5. Constraint comments say `do not remove`, `do not change wording`, or `talk to X before changing`. Leave keeps about things we cannot change. Offer the cheapest in-scope type, runtime, test, or CI lint. Wait for interactive approval. Unattended work requires caller pre-approval. If approved, encode and verify the replacement, then delete. Otherwise retain the comment, report the constraint unenforced, and sketch out-of-scope work.
6. Report the deletion count, restored comments, retained unresolved comments, reruns, architect sketch, fixes, encoding offers, encodings, unenforced constraints, and other open work.
