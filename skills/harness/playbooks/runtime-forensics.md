### Runtime forensics

**You own the diagnosis. Instrument the live process, don't theorize from source.** The deliverable is a cited diagnosis, not a fix.

Use the host's read/search, filesystem, profiling, live-instrumentation, and delegation tools and the matching control skill. Resolve named skills through Harness's skill catalog rules. Follow the user's authorization and the host's permission rules. Report unavailable tools, skills, or denied access without claiming affected steps ran or an untested mechanism was confirmed.

1. Capture the live signal on the matching surface via the control skill: a CPU profile for a spinning process, a heap snapshot for a leak, a CDP trace for a visual glitch. A real artifact, not a guess.
2. Reduce the artifact to the smoking gun: the function on the hot path, the retainer chain from the leaked object to a GC root, the loop firing without input. Parse large artifacts in a subagent (the **principle-guard-the-context-window** principle skill), keep the reduced finding in the main thread.
3. Prove the mechanism before believing it. Inject instrumentation into the running process using host-appropriate tooling, such as CDP eval, or hotfix the live code without reloading, to confirm the hypothesis cheaply.
4. Map the finding back to source: file, symbol, the line that allocates or schedules.
5. Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only forensics`.

**Reply:** the signal captured, the reduced finding, how you proved the mechanism, the source location, artifact paths. No fix unless asked. Hand back to **Bug fix** (`bug-fix.md`) or **Perf issue** (`perf-issue.md`) once the cause is known.
