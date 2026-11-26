"""Build numbered upstream proposals and replay owner decisions without side effects."""

from hashlib import sha256
from html import escape
import json
import re


FIELDS = ("key", "revision", "evidence", "decision", "behavior", "preserve", "verify", "why")
DECISIONS = {"adopt", "adapt", "keep", "defer", "blocked"}
COMMAND = re.compile(
    r"(approve|hold|defer|revisit)(?: +P([1-9][0-9]*))?"
    r"(?: +items? +([1-9][0-9]*(?: *, *[1-9][0-9]*)*))?", re.ASCII | re.IGNORECASE)


def _digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(data.encode()).hexdigest()


def _dependencies(key, candidates):
    reachable = set()
    pending = list(candidates[key]["depends"])
    while pending:
        dependency = pending.pop()
        if dependency not in reachable:
            reachable.add(dependency)
            if dependency in candidates:
                pending.extend(candidates[dependency]["depends"])
    return reachable


def make_proposal(previous, candidates, *, merged=None):
    """Keep stable item numbers, even across removal and reappearance of a source."""
    by_key = {}
    for candidate in candidates:
        if any(not isinstance(candidate.get(k), str) or not candidate[k].strip() for k in FIELDS):
            raise ValueError("proposal item requires source, revision, evidence, decision and review text")
        key = candidate["key"]
        dependencies = candidate.get("depends", [])
        if (key in by_key or candidate["decision"] not in DECISIONS or not isinstance(dependencies, list)
                or not all(isinstance(d, str) and d.strip() for d in dependencies)):
            raise ValueError(f"invalid proposal item or dependencies for {key}")
        paths = candidate.get("evidence_paths", [])
        source = candidate.get("source_url", "")
        if not isinstance(paths, list) or not all(isinstance(p, str) and p.strip() for p in paths):
            raise ValueError(f"invalid evidence paths for {key}")
        if not isinstance(source, str):
            raise ValueError(f"invalid source URL for {key}")
        by_key[key] = {**{k: candidate[k] for k in FIELDS}, "depends": sorted(set(dependencies)),
                       "evidence_paths": sorted(set(paths)), "source_url": source}

    numbers = dict(previous["numbers"]) if previous else {}
    retired = dict(previous.get("retired", {})) if previous else {}
    if previous:
        retired.update((i["key"], i["digest"]) for i in previous["items"])
    retired = {k: value for k, value in retired.items() if k not in by_key}
    confirmed = {k: value for k, value in retired.items() if value in (merged or {})}
    digests = {}

    def fingerprint(key):
        if key not in by_key:
            return confirmed.get(key)
        if key not in digests:
            related = _dependencies(key, by_key)
            if key in related:
                dependencies = {k: by_key.get(k, confirmed.get(k)) for k in related}
            else:
                dependencies = {k: fingerprint(k) for k in by_key[key]["depends"]}
            digests[key] = _digest([by_key[key], dependencies])
        return digests[key]

    items = []
    for key in sorted(by_key):
        if key not in numbers:
            numbers[key] = max(numbers.values(), default=0) + 1
        items.append({**by_key[key], "id": numbers[key], "digest": fingerprint(key)})
    items.sort(key=lambda row: row["id"])
    version = previous["version"] if previous else 1
    if previous and items != previous["items"]:
        version += 1
    return {"version": version, "items": items, "numbers": numbers, "retired": retired}


def _text(value):
    return escape(" ".join(value.split()), quote=False).replace("|", "&#124;")


