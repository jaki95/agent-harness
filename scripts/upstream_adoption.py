#!/usr/bin/env python3
"""Reconcile a trusted monitor issue, owner decisions and their adoption PRs."""

import argparse
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import tempfile
import time

import adoption_decisions as decisions
import adoption_execution as execution
import monitor_upstream as monitor
import review_upstream as review


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def failure(message):
    return monitor.MonitorError("adoption", message)


def object_schema(properties):
    return {"type": "object", "required": list(properties), "additionalProperties": False, "properties": properties}


TEXT = {"type": "string", "minLength": 1, "maxLength": 2000}
CHOICE = {"type": "string", "enum": ["adopt", "adapt", "keep", "defer", "blocked"]}
PROPOSAL_FIELDS = {
    "decision": CHOICE, "behavior": TEXT, "preserve": TEXT, "verify": TEXT, "why": TEXT,
    "depends": {"type": "array", "items": {"type": "string"}},
}
PROPOSE = ("Recommend one upstream adoption decision. Name the observable behavior and local customizations, "
           "a representative task with a concrete expected result, and why it is worth doing. For keep, "
           "verify registry-only changes. Identify required source keys from the supplied batch, including "
           "blocked sources. If there is a previous proposal, explain in why what changed since that review or deferral. Do not claim checks ran. Dependencies are required decisions, not related topics.")
DISCUSS = ("Answer the maintainer's new comment in context. Return revisions only for requested changes to "
           "the proposal, or to reconsider the named item on a revisit. A question alone gets an answer. "
           "Retain item scope and dependencies. Approval, testing, merge and installation are outside your role.")


def validate_output(value, schema):
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}
    allowed = kind if isinstance(kind, list) else [kind]
    if all(k in types for k in allowed) and type(value) not in [types[k] for k in allowed]:
        raise failure("Model returned an unexpected JSON type")
    if "enum" in schema and value not in schema["enum"]:
        raise failure("Model returned a choice outside the allowed set")
    if kind == "object":
        fields = schema.get("properties", {})
        if set(schema.get("required", ())) - value.keys() or (
                schema.get("additionalProperties") is False and value.keys() - fields.keys()):
            raise failure("Model returned an invalid set of fields")
        for key, field in fields.items():
            if key in value:
                validate_output(value[key], field)
    if kind == "array":
        for item in value:
            validate_output(item, schema["items"])
    if isinstance(value, (str, list)):
        low, high = ("minLength", "maxLength") if kind == "string" else ("minItems", "maxItems")
        if len(value) < schema.get(low, 0) or len(value) > schema.get(high, monitor.LIMIT):
            raise failure("Model output exceeds the declared size limits")
    return value


class IssueGitHub(monitor.GitHub):
    def verify_originals(self, comments):
        """REST timestamps have second precision; require GitHub's edit history as well."""
        query = ("query($ids: [ID!]!) { nodes(ids: $ids) { ... on IssueComment "
                 "{ id body lastEditedAt includesCreatedEdit } } }")
        for i in range(0, len(comments), 30):
            batch = comments[i:i + 30]
            nodes = self.request("POST", "graphql", {"query": query, "variables": {
                "ids": [c["node_id"] for c in batch]}})["data"]["nodes"]
            if len(nodes) != len(batch):
                raise failure("Incomplete GitHub comment provenance")
            for note, node in zip(batch, nodes):
                if not node or node["id"] != note["node_id"]:
                    raise failure("Owner comment moved during collection")
                if node["lastEditedAt"] or node["includesCreatedEdit"] or node["body"] != note["body"]:
                    note["updated_at"] = "edited"


