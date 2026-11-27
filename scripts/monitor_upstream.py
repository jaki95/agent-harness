#!/usr/bin/env python3
"""Detect upstream skill changes and optionally reconcile the current issue batch."""

import argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextlib import ExitStack
from dataclasses import asdict, dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse

from check import NAME, check_record, load_index


ROOT = Path(__file__).resolve().parents[1]
LIMIT = 2 * 1024 * 1024
TIMEOUT = 90
ISSUE_LIMIT = 60000
MARKER = "<!-- agent-harness-upstream-monitor:v1 -->"
STAGING = MARKER + "\nPreparing the first upstream review snapshot. The monitor will resume an interrupted upload."
SNAPSHOT_REF = re.compile(r"<!-- upstream-snapshot-parts:([0-9a-f]{64}):([1-9][0-9]{0,4}) -->")
SNAPSHOT = re.compile(r"<!-- upstream-snapshot:(.*?) -->")
ACTIONS_LOGIN = "github-actions[bot]"


@dataclass(frozen=True)
class Source:
    skill: str
    id: str
    repository: str
    ref: str
    paths: tuple
    reviewed: str
    incorporated: str | None
    notes: str

    @classmethod
    def from_registry(cls, skill, item, notes):
        return cls(skill, item["id"], item["repository"], item["ref"], watch_paths(item["paths"]),
                   item["last_reviewed_revision"], item["last_incorporated_revision"], notes)

    @property
    def key(self):
        return f"{self.skill}/{self.id}"


@dataclass(frozen=True)
class Change:
    kind: str
    old_path: str | None
    new_path: str | None
    old_object: str
    new_object: str
    old_mode: str
    new_mode: str


@dataclass(frozen=True)
class Result:
    source: Source
    status: str
    head: str = ""
    changes: tuple = ()
    error: str = ""
    detail: str = ""
    missing_paths: tuple = ()
    upstream_patch: str = ""
    customization_patch: str = ""
    comparison_note: str = ""


@dataclass(frozen=True)
class Report:
    results: tuple
    errors: tuple = ()

    @property
    def failed(self):
        return bool(self.errors or any(r.status == "unknown" for r in self.results))


class MonitorError(Exception):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(detail)


def run(args, *, env=None, limit=LIMIT, timeout=TIMEOUT, input=None, read_stdout=None):
    with ExitStack() as stack:
        out = stack.enter_context(tempfile.TemporaryFile())
        err = stack.enter_context(tempfile.TemporaryFile())
        incoming = stack.enter_context(tempfile.TemporaryFile())
        if input is not None:
            incoming.write(input)
            incoming.seek(0)
        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE if read_stdout else out, stderr=err,
                                    stdin=incoming if input is not None else subprocess.DEVNULL,
                                    env=env, start_new_session=os.name == "posix")
        except OSError as exc:
            raise MonitorError("command-unavailable", str(exc)) from exc
        reader = None
        try:
            deadline = time.monotonic() + timeout
            if read_stdout:
                pipe = stack.enter_context(proc.stdout)
                pool = stack.enter_context(ThreadPoolExecutor(max_workers=1))
                reader = pool.submit(read_stdout, pipe)
            while True:
                try:
                    proc.wait(timeout=max(0.001, min(0.1, deadline - time.monotonic())))
                    break
                except subprocess.TimeoutExpired:
                    if reader and reader.done():
                        reader.result()
                    if out.tell() + err.tell() > limit:
                        raise MonitorError("output-limit", "Command output exceeded the evidence limit")
                    if time.monotonic() >= deadline:
                        raise MonitorError("timeout", "Command exceeded its time limit")
            if out.tell() + err.tell() > limit:
                raise MonitorError("output-limit", "Command output exceeded the evidence limit")
            out.seek(0)
            err.seek(0)
            diagnostic = err.read().decode("utf-8", errors="replace").strip()
            if proc.returncode:
                raise MonitorError("command-failed", diagnostic[:2000] or f"Command exited {proc.returncode}")
            if reader:
                try:
                    return reader.result(timeout=max(0, deadline - time.monotonic()))
                except FutureTimeout as exc:
                    raise MonitorError("timeout", "Command exceeded its time limit") from exc
            return out.read()
        finally:
            if proc.poll() is None or (reader and not reader.done()):
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                proc.wait()


