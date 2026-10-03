# Worktree audit

Read this contract before cleanup. The helper requires Python 3.10+, Git supporting `worktree list --porcelain -z`, and filesystem access to the requested repository's worktrees. Optional PR reads require authenticated gh. It has no deletion, fetch, simulator, or cache-clearing command and installs no dependencies.

Resolve Harness through the host catalog and invoke its bundled helper:

```sh
python3 <Harness-package>/scripts/worktree-audit.py --repo <repo-dir> --base <fresh-trunk-ref>
python3 <Harness-package>/scripts/worktree-audit.py --repo <repo-dir> --base <fresh-trunk-ref> --usage <receipt.json> --github --sizes
```

`--repo` defaults to the current directory; `--base` defaults to `origin/main`. Select the actual trunk for other repositories. Refresh and verify that ref through authorized Git operations before relying on merge evidence. The helper does not fetch and cannot certify a local ref's freshness. `--github` reads current PR history for each branch. `--sizes` scans allocated size without following symlink directories; run large scans in the background when supported. Unrequested or inaccessible evidence is reported instead of inferred.

The JSON report includes repository identity, observation time, base SHA, disk usage on that filesystem, and each Git-listed worktree's path, head, branch, age, optional size, file status, PR state, usage receipt, merge evidence, errors, and advice. Git paths and status records are NUL-delimited, preserving spaces, newlines, and rename paths. Git commands disable optional locks to avoid refreshing indexes. Exit `0` means the report was produced, not that any worktree can be deleted. Fatal input or repository errors exit `1`; per-worktree evidence gaps remain in the report as holds.

## Supply current usage evidence

First run without `--usage` to get exact paths and heads. Gather the current project's ownership, active and pinned chats, and delegated worktrees through supported host tools or explicit user evidence. Do not search other projects' private histories. A receipt uses this shape, filled with actual values:

```json
{
  "repository": "<exact repository path from the audit>",
  "complete": true,
  "worktrees": [
    {
      "path": "<exact Git-listed path>",
      "head": "<current head SHA>",
      "owned": true,
      "active": false,
      "pinned": false,
      "abandoned": false,
      "evidence": "<current host record or explicit user evidence, including child worktrees>"
    }
  ]
}
```

Set completeness to true only after checking the relevant host records and delegated work. Missing, incomplete, wrong-repository, duplicate, or stale-head receipts do not establish inactivity or ownership. A matching head is necessary and does not prove that a receipt remains current; refresh activity evidence immediately before deletion. Explicit abandonment is its own fact and is not inferred from age or a closed PR.

## Interpret advice

The helper holds the primary and invocation worktrees, locked or unavailable trees, active or pinned work, unknown ownership/activity, tracked edits, untracked files, ignored content, detached heads, open PRs, incomplete metadata, and unconfirmed merge or abandonment. Untracked and ignored files may contain valuable work. Review them individually before any authorized disposal.

Merge evidence is either current HEAD ancestry under the chosen trunk SHA or a merged same-repository PR whose published head exactly matches the worktree. A closed-unmerged PR proves neither; a merged PR at an older head does not cover newer local commits. Failed or truncated GitHub reads stay explicit gaps. A retained branch ref must preserve committed work before removal, including explicitly abandoned work.

An `eligible-for-confirmation` bucket means the supplied facts pass the audit's initial gates. It grants no deletion permission. Recheck live HEAD and status, file preservation, ownership, and activity through the cleanup playbook before removing that exact candidate. Simulator IDs, runtimes, application state, and caches have separate ownership and preservation checks; the helper does not assess them.
