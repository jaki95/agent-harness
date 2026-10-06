#!/usr/bin/env python3
"""Capture read-only GitHub PR evidence. Collection never authorizes a merge."""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import threading
import time


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
PAGE_INFO = "totalCount pageInfo { hasNextPage endCursor }"
SNAPSHOT_QUERY = """query Snapshot($owner:String!,$name:String!,$number:Int!) {
  repository(owner:$owner,name:$name) { nameWithOwner pullRequest(number:$number) {
    id number url headRefOid baseRefOid baseRefName state isDraft
    mergeable mergeStateStatus reviewDecision mergedAt autoMergeRequest { enabledAt }
  } }
}"""
THREADS_QUERY = """query Threads($owner:String!,$name:String!,$number:Int!,$cursor:String) {
  repository(owner:$owner,name:$name) { nameWithOwner pullRequest(number:$number) {
    reviewThreads(first:100,after:$cursor) { nodes {
      id isResolved isOutdated path line
    } PAGE_INFO }
  } }
}""".replace("PAGE_INFO", PAGE_INFO)
COMMENTS_QUERY = """query Comments($id:ID!,$cursor:String) {
  node(id:$id) { ... on PullRequestReviewThread {
    id comments(first:100,after:$cursor) { nodes {
      id url body author { login } path line
    } PAGE_INFO }
  } }
}""".replace("PAGE_INFO", PAGE_INFO)
COMMITS_QUERY = """query Commits($owner:String!,$name:String!,$number:Int!,$cursor:String) {
  repository(owner:$owner,name:$name) { nameWithOwner pullRequest(number:$number) {
    commits(first:100,after:$cursor) { nodes { commit { id oid } } PAGE_INFO }
  } }
}""".replace("PAGE_INFO", PAGE_INFO)
CHECKS_QUERY = """query Checks($id:ID!,$prId:ID!,$cursor:String) {
  node(id:$id) { ... on Commit { id oid statusCheckRollup {
    contexts(first:100,after:$cursor) { nodes {
      __typename
      ... on CheckRun { id databaseId name status conclusion detailsUrl
        isRequired(pullRequestId:$prId) checkSuite { commit { oid } } }
      ... on StatusContext { id context state targetUrl
        isRequired(pullRequestId:$prId) commit { oid } }
    } PAGE_INFO }
  } } }
}""".replace("PAGE_INFO", PAGE_INFO)


class ReadError(Exception):
    pass


def field(value, key, expected, nullable=False):
    if not isinstance(value, dict) or key not in value:
        raise ReadError(f"missing field {key}")
    result = value[key]
    if nullable and result is None:
        return None
    if type(result) is not expected or (expected is str and not result):
        raise ReadError(f"invalid field {key}")
    return result


def stamp():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Snapshot:
    id: str
    repository: str
    number: int
    url: str
    head_sha: str
    base_sha: str
    base_ref: str
    state: str
    draft: bool
    mergeable: str
    merge_state: str
    review_decision: str | None
    merged_at: str | None
    auto_merge: bool