class Git:
    def __init__(self, directory):
        self.directory = directory
        self.env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_LITERAL_PATHSPECS="1")
        for key in list(self.env):
            if key.startswith("GIT_CONFIG_") and key not in ("GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL"):
                self.env.pop(key)
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                    "GIT_INDEX_FILE", "GIT_EXTERNAL_DIFF", "GIT_CONFIG", "GIT_ASKPASS", "SSH_ASKPASS",
                    "GIT_ALLOW_PROTOCOL", "GIT_CONFIG_PARAMETERS"):
            self.env.pop(key, None)
        run(["git", "init", "--bare", str(directory)], env=self.env)

    def command(self, *args, read_stdout=None):
        return run(["git", "--git-dir", str(self.directory), "-c", f"core.hooksPath={os.devnull}",
                    "-c", "credential.helper=", "-c", "protocol.allow=never",
                    "-c", "protocol.https.allow=always", "-c", "protocol.http.allow=always",
                    *args], env=self.env, read_stdout=read_stdout)

    def fetch(self, repository, ref):
        if ref.startswith("-"):
            raise MonitorError("invalid-ref", "Ref cannot start with a dash")
        self.command("check-ref-format", "--allow-onelevel", ref)
        self.command("config", "remote.source.url", repository)
        self.command("config", "remote.source.promisor", "true")
        self.command("config", "remote.source.partialclonefilter", "blob:none")
        self.command("fetch", "--filter=blob:none", "--no-tags", "--no-recurse-submodules", "--", "source", ref)
        return self.command("rev-parse", "FETCH_HEAD^{commit}").decode().strip()

    def tree(self, revision, paths):
        try:
            entries = self.command("ls-tree", "-rz", "--full-tree", revision, "--", *paths)
        except MonitorError as exc:
            if exc.code == "command-failed":
                raise MonitorError("missing-commit", f"Cannot inspect commit {revision}") from exc
            raise
        tree = {}
        for entry in entries.split(b"\0"):
            if entry:
                meta, path = entry.split(b"\t", 1)
                mode, kind, oid = meta.decode().split()
                tree[path.decode("utf-8", errors="surrogateescape")] = (mode, kind, oid)
        return tree

    def changes(self, before, after, paths):
        # Git needs both sides of a move to pair paths across a watch boundary.
        return self.command("diff", "--no-ext-diff", "--no-textconv", "--raw", "-z", "--no-abbrev", "-M",
                            before, after, read_stdout=lambda pipe: watched_changes(pipe, paths))


def nul_fields(pipe):
    pending = b""
    for chunk in iter(lambda: pipe.read(65536), b""):
        *fields, pending = (pending + chunk).split(b"\0")
        yield from fields
        if len(pending) > LIMIT:
            raise MonitorError("output-limit", "Git diff field exceeds the evidence limit")
    if pending:
        raise MonitorError("invalid-diff", "Git diff returned an incomplete field")


def watched_changes(pipe, paths):
    tokens = nul_fields(pipe)
    changes = []
    retained = 0
    for token in tokens:
        old_mode, new_mode, old_oid, new_oid, status = token.decode().lstrip(":").split()
        first = next(tokens)
        kind = status[0]
        second = next(tokens) if kind == "R" else first
        old = None if kind == "A" else first.decode("utf-8", errors="surrogateescape")
        new = None if kind == "D" else second.decode("utf-8", errors="surrogateescape")
        if watches(old, paths) or watches(new, paths):
            retained += len(token) + len(first) + 2
            if kind == "R":
                retained += len(second) + 1
            if retained > LIMIT:
                raise MonitorError("output-limit", "Watched Git changes exceed the evidence limit")
            changes.append(Change(kind, old, new, old_oid, new_oid, old_mode, new_mode))
    return tuple(changes)