class Journal:
    """Persist decisions and the exact outgoing comment before submitting it."""

    def __init__(self, directory):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "session.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            "history": [], "originals": {}, "handled": [], "results": {}, "merged": {}, "outbox": {}}

    def save(self):
        review.atomic_json(self.path, self.state)

    def originals(self, comments, owner, client):
        if isinstance(client, IssueGitHub):
            client.verify_originals([c for c in comments if monitor.authored_by(c, {owner})
                                     and str(c["id"]) not in self.state["originals"]
                                     and c.get("created_at") == c.get("updated_at")])
        originals = decisions.remember_comments(self.state["originals"], comments, owner)
        self.state["originals"] = originals
        self.save()
        return sorted(originals.values(), key=lambda c: c["id"])

    def check_receipts(self, comments, bot):
        saved = self.state.get("published", {})
        seen = {str(c["id"]): c for c in comments if monitor.authored_by(c, {bot})}
        for key, expected in saved.items():
            if key not in seen or digest(seen[key]["body"]) != expected:
                raise failure("Published adoption receipt changed or disappeared. Reconcile before continuing.")

    def post(self, client, number, bot, key, body):
        pending = self.state.setdefault("pending_posts", {})
        content = pending.get(key, body)
        marker = f"<!-- harness-adoption:{digest(key)} -->"
        body = content + "\n\n" + marker
        if len(body.encode()) > monitor.ISSUE_LIMIT:
            raise failure("Comment exceeds the issue limit")
        comments = client.comments(number)
        receipts = [c for c in comments if monitor.authored_by(c, {bot})
                    and (c.get("body") or "").endswith(marker)]
        outbox = self.state["outbox"]
        if receipts:
            if len(receipts) != 1 or receipts[0]["body"] != body:
                raise failure("Issue comment receipt differs from the prepared content")
            outbox[key] = receipts[0]["id"]
        elif key in outbox and outbox[key]:
            raise failure("A delivered automation comment was removed or edited")
        else:
            pending[key] = content
            outbox[key] = None
            self.save()
            receipt = client.comment(number, body)
            if not monitor.authored_by(receipt, {bot}) or receipt.get("body") != body:
                raise failure("Comment did not come from the configured GitHub App")
            outbox[key] = receipt["id"]
        pending.pop(key, None)
        self.state.setdefault("published", {})[str(outbox[key])] = digest(body)
        self.save()
        return outbox[key]

    def post_proposal(self, client, number, bot, proposal):
        # Publish long tables in order. Only the final receipt activates approval.
        text = decisions.render_proposal(proposal)
        chunks, lines, size = [], [], 0
        for line in text.splitlines(keepends=True):
            if size + len(line.encode()) > monitor.ISSUE_LIMIT - 512:
                chunks.append("".join(lines))
                lines, size = [], 0
            lines.append(line)
            size += len(line.encode())
        chunks.append("".join(lines))
        for index, chunk in enumerate(chunks, 1):
            key = f"proposal-{proposal['version']}-{index}"
            comment_id = self.post(client, number, bot, key, chunk.rstrip())
        return comment_id