class Collector:
    def __init__(self, repo, number, timeout, max_pages):
        owner, name = repo.split("/")
        self.repo = repo
        self.variables = {"owner": owner, "name": name, "number": number}
        self.deadline = time.monotonic() + timeout
        self.max_pages = max_pages
        self.pages = 0
        self.bytes_read = 0
        self.receipt = {
            "schema_version": 1, "repository": repo, "number": number, "url": None,
            "started_at": stamp(), "finished_at": None, "capabilities": {},
            "before": None, "after": None, "capture_status": "incomplete",
            "review_threads": [], "current_checks": [], "historical_checks": [],
            "required_checks": {"observed_state": "unknown", "policy_state": "unknown", "items": []},
            "limitations": [],
            "scope_notes": [
                "History covers rollups for retained PR commits, not every rerun or deleted force-push commit.",
                "Equal refs do not freeze comments or CI during capture, or prevent changes after capture.",
                "Observed requirements cannot prove all configured required contexts have reported.",
                "Independent verification and merge authorization remain separate.",
            ],
        }

    def command(self, arguments, payload=None):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ReadError("global deadline exceeded")
        budget = min(MAX_RESPONSE_BYTES, MAX_TOTAL_BYTES - self.bytes_read)
        if budget <= 0:
            raise ReadError("total response byte limit exceeded")
        try:
            process = subprocess.Popen(["gh", *arguments], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as exc:
            raise ReadError(f"gh unavailable: {exc}") from exc
        buffers = [bytearray(), bytearray()]
        lock = threading.Lock()
        overflow = threading.Event()

        def drain(stream, buffer):
            try:
                while True:
                    chunk = stream.read(8192)
                    if not chunk:
                        break
                    with lock:
                        available = budget - sum(map(len, buffers))
                        buffer.extend(chunk[:max(0, available)])
                        if len(chunk) > available:
                            overflow.set()
                            process.kill()
                            break
            finally:
                stream.close()

        readers = [threading.Thread(target=drain, args=(stream, buffer), daemon=True)
                   for stream, buffer in zip((process.stdout, process.stderr), buffers)]
        for reader in readers:
            reader.start()
        try:
            process.stdin.write(payload or b"")
            process.stdin.close()
            process.wait(timeout=max(0.001, self.deadline - time.monotonic()))
            for reader in readers:
                reader.join(timeout=max(0, self.deadline - time.monotonic()))
            if any(reader.is_alive() for reader in readers):
                raise ReadError("global deadline exceeded while reading response")
        except subprocess.TimeoutExpired as exc:
            raise ReadError("global deadline exceeded") from exc
        except OSError as exc:
            raise ReadError(f"gh input failed: {exc}") from exc
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            for reader in readers:
                reader.join(timeout=0.1)
            self.bytes_read += sum(map(len, buffers))
        if overflow.is_set():
            raise ReadError("response byte limit exceeded")
        if process.returncode:
            message = bytes(buffers[1]).decode(errors="replace").strip().replace("\n", " ")[:300]
            raise ReadError(f"gh read failed ({process.returncode}): {message}")
        return bytes(buffers[0])

    def query(self, document, variables):
        payload = json.dumps({"query": document, "variables": variables}).encode()
        raw = self.command(["api", "graphql", "--input", "-"], payload)
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise ReadError("invalid JSON response") from exc
        if not isinstance(value, dict) or value.get("errors"):
            raise ReadError("GraphQL response errors")
        return field(value, "data", dict)

    def pr(self, data):
        repository = field(data, "repository", dict)
        if field(repository, "nameWithOwner", str).casefold() != self.repo.casefold():
            raise ReadError("repository identity mismatch")
        return field(repository, "pullRequest", dict)

    def snapshot(self):
        value = self.pr(self.query(SNAPSHOT_QUERY, self.variables))
        snapshot = Snapshot(
            field(value, "id", str), self.repo, field(value, "number", int), field(value, "url", str),
            field(value, "headRefOid", str), field(value, "baseRefOid", str),
            field(value, "baseRefName", str), field(value, "state", str),
            field(value, "isDraft", bool), field(value, "mergeable", str),
            field(value, "mergeStateStatus", str), field(value, "reviewDecision", str, True),
            field(value, "mergedAt", str, True), field(value, "autoMergeRequest", dict, True) is not None,
        )
        if snapshot.number != self.variables["number"]:
            raise ReadError("PR identity mismatch")
        for sha in (snapshot.head_sha, snapshot.base_sha):
            if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
                raise ReadError("invalid snapshot commit SHA")
        return snapshot

    def connection(self, document, variables, extract):
        cursor, seen_cursors, seen_ids = None, set(), set()
        expected_total = None
        while True:
            if self.pages >= self.max_pages:
                raise ReadError("global page limit exceeded")
            self.pages += 1
            connection = extract(self.query(document, {**variables, "cursor": cursor}))
            nodes = field(connection, "nodes", list)
            total = field(connection, "totalCount", int)
            if total < 0 or (expected_total is not None and total != expected_total):
                raise ReadError("connection total changed or invalid")
            expected_total = total
            page = field(connection, "pageInfo", dict)
            more = field(page, "hasNextPage", bool)
            next_cursor = field(page, "endCursor", str, True)
            for node in nodes:
                record = node if isinstance(node, dict) and "id" in node else field(node, "commit", dict)
                identity = field(record, "id", str)
                if identity in seen_ids:
                    raise ReadError("duplicate connection node")
                seen_ids.add(identity)
                yield node
            if not more:
                if len(seen_ids) != expected_total:
                    raise ReadError("connection count does not match totalCount")
                return
            if not nodes or not next_cursor or next_cursor in seen_cursors:
                raise ReadError("pagination did not advance")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def threads(self):
        for value in self.connection(THREADS_QUERY, self.variables,
                                     lambda data: field(self.pr(data), "reviewThreads", dict)):
            thread = {"id": field(value, "id", str), "resolved": field(value, "isResolved", bool),
                      "outdated": field(value, "isOutdated", bool), "path": field(value, "path", str),
                      "line": field(value, "line", int, True), "comments": []}
            self.receipt["review_threads"].append(thread)

            def comments(data):
                node = field(data, "node", dict)
                if field(node, "id", str) != thread["id"]:
                    raise ReadError("thread identity mismatch")
                return field(node, "comments", dict)

            for comment in self.connection(COMMENTS_QUERY, {"id": thread["id"]}, comments):
                author = field(comment, "author", dict, True)
                body = comment.get("body")
                if not isinstance(body, str):
                    raise ReadError("invalid comment body")
                thread["comments"].append({
                    "id": field(comment, "id", str), "url": field(comment, "url", str), "body": body,
                    "author": field(author, "login", str) if author else None,
                    "path": field(comment, "path", str), "line": field(comment, "line", int, True),
                })

    def checks(self, before):
        commits = []
        for value in self.connection(COMMITS_QUERY, self.variables,
                                     lambda data: field(self.pr(data), "commits", dict)):
            commit = field(value, "commit", dict)
            commits.append((field(commit, "id", str), field(commit, "oid", str)))
        if before.head_sha not in [sha for _, sha in commits]:
            raise ReadError("published head absent from retained PR commits")
        for identity, sha in commits:
            def contexts(data):
                node = field(data, "node", dict)
                if field(node, "id", str) != identity or field(node, "oid", str) != sha:
                    raise ReadError("queried commit identity mismatch")
                rollup = field(node, "statusCheckRollup", dict, True)
                if rollup is None:
                    return {"nodes": [], "totalCount": 0, "pageInfo": {"hasNextPage": False, "endCursor": None}}
                return field(rollup, "contexts", dict)

            for value in self.connection(CHECKS_QUERY, {"id": identity, "prId": before.id}, contexts):
                kind = field(value, "__typename", str)
                if kind == "CheckRun":
                    observed_sha = field(field(field(value, "checkSuite", dict), "commit", dict), "oid", str)
                    check = {"run_id": field(value, "databaseId", int), "name": field(value, "name", str),
                             "status": field(value, "status", str),
                             "conclusion": field(value, "conclusion", str, True),
                             "url": field(value, "detailsUrl", str, True)}
                elif kind == "StatusContext":
                    observed_sha = field(field(value, "commit", dict), "oid", str)
                    check = {"run_id": None, "name": field(value, "context", str),
                             "status": field(value, "state", str), "conclusion": None,
                             "url": field(value, "targetUrl", str, True)}
                else:
                    raise ReadError("unsupported check context type")
                if observed_sha != sha:
                    raise ReadError("check commit attribution mismatch")
                check.update(id=field(value, "id", str), kind=kind, head_sha=observed_sha,
                             required=field(value, "isRequired", bool))
                check["observed_state"] = check_state(check)
                target = "current_checks" if observed_sha == before.head_sha else "historical_checks"
                self.receipt[target].append(check)

    def collect(self):
        before, after = None, None
        failures = self.receipt["limitations"]
        try:
            version = self.command(["--version"]).decode(errors="replace").splitlines()
            self.receipt["capabilities"]["gh_version"] = version[0] if version else None
            help_text = self.command(["api", "--help"]).decode(errors="replace")
            if "--input" not in help_text:
                raise ReadError("gh api lacks --input capability")
            self.receipt["capabilities"]["graphql_input"] = True
            before = self.snapshot()
            self.receipt["before"] = asdict(before)
            self.receipt["url"] = before.url
            self.threads()
            self.checks(before)
            self.receipt["capabilities"]["selected_graphql_fields"] = True
        except ReadError as exc:
            failures.append(str(exc))
        if before:
            try:
                after = self.snapshot()
                self.receipt["after"] = asdict(after)
            except ReadError as exc:
                failures.append(f"final snapshot unavailable: {exc}")
        changed = before and after and (
            before.id, before.number, before.url, before.head_sha, before.base_sha, before.base_ref, before.state
        ) != (after.id, after.number, after.url, after.head_sha, after.base_sha, after.base_ref, after.state)
        if changed:
            failures.append("PR identity or published refs changed during capture")
        self.receipt["capture_status"] = "changed" if changed else "incomplete" if failures else "complete"
        required = [check for check in self.receipt["current_checks"] if check["required"]]
        states = {check["observed_state"] for check in required}
        observed = ("unknown" if failures or "unknown" in states else "fail" if "fail" in states
                    else "pending" if "pending" in states else "pass" if states else "none_observed")
        self.receipt["required_checks"].update(observed_state=observed, items=required)
        self.receipt["finished_at"] = stamp()
        return self.receipt


def check_state(check):
    if check["kind"] == "StatusContext":
        return {"SUCCESS": "pass", "PENDING": "pending", "ERROR": "fail", "FAILURE": "fail"}.get(check["status"], "unknown")
    if check["status"] in {"QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED", "PENDING"}:
        return "pending"
    if check["status"] != "COMPLETED":
        return "unknown"
    if check["conclusion"] in {"SUCCESS", "NEUTRAL", "SKIPPED"}:
        return "pass"
    if check["conclusion"] in {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE"}:
        return "fail"
    return "unknown"


def summarize(receipt):
    before = receipt["after"] or receipt["before"] or {}
    threads = receipt["review_threads"]
    optional_failures = sum(not check["required"] and check["observed_state"] == "fail"
                            for check in receipt["current_checks"])
    lines = [f"PR {receipt['repository']}#{receipt['number']}",
             f"Capture {receipt['capture_status']}", f"Head {before.get('head_sha', 'unknown')}",
             f"Base {before.get('base_sha', 'unknown')}",
             f"Merge state {before.get('merge_state', 'unknown')}; review {before.get('review_decision') or 'unknown'}",
             f"Required observed {receipt['required_checks']['observed_state']}; policy unknown",
             f"Threads {len(threads)}; unresolved {sum(not thread['resolved'] for thread in threads)}; outdated {sum(thread['outdated'] for thread in threads)}",
             f"Current checks {len(receipt['current_checks'])}; optional failures {optional_failures}",
             f"Historical retained rollup contexts {len(receipt['historical_checks'])}",
             f"Collection limitations {len(receipt['limitations'])}; see JSON for full findings and scope.",
             "Independent verification and merge authorization remain separate."]
    for limitation in receipt["limitations"][:4]:
        lines.append("Limitation " + " ".join(limitation.split())[:240])
    return "\n".join(lines) + "\n"


def positive_int(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def positive_timeout(value):
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("number", type=positive_int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=positive_timeout, default=60)
    parser.add_argument("--max-pages", type=positive_int, default=200)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("--repo must be OWNER/REPO")
    receipt = Collector(args.repo, args.number, args.timeout, args.max_pages).collect()
    encoded = json.dumps(receipt, indent=2) + "\n"
    if args.output:
        try:
            args.output.write_text(encoded, encoding="utf-8")
        except OSError as exc:
            print(f"Receipt output failed: {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(encoded)
    sys.stderr.write(summarize(receipt))
    return 0 if receipt["capture_status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