def watch_paths(paths):
    normalized = []
    for path in paths:
        name = str(PurePosixPath(path))
        if name != "." and path.endswith(("/", "/.")):
            name += "/"
        normalized.append(name)
    return tuple(normalized)


def watches(path, watched):
    return path is not None and any(p == "." or (not p.endswith("/") and path == p)
                                   or path.startswith(p.rstrip("/") + "/") for p in watched)


def inspect_source(source, root, git, head):
    before = git.tree(source.reviewed, source.paths)
    after = git.tree(head, source.paths)
    try:
        git.command("merge-base", "--is-ancestor", source.reviewed, head)
    except MonitorError as exc:
        if exc.code == "command-failed":
            raise MonitorError("history-rewritten", "Reviewed commit is not an ancestor of the source ref") from exc
        raise
    changes = () if before == after else git.changes(source.reviewed, head, source.paths)
    missing = tuple(p for p in source.paths if not any(watches(path, (p,)) for path in after))
    patch = ""
    comparison = ""
    note = "No pending upstream changes."
    if changes:
        paths = sorted({p for c in changes for p in (c.old_path, c.new_path) if p is not None})
        patch = git.command("diff", "--no-ext-diff", "--no-textconv", "--binary", "-M",
                            source.reviewed, head, "--", *paths).decode("utf-8", errors="replace")
        incorporated = source.incorporated or source.reviewed
        origin_tree = before if incorporated == source.reviewed else git.tree(incorporated, source.paths)
        entrypoints = [p for p in origin_tree if p.rsplit("/", 1)[-1] == "SKILL.md" and watches(p, source.paths)]
        if len(entrypoints) == 1 and origin_tree[entrypoints[0]][0] in ("100644", "100755"):
            upstream = git.command("show", f"{incorporated}:{entrypoints[0]}").decode("utf-8", errors="replace")
            local_path = root / "skills" / source.skill / "SKILL.md"
            if local_path.stat().st_size > LIMIT:
                raise MonitorError("output-limit", "Local skill entrypoint exceeds the evidence limit")
            local = local_path.read_text(encoding="utf-8")
            comparison = "".join(difflib.unified_diff(upstream.splitlines(True), local.splitlines(True),
                                  fromfile=f"upstream/{entrypoints[0]}@{incorporated}",
                                  tofile=f"local/skills/{source.skill}/SKILL.md"))
            if len(comparison.encode()) > LIMIT:
                raise MonitorError("output-limit", "Customization comparison exceeds the evidence limit")
            note = (f"Entrypoint comparison uses {incorporated}. Supporting files have no declared local mapping. "
                    "This comparison does not establish equivalence between directories.")
        else:
            note = "Entrypoint comparison needs an explicit mapping. No unique watched SKILL.md exists in the incorporation snapshot."
    return Result(source, "unknown" if missing else "pending" if changes else "unchanged", head, changes,
                  "missing-path" if missing else "", "Watched paths are absent at the source ref" if missing else "",
                  missing, patch, comparison, note)


