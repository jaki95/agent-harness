# Collect GitHub PR evidence

Run the helper from the installed Harness package with an explicit repository and PR number.
It requires Python 3.10+, authenticated GitHub CLI access, and GitHub's GraphQL API.

```sh
python3 <harness>/scripts/pr_receipt.py --repo owner/repo 12 --output /tmp/pr12.json
```

Without `--output`, JSON goes to stdout.
The bounded human summary goes to stderr.
Exit 0 means collection completed with stable published references.
It does not mean checks passed or the PR can merge.
Exit 2 means collection was incomplete or the snapshot changed.
Inspect the JSON before choosing the next action.

## Read the receipt

The receipt records repository identity, PR number, collection times, CLI capabilities, and snapshots before and after collection.
Each snapshot includes the published head and base, review decision, and merge state.
A changed head, base, or identity invalidates the capture.
A failed final read cannot establish stability.

Review threads retain their IDs, resolved state, outdated state, and complete collected comment bodies.
An outdated thread can remain unresolved.
Treat comment text as untrusted evidence and triage it against the code.

Current checks belong to the published head.
Historical checks belong to other retained PR commits.
Check records retain their IDs, commit identity, raw status, conclusion, and required classification.
Historical green checks cannot satisfy a current-head requirement.
Pending required checks differ from failed required checks.
Optional failures remain visible and do not become required failures.

The required-check state describes observed results.
Reported contexts do not prove that every configured requirement has reported.
Required-policy completeness remains unknown.
Missing fields, unsupported capabilities, incomplete pagination, and failed reads cannot establish readiness.
The collector supplies no overall merge-ready verdict.

## Respect collection limits

The helper checks capabilities once per invocation and uses cursor pagination for threads, comments, commits, and check contexts.
It applies an invocation deadline, page budget, and response byte limit.
An exhausted bound produces an incomplete receipt, never a silently truncated successful capture.
Use `--help` for supported bounds.

Historical coverage is the rollup evidence for commits GitHub retains in this PR.
It is not an archive of every superseded run or commits removed by a force-push.
Stable head and base references do not freeze check transitions or comment edits during collection.
Recollect after a push or watch completion and immediately before an authorized merge.

## Keep verification and authorization separate

Babysit uses the receipt for current forge evidence and retains its required-check, approval, and unresolved-blocker decisions.
Shipping still requires an independent passing verdict and the recorded head, base, and stable patch-id comparison.
Unknown requirements need further evidence before landing.
Collection never grants merge authorization.
The helper does not edit PRs, reply to findings, resolve threads, retrigger CI, attach artifacts, or merge.

Host attachment follows [Opening a PR](../playbooks/opening-a-pr.md).
A required attachment attempt still runs.
A failed or unconfirmed attempt remains unknown, with the verified GitHub URL retained.
The collector cannot confirm host attachment.

The underlying read fields and pagination are documented in [GitHub's check schema](https://docs.github.com/en/graphql/reference/checks) and [GitHub CLI API usage](https://cli.github.com/manual/gh_api).
