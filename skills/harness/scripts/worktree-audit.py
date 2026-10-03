#!/usr/bin/env python3
"""Read-only worktree audit. Buckets are advice and never authorize deletion."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


class AuditError(Exception):
    pass


def command(argv, cwd):
    try:
        return subprocess.run(argv, cwd=cwd, capture_output=True, timeout=60,
                              env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuditError(f"{argv[0]} read failed: {exc}") from exc


def git(repo, *arguments):
    result = command(["git", "--no-optional-locks", "-C", str(repo), *arguments], repo)
    if result.returncode:
        raise AuditError(os.fsdecode(result.stderr).strip() or "git read failed")
    return result.stdout


def parse_worktrees(raw):
    rows, row = [], {}
    for token in os.fsdecode(raw).split("\0"):
        if not token:
            if row:
                if not row.get("path"):
                    raise AuditError("worktree porcelain record has no path")
                rows.append(row)
                row = {}
            continue
        key, _, value = token.partition(" ")
        if key == "worktree":
            row["path"] = value
        elif key == "HEAD":
            row["head"] = value
        elif key == "branch":
            row["branch"] = value.removeprefix("refs/heads/")
        elif key in ("locked", "prunable"):
            row[key] = value or True
        elif key in ("bare", "detached"):
            row[key] = True
    if row:
        raise AuditError("worktree porcelain record is not terminated")
    return rows


def parse_status(raw):
    entries = os.fsdecode(raw).split("\0")
    tracked, untracked, ignored = [], [], []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2] != " ":
            raise AuditError("malformed worktree status")
        state, path = entry[:2], entry[3:]
        if state == "??":
            untracked.append(path)
        elif state == "!!":
            ignored.append(path)
        else:
            record = {"status": state, "path": path}
            if "R" in state or "C" in state:
                if index >= len(entries) or not entries[index]:
                    raise AuditError("rename status has no original path")
                record["original_path"] = entries[index]
                index += 1
            tracked.append(record)
    return {"tracked": tracked, "untracked": untracked, "ignored": ignored}


def load_usage(path, repo):
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict) or not isinstance(value.get("repository"), str)
            or Path(value["repository"]).resolve() != repo
            or type(value.get("complete")) is not bool
            or not isinstance(value.get("worktrees"), list)):
        raise AuditError("usage file must identify this repository, completeness, and worktrees")
    if not value["complete"]:
        return {}
    result = {}
    for row in value["worktrees"]:
        if (not isinstance(row, dict) or not isinstance(row.get("path"), str)
                or not all(type(row.get(field)) is bool for field in ("owned", "active", "pinned", "abandoned"))
                or not isinstance(row.get("head"), str) or not row["head"]
                or not isinstance(row.get("evidence"), str) or not row["evidence"].strip()):
            raise AuditError("usage rows need path, head, ownership, activity, pin, abandonment, and evidence")
        key = str(Path(row["path"]).resolve())
        if key in result:
            raise AuditError("usage file has duplicate worktree paths")
        result[key] = row
    return result


def size_bytes(path):
    total, seen = 0, set()

    def fail(error):
        raise error

    for directory, folders, files in os.walk(path, followlinks=False, onerror=fail):
        for name in folders + files:
            item = Path(directory) / name
            stat = item.lstat()
            identity = (stat.st_dev, stat.st_ino)
            if identity in seen:
                continue
            seen.add(identity)
            total += stat.st_blocks * 512 if hasattr(stat, "st_blocks") else stat.st_size
    return total


def github_prs(repo, branch):
    fields = "number,state,headRefName,headRefOid,isCrossRepository"
    result = command(["gh", "pr", "list", "--head", branch, "--state", "all",
                      "--limit", "100", "--json", fields], repo)
    if result.returncode:
        raise AuditError(os.fsdecode(result.stderr).strip() or "GitHub PR lookup failed")
    rows = json.loads(result.stdout)
    if not isinstance(rows, list) or len(rows) >= 100:
        raise AuditError("GitHub PR history is incomplete or malformed")
    for row in rows:
        if (not isinstance(row, dict) or type(row.get("number")) is not int
                or row.get("state") not in ("OPEN", "MERGED", "CLOSED")
                or row.get("headRefName") != branch
                or not isinstance(row.get("headRefOid"), str)
                or type(row.get("isCrossRepository")) is not bool):
            raise AuditError("GitHub returned malformed PR metadata")
    return [row for row in rows if not row["isCrossRepository"]]


def classify(row):
    reasons = []
    usage = row["usage"]
    if row["primary"]:
        reasons.append("primary-worktree")
    if row["current"]:
        reasons.append("invocation-worktree")
    if row.get("locked"):
        reasons.append("locked-worktree")
    if row.get("bare") or row.get("prunable"):
        reasons.append("unavailable-worktree")
    if row["errors"]:
        reasons.append("incomplete-metadata")
    if usage is None or usage["head"] != row.get("head"):
        reasons.append("unknown-or-stale-usage")
    else:
        if not usage["owned"]:
            reasons.append("ownership-not-confirmed")
        if usage["active"] or usage["pinned"]:
            reasons.append("in-use-or-pinned")
    if row["tracked"]:
        reasons.append("tracked-edits")
    if row["untracked"]:
        reasons.append("untracked-files")
    if row["ignored"]:
        reasons.append("ignored-files-need-disposal-review")
    if not row.get("branch"):
        reasons.append("detached-head-needs-retention-review")
    if row["prs"] is not None and any(pr["state"] == "OPEN" for pr in row["prs"]):
        reasons.append("open-pr")
    if not row["merged"] and not (usage is not None and usage["abandoned"]):
        reasons.append("merge-or-abandonment-not-confirmed")
    return {"bucket": "hold" if reasons else "eligible-for-confirmation", "reasons": reasons}


def audit(repository, base, usage_path=None, use_github=False, sizes=False):
    requested = Path(repository).resolve()
    repo = Path(os.fsdecode(git(requested, "rev-parse", "--show-toplevel")).removesuffix("\n")).resolve()
    records = parse_worktrees(git(repo, "worktree", "list", "--porcelain", "-z"))
    usage = load_usage(usage_path, repo)
    base_sha = None
    base_error = None
    try:
        base_sha = os.fsdecode(git(repo, "rev-parse", "--verify", f"{base}^{{commit}}")).strip()
    except AuditError as exc:
        base_error = str(exc)
    result = []
    for index, record in enumerate(records):
        path = Path(record["path"])
        row = {**record, "primary": index == 0, "current": path.resolve() == repo,
               "tracked": [], "untracked": [], "ignored": [],
               "prs": None, "merged": False, "merge_evidence": None, "age_days": None,
               "size_bytes": None, "errors": [], "usage": usage.get(str(path.resolve()))}
        if not record.get("bare") and not record.get("prunable"):
            try:
                row.update(parse_status(git(path, "status", "--porcelain=v1", "-z",
                                            "--untracked-files=all", "--ignored=matching")))
                head = os.fsdecode(git(path, "rev-parse", "--verify", "HEAD^{commit}")).strip()
                if head != row.get("head"):
                    raise AuditError("worktree HEAD changed during discovery")
                timestamp = int(git(path, "log", "-1", "--format=%ct", "HEAD").strip())
                row["age_days"] = max(0, (int(datetime.now(timezone.utc).timestamp()) - timestamp) // 86400)
                if base_sha:
                    check = command(["git", "--no-optional-locks", "-C", str(path),
                                     "merge-base", "--is-ancestor", head, base_sha], path)
                    if check.returncode not in (0, 1):
                        raise AuditError("merge ancestry check failed")
                    if check.returncode == 0:
                        row.update(merged=True, merge_evidence=f"HEAD is an ancestor of {base_sha}")
                if use_github and row.get("branch"):
                    row["prs"] = github_prs(repo, row["branch"])
                    matching = next((pr for pr in row["prs"] if pr["state"] == "MERGED" and pr["headRefOid"] == head), None)
                    if matching:
                        row.update(merged=True, merge_evidence=f"PR #{matching['number']} merged at this exact head")
                if not base_sha and not row["merged"]:
                    row["errors"].append(f"merge base unavailable: {base_error}")
                if sizes:
                    row["size_bytes"] = size_bytes(path)
            except (AuditError, OSError, ValueError) as exc:
                row["errors"].append(str(exc))
        row.update(classify(row))
        result.append(row)
    disk = shutil.disk_usage(repo)
    return {"repository": str(repo), "observed_at": datetime.now(timezone.utc).isoformat(),
            "base": base, "base_sha": base_sha, "base_error": base_error,
            "github_queried": use_github, "usage_supplied": usage_path is not None,
            "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
            "worktrees": sorted(result, key=lambda row: -(row["size_bytes"] or 0))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--usage", type=Path, help="current host ownership and activity receipt")
    parser.add_argument("--github", action="store_true", help="read current PR history with authenticated gh")
    parser.add_argument("--sizes", action="store_true", help="scan allocated sizes without following symlinks")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(audit(args.repo, args.base, args.usage, args.github, args.sizes), indent=2))
        return 0
    except (AuditError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