def collect(root, *, git_factory=Git):
    index, errors = load_index(root)
    sources = []
    for skill, record in sorted(index.items()):
        if not NAME.fullmatch(skill):
            errors.append(f"Invalid skill name {skill!r}")
        errors.extend(f"{skill}: {error}" for error in check_record(record))
        if errors:
            continue
        for item in record["sources"]:
            sources.append(Source.from_registry(skill, item, record["maintenance_notes"]))
    if errors:
        return Report((), tuple(errors))
    results = []
    with tempfile.TemporaryDirectory(prefix="upstream-monitor-") as scratch:
        groups = {}
        for source in sources:
            groups.setdefault((source.repository, source.ref), []).append(source)
        for number, ((repository, ref), group) in enumerate(sorted(groups.items())):
            try:
                git = git_factory(Path(scratch) / str(number))
                head = git.fetch(repository, ref)
            except MonitorError as exc:
                results.extend(Result(s, "unknown", error=exc.code, detail=str(exc)) for s in group)
                continue
            for source in group:
                try:
                    results.append(inspect_source(source, root, git, head))
                except (MonitorError, OSError, UnicodeError) as exc:
                    code = exc.code if isinstance(exc, MonitorError) else "comparison-unavailable"
                    results.append(Result(source, "unknown", head=head, error=code, detail=str(exc)))
    return Report(tuple(sorted(results, key=lambda r: r.source.key)))


def source_link(source, head):
    parsed = urlparse(source.repository)
    if parsed.hostname == "github.com" and head:
        return source.repository.removesuffix(".git").rstrip("/") + f"/compare/{source.reviewed}...{head}"
    return source.repository


def render(report):
    data = {"schema_version": 1, "results": [asdict(r) for r in report.results], "errors": list(report.errors)}
    lines = ["# Upstream skill report", "", "Detection does not change skills or review revisions.", ""]
    lines.extend(f"Registry error: {error}" for error in report.errors)
    for result in report.results:
        source = result.source
        lines.extend([f"## {source.key}", "", f"Status: {result.status}.", "",
                      f"Source: {source.repository}", f"Watched paths: {json.dumps(source.paths)}",
                      f"Reviewed revision: {source.reviewed}", f"Observed revision: {result.head or 'unavailable'}", ""])
        if result.error:
            lines.extend([f"Investigation required. {result.error}. {result.detail}", ""])
        if result.missing_paths:
            lines.extend([f"Missing paths: {json.dumps(result.missing_paths)}", ""])
        if result.changes:
            lines.extend([f"[Upstream comparison]({source_link(source, result.head)})", "",
                          "### Upstream patch", "", "````diff", result.upstream_patch, "````", "",
                          "### Local customizations", "", result.comparison_note, "", source.notes, "",
                          "````diff", result.customization_patch or "No entrypoint differences or no unique mapping.", "````", ""])
    return data, "\n".join(lines)


def compact(report, previous):
    old = {item["key"]: item for item in previous.get("sources", [])}
    if report.errors:
        preserved = [dict(item, status="unknown", error="registry-invalid") for item in old.values()]
        return {"sources": preserved, "errors": list(report.errors)}
    items = []
    for result in report.results:
        source = result.source
        item = {"key": source.key, "repository": source.repository, "ref": source.ref, "paths": list(source.paths),
                "reviewed": source.reviewed, "status": result.status, "error": result.error,
                "missing_paths": list(result.missing_paths), "changes": [asdict(c) for c in result.changes]}
        prior = old.get(source.key)
        if prior and watch_paths(prior["paths"]) == source.paths:
            # Existing generation fingerprints include the registered path spelling.
            item["paths"] = prior["paths"]
        if result.head:
            item["observed_revision"] = result.head
        if result.status == "unknown" and not result.changes and prior and all(
                prior.get(k) == item[k] for k in ("repository", "ref", "paths", "reviewed")):
            item["changes"] = prior.get("changes", [])
            item.pop("observed_revision", None)
            if prior.get("observed_revision"):
                item["observed_revision"] = prior["observed_revision"]
            if prior.get("link"):
                item["link"] = prior["link"]
        elif result.changes:
            item["link"] = source_link(source, result.head)
        items.append(item)
    return {"sources": items, "errors": list(report.errors)}


