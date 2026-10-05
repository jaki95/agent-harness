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
5. Read changed-file details in the issue. Open the linked workflow run and download `upstream-skill-report` for complete patches.
6. Configure the recurring Codex reviewer below to receive analysis and suggested next actions in comments.

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

## Review each new queue with Codex

The recurring reviewer checks the digest every fifteen minutes. Each new actionable queue generation receives one Codex analysis comment covering every pending source, local customizations, suggested decisions, concrete next actions, and evidence limits. Identical findings trigger no model call and no new comment. Detection stays on the weekly Actions schedule; manually triggered detections receive the same reviews.

The reviewer uses an existing authenticated Codex CLI and authenticated `gh` on an available Linux host with a systemd user manager. It needs no API key or repository secret. The host must remain running and the user manager must remain active for unattended reviews. Check `loginctl show-user "$USER" --property=Linger` if the host relies on timers after logout. Codex CLI 0.160.0 supports the execution options used here. A later incompatible CLI change is reported as a review failure rather than treated as completion.

The worker fetches current harness `main` into a temporary bare repository and reads only regular registry and skill files from its pinned commit. Dirty working-tree files are irrelevant. It fetches each queued upstream commit by its exact SHA, even when the upstream ref has advanced. It verifies the changed paths, object IDs, and modes against the detector snapshot. If current registry tracking no longer matches the queue, run detection again. Evidence has a total 1 MiB limit. Oversized evidence fails without presenting a partial patch as a complete review.

Codex receives these files and patches as untrusted data in a structured prompt. Its shell, apps, web search, image, and delegation features are disabled; its sandbox is read-only and project rules are ignored. The worker rejects execution traces containing tool calls or unknown execution items. It validates exact source coverage, recommendations, nonempty actions, and references to supplied evidence paths before publication. A completed review never adopts material, installs skills, or advances review revisions.

Stage a versioned maintenance bundle in a stable location, separate from disposable worktrees and runtime skills. All paths below are explicit examples to replace with host paths. Locate existing executables with `command -v codex`, `command -v gh`, and `command -v python3`.

```sh
python3 scripts/install_upstream_reviewer.py \
  --runtime-dir /absolute/stable/upstream-review/version-1 \
  --state-dir /absolute/state/upstream-review \
  --unit-dir /absolute/systemd/user \
  --codex /absolute/bin/codex \
  --gh /absolute/bin/gh \
  --python /absolute/bin/python3 \
  --issue-repo OWNER/REPO \
  --model gpt-6.1-sol --effort high
```

The installer copies three maintenance scripts and writes a service and timer. It installs no dependencies or runtime skills and does not enable units. It uses the existing user's authentication. Omit `--model` to use the CLI default model, or specify the intended model explicitly. The service sets `PATH` for the supplied executables and `TMPDIR` under the state directory.

Run the staged command once to prove authentication, analysis, and issue delivery before enabling the timer. Supplying `--issue-repo` explicitly authorizes review comments.

```sh
TMPDIR=/absolute/state/upstream-review/scratch \
  /absolute/bin/python3 /absolute/stable/upstream-review/version-1/review_upstream.py \
  --state-dir /absolute/state/upstream-review --issue-repo OWNER/REPO \
  --codex /absolute/bin/codex --model gpt-6.1-sol --effort high
systemctl --user daemon-reload
systemctl --user enable --now agent-harness-upstream-review.timer
systemctl --user list-timers agent-harness-upstream-review.timer
```

The unit directory must be in the user's systemd search path. Check runs with `systemctl --user status agent-harness-upstream-review.service` and `journalctl --user -u agent-harness-upstream-review.service`. A model run has a ten-minute deadline; the service has a twenty-minute deadline. Failures post at most one comment per queue generation and error category, then retry after one hour. Restoring authentication or evidence availability needs no manual acknowledgement. Failed analyses never receive a completion marker.

Completed output is atomically cached before delivery. A retry verifies evidence again and reuses the output if its evidence digest matches. The worker rereads the queue before posting and discards stale delivery. Tagged review comments are the delivery record, including recovery after GitHub accepted a comment but the connection failed. A nonblocking local lock prevents overlapping timer and manual runs. Actions owns the issue body; the reviewer owns its comments. Every review states its queue generation and evidence revisions, so historical reviews remain distinguishable when a queue changes.

For an upgrade, stop the timer and active service, stage a new versioned bundle with the same state directory, reload systemd, prove a one-shot run, then enable the timer again. To disable recurring review:

```sh
systemctl --user disable --now agent-harness-upstream-review.timer
systemctl --user stop agent-harness-upstream-review.service
```

Disabling the reviewer leaves weekly detection and existing review comments available.

## Record the review

Review the upstream patch beside the customization comparison. Choose the changes to adopt, partially adopt, or reject.

Update `last_reviewed_revision` after considering the relevant changes. Advance `last_incorporated_revision` only when incorporating upstream material. Update the maintenance notes and any consequential review record in the same Git change. Follow [registry conventions](registry.md#review-decisions).

The monitor never adopts changes, updates registry revisions, installs skills, or creates an adoption PR.
