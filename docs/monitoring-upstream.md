# Keep track of external skill updates

Use the monitor to review upstream changes without changing local skills or registry revisions. Python 3.10 or newer and Git are required. GitHub Actions publishes the queue with its workflow token.

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

Exit code `0` means every comparison completed, including comparisons with pending changes. Exit code `1` means detection or publication failed. An unknown status requires investigation. Missing paths, unavailable commits or refs, rewritten history, unavailable comparison evidence, and command limits cannot count as a clean result. Commands have a 90-second timeout and a 2 MiB evidence limit. The detector reads the watched trees first. If they differ, it streams the repository-wide diff to identify moves across watch boundaries. Only matching change records count toward the evidence limit for that diff. Oversized watched evidence fails visibly.

## Receive the weekly digest

1. Merge `.github/workflows/monitor-upstream.yml` to `main` to activate the schedule.
2. Enable GitHub Actions and issue creation for the repository if its settings restrict them.
3. Run **Monitor upstream skills** manually or wait for the Monday 08:17 UTC schedule.
4. Each new batch creates an **External skill updates** issue. Subscribe to each new issue or enable repository issue notifications; subscriptions to completed batches do not carry over.
5. Read the source summary in the issue. Open the linked workflow run and download `upstream-skill-report` for complete patches.
6. Configure the [issue-driven operator](upstream-operator.md) to receive numbered proposals, discuss changes and approve selected items on the issue.

The workflow runs only on `main`. Scheduled and manual runs share the `upstream-skill-monitor` concurrency group, so one run at a time can create or update the queue. Its job has read access to contents and write access to issues. It preserves reports even when detection or publication fails, and the workflow retains a failed result.

[GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) run on the default branch. Scheduling is best effort. Runs can be delayed or dropped under load. GitHub disables schedules in inactive public repositories after 60 days. Use the manual trigger when you need a current comparison.

The monitor recognizes a queue issue by its GitHub author and the marker on its first line. It recognizes a notification by its author and full generated body. The default monitor publishers are `github-actions[bot]` and the owner in `OWNER/REPO`. Keep review discussion in comments. Each batch starts at generation 1, and issue creation delivers its initial notification. Later queue changes within that batch add one tagged notification comment per generation. Identical findings stay quiet, including runs with unrelated upstream heads or different transport error messages. Notification delivery follows your GitHub subscription settings.

When a batch exceeds the 60,000-byte issue limit, the monitor stores the exact queue snapshot in numbered comments on that issue. It confirms the parts before updating the issue body with their count and SHA-256 digest. The reviewer accepts parts only from configured monitor accounts and verifies the digest before analysis. The prior generation stays readable during upload. For a new batch, the reviewer waits until its first snapshot is complete. Rerunning the monitor reuses parts already delivered.

The linked Actions artifact retains full patches for 30 days. Snapshot comments stay with the issue so a late reviewer needs only the existing issue and repository access. A missing or edited part prevents review and reports a snapshot error. Upgrade the installed reviewer before publishing a batch in this format. The updated worker also reads older inline snapshots.

A source outage preserves its previous pending file identities when the repository, ref, watched paths, and reviewed revision still match. It reports the outage and keeps the issue open. A changed review revision or removed registry source drops its old proposal. Invalid registry data preserves the previous queue until the registry becomes readable again.

Manually closing an unresolved issue does not acknowledge a review. The next run reopens it. The monitor closes the issue only when all configured comparisons are clean. A closed issue with a valid clean snapshot is a completed batch: later detections leave its body and comments unchanged and create a fresh issue for new changes or errors. Clean detections with only completed history stay quiet.

An open issue with a clean snapshot remains the current batch until closure succeeds, so an interrupted close can be retried. Closed issues with pending changes or errors remain unfinished. Multiple unfinished marked issues require manual duplicate cleanup, while malformed snapshots require repair before detection or review can continue. Both the monitor and reviewer use these rules.

