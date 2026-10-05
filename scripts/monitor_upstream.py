#!/usr/bin/env python3
"""Detect upstream skill changes and optionally reconcile one GitHub issue."""

import argparse
from dataclasses import asdict, dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
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
SNAPSHOT = re.compile(r"<!-- upstream-snapshot:(.*?) -->", re.DOTALL)


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


def run(args, *, env=None, limit=LIMIT, timeout=TIMEOUT, input=None):
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err, tempfile.TemporaryFile() as incoming:
        if input is not None:
            incoming.write(input)
            incoming.seek(0)
        try:
            proc = subprocess.Popen(args, stdout=out, stderr=err, stdin=incoming if input is not None else subprocess.DEVNULL, env=env, start_new_session=os.name == "posix")
        except OSError as exc:
            raise MonitorError("command-unavailable", str(exc)) from exc
        try:
            deadline = time.monotonic() + timeout
            while True:
                try:
                    proc.wait(timeout=max(0.001, min(0.1, deadline - time.monotonic())))
                    break
                except subprocess.TimeoutExpired:
                    if out.tell() + err.tell() > limit:
                        raise MonitorError("output-limit", "Command output exceeded the evidence limit")
                    if time.monotonic() >= deadline:
                        raise MonitorError("timeout", "Command exceeded its time limit")
            if out.tell() + err.tell() > limit:
                raise MonitorError("output-limit", "Command output exceeded the evidence limit")
            out.seek(0)
            err.seek(0)
            output = out.read()
            diagnostic = err.read().decode("utf-8", errors="replace").strip()
            if proc.returncode:
                raise MonitorError("command-failed", diagnostic[:2000] or f"Command exited {proc.returncode}")
            return output
        finally:
            if proc.poll() is None:
                if os.name == "posix":
                    os.killpg(proc.pid, signal.SIGKILL)
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

    def command(self, *args):
        return run(["git", "--git-dir", str(self.directory), "-c", f"core.hooksPath={os.devnull}",
                    "-c", "credential.helper=", "-c", "protocol.allow=never",
                    "-c", "protocol.https.allow=always", "-c", "protocol.http.allow=always",
                    *args], env=self.env)

    def fetch(self, repository, ref):
        if ref.startswith("-"):
            raise MonitorError("invalid-ref", "Ref cannot start with a dash")
        self.command("check-ref-format", "--allow-onelevel", ref)
        self.command("config", "remote.source.url", repository)
        self.command("config", "remote.source.promisor", "true")
        self.command("config", "remote.source.partialclonefilter", "blob:none")
        self.command("fetch", "--filter=blob:none", "--no-tags", "--no-recurse-submodules", "--", "source", ref)
        return self.command("rev-parse", "FETCH_HEAD^{commit}").decode().strip()

    def tree(self, revision):
        try:
            entries = self.command("ls-tree", "-rz", "--full-tree", revision)
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

    def changes(self, before, after):
        tokens = iter(self.command("diff", "--no-ext-diff", "--no-textconv", "--raw", "-z", "--no-abbrev", "-M", before, after).split(b"\0"))
        changes = []
        for token in tokens:
            if not token:
                continue
            old_mode, new_mode, old_oid, new_oid, status = token.decode().lstrip(":").split()
            first = next(tokens).decode("utf-8", errors="surrogateescape")
            kind = status[0]
            second = next(tokens).decode("utf-8", errors="surrogateescape") if kind == "R" else first
            changes.append(Change(kind, None if kind == "A" else first,
                                  None if kind == "D" else second,
                                  old_oid, new_oid, old_mode, new_mode))
        return tuple(changes)


def watches(path, watched):
    return path is not None and any(p == "." or (not p.endswith("/") and path == p)
                                   or path.startswith(p.rstrip("/") + "/") for p in watched)


def inspect_source(source, root, git, head):
    before = git.tree(source.reviewed)
    after = git.tree(head)
    try:
        git.command("merge-base", "--is-ancestor", source.reviewed, head)
    except MonitorError as exc:
        if exc.code == "command-failed":
            raise MonitorError("history-rewritten", "Reviewed commit is not an ancestor of the source ref") from exc
        raise
    changes = tuple(c for c in git.changes(source.reviewed, head)
                    if watches(c.old_path, source.paths) or watches(c.new_path, source.paths))
    missing = tuple(p for p in source.paths if not any(watches(path, (p,)) for path in after))
    patch = ""
    comparison = ""
    note = "No pending upstream changes."
    if changes:
        paths = sorted({p for c in changes for p in (c.old_path, c.new_path) if p is not None})
        patch = git.command("diff", "--no-ext-diff", "--no-textconv", "--binary", "-M",
                            source.reviewed, head, "--", *paths).decode("utf-8", errors="replace")
        incorporated = source.incorporated or source.reviewed
        origin_tree = before if incorporated == source.reviewed else git.tree(incorporated)
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
            sources.append(Source(skill, item["id"], item["repository"], item["ref"], tuple(item["paths"]),
                                  item["last_reviewed_revision"], item["last_incorporated_revision"], record["maintenance_notes"]))
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


