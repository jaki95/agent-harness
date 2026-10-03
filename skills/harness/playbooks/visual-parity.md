### Visual parity

**You own pixel-exact equivalence. The baseline is the spec. You do not touch it.** Equivalence is verified by image diff, not by eye.

Use Git and the host's filesystem, execution, image-comparison, and delegation tools and the matching control skill. Resolve named skills through Harness's skill catalog rules. Follow the user's authorization and the host's permission rules. Report unavailable tools, skills, or denied access without claiming affected steps ran. Missing baselines or image comparisons cannot support a parity claim.

1. Establish the baseline first, before any migration: a visual regression harness that screenshots the current component across its states, plus the target when matching two implementations. No baseline, no parity claim. A blocking prerequisite, not a follow-up.
2. Anti-shortcut clauses, stated and held: no harness modifications, no baseline tampering, no component restructuring to make a diff pass. If the baseline looks wrong, stop and ask, don't edit it.
3. Migrate one component at a time. Parallelize across worktrees, one owner per component (the **principle-separate-before-serializing-shared-state** principle skill). Shared primitives migrate first as a blocking phase.
4. Verify each component against its baseline via image diff on the matching surface via the control skill. A nonzero diff is a fail. Investigate the pixel delta. For each component, keep testing evidence-grounded changes until the diff is zero or a concrete blocker prevents further progress. Report the blocker and do not count it as a pass.
5. Run **Opening a PR** (`opening-a-pr.md`) for task-authorized PR preparation or creation, per component or per safe batch.

**Reply:** components migrated, the diff result for each, the baseline harness location, what's left.
