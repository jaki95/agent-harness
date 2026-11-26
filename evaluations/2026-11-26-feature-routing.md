# Adding a CLI filter through Feature

## Task and checks

The fixture extends `orch unit list` with an optional exact `--branch` filter. Existing list filters already establish the owning command, row format, and comparisons. Each fresh Git project started with the same [orchestration CLI](https://github.com/jaki95/agent-harness/blob/f6e39b1/skills/harness/scripts/orch.py#L403) and [tests](https://github.com/jaki95/agent-harness/blob/f6e39b1/scripts/tests/test_orch.py). The original [Feature playbook](https://github.com/jaki95/agent-harness/blob/f6e39b1/skills/harness/playbooks/feature.md) and a candidate with a conditional Architect step were the only workflow difference.

Both coordinators received the same prompt. Implement the filter, retain the order and contents of rows, combine all filters by intersection, match unassigned rows when given an explicit empty string, exercise the CLI, and obtain an independent read-only review. Each worked in a separate project. The grader was outside both projects.

To repeat the grading, add these units in order. Use `unit set` to assign state and branch. Leave the last branch unset.

| Unit | Track | State | Branch |
| --- | --- | --- | --- |
| a | build | building | one |
| b | ui | building | one |
| c | build | done | one |
| d | build | building | one-x |
| e | build | building | |

Use `unit list --json` and compare the entire rows with those returned by `unit set`. The unfiltered list must return a, b, c, d, e. Branch `one` must return a, b, c. Add state `building` and track `build` to select a. A missing branch and uppercase `ONE` must each return an empty list. Branch `''` must return e. State `building` and track `build` alone must still return a, d, e. The original CLI failed this grader at its first use of `--branch`.

## Results

Two fresh Codex CLI 0.172.0 sessions used gpt-6.2-astra at high reasoning effort. I ran the same seven CLI checks against both finished implementations. Both preserved full rows in order and produced byte-identical runtime code. Each added a regression test to the 16 existing tests.

| Route | Child agents observed in session records | Independent implementation review | CLI results | Fixture unit tests |
| --- | --- | --- | --- | --- |
| Architect | Seven. One source reader, three designers, one design judge, one implementer, one reviewer. | No findings | 7 of 7 | 17 of 17 |
| Existing pattern | Two. One implementer and one reviewer. | No findings | 7 of 7 | 17 of 17 |

The Architect route also exercised a branch starting with `+`, which the storage format escapes. Both implementations use the same existing comparison helper. A separate read-only session selected the existing-pattern route for the filter and Architect for a hypothetical change involving concurrent queue writers on separate hosts.

A third fresh project used the [final playbook](../skills/harness/playbooks/feature.md). Its coordinator selected one implementer and one independent reviewer. The result passed the same seven CLI checks.

This case supports keeping an independent implementation review and omitting design exploration when a neighboring feature already settles the design. It covers one read-only filter. The child counts measure delegation in these runs. They do not estimate time, cost, or review quality on features that change storage or ownership.