A push to `main` that changes `registry/skills.json` runs detection again. With the issue-driven operator active, it reconciles PR receipts before closing the batch. If fresh upstream changes are already pending at that detection, the current batch remains open until those changes are reviewed too.

## Request a publication from the command line

Run the monitor on the target repository's `main` with a GitHub account that can dispatch workflows:

```sh
gh workflow run monitor-upstream.yml --repo OWNER/REPO --ref main
```

The workflow reads the registry on `main` and publishes the result. To inspect an unmerged checkout, run the local report command above. Replace older local `--issue-repo` publication commands in scripts and timers with the workflow dispatch before the next run.

If previous queues used a separate publisher account, retain its login in the repository's `UPSTREAM_MONITOR_LOGIN` Actions variable and the reviewer installer's `--monitor-login` argument. This lets the workflow and reviewer find existing issues and snapshot parts during the transition.

## Review and approve changes on the issue

The [private operator](upstream-operator.md) uses one-shot jobs for proposals and adoption. Each item names the upstream revision, the proposed change, local behavior to preserve, dependencies and a verification task. Ask a question in a comment, or post a new standalone command from the configured owner account.

| Example | Effect |
| --- | --- |
| `approve P3` | Approve eligible items from proposal 3. |
| `approve P3 items 1,3` | Approve this selection as one PR. Dependencies need their own approval. |
| `hold P3 item 1` | Stop merging this item and its dependants. A merge already submitted requires a separate revert decision. |
| `defer P3 item 2` | Leave this item open until relevant evidence changes or you revisit it. |
| `revisit item 2` | Ask the worker to reconsider the item. |

The worker rereads the conversation when it reconnects and before a write. Each approval has one branch. CI and an independent check of the final head gate merging. Changes to approval, permissions or merge policy require the operator to merge the PR. A merged decision updates the source repository. Refresh installed skills separately.

## Standalone analysis-only reviewer

For an installation using only the standalone reviewer, its optional timer checks the published digest on the installed schedule. Keep this timer disabled when using the private operator. Each new actionable queue generation receives a Codex review covering every pending source, local customizations, suggested decisions, concrete next actions, and evidence limits. Identical findings trigger no model call and no new comment. Detection stays on the weekly Actions schedule; manually triggered detections receive the same reviews.

The reviewer uses an existing authenticated Codex CLI and authenticated `gh` on an available Linux host with a systemd user manager. It needs no API key or repository secret. The host must remain running and the user manager must remain active for unattended reviews. Check `loginctl show-user "$USER" --property=Linger` if the host relies on timers after logout. Codex CLI 0.160.0 supports the execution options used here. A later incompatible CLI change is reported as a review failure rather than treated as completion.

The worker fetches current harness `main` into a temporary bare repository and reads regular registry, skill, and matching maintainer test files from its pinned commit. Dirty working-tree files are irrelevant. It fetches each queued upstream commit by its exact SHA, even when the upstream ref has advanced. It verifies the changed paths, object IDs, and modes against the detector snapshot. If current registry tracking no longer matches the queue, run detection again. The worker reads each local entrypoint and looks for local counterparts to changed upstream files by their package-relative paths. For tests kept outside an installed package, it also checks `tests/<skill>/test/` for a changed upstream `scripts/test/` file and `tests/<skill>/package.json` for a changed upstream `scripts/package.json`. It reports how many other package files it omitted and which changed paths lack a matching file in the model input. Matching names establish candidates for comparison. Each model request includes complete patches for its selected sources and at most 1 MiB of evidence. The worker splits larger batches across requests.

If a source exceeds the limit on its own or its evidence cannot be verified, the worker lists it as incomplete and reviews the other sources. The partial comment includes the findings and identifies sources requiring manual review or a successful retry. It does not mark the queue complete. A queue-wide registry or detector error still blocks the review.

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

The installer copies three maintenance scripts and writes a service and timer. It installs no dependencies or runtime skills and does not enable units. It uses the existing user's authentication. Omit `--model` to use the CLI default model, or specify the intended model explicitly. The service runs the exact Python, Codex, and GitHub CLI executables supplied at installation. It sets `TMPDIR` under the state directory.