def fingerprint(snapshot):
    identity = {"sources": [{k: v for k, v in item.items() if k not in ("link", "observed_revision")} for item in snapshot["sources"]],
                "errors": snapshot["errors"]}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def issue_body(snapshot, digest, generation, *, reference=None):
    metadata = dict(snapshot, fingerprint=digest, generation=generation)
    lines = [MARKER, "# External skill updates", "", "This body is maintained by the upstream monitor. Add human notes in comments.",
             "Subscribe to this issue for update notifications. Review the report before adopting changes.",
             ("The private operator posts a numbered proposal for each changed batch. If no proposal has appeared yet, review is pending."
              if os.environ.get("UPSTREAM_OPERATOR_REPO") else
              "The configured Codex reviewer posts analysis and suggested next actions in comments for each new queue generation."), ""]
    for item in snapshot["sources"]:
        if item["status"] == "unchanged":
            continue
        label = item["key"]
        if item.get("link"):
            label = f"[{label}]({item['link']})"
        lines.append(f"- {label}. {item['status']}. {len(item['changes'])} changed file(s)." +
                     (f" Investigation required. {item['error']}." if item["error"] else ""))
        for change in (() if reference else item["changes"]):
            paths = [p for p in (change["old_path"], change["new_path"]) if p is not None]
            lines.append("  - " + change["kind"] + ". " + " → ".join(dict.fromkeys(json.dumps(p) for p in paths)))
        if item["status"] == "unknown" and item["changes"]:
            lines.append("  Previous pending changes remain unresolved.")
    lines.extend(f"- Registry error. {error}" for error in snapshot["errors"])
    if all(i["status"] == "unchanged" for i in snapshot["sources"]) and not snapshot["errors"]:
        lines.append("All configured sources are clean.")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if repo and run_id:
        lines.extend(["", f"[Workflow run and report artifact]({server}/{repo}/actions/runs/{run_id})"])
    if reference:
        lines.extend(["", f"The full queue snapshot for generation {generation} is in the monitor's comments on this issue.",
                      "", reference])
        if len("\n".join(lines).encode()) > ISSUE_LIMIT:
            return f"{MARKER}\nUpstream review generation {generation}. See the snapshot comments on this issue.\n\n{reference}"
    else:
        encoded = snapshot_json(metadata)
        lines.extend(["", f"<!-- upstream-snapshot:{encoded} -->"])
    return "\n".join(lines)


def snapshot_json(metadata):
    return json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True).replace("--", "\\u002d\\u002d")


def part_heading(digest, index):
    return f"Upstream snapshot part {index} for `{digest}`."


def publish_snapshot(client, issue, snapshot, digest, generation, publishers):
    body = issue_body(snapshot, digest, generation)
    if len(body.encode()) <= ISSUE_LIMIT:
        if issue:
            client.edit(issue["number"], body=body)
            return issue["number"]
        return client.create(body)["number"]

    payload = snapshot_json(dict(snapshot, fingerprint=digest, generation=generation))
    sha = hashlib.sha256(payload.encode("ascii")).hexdigest()
    width = ISSUE_LIMIT - len(part_heading(sha, 10000)) - len("\n\n<!--  -->")
    if width <= 0 or len(payload) > width * 10000:
        raise MonitorError("issue-limit", "Queue exceeds the supported issue body limit or comment count")
    pieces = [payload[pos:pos + width] for pos in range(0, len(payload), width)]
    reference = f"<!-- upstream-snapshot-parts:{sha}:{len(pieces)} -->"
    body = issue_body(snapshot, digest, generation, reference=reference)
    if len(body.encode()) > ISSUE_LIMIT:
        raise MonitorError("issue-limit", "Queue reference exceeds the issue body limit")
    if not issue:
        issue = client.create(STAGING)
    number = issue["number"]
    existing = {note.get("body") for note in client.comments(number) if authored_by(note, publishers)}
    for index, piece in enumerate(pieces, 1):
        part = f"{part_heading(sha, index)}\n\n<!-- {piece} -->"
        if part not in existing:
            client.comment(number, part)
    read_snapshot(client, {"number": number, "body": body}, publishers)
    client.edit(number, body=body)
    return number


