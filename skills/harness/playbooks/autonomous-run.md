### Autonomous run

**You own the exit condition. Define done, then drive to it without stopping.**

Use the host's execution, filesystem, verification, delegation, and supported watch or wake tools as the task requires. Resolve named skills through Harness's catalog rules. Follow current task authorization and host permissions. Report unavailable tools, access, or unattended execution without claiming an active watcher or heartbeat. Continue authorized work that does not depend on the missing capability.

1. State the exit condition as a checkable predicate before the first iteration (tests green, repro fixed, all N PRs merged, pixel-diff zero).
2. Pick a supported host watch or wake mechanism. An event to watch (CI, a merge, a ref advancing) gets an event watcher, using a host delegate when supported, with a long time-based heartbeat as fallback. No event gets a fixed-interval heartbeat sized to when the result is worth re-checking. Use only capabilities the host exposes and the task authorizes; if unattended execution is unavailable, report it without claiming a watcher or heartbeat remains active.
3. Each iteration makes the smallest change the evidence justifies, verifies it against the predicate, commits if it advanced, discards changes that didn't help. Belt-and-suspenders that "might help" gets reverted, not left to ride.
   Sequence the work via the **principle-sequence-verifiable-units** principle skill, verifying each unit before the next instead of batching checks at the end.
4. Address task-related broken skills, bugs, flaky verifiers, review noise, tooling failures, orphaned follow-ups, and fixable drift within authorized scope through Harness. Put independent fixes in their own PR when task-authorized. Record unrelated discoveries as concrete follow-ups rather than broadening the run. Do not park authorized reversible work for the human. Surface missing authorization or required host approval, genuine product or preference calls no experiment can settle, or a real dead end. Keep the predicate as the main drive, and return to it after each side fix.
5. Checkpoint every iteration via the **show-me-your-work** skill, a row for what changed and whether the predicate moved.
6. Stop when the predicate is met or the user explicitly pauses the run. A plateau is not a stop, so keep going and pivot your approach to push past it. Surface a genuine dead end rather than spinning, and never relax the predicate to declare victory.

**Reply:** the exit condition, iterations run, what landed, what was discarded, final predicate state.
