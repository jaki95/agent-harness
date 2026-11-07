---
name: swarm
description: "Fan out N parallel workers, drain them, and return one report. Use for /swarm, 'swarm this', or parallel coverage, races, gauntlets, and exploration."
disable-model-invocation: true
---

# Swarm

## Start

Open a todo list with one entry per phase when the host exposes that tool; otherwise record the phases in the task plan and follow them directly. Use available host delegation tools within task authorization, permission, and concurrency limits. Resolve named skills through the host catalog. Missing delegation leaves the swarm incomplete and is reported without inventing worker results.

1. Frame
2. Fan out
3. Aggregate
4. Report

## Phase A: Frame

1. State the done predicate and the artifact or report the swarm must return.
2. Choose the shape. Partition into slices, race N workers on identical briefs, or mix both. For a race or mixed shape, declare `first pass`, `rank all`, or `best-of` before spawning.
3. Pick worker models from the host's existing `swarm workers` or task-role configuration; otherwise inherit the parent model. Do not invent a model name or read a personal configuration path. If a configured model is unavailable, use an available configured fallback or parent inheritance and disclose it. Model diversity is optional. For a requested model race, name each arm's actual model up front and report unavailable requested arms as coverage gaps. Use configured role settings for reasoning and speed where supported; otherwise inherit the host defaults.
4. Give each worker its own writable output when it writes. When workers verify or measure commits, each brief names the exact SHAs. A measurement brief also names the method (sample count, what one sample is, order). The worker records both in its result.

## Phase B: Fan out

Prepare all N independent briefs and dispatch workers through supported host tools, using background execution when available and the step 3 models or parent inheritance. Fill available concurrency slots and refill as workers finish until all N have been dispatched. Use execution environments with the files, controls, and credentials each worker needs; do not assume a cloud worker can access the user's machine.

When a worker must start from a non-default pushed branch, use the host's supported branch or worktree setup and verify the actual checkout SHA before accepting results.

Every brief stands alone. Include the goal, scope, exact slice or race arm, how to verify, and what to report. Reports use `PASS`, `ISSUES`, or `BLOCKED` with evidence. A worker that can prove a defect reports `ISSUES` and lists every issue it can prove, not only the first.

If a worker drops out, proceed with N-1 and note it.

## Phase C: Aggregate

Read the terminal results. Drop a result that does not record the SHAs and method its brief names, and respawn that worker once. After a second miss, record a gap. A gap does not count as a pass. For coverage, every required slice needs a result. For a race, apply the selection rule declared up front. Use first pass, rank all, or best-of. Do not paste raw worker dumps.

## Phase D: Report

Return one consolidated in-chat report with a result table, issue one-liners, gaps or dropouts, and the race rule when used.
