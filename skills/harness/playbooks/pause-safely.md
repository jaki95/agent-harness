### Pause safely

**You own a clean stop. Leave a checkpoint a cold-start agent can resume from.** This is explicit only. On "keep going", "going to bed, keep going", or "don't stop", do not pause.

Use available host filesystem, Git, execution, delegation, and matching verification tools within task authorization and host permissions. Resolve named skills through Harness's catalog rules and bundled resources from its installed package. Report unavailable tools, records, controls, or access without claiming an affected step completed. Compaction alone does not request a pause; checkpoint context and continue the active task.

1. Stop at a safe boundary. Finish the current atomic step or back out of it. Start nothing new. Send nested subagents a zero-writes hold and request supported cancellation or interruption; confirm stopped writers and report any unconfirmed stop.
2. Take no irreversible action to pause. No new PR. Push a checkpoint to an existing published branch only within existing task authorization and host permissions.
3. Make the work durable. Commit task-owned uncommitted edits as one clear `wip:` commit on the current branch so nothing is lost. Stage only task-owned paths or hunks; preserve unrelated edits without including them in the checkpoint. If ownership cannot be separated safely, retain the edits on disk and record that limitation. If the tree is broken, say so in the commit body in one line.
4. Write the resume note off-context. Capture intent, what you were doing, progress and what's verified, current state, next steps, key files, and gotchas. Write it to an authorized task or project location, or a host-provided checkpoint store. For compaction alone, save the resume context and continue; do not perform the pause or cancellation steps. If a show-me-your-work trail exists, point at it instead of duplicating it.

**Reply:** where you are in the loop, what's on disk versus still in your head (paths, no diff dumps), the commits you made and whether the tree is clean, and the first action on resume. This is a pause, not a final report.
