import json
from pathlib import Path
import sys
import subprocess
import time


path = Path(sys.argv[1])
state = json.loads(path.read_text())
request = json.load(sys.stdin)
operation = request["operation"]
state["calls"].append(operation)

def save():
    path.write_text(json.dumps(state))

save()
if state.get("mode") == "pipe-holder":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    state["child_pid"] = child.pid
    save()
    sys.exit()
if state.get("mode") == "oversized":
    print("x" * 100000)
    sys.exit()
if state.get("mode") == "malformed":
    print("{")
    sys.exit()
if state.get("mode") == "unsupported":
    print(json.dumps({"supported": False}))
    sys.exit()
rows = [row for row in state["registrations"] if row["program_key"] == request["program_key"]]
if operation == "ensure":
    if not rows:
        row = {"registration_id": "owned-1", "program_key": request["program_key"],
               "target": request["target"], "cadence_seconds": 3600, "status": "enabled"}
        state["registrations"].append(row)
    else:
        rows[0]["status"] = "enabled"
    save()
    if state.get("mode") == "lost-create":
        time.sleep(5)
    print(json.dumps({"registration_id": "owned-1"}))
elif operation == "cancel":
    if state.get("mode") == "cancel-timeout":
        time.sleep(5)
    for row in rows:
        if row["registration_id"] == request["registration_id"]:
            row["status"] = "disabled"
    save()
    print(json.dumps({"cancelled": True}))
else:
    if state.get("mode") == "wrong-owner" and operation == "readback" and rows:
        rows[0]["program_key"] = "another-program"
    if state.get("mode") == "duplicate" and rows:
        rows = rows + rows
    if state.get("mode") == "hang":
        time.sleep(5)
    print(json.dumps({"supported": True,
                      "capabilities": {name: True for name in
                          ("durable", "exact_lookup", "idempotent_ensure", "scoped_cancel", "readback")},
                      "registrations": rows}))
