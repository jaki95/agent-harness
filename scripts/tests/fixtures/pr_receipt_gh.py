#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
import time


scenario = json.loads(Path(os.environ["RECEIPT_SCENARIO"]).read_text())
log = Path(os.environ["RECEIPT_LOG"])
arguments = sys.argv[1:]
with Path(os.environ["RECEIPT_COMMANDS"]).open("a") as stream:
    stream.write(json.dumps(arguments) + "\n")
if arguments == ["--version"]:
    print("gh version fixture")
elif arguments == ["api", "--help"]:
    print("gh api --input -")
elif arguments == ["api", "graphql", "--input", "-"]:
    request = json.load(sys.stdin)
    query, variables = request["query"], request["variables"]
    if not query.startswith("query ") or "mutation" in query:
        sys.exit("unexpected write query")
    operation = query.split("(", 1)[0].split()[1]
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    with log.open("a") as stream:
        stream.write(json.dumps({"operation": operation, "variables": variables}) + "\n")
    if operation in ("Snapshot", "Threads", "Commits"):
        if (variables["owner"], variables["name"], variables["number"]) != ("fixture", "project", 12):
            sys.exit("incorrect explicit repository identity")
    if operation == "Checks" and variables["prId"] != "PR_fixture":
        sys.exit("incorrect required-check PR identity")
    key = operation + ":" + str(variables.get("id", "")) + ":" + str(variables.get("cursor", ""))
    if operation == "Snapshot":
        key = "Snapshot:" + str(sum(call["operation"] == "Snapshot" for call in calls))
    reply = scenario.get(key)
    if reply is None:
        sys.exit("fixture has no reply for " + key)
    if "delay" in reply:
        time.sleep(reply["delay"])
    if "bytes" in reply:
        sys.stdout.write("x" * reply["bytes"])
    elif "raw" in reply:
        sys.stdout.write(reply["raw"])
    elif "exit" in reply:
        print("fixture read denied", file=sys.stderr)
        sys.exit(reply["exit"])
    else:
        print(json.dumps(reply))
else:
    sys.exit("unexpected gh command " + repr(arguments))