def render_proposal(proposal):
    version = proposal["version"]
    items = proposal["items"]
    lines = [f"## Proposal P{version} · {len(items)} decisions", "",
             "| Item | Recommendation | What approval means |", "| --- | --- | --- |"]
    for item in items:
        lines.append(f"| {item['id']} · {_text(item['key'])} | {_text(item['decision'])} | {_text(item['behavior'])} |")
    lines.extend(["", f"Reply `approve P{version}` for all eligible items or "
                  f"`approve P{version} item {items[0]['id'] if items else 1}` to select one. "
                  "Ask questions in plain English.", "",
                  "<details><summary>Reasons, evidence, dependencies, and verification</summary>", ""])
    for item in items:
        dependencies = ", ".join(
            f"item {proposal['numbers'][d]}" if d in proposal["numbers"] else f"{_text(d)} (unavailable)"
            for d in item["depends"]) or "none"
        lines.extend([f"**{item['id']} · {_text(item['key'])}**", "",
                      f"- Reason: {_text(item['why'])}", f"- Preserve: {_text(item['preserve'])}",
                      f"- Verify: {_text(item['verify'])}", f"- Depends on: {dependencies}",
                      f"- Upstream revision: {_text(item['revision'])}. Evidence digest: {_text(item['evidence'])}."])
        source = item.get("source_url", "")
        if re.fullmatch(r"https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/(?:compare|commit|blob)/[A-Za-z0-9_/%~.-]+", source):
            lines.append(f"- [Upstream change]({source})")
        for evidence_path in item.get("evidence_paths", []):
            lines.append(f"- <code>{escape(evidence_path)}</code>")
        lines.append("")
    return "\n".join([*lines, "</details>"])


class _Ledger:
    def __init__(self, merged):
        self.merged = merged
        self.items = {}
        self.history = {}
        self.confirmed_keys = set()
        self.states = {}
        self.groups = {}
        self.responses = {}
        self.discussion = []
        self.revisit = []
        self.defer_reasons = {}

    def proposal(self, proposal):
        version = proposal["version"]
        if version != len(self.history) + 1:
            raise ValueError("proposal history must contain each version in order")
        current = {i["id"]: i for i in proposal["items"]}
        self.history[version] = current
        previous = self.items
        self.items = current
        self.confirmed_keys = {k for k, value in proposal.get("retired", {}).items() if value in self.merged}
        for number, item in current.items():
            if item["digest"] in self.merged:
                self.states[number] = "merged"
            elif number not in previous or previous[number]["digest"] != item["digest"]:
                self.defer_reasons.pop(number, None)
                if self.states.get(number) != "held":
                    self.states[number] = {"blocked": "blocked", "defer": "deferred"}.get(item["decision"], "pending")
        for group in self.groups.values():
            group.intersection_update(n for n in current if self.states[n] == "approved")

    def dependencies(self, number):
        by_key = {item["key"]: item for item in self.items.values()}
        keys = _dependencies(self.items[number]["key"], by_key)
        return {by_key[k]["id"] if k in by_key else None for k in keys - self.confirmed_keys}

    def command(self, comment, match, reason=""):
        action, version, selection = match.groups()
        action = action.lower()
        if not version and (action != "revisit" or not selection):
            return "Name the proposal version, for example `approve P3 item 2`."
        version = int(version) if version else len(self.history)
        proposal = self.history.get(version)
        if not proposal:
            return f"Unknown proposal P{version}."
        if selection:
            numbers = {int(n) for n in selection.split(",")}
        else:
            numbers = {n for n, i in proposal.items() if action != "approve" or
                       (i["decision"] in {"adopt", "adapt", "keep"} and self.states.get(n) not in {"held", "deferred", "merged"})}
        if not numbers or not numbers.issubset(proposal):
            return "Selection is empty or contains an unavailable item."
        retired = numbers - self.items.keys()
        if any(proposal[n]["digest"] not in self.merged for n in retired):
            return "Selection contains an unavailable item."
        numbers -= retired
        if action == "approve" and any(self.items[n]["digest"] != proposal[n]["digest"] for n in numbers):
            return "The selected proposal changed. Review the current proposal before approving."
        if action == "approve":
            return self.approve(numbers, str(comment["id"]))
        already_merged = retired | {n for n in numbers if self.states[n] == "merged"}
        numbers -= already_merged
        merged_note = (f" Items {_numbers(already_merged)} already merged. A revert needs a new decision."
                       if already_merged else "")
        if not numbers:
            return merged_note.strip()
        if action == "revisit":
            for n in numbers:
                if self.states[n] == "deferred" and self.items[n]["decision"] in {"adopt", "adapt", "keep"}:
                    self.states[n] = "pending"
            self.revisit.append(comment)
            return "Requested another review of items " + _numbers(numbers) + "." + merged_note
        dependants = {n for n in self.items if self.states[n] == "approved" and self.dependencies(n) & numbers}
        for n in numbers | dependants:
            self.states[n] = "deferred" if n in numbers and action == "defer" else "held"
        if action == "defer" and reason:
            self.defer_reasons.update({n: reason for n in numbers})
        for group in self.groups.values():
            group.difference_update(numbers | dependants)
        message = ("Deferred" if action == "defer" else "Held") + " items " + _numbers(numbers)
        if dependants - numbers:
            message += "; also held dependent items " + _numbers(dependants - numbers)
        return message + "." + (f" Reason: {_text(reason)}." if reason else "") + merged_note

    def approve(self, numbers, group):
        for number in sorted(numbers):
            item = self.items[number]
            if item["decision"] in {"defer", "blocked"}:
                return f"Item {number} needs a new proposal before approval."
            dependencies = self.dependencies(number)
            if number in dependencies or None in dependencies:
                return f"Item {number} has cyclic or unavailable dependencies."
            missing = {n for n in dependencies - numbers if self.states[n] not in {"approved", "merged"}}
            if missing:
                return f"Item {number} also requires approval for items {_numbers(missing)}."
        fresh = {n for n in numbers if self.states[n] not in {"approved", "merged"}}
        if not fresh:
            return "These items were already approved or merged."
        self.groups[group] = fresh
        for number in fresh:
            self.states[number] = "approved"
        return "Approved items " + _numbers(fresh) + "."

    def result(self):
        groups, waiting = {}, {}
        for group, numbers in self.groups.items():
            waiting_for = {d for n in numbers for d in self.dependencies(n) - numbers
                           if self.states.get(d) != "merged"}
            if waiting_for:
                waiting[group] = sorted(numbers)
            groups[group] = [] if waiting_for else sorted(numbers)
        return {"groups": groups, "waiting": waiting, "statuses": {str(n): self.states[n] for n in self.items},
                "defer_reasons": {str(n): reason for n, reason in self.defer_reasons.items()
                                  if n in self.items and self.states[n] == "deferred"},
                "responses": self.responses, "discussion": self.discussion, "revisit": self.revisit}