def read_snapshot(client, issue, publishers):
    body = issue["body"]
    ref = SNAPSHOT_REF.fullmatch(body.rstrip("\r\n").rsplit("\n", 1)[-1])
    if ref:
        sha, count = ref[1], int(ref[2])
        parts = {}
        pattern = re.compile(r"Upstream snapshot part ([1-9][0-9]{0,4}) for `" + sha + r"`\.\n\n<!-- ([^\r\n]*) -->")
        for note in client.comments(issue["number"]):
            if not authored_by(note, publishers):
                continue
            match = pattern.fullmatch(note.get("body") or "")
            if match:
                index, piece = int(match[1]), match[2]
                if index > count or parts.setdefault(index, piece) != piece:
                    raise MonitorError("invalid-snapshot", "Conflicting upstream snapshot parts")
        if len(parts) != count:
            raise MonitorError("invalid-snapshot", "Missing upstream snapshot parts")
        payload = "".join(parts[i] for i in range(1, count + 1))
        if hashlib.sha256(payload.encode()).hexdigest() != sha:
            raise MonitorError("invalid-snapshot", "Upstream snapshot parts do not match their digest")
        body = f"<!-- upstream-snapshot:{payload} -->"
    snapshot = parse_snapshot(body)
    if fingerprint(snapshot) != snapshot["fingerprint"]:
        raise MonitorError("invalid-snapshot", "Queue fingerprint does not match its source identities")
    return snapshot


