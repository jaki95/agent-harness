# Keep track of external skill updates

Use the monitor to review upstream changes without changing local skills or registry revisions. Python 3.10 or newer and Git are required. GitHub issue publication also requires an authenticated `gh` command with issue write access.

## Inspect changes locally

Run the detector from the repository root:

```sh
python3 scripts/monitor_upstream.py --output-dir work/upstream-report
```

Open `work/upstream-report/report.md` for the review proposal. Use `report.json` for source statuses, full object IDs, and old and new file modes.

To run from another directory, invoke the script by its full path. It finds the repository relative to its own file. Use `--root PATH` to inspect another harness checkout. Put reports outside `skills/`, `registry/`, `reviews/`, and `.git`.

If your host limits its system temporary directory, choose a writable scratch directory with the standard `TMPDIR` environment variable:

```sh
mkdir -p work/upstream-scratch
TMPDIR="$PWD/work/upstream-scratch" python3 scripts/monitor_upstream.py --output-dir work/upstream-report
```

The detector compares each source ref with its `last_reviewed_revision`. It fetches each repository and ref once into a temporary bare Git repository. The fetch keeps full commit history and requests a blob filter to avoid downloading unrelated historical file content. A server that ignores this filter can require more disk space. The detector never checks out or executes upstream files.

Watched paths cover files and directories. A trailing slash requires a directory. `.` watches the whole repository. Git treats path names literally. The report includes additions, deletions, mode changes, and moves into or out of watched paths. Unrelated upstream edits do not change the notification identity.

Each changed source includes its upstream patch. When one watched upstream `SKILL.md` exists at the incorporated revision, the report compares that entrypoint with the local skill. Inspiration without an incorporated revision uses the reviewed revision. The report includes maintenance notes. Supporting files need an explicit local mapping before you can judge their equivalence.

Exit code `0` means every comparison completed, including comparisons with pending changes. Exit code `1` means detection or publication failed. An unknown status requires investigation. Missing paths, unavailable commits or refs, rewritten history, unavailable comparison evidence, and command limits cannot count as a clean result. Commands have a 90-second timeout and a 2 MiB output limit. Oversized evidence fails visibly rather than presenting a partial patch as complete.

## Receive the weekly digest

1. Merge `.github/workflows/monitor-upstream.yml` to `main` to activate the schedule.
2. Enable GitHub Actions and issue creation for the repository if its settings restrict them.
3. Run **Monitor upstream skills** manually or wait for the Monday 08:17 UTC schedule.
4. When the first actionable result creates **External skill updates**, subscribe to that issue.
5. Open the linked workflow run and download `upstream-skill-report` to inspect complete evidence.

The workflow runs only on `main`. A single concurrency group serializes publishers. Its job has read access to contents and write access to issues. It preserves reports even when detection or publication fails, and the workflow retains a failed result.

[GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) run on the default branch. Scheduling is best effort. Runs can be delayed or dropped under load. GitHub disables schedules in inactive public repositories after 60 days. Use the manual trigger when you need a current comparison.

The issue body is machine-owned. Keep review discussion in comments. Its first creation delivers the initial notification. Later queue changes add one tagged notification comment per generation. Identical findings stay quiet, including runs with unrelated upstream heads or different transport error messages. Notification delivery follows your GitHub subscription settings.

A source outage preserves its previous pending file identities when the repository, ref, watched paths, and reviewed revision still match. It reports the outage and keeps the issue open. A changed review revision or removed registry source drops its old proposal. Invalid registry data preserves the previous queue until the registry becomes readable again.

Manually closing an unresolved issue does not acknowledge a review. The next run reopens it. The monitor closes the issue only when all configured comparisons are clean. It reopens the same issue for later changes. Multiple issues with the monitor marker require manual duplicate cleanup before publication can continue.

## Publish a local report to the issue

To authorize publication in a local run, supply the repository explicitly:

```sh
python3 scripts/monitor_upstream.py --output-dir work/upstream-report --issue-repo OWNER/REPO
```

Without `--issue-repo`, the command performs detection and writes local reports only. It does not infer a publication destination or subscribe other users.

## Record the review

Review the upstream patch beside the customization comparison. Choose the changes to adopt, partially adopt, or reject.

Update `last_reviewed_revision` after considering the relevant changes. Advance `last_incorporated_revision` only when incorporating upstream material. Update the maintenance notes and any consequential review record in the same Git change. Follow [registry conventions](registry.md#review-decisions).

The monitor never adopts changes, updates registry revisions, installs skills, or creates an adoption PR.
