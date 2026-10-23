#!/usr/bin/env python3

import json
import os
from pathlib import Path
import subprocess
import sys


scenario = json.loads(Path(os.environ["PUBLISH_SCENARIO"]).read_text())
log = Path(os.environ["PUBLISH_LOG"])
calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
arguments = sys.argv[1:]
payload = json.load(sys.stdin) if "--input" in arguments else None
with log.open("a") as stream:
    stream.write(json.dumps({"arguments": arguments, "payload": payload}) + "\n")

if arguments[:2] == ["api", "graphql"]:
    assert payload["query"].startswith("query Snapshot(")
    assert payload["variables"]["owner"] == "fixture"
    assert payload["variables"]["name"] == "project"
    count = sum(call["arguments"][:2] == ["api", "graphql"] for call in calls)
    snapshots = scenario["snapshots"]
    snapshot = snapshots[min(count, len(snapshots) - 1)]
    if scenario.get("head_from_remote"):
        result = subprocess.run(["git", "--git-dir", scenario["remote"], "rev-parse",
                                 "refs/heads/actual-topic"], capture_output=True, text=True)
        if result.returncode == 0:
            snapshot["headRefOid"] = result.stdout.strip()
    print(json.dumps({"data": {"repository": {"nameWithOwner": "fixture/project",
                                              "pullRequest": snapshot}}}))
elif arguments[:2] == ["api", "repos/fixture/project/stacks?pull_request=12&per_page=2"]:
    print(json.dumps(scenario.get("stacks", [])))
elif arguments[:2] == ["api", "repos/fixture/project/pulls/12/merge-async"]:
    assert arguments[arguments.index("--method") + 1] == "PUT"
    if "merge_error" in scenario:
        print(scenario["merge_error"], file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(scenario["merge_response"]))
elif arguments[:2] == ["api", "repos/fixture/project/pulls/12/merge-async/630b9d5e-3f2a-4f7e-8b0c-2d5f9a8c1e42"]:
    print(json.dumps(scenario["poll_response"]))
else:
    print("unexpected gh invocation: " + repr(arguments), file=sys.stderr)
    raise SystemExit(1)