def _numbers(numbers):
    return ", ".join(str(n) for n in sorted(numbers))


def _owner_comment(comment, owner):
    author = comment.get("user") or {}
    return (isinstance(author.get("login"), str) and author["login"].casefold() == owner.casefold()
            and author.get("type", "User") == "User" and bool(comment.get("created_at"))
            and comment.get("updated_at") == comment["created_at"]
            and not comment.get("performed_via_github_app"))


def remember_comments(recorded, observed, owner):
    """Return original owner comments for durable replay across edits and deletions."""
    originals = dict(recorded)
    for comment in observed:
        if _owner_comment(comment, owner):
            key = str(comment["id"])
            if key not in originals:
                originals[key] = {field: comment.get(field) for field in
                                  ("id", "body", "user", "created_at", "updated_at", "performed_via_github_app")}
    return originals


def replay(history, comments, owner, *, merged=None):
    """Replay trusted proposal publications and original owner comments chronologically.

    The bridge authenticates proposal records and supplies confirmed merge receipts.
    GitHub REST comment IDs order proposals and decisions on the same issue.
    """
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("missing approval owner")
    ledger = _Ledger(merged or {})
    events = {p["comment_id"]: ("proposal", p) for p in history}
    if len(events) != len(history):
        raise ValueError("duplicate proposal comment id")
    for comment in comments:
        if not _owner_comment(comment, owner):
            continue
        number = comment["id"]
        if number not in events:
            events[number] = ("comment", comment)
        elif events[number][0] == "comment" and events[number][1] != comment:
            raise ValueError("conflicting issue comment records")
    for number, (kind, value) in sorted(events.items()):
        if kind == "proposal":
            ledger.proposal(value)
            continue
        body = value["body"].strip()
        reason = ""
        if body.lower().startswith("defer ") and "\n" not in body:
            body, _, reason = body.partition(" because ")
        match = COMMAND.fullmatch(body)
        if match:
            ledger.responses[str(number)] = ledger.command(value, match, reason)
        elif ledger.history:
            ledger.discussion.append(value)
    return ledger.result()
