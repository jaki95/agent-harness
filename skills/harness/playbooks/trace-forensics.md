### Trace forensics

**You own the diagnosis from the artifact. Load it, shape it, narrow to the cause, attribute to source.**

Use the host's filesystem, read/search, artifact-parsing, querying, and delegation tools. Resolve named skills through Harness's skill catalog rules. Follow the user's authorization and the host's permission rules. Report unavailable tools, skills, or denied access without claiming affected steps ran, and preserve the confidence limitations below.

Distinct from **Runtime forensics**, which instruments the live process. Here the capture already exists. The artifact is a fixed dataset, read it, don't re-run it. Keep tooling generic so the playbook stays portable: a DevTools or trace parser for cpuprofile and `.json.gz`, a text editor for a spindump, your heap tooling for a heapsnapshot.

1. Identify the format and load it with the right tool. Parse large artifacts in a subagent (the **principle-guard-the-context-window** skill) and keep the reduced finding in the main thread.
2. Transform the raw artifact into a form you can query using tools appropriate to its format. SQLite with one row per sample, frame, or node is an option when useful, rather than a requirement for every artifact. Reach the queryable shape before detailed analysis.
3. Narrow to the cause. Query for the frames that hold the most time and walk the call tree to the hot path. For a leak, follow the retainer chain from the leaked object to a GC root. For a spindump, find the thread stuck on-CPU or blocked and its wait reason.
4. Attribute to source. Map the hot frame to file, symbol, and line via the artifact's own symbols. A frame with no source mapping is not yet a diagnosis. Resolve the symbols, or say plainly the artifact does not carry them.
5. Confirm against a paired capture when you have one. Diff a before and after artifact. Without one, mark the finding as the strongest hypothesis the artifact supports, not a confirmed cause.
6. Hand back a cited diagnosis, no fix unless asked. Route to **Bug fix** (`bug-fix.md`) or **Perf issue** (`perf-issue.md`) once the cause is known. Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only forensics`.

**Reply:** the artifact and format, the reduced finding, the source location, the artifact paths, and whether a paired capture confirmed it.