class Worker:
    def __init__(self, repo, owner, bot, client, state_dir, ask, *, gather=review.gather_evidence,
                 execute=execution.execute_group, monitor_login=None):
        self.repo, self.owner, self.bot = repo, owner.casefold(), bot.casefold()
        if self.owner == self.bot:
            raise failure("The proposal author and approving owner must be distinct accounts")
        self.client, self.directory, self.ask = client, state_dir, ask
        self.gather, self.execute = gather, execute
        self.publishers = monitor.monitor_publishers(repo, monitor_login)

    def queue(self, number):
        issue = self.client.request("GET", f"{self.client.base}/{number}")
        if (issue.get("number") != number or "pull_request" in issue
                or not monitor.authored_by(issue, self.publishers)
                or (issue.get("body") or "").splitlines()[:1] != [monitor.MARKER]
                or issue["body"] == monitor.STAGING):
            return None
        snapshot = monitor.read_snapshot(self.client, issue, self.publishers)
        return issue, review.Queue(review.ReviewKey(number, snapshot["generation"], snapshot["fingerprint"]), snapshot)

    def main_head(self):
        return self.client.request("GET", f"repos/{self.repo}/git/ref/heads/main")["object"]["sha"]

    def run(self, number):
        record = self.queue(number)
        if not record:
            return "no monitor queue"
        issue, queue = record
        journal = Journal(self.directory / str(number))
        state = journal.state
        history = state["history"]
        comments = self.client.comments(number)
        journal.check_receipts(comments, self.bot)
        journal.originals(comments, self.owner, self.client)
        known_markers = {f"<!-- harness-adoption:{digest(key)} -->" for key in state["outbox"]}
        for note in comments:
            lines = (note.get("body") or "").splitlines()
            if (monitor.authored_by(note, {self.bot}) and lines and lines[-1].startswith("<!-- harness-adoption:")
                    and lines[-1] not in known_markers):
                raise failure("Issue has an unrecorded adoption receipt. Restore the durable journal before continuing.")
        # Complete a partially delivered proposal using its prepared version and text.
        # Freshness is checked again before any execution, even after recovery.
        def finish_proposal():
            proposal = state["publishing"]
            proposal["comment_id"] = journal.post_proposal(self.client, number, self.bot, proposal)
            history.append(proposal)
            del state["publishing"]
            journal.save()

        if state.get("publishing"):
            finish_proposal()
        active = issue["state"] == "open" and monitor.is_actionable(queue.snapshot)
        if not active and not history:
            if not monitor.is_actionable(queue.snapshot):
                if self.close_clean(number, queue):
                    state["terminal"] = True
                    journal.save()
            return "no actionable queue"
        # An async or human merge can precede the detector wake. Retain its decision
        # before computing fingerprints for items that depend on the merged source.
        if history:
            prior = decisions.replay(history, state["originals"].values(), self.owner, merged=state["merged"])
            observations = execution.Execution(self.repo, number, journal.directory, self.client, {}, self.ask)
            for gid in set(prior["groups"]) | state["results"].keys():
                if state["results"].get(gid, {}).get("status") == "merged":
                    continue
                observed = self.execute(observations, int(gid), [], lambda: [])
                if observed["status"] == "merged":
                    for item_digest in observed["digests"]:
                        state["merged"][item_digest] = observed["url"]
                    state.setdefault("unreported_merges", {})[gid] = observed
                    journal.save()
        sources, candidates = {}, []
        proof = None
        if active:
            try:
                with tempfile.TemporaryDirectory(dir=journal.directory) as tmp:
                    proof = review.validate_evidence(self.gather(self.repo, queue, Path(tmp)), queue)
            except monitor.MonitorError as exc:
                journal.post(self.client, number, self.bot, f"failure-{queue.key.digest}-{exc.code}",
                             f"Review is blocked. Evidence could not be verified (`{exc.code}`).")
                return "blocked"
            sources = {s["key"]: s for s in proof.sources}
            previous = {i["key"]: i for i in history[-1]["items"]} if history else {}
            queued = {s["key"]: s for s in queue.snapshot["sources"]}
            for source in proof.sources:
                key = source["key"]
                identity = digest({k: v for k, v in source.items() if k != "observed_revision"})
                old = previous.get(key)
                candidate = {"key": key, "revision": source["observed_revision"], "evidence": identity, "evidence_paths": sorted(review.evidence_paths(source)),
                             "source_url": queued[key].get("link", "")}
                if old and old["evidence"] == identity and key not in state.get("retry_sources", []):
                    candidate.update({k: old[k] for k in (*PROPOSAL_FIELDS, "revision", "source_url")})
                    sources[key] = {**source, "observed_revision": old["revision"]}
                else:
                    previous_review = None
                    if old:
                        previous_review = {"item": old, "status": prior["statuses"].get(str(old["id"])),
                                           "defer_reason": prior["defer_reasons"].get(str(old["id"]))}
                    cache_key = digest([identity, previous_review])
                    cache = journal.directory / f"analysis-{cache_key}.json"
                    try:
                        schema = object_schema(PROPOSAL_FIELDS)
                        if not cache.is_file():
                            response = self.ask(PROPOSE, {"source": source, "previous_review": previous_review, "batch": [
                                item["key"] for item in queue.snapshot["sources"] if item["status"] != "unchanged"]}, schema)
                            review.atomic_json(cache, validate_output(response, schema))
                        candidate.update(validate_output(json.loads(cache.read_text()), schema))
                        if key in state.get("retry_sources", []):
                            state["retry_sources"].remove(key)
                    except monitor.MonitorError as exc:
                        retry = state.setdefault("retry_sources", [])
                        if key not in retry:
                            retry.append(key)
                        candidate.update(decision="blocked", behavior="Source review is incomplete.",
                                         preserve="Keep current behavior.", verify="Retry the source review.",
                                         why=f"Codex review failed ({exc.code}).", depends=[])
                    journal.save()
                candidates.append(candidate)
            for key, reason in proof.unavailable:
                item = next(s for s in queue.snapshot["sources"] if s["key"] == key)
                candidates.append({"key": key, "revision": item.get("observed_revision") or item["reviewed"],
                    "evidence": digest(item), "decision": "blocked", "why": reason, "depends": [],
                    "behavior": "Evidence is incomplete.", "preserve": "Keep the installed behavior.",
                    "verify": "Recover the missing evidence before approval."})

        def fresh():
            observed = self.queue(number)
            return bool(observed and observed[0]["state"] == "open" and observed[1] == queue
                        and proof and self.main_head() == proof.harness_revision)

        def publish(candidates):
            proposal = decisions.make_proposal(history[-1] if history else None, candidates, merged=state["merged"])
            if history and history[-1]["version"] == proposal["version"]:
                return
            if not fresh():
                raise monitor.MonitorError("queue-moved", "Queue or main changed before proposal publication")
            state["publishing"] = proposal
            journal.save()
            finish_proposal()

        def replay():
            current_comments = self.client.comments(number)
            journal.check_receipts(current_comments, self.bot)
            return decisions.replay(history, journal.originals(current_comments, self.owner, self.client),
                                    self.owner, merged=state["merged"])

        if active:
            publish(candidates)
        if not history:
            return "quiet"
        snapshot = replay()
        if active:
            requests = {c["id"]: c for c in snapshot["discussion"] + snapshot["revisit"] if c["id"] not in state["handled"]}
            for cid, comment in sorted(requests.items()):
                if cid < history[0]["comment_id"]:
                    continue
                self.discuss(journal, number, comment, sources, publish)
            snapshot = replay()
        for cid, message in snapshot["responses"].items():
            key = f"ack-{cid}"
            if key not in state["outbox"] or not state["outbox"][key]:
                journal.post(self.client, number, self.bot, key, message)

        ctx = execution.Execution(self.repo, number, journal.directory, self.client, sources, self.ask)
        def group_items(snapshot, gid):
            ids = snapshot["groups"].get(str(gid), [])
            return [item for item in history[-1]["items"] if item["id"] in ids]

        results = []
        for gid in sorted(set(snapshot["groups"]) | state["results"].keys() | state.get("unreported_merges", {}).keys(), key=int):
            if state["results"].get(gid, {}).get("status") == "merged":
                continue
            def recheck():
                current = replay()
                if any(c["id"] > history[0]["comment_id"] and c["id"] not in state["handled"]
                       for c in current["discussion"] + current["revisit"]):
                    return []
                if not fresh():
                    raise monitor.MonitorError("queue-moved", "Queue or main moved before execution")
                return group_items(current, gid)
            items = group_items(snapshot, gid) if active else []
            result = state.get("unreported_merges", {}).get(gid) or self.execute(ctx, int(gid), items, recheck)
            results.append(result["status"])
            if result["status"] == "merged":
                for item_digest in result.get("digests", []):
                    state["merged"][item_digest] = result["url"]
            prior = state["results"].get(str(gid))
            if result["status"] not in {"waiting", "settling", "changed"}:
                key = f"result-{gid}-{digest(result)}"
                first_pr = result["status"] != "published" or not prior or prior.get("pr") != result.get("pr")
                if first_pr and (not prior or digest(prior) != digest(result)):
                    message = result["message"]
                    if result.get("url"):
                        message += "\n\n" + result["url"]
                    if result["status"] == "merged":
                        landed = {item["id"]: item for proposal in history for item in proposal["items"]
                                  if item["digest"] in result["digests"]}
                        names = ", ".join(f"{i} · {item['key']} ({item['decision']})" for i, item in sorted(landed.items()))
                        message += "\n\nMerged items: " + names + "."
                        remaining = replay()["statuses"]
                        outstanding = [str(i) for i, status in remaining.items() if status != "merged"]
                        message += "\n\nOpen items: " + (", ".join(outstanding) or "none") + "."
                    if key not in state["outbox"] or not state["outbox"][key]:
                        journal.post(self.client, number, self.bot, key, message)
                state["results"][str(gid)] = result
                state.get("unreported_merges", {}).pop(gid, None)
            journal.save()
        if not active and not monitor.is_actionable(queue.snapshot):
            latest = replay()
            # Fully withdrawn approvals can leave an inspectable PR. Only live
            # approvals and submitted merges participate in the close decision.
            if all(s == "merged" for s in latest["statuses"].values()) and all(
                    status in {"held", "merged"} for status in results):
                if self.close_clean(number, queue):
                    state["terminal"] = True
                    journal.save()
            else:
                journal.post(self.client, number, self.bot, f"closeout-{queue.key.digest}",
                             "Detection is clean, but prior decisions or PRs still need reconciliation.")
        return ", ".join(results) or "reviewed"

    def close_clean(self, number, queue):
        current = self.queue(number)
        if current and current[1] == queue and not monitor.is_actionable(queue.snapshot):
            if current[0]["state"] == "open":
                self.client.edit(number, state="closed")
            return True
        return False

    def discuss(self, journal, number, comment, sources, publish):
        state = journal.state
        cid = comment["id"]
        latest = state["history"][-1]
        schema = object_schema({"answer": TEXT, "revisions": {"type": "array", "items": object_schema({
            "key": {"type": "string"}, **PROPOSAL_FIELDS})}})
        file = journal.directory / f"reply-{cid}.json"
        command = decisions.COMMAND.fullmatch(comment["body"].strip())
        selected = {int(n) for n in command[3].split(",")} if command and command[3] else set()
        if not file.exists():
            evidence = {}
            for item in latest["items"]:
                key = item["key"]
                if key in sources and (not selected or item["id"] in selected):
                    source = sources[key]
                    evidence[key] = {"changed_paths": sorted(review.evidence_paths(source)),
                                     "maintenance_notes": source.get("maintenance_notes", ""),
                                     "upstream_patch_excerpt": source.get("upstream_patch", "")[:8000],
                                     "customization_patch_excerpt": source.get("customization_patch", "")[:2000]}
            earlier = [c for c in self.client.comments(number) if c["id"] < cid and
                       (str(c["id"]) in state["originals"] or str(c["id"]) in state.get("published", {}))]
            payload = {"proposal": latest, "maintainer_comment": comment["body"], "evidence": evidence,
                       "recent_conversation": [state["originals"].get(str(c["id"]), c)["body"][:4000]
                                               for c in sorted(earlier, key=lambda c: c["id"])[-8:]]}
            response = validate_output(self.ask(DISCUSS, payload, schema), schema)
            review.atomic_json(file, {"version": latest["version"], "response": response})
        saved = json.loads(file.read_text())
        response = saved["response"]
        journal.post(self.client, number, self.bot, f"reply-{cid}", response["answer"])
        if response["revisions"] and latest["version"] == saved["version"]:
            revised = {r["key"]: r for r in response["revisions"]}
            eligible = {i["key"] for i in latest["items"] if i["key"] in sources and
                        (not selected or i["id"] in selected)}
            if set(revised) - eligible or len(revised) != len(response["revisions"]):
                raise failure("Discussion proposed a duplicate, unavailable or unrequested source")
            candidates = [{k: v for k, v in item.items() if k in {*PROPOSAL_FIELDS, "key", "revision", "evidence", "evidence_paths", "source_url"}}
                          for item in latest["items"]]
            for item in candidates:
                item.update(revised.get(item["key"], {}))
            publish(candidates)
        state["handled"].append(cid)
        journal.save()

    def settle(self, number):
        for delay in (0, 5, 15, 30):
            if delay:
                time.sleep(delay)
            try:
                status = self.run(number)
            except monitor.MonitorError as exc:
                if exc.code != "queue-moved":
                    raise
                continue
            if not {"changed", "settling"}.intersection(status.split(", ")):
                return status
        journal = Journal(self.directory / str(number))
        revision = journal.state["history"][-1]["version"] if journal.state["history"] else 0
        journal.post(self.client, number, self.bot, f"settling-{revision}",
                     "GitHub or the approval changed during verification. The worker paused after four "
                     "checks. Use the private workflow to retry once the PR and checks have settled.")
        return "blocked"

    def run_checked(self, number):
        try:
            return self.settle(number)
        except (OSError, ValueError, TypeError, KeyError, monitor.MonitorError) as exc:
            # Never echo command stderr, paths or model inputs into a public issue.
            code = exc.code if isinstance(exc, monitor.MonitorError) else type(exc).__name__
            record = self.queue(number)
            if record and record[0]["state"] == "open":
                journal = Journal(self.directory / str(number))
                journal.post(self.client, number, self.bot, f"blocked-{record[1].key.digest}-{code}",
                             f"Reconciliation stopped (`{code}`). Inspect the private worker run before retrying.")
            raise

    def reconcile(self, number=None):
        if isinstance(self.client, IssueGitHub) and self.client.viewer_login() != self.bot:
            raise failure("The authenticated GitHub identity does not match the configured worker App")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        with (self.directory / "adoption.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            # Only open batches can take new decisions. Closed batches with work
            # in flight are discovered from their journals, independently of old snapshots.
            open_batches = {i["number"] for i in self.client.issues() if i.get("state") == "open"
                            and "pull_request" not in i and monitor.authored_by(i, self.publishers)
                            and (i.get("body") or "").splitlines()[:1] == [monitor.MARKER]}
            if len(open_batches) > 1:
                raise failure("Multiple open monitor issues require reconciliation")
            if number:
                return self.run_checked(number)
            numbers = open_batches | {int(p.name) for p in self.directory.iterdir() if p.is_dir() and p.name.isdecimal()
                                      and (p / "session.json").exists()}
            completed, errors = [], []
            for index in sorted(numbers):
                try:
                    if (index not in open_batches
                            and Journal(self.directory / str(index)).state.get("terminal")):
                        continue
                    completed.append(f"#{index} {self.run_checked(index)}")
                except (OSError, ValueError, TypeError, KeyError, monitor.MonitorError) as exc:
                    errors.append(f"#{index} {exc}")
            if errors:
                raise failure(" | ".join(completed + errors))
            return "; ".join(completed) or "No actionable queue"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--bot", required=True)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--issue", type=int)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--gh", default="gh")
    parser.add_argument("--model")
    parser.add_argument("--effort", choices=("low", "medium", "high", "xhigh"), default="high")
    args = parser.parse_args()
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_-][A-Za-z0-9._-]*", args.repo)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", args.owner)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*\[bot\]", args.bot)):
        parser.error("expected OWNER/REPO, a human owner login, and a dedicated App bot login")
    if args.issue is not None and args.issue < 1:
        parser.error("issue must be positive")
    try:
        def ask(role, payload, schema):
            with tempfile.TemporaryDirectory() as tmp:
                raw = review.codex_json(role, payload, schema, Path(tmp), codex=args.codex,
                                        model=args.model, effort=args.effort)
                return validate_output(raw, schema)
        worker = Worker(args.repo, args.owner, args.bot, IssueGitHub(args.repo, args.gh),
                        args.state_dir / args.repo, ask, monitor_login=os.environ.get("UPSTREAM_MONITOR_LOGIN"))
        print(worker.reconcile(args.issue))
        return 0
    except (OSError, ValueError, TypeError, KeyError, monitor.MonitorError) as exc:
        print(f"Reconciliation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
