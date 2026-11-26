#!/usr/bin/env python3
"""Request one private reconciliation job after the runner service starts."""

import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request


def encode(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def identity(client_id, key):
    now = int(time.time())
    claims = json.dumps({"iss": client_id, "iat": now - 60, "exp": now + 540}).encode()
    signed = (encode(b'{"alg":"RS256","typ":"JWT"}') + "." + encode(claims)).encode("ascii")
    signature = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(key)],
                               input=signed, capture_output=True, check=True, timeout=10).stdout
    return signed.decode("ascii") + "." + encode(signature)


def api(method, endpoint, token, data=None):
    request = urllib.request.Request("https://api.github.com/" + endpoint, method=method,
                                     data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Authorization": "Bearer " + token,
                                              "Accept": "application/vnd.github+json",
                                              "Content-Type": "application/json",
                                              "User-Agent": "agent-harness-upstream-dispatch"})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}


def dispatch(repository, jwt, request=api):
    base = f"repos/{repository}"
    installation = request("GET", base + "/installation", jwt)["id"]
    issued = request("POST", f"app/installations/{installation}/access_tokens", jwt,
                     {"repositories": [repository.split("/")[1]], "permissions": {"actions": "write"}})
    token = issued["token"]
    try:
        repo = request("GET", base, token)
        if repo["private"] is not True or repo["full_name"].casefold() != repository.casefold():
            raise ValueError("The operator workflow must be in the configured private repository")
        request("POST", base + "/actions/workflows/upstream-adoption.yml/dispatches", token,
                {"ref": repo["default_branch"]})
    finally:
        request("DELETE", "installation/token", token)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--private-key", required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("--repo must be OWNER/REPOSITORY")
    try:
        dispatch(args.repo, identity(args.client_id, args.private_key))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"Private workflow dispatch failed: {exc}", file=sys.stderr)
        return 1
    print("Requested reconciliation in the private operator repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
