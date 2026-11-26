# How on three narrow code questions

How now answers a narrow lookup directly and cites the implementation. Both routes answered all three questions correctly. The delegated route used a coordinator and a separate explainer to reach the same answers. The complex investigation workflow still uses independent explorers.

## Questions and grading

The questions refer to commit `c0f1d31977dcddfac75f6c19e413d0ba8f8aefb7`. Each answer had to give the behavior below and cite the lines that establish it.

| Question | Expected answer |
| --- | --- |
| What does `load_index` return when a nested registry object repeats a key? | An empty dictionary and an error list naming the duplicate key. [JSON reader](../scripts/check.py#L141) |
| Do watches for `pkg` and `pkg/` match `pkg`, `pkg/x`, `pkg-old`, and a missing path? | In order, the first watch returns true, true, false, false. The second returns false, true, false, false. [Path matching](../scripts/monitor_upstream.py#L186) |
| Where does `parse_status` put the original path of a rename, and what happens if it is missing? | The tracked record gets an `original_path` field. A missing or empty original path raises `AuditError`. [Status parser](../skills/harness/scripts/worktree-audit.py#L76) |

## Method and observations

Run each route in a fresh, read-only Codex CLI session against the same checkout. Give it all three questions in order and ask for a brief answer with exact file and line references. For the direct route, ask it to inspect the files itself. For the delegated route, ask it to use the checkout's How simple-lookup workflow and send the same questions to one read-only explainer.

The recorded comparison used Codex CLI 0.172.0 and the configured gpt-6.2-astra model at high reasoning effort. The session records confirm one child for the delegated run and none for the direct run. I checked the answers and citations against the three implementations.

| Recorded run | Correct answers with supporting citations | Elapsed time for all three | Input tokens, including cached | Cached input tokens | Output tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct | 3 of 3 | 19.68 s | 53,855 | 27,648 | 485 |
| Delegated, coordinator | 3 of 3 | 75.27 s including child | 205,192 | 187,776 | 939 |
| Delegated, explainer | Included above | Included above | 94,224 | 91,520 | 541 |

Elapsed time covers CLI startup through process exit. Token counts come from the individual session records. An earlier trial of each route used ephemeral sessions. The recorded pair ran in the reverse order so the child and its token counts could be checked. The checkout was shared and cache usage differed. These observations support removing mandatory delegation for these lookups. They do not establish a general timing difference, a dollar cost, or comparative quality on cross-cutting work.

A fresh agent then used the revised skill on a fourth question about changes to a source's link or observed revision. It traced the fingerprint calculation, ran it with each field changed, and correctly reported that both changes leave the digest unchanged. It cited the two relevant lines and answered without a delegate. [Fingerprint calculation](../scripts/monitor_upstream.py#L324)
