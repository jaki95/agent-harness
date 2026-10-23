#!/usr/bin/env python3
"""Publish an existing PR or request one guarded merge after authorized verification."""

import argparse
from dataclasses import asdict
import json
import math
import re
import subprocess
import sys
import time
from urllib.parse import urlparse

from pr_receipt import Collector, ReadError, field, positive_int, positive_timeout


class Publisher:
    def __init__(self, args):
        self.args = args
        self.reader = Collector(args.repo, args.number, args.timeout, 1)

    def git(self, *arguments):
        remaining = self.reader.deadline - time.monotonic()
        if remaining <= 0:
            raise ReadError("global deadline exceeded")
        try:
            result = subprocess.run(["git", *arguments], capture_output=True, text=True,
                                    timeout=remaining, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ReadError(f"git command failed: {exc}") from exc
        if result.returncode:
            raise ReadError(f"git {arguments[0]} failed: {result.stderr.strip()[:500]}")
        return result.stdout.strip()

    def api(self, endpoint, payload=None):
        arguments = ["api", endpoint, "--method", "GET" if payload is None else "PUT",
                     "-H", "X-GitHub-Api-Version: 2026-03-10"]
        if payload is not None:
            arguments += ["--input", "-"]
        raw = self.reader.command(arguments, None if payload is None else json.dumps(payload).encode())
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise ReadError("invalid JSON response") from exc

    def current(self):
        snapshot = self.reader.snapshot()
        if snapshot.head_sha != self.args.expected_head:
            raise ReadError("published head differs from --expected-head")
        if snapshot.state != "OPEN":
            raise ReadError("PR is not open")
        return snapshot

    def unchanged(self, before):
        after = self.current()
        keys = ("id", "url", "head_ref", "head_repository", "head_url", "head_ssh_url",
                "base_ref", "base_sha")
        if any(getattr(before, key) != getattr(after, key) for key in keys):
            raise ReadError("PR target or base changed before publication")
        return after

    def push(self, before):
        if before.head_repository is None:
            raise ReadError("head repository is unavailable")
        parsed = urlparse(before.head_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path.strip("/") != before.head_repository):
            raise ReadError("head repository URL does not match GitHub identity")
        target = before.head_url + ".git"
        if self.args.transport == "ssh":
            target = before.head_ssh_url
            if target != f"git@{parsed.hostname}:{before.head_repository}.git":
                raise ReadError("head repository SSH URL does not match GitHub identity")
        ref = "refs/heads/" + before.head_ref
        self.git("check-ref-format", ref)
        local_head = self.git("rev-parse", "--verify", "HEAD^{commit}")
        remote = self.git("ls-remote", "--refs", target, ref)
        if not remote:
            raise ReadError("published head branch does not exist; refusing branch creation")
        if remote.split() != [self.args.expected_head, ref]:
            raise ReadError("remote head differs from --expected-head")
        if not self.args.allow_rewrite:
            self.git("merge-base", "--is-ancestor", self.args.expected_head, local_head)
        self.unchanged(before)
        self.git("-c", "push.recurseSubmodules=no", "push", "--porcelain", "--no-follow-tags",
                 f"--force-with-lease={ref}:{self.args.expected_head}", target, f"{local_head}:{ref}")
        remote = self.git("ls-remote", "--refs", target, ref)
        after = self.reader.snapshot()
        if (remote.split() != [local_head, ref] or after.head_sha != local_head
                or after.head_ref != before.head_ref or after.head_repository != before.head_repository):
            raise ReadError("push sent but publication not confirmed; inspect before retrying")
        return {**asdict(after), "status": "published"}, 0

    def check_stack(self, before):
        stacks = self.api(f"repos/{self.args.repo}/stacks?pull_request={self.args.number}&per_page=2")
        if not isinstance(stacks, list) or len(stacks) > 1:
            raise ReadError("native stack membership is ambiguous")
        if not stacks:
            return None
        stack = stacks[0]
        members = field(stack, "pull_requests", list)
        numbers = [field(member, "number", int) for member in members]
        if numbers.count(self.args.number) != 1 or len(set(numbers)) != len(numbers):
            raise ReadError("native stack does not identify the requested PR exactly once")
        position = numbers.index(self.args.number)
        for member in members[:position]:
            if (field(member, "merged_at", str, True) is None
                    or field(member, "state", str) != "closed"):
                raise ReadError(f"native stack predecessor #{member['number']} is not merged")
        target = members[position]
        if (field(target, "state", str) != "open" or field(target, "merged_at", str, True) is not None
                or field(field(target, "head", dict), "sha", str) != before.head_sha):
            raise ReadError("native stack head or state differs from PR snapshot")
        return field(stack, "number", int)

    def merge(self, before):
        stack_number = self.check_stack(before)
        current = self.unchanged(before)
        if current.draft:
            raise ReadError("PR is still a draft")
        endpoint = f"repos/{self.args.repo}/pulls/{self.args.number}/merge-async"
        payload = {"sha": self.args.expected_head, "merge_method": "squash",
                   "merge_action": "default", "bypass_rules": False}
        response = self.api(endpoint, payload)
        wait_until = min(self.reader.deadline, time.monotonic() + self.args.wait)
        while True:
            status = field(response, "status", str)
            details = field(response, "details", dict)
            result = {"repository": self.args.repo, "number": self.args.number,
                      "head_sha": self.args.expected_head, "stack_number": stack_number,
                      "status": status, "details": details}
            if status == "merged":
                after = self.reader.snapshot()
                if after.state != "MERGED" or not after.merged_at or after.head_sha != before.head_sha:
                    raise ReadError("merge response received but merged PR state not confirmed")
                return result, 0
            if status == "enqueued":
                return result, 3
            if status == "failed":
                raise ReadError("merge failed: " + str(details.get("message", "unknown reason")))
            if status != "pending":
                raise ReadError("unknown asynchronous merge status")
            request_id = field(details, "uuid", str)
            if not re.fullmatch(r"[0-9a-f-]{36}", request_id):
                raise ReadError("invalid asynchronous merge request ID")
            if any(details.get(key) != value for key, value in {
                "expected_head_sha": self.args.expected_head, "merge_method": "squash",
                "merge_action": "default", "bypass_rules": False,
            }.items()):
                raise ReadError("pending merge options differ from guarded request")
            if time.monotonic() >= wait_until:
                return result, 3
            time.sleep(min(1, max(0, wait_until - time.monotonic())))
            if time.monotonic() >= wait_until:
                return result, 3
            response = self.api(endpoint + "/" + request_id)


def wait_seconds(value):
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise argparse.ArgumentTypeError("must be finite and nonnegative")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("push", "merge"):
        command = commands.add_parser(name)
        command.add_argument("--repo", required=True)
        command.add_argument("number", type=positive_int)
        command.add_argument("--expected-head", required=True)
        command.add_argument("--timeout", type=positive_timeout, default=60)
        if name == "push":
            command.add_argument("--allow-rewrite", action="store_true")
            command.add_argument("--transport", choices=("ssh", "https"), default="ssh")
        else:
            command.add_argument("--wait", type=wait_seconds, default=10)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("--repo must be OWNER/REPO")
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_head):
        parser.error("--expected-head must be a full lowercase commit SHA")
    try:
        publisher = Publisher(args)
        before = publisher.current()
        result, code = getattr(publisher, args.action)(before)
    except ReadError as exc:
        print(f"Publication stopped: {exc}", file=sys.stderr)
        print("A write may have been accepted. Inspect current GitHub state before retrying.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