def issue_body(snapshot, digest, generation):
    metadata = dict(snapshot, fingerprint=digest, generation=generation)
    lines = [MARKER, "# External skill updates", "", "This body is maintained by the upstream monitor. Add human notes in comments.",
             "Subscribe to this issue for update notifications. Review the report before adopting changes.",
             "The configured Codex reviewer posts analysis and suggested next actions in comments for each new queue generation.", ""]
    for item in snapshot["sources"]:
        if item["status"] == "unchanged":
            continue
        label = item["key"]
        if item.get("link"):
            label = f"[{label}]({item['link']})"
        lines.append(f"- {label}. {item['status']}. {len(item['changes'])} changed file(s)." +
                     (f" Investigation required. {item['error']}." if item["error"] else ""))
        for change in item["changes"]:
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
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True).replace("--", "\\u002d\\u002d")
    lines.extend(["", f"<!-- upstream-snapshot:{encoded} -->"])
    body = "\n".join(lines)
    if len(body.encode()) > ISSUE_LIMIT:
        raise MonitorError("issue-limit", "Issue snapshot exceeds the body limit. Inspect the report artifact.")
    return body


class GitHub:
    def __init__(self, repository):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise MonitorError("invalid-repository", "Issue repository must be OWNER/REPO")
        self.base = f"repos/{repository}/issues"

    def request(self, method, endpoint, payload=None):
        args = ["gh", "api", "--method", method, endpoint]
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

    def pages(self, endpoint):
        page = 1
        records = []
        while page <= 100:
            separator = "&" if "?" in endpoint else "?"
            batch = self.request("GET", f"{endpoint}{separator}per_page=100&page={page}")
            if not isinstance(batch, list) or not all(isinstance(item, dict) for item in batch):
                raise MonitorError("invalid-api-response", "GitHub list response must be an array of objects")
            records.extend(batch)
            if len(batch) < 100:
                return records
            page += 1
        raise MonitorError("pagination-limit", "Issue or comment discovery exceeded 100 pages")

    def issues(self):
        return self.pages(self.base + "?state=all")

    def comments(self, number):
        return self.pages(f"{self.base}/{number}/comments")

    def create(self, body):
        return self.request("POST", self.base, {"title": "External skill updates", "body": body})

    def edit(self, number, **fields):
        return self.request("PATCH", f"{self.base}/{number}", fields)

    def comment(self, number, body):
        return self.request("POST", f"{self.base}/{number}/comments", {"body": body})


def parse_snapshot(body):
    match = SNAPSHOT.search(body)
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


def reconcile_issue(report, repository, *, issues=None):
    client = issues or GitHub(repository)
    matches = [i for i in client.issues() if "pull_request" not in i and MARKER in (i.get("body") or "")]
    if len(matches) > 1:
        raise MonitorError("duplicate-issues", "Multiple marked issues exist. Resolve the duplicate before publishing.")
    issue = matches[0] if matches else None
    if issue and (type(issue.get("number")) is not int or issue.get("state") not in ("open", "closed")):
        raise MonitorError("invalid-api-response", "Monitor issue is missing a valid number or state")
    previous = {}
    if issue:
        previous = parse_snapshot(issue.get("body") or "")
    snapshot = compact(report, previous)
    digest = fingerprint(snapshot)
    actionable = bool(snapshot["errors"] or any(i["status"] != "unchanged" for i in snapshot["sources"]))
    if not issue:
        if not actionable:
            return "quiet"
        client.create(issue_body(snapshot, digest, 1))
        return "created"
    generation = previous["generation"]
    changed = digest != previous.get("fingerprint")
    if changed:
        generation += 1
        client.edit(issue["number"], body=issue_body(snapshot, digest, generation))
    target = "open" if actionable else "closed"
    if issue["state"] != target:
        client.edit(issue["number"], state=target)
    if actionable and generation > 1:
        token = f"<!-- upstream-notification:{generation}:{digest} -->"
        if not any(token in (comment.get("body") or "") for comment in client.comments(issue["number"])):
            client.comment(issue["number"], "The external skill review queue changed. Inspect the maintained issue and report.\n\n" + token)
    return "updated" if changed else "reopened" if issue["state"] != target and actionable else "closed" if not actionable else "quiet"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="harness repository root")
    parser.add_argument("--output-dir", type=Path, required=True, help="directory for report.json and report.md")
    parser.add_argument("--issue-repo", help="explicitly publish the maintained issue to OWNER/REPO")
    args = parser.parse_args()
    try:
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
            print(f"Issue reconciliation {reconcile_issue(report, args.issue_repo)}.")
        if report.failed:
            print("Upstream state is unknown for one or more sources. Inspect report.json.", file=sys.stderr)
        return int(report.failed)
    except (MonitorError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
