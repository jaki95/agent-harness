# Publish an existing pull request

Use `pr_publish.py` after the task authorizes the action.
It uses Python 3.10+, Git, authenticated `gh`, and GitHub's GraphQL and REST APIs.
The repository argument identifies the PR's base repository.
GitHub supplies its head repository and branch, including forks.
The helper does not accept a guessed destination branch or remote.

## Push the local commit

Record the published head from a fresh [PR receipt](pr-receipt.md).
Run from the checkout whose committed `HEAD` should replace it:

```sh
python3 <harness>/scripts/pr_publish.py push --repo owner/repo 12 --expected-head <published-sha>
```

The command checks the live PR and existing remote ref, then pushes to that exact ref with an explicit lease on the recorded SHA.
A missing branch, changed head, renamed target, or failed read stops publication.
The lease also rejects deletion or movement between the read and push.
It cannot create the first branch for a new PR.
The local branch name and `origin` do not select the destination.
Uncommitted files are not published.

By default, the local commit must descend from the recorded head, which must be available locally.
Use `--allow-rewrite` only for an authorized rebase or replacement of that PR's history.
It retains the same lease.
Use `--transport https` when Git credentials use HTTPS; the default is SSH.
Both URLs come from GitHub's head repository metadata.
The command confirms the remote ref and the PR head after the push.

## Merge one verified PR

Complete the independent review, patch identity comparison, current checks, approvals, and task authorization required by [Shipping](../playbooks/shipping.md).
Then run:

```sh
python3 <harness>/scripts/pr_publish.py merge --repo owner/repo 12 --expected-head <verified-published-sha>
```

The command reads native stack membership from GitHub.
It refuses a PR with any unmerged predecessor, including a closed predecessor that did not merge.
It sends one squash merge request with the expected head and rule bypass disabled.
GitHub chooses the configured merge queue when one exists.
The command never submits descendants or retargets branches.

GitHub's asynchronous merge API is required for native stacks.
It can merge every open predecessor of the requested PR, so only the current bottom PR is eligible here.
GitHub does not provide an atomic stack-version guard: avoid concurrent stack edits while landing, and recompute membership, head, base, and patch identity after each merge.
A native stack can rebase its next PR automatically.
Reuse no old head guard after that change.

The helper waits up to 10 seconds for the request result; `--wait 0` returns immediately.
A `pending` or `enqueued` result is not a completed merge.
The result includes GitHub's request details for the existing shipping watch to inspect.
Do not start another mutation loop.
An existing request conflict stops the command without a fallback or retry.
GitHub native stacks do not support auto-merge; wait for readiness and invoke this command for the current bottom PR.

## Read the result

JSON goes to stdout on a confirmed result.
Exit 0 means the push was confirmed, or the merge result and PR merged state were confirmed.
Exit 3 means the merge request remains pending or enqueued.
Exit 2 means the operation failed or its outcome could not be confirmed.
A failed write response can still follow an accepted write; inspect GitHub before retrying.
`--timeout` bounds each invocation, including reads, Git operations, and the merge wait.

This helper executes an authorized action and preserves its target and head guard.
It does not supply review verdicts, establish required-check completeness, or grant merge permission.
Unsupported stack APIs and unknown states stop the operation.
The [read-only receipt](pr-receipt.md) remains separate.

The API contracts are documented in [GitHub's stack endpoints](https://docs.github.com/en/rest/pulls/stacks), [asynchronous merge endpoints](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request-asynchronously), and [native stack merge rules](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-stacked-pull-requests).