class GitHub:
    def __init__(self, repository, gh="gh"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise MonitorError("invalid-repository", "Issue repository must be OWNER/REPO")
        self.base = f"repos/{repository}/issues"
        self.gh = gh

    def request(self, method, endpoint, payload=None):
        args = [self.gh, "api", "--method", method, endpoint]
        if payload is None:
            raw = run(args)
        else:
            with tempfile.TemporaryDirectory(prefix="upstream-api-") as scratch:
                body = Path(scratch) / "request.json"
                body.write_text(json.dumps(payload), encoding="utf-8")
                raw = run([*args, "--input", str(body)])
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise MonitorError("invalid-api-response", "GitHub returned invalid JSON") from exc

    def viewer_login(self):
        response = self.request("POST", "graphql", {"query": "query { viewer { login } }"})
        try:
            login = response["data"]["viewer"]["login"]
            if not isinstance(login, str) or not login.strip():
                raise ValueError
            return login.casefold()
        except (TypeError, KeyError, ValueError) as exc:
            raise MonitorError("invalid-api-response", "GitHub did not identify the authenticated publisher") from exc

    def pages(self, endpoint):
        size = 100
        records = []
        separator = "&" if "?" in endpoint else "?"
        while len(records) < 10000:
            page, skip = divmod(len(records), size)
            try:
                batch = self.request("GET", f"{endpoint}{separator}per_page={size}&page={page + 1}")
            except MonitorError as exc:
                if exc.code != "output-limit" or size == 1:
                    raise
                size = max(1, size // 2)
                continue
            if not isinstance(batch, list) or not all(isinstance(item, dict) for item in batch):
                raise MonitorError("invalid-api-response", "GitHub list response must be an array of objects")
            records.extend(batch[skip:])
            if len(batch) < size and len(records) <= 10000:
                return records
        raise MonitorError("pagination-limit", "Issue or comment discovery reached 10,000 records")

    def issues(self):
        return self.pages(self.base + "?state=all")

    def comments(self, number):
        return self.pages(f"{self.base}/{number}/comments")

    def create(self, body):
        return self.request("POST", self.base, {"title": "External skill updates", "body": body})

    def lock(self, number):
        # GitHub returns 204 with no JSON body.
        run([self.gh, "api", "--method", "PUT", f"{self.base}/{number}/lock"])

    def edit(self, number, **fields):
        return self.request("PATCH", f"{self.base}/{number}", fields)

    def comment(self, number, body):
        return self.request("POST", f"{self.base}/{number}/comments", {"body": body})


def parse_snapshot(body):
    match = SNAPSHOT.fullmatch(body.rstrip("\r\n").rsplit("\n", 1)[-1])
    try:
        previous = json.loads(match[1]) if match else None
        if (not isinstance(previous, dict) or not isinstance(previous.get("sources"), list)
                or not isinstance(previous.get("errors"), list)
                or not all(isinstance(e, str) for e in previous["errors"])
                or type(previous.get("generation")) is not int or previous["generation"] < 1
                or not isinstance(previous.get("fingerprint"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", previous["fingerprint"])):
            raise ValueError
        keys = set()
        for item in previous["sources"]:
            if (not isinstance(item, dict)
                    or not all(isinstance(item.get(k), str) for k in ("key", "repository", "ref", "reviewed", "error"))
                    or item.get("status") not in ("unchanged", "pending", "unknown")
                    or not all(isinstance(item.get(k), list) and all(isinstance(p, str) for p in item[k])
                               for k in ("paths", "missing_paths"))
                    or not isinstance(item.get("changes"), list)
                    or ("link" in item and not isinstance(item["link"], str))
                    or ("observed_revision" in item and (not isinstance(item["observed_revision"], str)
                        or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", item["observed_revision"])))
                    or item["key"] in keys):
                raise ValueError
            keys.add(item["key"])
            for change in item["changes"]:
                if (not isinstance(change, dict)
                        or not all(isinstance(change.get(k), str) for k in
                                   ("kind", "old_object", "new_object", "old_mode", "new_mode"))
                        or not all(k in change and (change[k] is None or isinstance(change[k], str))
                                   for k in ("old_path", "new_path"))):
                    raise ValueError
        return previous
    except (ValueError, TypeError, KeyError) as exc:
        raise MonitorError("invalid-snapshot", "Existing monitor issue has an invalid snapshot") from exc


def is_actionable(snapshot):
    return bool(snapshot["errors"] or any(i["status"] != "unchanged" for i in snapshot["sources"]))


def monitor_publishers(repository, monitor_login):
    return {ACTIONS_LOGIN, (monitor_login or repository.split("/", 1)[0]).casefold()}


def authored_by(record, publishers):
    user = record.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    return isinstance(login, str) and login.casefold() in publishers


def select_issue(client, publishers):
    unfinished = []
    for issue in client.issues():
        if ("pull_request" in issue or not authored_by(issue, publishers)
                or (issue.get("body") or "").splitlines()[:1] != [MARKER]):
            continue
        if (type(issue.get("number")) is not int or issue["number"] < 1
                or issue.get("state") not in ("open", "closed")):
            raise MonitorError("invalid-api-response", "Monitor issue is missing a valid number or state")
        if issue["body"] == STAGING:
            unfinished.append((issue, {}))
            continue
        snapshot = read_snapshot(client, issue, publishers)
        if issue["state"] != "closed" or is_actionable(snapshot):
            unfinished.append((issue, snapshot))
    if len(unfinished) > 1:
        raise MonitorError("duplicate-issues", "Multiple unfinished marked issues exist. Resolve the duplicate before continuing.")
    return unfinished[0] if unfinished else (None, {})


def reconcile_batch(report, repository, *, issues=None, monitor_login=None, adoption=False):
    client = issues or GitHub(repository)
    publishers = monitor_publishers(repository, monitor_login)
    if client.viewer_login() not in publishers:
        raise MonitorError("publisher-mismatch", "Configure the authenticated monitor publisher with --monitor-login")
    issue, previous = select_issue(client, publishers)
    snapshot = compact(report, previous)
    digest = fingerprint(snapshot)
    actionable = is_actionable(snapshot)
    if not issue and not actionable:
        return "quiet", None
    new_issue = issue is None
    if adoption and new_issue:
        # Create and lock a staging issue before exposing a snapshot the worker can act on.
        issue = client.create(STAGING)
    needs_lock = adoption and issue.get("locked") is not True
    if needs_lock:
        client.lock(issue["number"])
    generation = previous.get("generation", 0)
    changed = digest != previous.get("fingerprint")
    if changed:
        generation += 1
        number = publish_snapshot(client, issue, snapshot, digest, generation, publishers)
        if new_issue:
            return "created", number
    # The adoption worker records the final PR receipt before closing a clean batch.
    handoff = adoption and not actionable and issue["state"] == "open"
    target = "open" if actionable or handoff else "closed"
    if issue["state"] != target:
        client.edit(issue["number"], state=target)
    if actionable and generation > 1:
        token = f"<!-- upstream-notification:{generation}:{digest} -->"
        body = "The external skill review queue changed. Inspect the maintained issue and report.\n\n" + token
        if not any(authored_by(comment, publishers) and (comment.get("body") or "").splitlines() == body.splitlines()
                   for comment in client.comments(issue["number"])):
            client.comment(issue["number"], body)
    action = "updated" if changed else "reopened" if issue["state"] != target and actionable else "closed" if not actionable else "quiet"
    if action == "quiet" and needs_lock:
        action = "locked"
    return ("awaiting-adoption" if handoff else action), issue["number"]


def reconcile_issue(report, repository, *, issues=None, monitor_login=None):
    action, _ = reconcile_batch(report, repository, issues=issues, monitor_login=monitor_login)
    return action


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="harness repository root")
    parser.add_argument("--output-dir", type=Path, required=True, help="directory for report.json and report.md")
    parser.add_argument("--issue-repo", help="publish the queue from OWNER/REPO's monitor workflow on main")
    parser.add_argument("--monitor-login", default=os.environ.get("UPSTREAM_MONITOR_LOGIN"),
                        help="trusted monitor login alongside GitHub Actions (default: repository owner)")
    args = parser.parse_args()
    try:
        if args.issue_repo:
            publisher_ref = f"{args.issue_repo}/.github/workflows/monitor-upstream.yml@refs/heads/main"
            if os.environ.get("GITHUB_WORKFLOW_REF") != publisher_ref:
                raise MonitorError("workflow-required", "Publish through the monitor workflow. Run "
                                   f"gh workflow run monitor-upstream.yml --repo {shlex.quote(args.issue_repo)} --ref main")
        root = args.root.resolve()
        output = args.output_dir.resolve()
        if any(output == (root / name).resolve() or (root / name).resolve() in output.parents
               for name in ("skills", "registry", "reviews", ".git")):
            raise MonitorError("unsafe-output", "Reports must be outside skills, registry, reviews, and .git")
        report = collect(root)
        data, markdown = render(report)
        output.mkdir(parents=True, exist_ok=True)
        for name, content in (("report.json", json.dumps(data, indent=2, ensure_ascii=True) + "\n"), ("report.md", markdown)):
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output, delete=False) as file:
                    temporary = Path(file.name)
                    file.write(content)
                os.replace(temporary, output / name)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        print(f"Report written to {output}. {sum(r.status == 'pending' for r in report.results)} pending source(s).")
        if args.issue_repo:
            adoption = bool(os.environ.get("UPSTREAM_OPERATOR_REPO"))
            action, issue = reconcile_batch(report, args.issue_repo, monitor_login=args.monitor_login, adoption=adoption)
            print(f"Issue reconciliation {action}.")
            if (issue and os.environ.get("GITHUB_OUTPUT")
                    and (action != "quiet" or os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as outputs:
                    outputs.write(f"issue={issue}\n")
        if report.failed:
            print("Upstream state is unknown for one or more sources. Inspect report.json.", file=sys.stderr)
        return int(report.failed)
    except (MonitorError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