Run the staged command once to prove authentication, analysis, and issue delivery before enabling the timer. Supplying `--issue-repo` explicitly authorizes review comments.

```sh
TMPDIR=/absolute/state/upstream-review/scratch \
  /absolute/bin/python3 /absolute/stable/upstream-review/version-1/review_upstream.py \
  --state-dir /absolute/state/upstream-review --issue-repo OWNER/REPO \
  --codex /absolute/bin/codex --gh /absolute/bin/gh --model gpt-6.1-sol --effort high
systemctl --user daemon-reload
systemctl --user enable --now agent-harness-upstream-review.timer
systemctl --user list-timers agent-harness-upstream-review.timer
```

The unit directory must be in the user's systemd search path. Check runs with `systemctl --user status agent-harness-upstream-review.service` and `journalctl --user -u agent-harness-upstream-review.service`. A model run has a ten-minute deadline; the service has a twenty-minute deadline. Failures post at most one comment per queue generation and error category, then retry after one hour. Restoring authentication or evidence availability needs no manual acknowledgement. Failed analyses never receive a completion marker.

Each successful model request is atomically cached before the next request or delivery. A retry verifies evidence again and reuses each result whose evidence digest matches. An unrelated change on Harness main does not trigger a new model call or a second partial review comment. Each published receipt records the revision used to verify the evidence. The cache identity includes the issue number as well as its generation and fingerprint, so a new batch cannot reuse the previous batch's delivery record. The worker rereads the queue before posting and discards stale delivery, including a change to another issue. The reviewer obtains its login from authenticated GitHub access. Only its own review comments with the generated heading and exact final marker count as delivery records. Keep the same reviewer account when upgrading to recognize its existing receipts. A short review uses one comment. The reviewer splits oversized reviews into numbered parts of at most 60,000 UTF-8 bytes and posts the summary receipt after reading back all parts. On retry it resumes with missing parts. If GitHub accepted a comment before the connection failed, the corresponding record confirms delivery. A nonblocking local lock prevents overlapping timer and manual runs. The monitor owns the issue body and any snapshot parts. The reviewer owns its analysis comments. Every review states its queue generation and evidence revisions, so historical reviews remain distinguishable when a queue changes.

For an upgrade, stop the timer and active service, stage a new versioned bundle with the same state directory, reload systemd, prove a one-shot run, then enable the timer again. The installed scripts are copies: merging changes to `main` does not upgrade the worker. Upgrade both `monitor_upstream.py` and `review_upstream.py` in the bundle before the detector creates a second marked issue. Older workers reject multiple marked issues even when all but one are completed.

For the batch-rotation rollout, retain the old bundle and units for rollback, then use the installer above with a new versioned runtime directory and the existing state and unit directories. After reloading systemd, inspect the service's `ExecStart` to confirm the new bundle. A quiet one-shot confirms discovery only; it does not prove fresh analysis or comment delivery. Re-enable the timer only after the check succeeds. Once multiple batches exist, rollbacks must retain support for completed issue history.

To disable recurring review:

```sh
systemctl --user disable --now agent-harness-upstream-review.timer
systemctl --user stop agent-harness-upstream-review.service
```

Disabling the reviewer leaves weekly detection and existing review comments available.

## Record the review

Review the upstream patch beside the customization comparison. Choose the changes to adopt, partially adopt, or reject.

Update `last_reviewed_revision` after considering the relevant changes. Advance `last_incorporated_revision` only when incorporating upstream material. Update the maintenance notes and any consequential review record in the same Git change. Follow [registry conventions](registry.md#review-decisions).

The monitor never adopts changes, updates registry revisions, installs skills, or creates an adoption PR.

When a watched upstream file is intentionally deleted, review the deletion and its replacement before retiring that path from the registry. Keep the baseline revision and document any independently maintained local implementation. A retired path no longer causes `missing-path`; this acknowledges the source change without requiring deletion of the local implementation.
