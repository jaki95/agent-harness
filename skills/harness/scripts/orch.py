#!/usr/bin/env python3
"""Plain-file orchestration bookkeeping. Requires Python 3.10+; frontier reads use gh."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4


UNIT_FIELDS = ("id", "track", "state", "branch", "pr", "sha", "brief")
LEDGER_FIELDS = ("pr", "sha", "verdict", "evidence", "verifier", "ts")
POINTER_FIELDS = ("ts", "agent", "unit", "status", "report")
VERDICTS = ("live-ui-verified", "unit-test-verified", "type-check-only",
            "verifier-blocked", "verifier-failed")


class StoreError(Exception):
    pass


class Missing(StoreError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def cell(value):
    result = re.sub(r"[\t\r\n]", " ", str(value))
    return "'" + result if result.startswith(("=", "+", "-", "@")) else result


def required(value, label):
    result = cell(value)
    if not result.strip():
        raise StoreError(f"{label} must not be empty")
    return result


def atomic_write(path, text):
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_table(path, fields):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise StoreError(f"store is not initialized at {path.parent}; run orch init") from exc
    if not lines or lines[0] != "\t".join(fields):
        raise StoreError(f"{path.name} has an invalid header")
    result = []
    for line in lines[1:]:
        if not line:
            continue
        values = line.split("\t")
        if len(values) != len(fields):
            raise StoreError(f"{path.name} has a malformed row")
        result.append(dict(zip(fields, values)))
    keys = ("id",) if fields == UNIT_FIELDS else ("pr", "sha")
    if len({tuple(row[key] for key in keys) for row in result}) != len(result):
        raise StoreError(f"{path.name} has duplicate keys")
    if fields == LEDGER_FIELDS and any(row["verdict"] not in VERDICTS for row in result):
        raise StoreError("ledger.tsv has an invalid verdict")
    return result


def write_table(path, fields, rows):
    lines = ["\t".join(fields)]
    lines.extend("\t".join(cell(row[field]) for field in fields) for row in rows)
    atomic_write(path, "\n".join(lines) + "\n")


def counts(rows, field):
    result = {}
    for row in rows:
        value = row[field]
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StoreError(f"cannot read {path.name}: {exc}") from exc


def frontier(store):
    value = read_json(store / "frontier.json")
    if value == {}:
        return {"generation": 0, "prs": [], "lowestUnmerged": None}
    if not isinstance(value, dict) or type(value.get("generation")) is not int or value["generation"] < 0:
        raise StoreError("frontier.json has an invalid generation")
    rows = value.get("prs")
    if not isinstance(rows, list):
        raise StoreError("frontier.json has invalid PR rows")
    for row in rows:
        if (not isinstance(row, dict) or type(row.get("pr")) is not int or row["pr"] < 1
                or not isinstance(row.get("branches"), str) or not row["branches"]
                or not isinstance(row.get("sha"), str) or not row["sha"]
                or row.get("state") not in ("OPEN", "MERGED", "CLOSED")):
            raise StoreError("frontier.json has an invalid PR row")
    if len({row["pr"] for row in rows}) != len(rows):
        raise StoreError("frontier.json has duplicate PRs")
    lowest = next((row["pr"] for row in rows if row["state"] != "MERGED"), None)
    if value.get("lowestUnmerged") != lowest:
        raise StoreError("frontier.json has an inconsistent lowest unmerged PR")
    return value


def gh_json(arguments, repo):
    try:
        result = subprocess.run(["gh", *arguments], cwd=repo, capture_output=True,
                                text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StoreError(f"gh read failed: {exc}") from exc
    if result.returncode:
        raise StoreError(f"gh read failed: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise StoreError("gh returned invalid JSON") from exc


def resolve_frontier(repo, expected):
    metadata = gh_json(["repo", "view", "--json", "nameWithOwner,defaultBranchRef"], repo)
    if (not isinstance(metadata, dict) or not isinstance(metadata.get("nameWithOwner"), str)
            or not re.fullmatch(r"[^/\s]+/[^/\s]+", metadata["nameWithOwner"])
            or not isinstance(metadata.get("defaultBranchRef"), dict)
            or not isinstance(metadata["defaultBranchRef"].get("name"), str)
            or not metadata["defaultBranchRef"]["name"]):
        raise StoreError("gh returned invalid repository metadata")
    trunk = metadata["defaultBranchRef"]["name"]
    fields = "number,headRefName,baseRefName,headRefOid,state,isCrossRepository"

    def snapshot():
        rows = []
        for pr in expected:
            row = gh_json(["pr", "view", str(pr), "--repo", metadata["nameWithOwner"],
                           "--json", fields], repo)
            if (not isinstance(row, dict) or type(row.get("number")) is not int or row["number"] != pr
                    or row.get("state") not in ("OPEN", "MERGED", "CLOSED")
                    or not isinstance(row.get("headRefName"), str) or not row["headRefName"]
                    or not isinstance(row.get("baseRefName"), str) or not row["baseRefName"]
                    or not isinstance(row.get("headRefOid"), str)
                    or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", row["headRefOid"])
                    or type(row.get("isCrossRepository")) is not bool):
                raise StoreError(f"gh returned invalid metadata for PR {pr}")
            if row["isCrossRepository"]:
                raise StoreError(f"PR {pr} is from a fork; a same-repository chain is required")
            rows.append({key: row[key] for key in fields.split(",")})
        return rows

    rows = snapshot()
    if snapshot() != rows:
        raise StoreError("PR heads or topology changed during discovery; refresh the frontier")
    seen_open = False
    merged_branches = set()
    active = []
    for row in rows:
        if row["state"] == "CLOSED":
            raise StoreError(f"PR {row['number']} closed without merging; reconcile the scope")
        if row["state"] == "MERGED":
            if seen_open:
                raise StoreError("merged PRs must form the historical prefix of the chain")
            merged_branches.add(row["headRefName"])
        else:
            seen_open = True
            active.append(row)
    by_branch = {row["headRefName"]: row for row in active}
    if len(by_branch) != len(active):
        raise StoreError("multiple open PRs share a head branch")
    roots = [row for row in active if row["baseRefName"] not in by_branch]
    children = {}
    for row in active:
        parent = row["baseRefName"]
        if parent in by_branch:
            children.setdefault(parent, []).append(row)
    if active:
        if len(roots) != 1 or any(len(group) != 1 for group in children.values()):
            raise StoreError("PR scope is not one linear chain; split stacks or repair topology")
        root = roots[0]
        if root["baseRefName"] not in {trunk, *merged_branches}:
            raise StoreError("stack root targets a branch outside the declared scope")
        ordered = []
        current = root
        while current is not None:
            if current["number"] in ordered:
                raise StoreError("PR chain contains a cycle")
            ordered.append(current["number"])
            current = next(iter(children.get(current["headRefName"], [])), None)
        if ordered != [row["number"] for row in active]:
            raise StoreError("frontier pin mismatch or disconnected PRs; use bottom-up order")
    return {"repository": metadata["nameWithOwner"], "trunk": trunk,
            "prs": [{"pr": row["number"], "branches": row["headRefName"],
                     "sha": row["headRefOid"], "state": row["state"], "base": row["baseRefName"]}
                    for row in rows]}


@contextmanager
def locked(store):
    store.mkdir(parents=True, exist_ok=True)
    with (store / ".orch.lock").open("a+b") as stream:
        try:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                if not stream.read(1):
                    stream.write(b" ")
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise StoreError("store lock is held by another writer; retry after it exits") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def read_gates(store):
    text = (store / "gates.md").read_text(encoding="utf-8").strip()
    if not text:
        return []
    if not text.startswith("# Gates\n\n## "):
        raise StoreError("gates.md has an invalid heading")
    rows = []
    for block in text[len("# Gates\n\n## "):].split("\n\n## "):
        lines = [line for line in block.splitlines() if line]
        row = {"id": lines[0]}
        for line in lines[1:]:
            match = re.fullmatch(r"- ([^:]+): (.*)", line)
            if not match:
                raise StoreError("gates.md has a malformed gate")
            row[match[1]] = match[2]
        if (not all(key in row for key in ("Status", "Question", "Options", "Default"))
                or row["Status"] not in ("open", "resolved")
                or (row["Status"] == "resolved" and "Answer" not in row)):
            raise StoreError("gates.md has a malformed gate")
        rows.append(row)
    if len({row["id"] for row in rows}) != len(rows):
        raise StoreError("gates.md has duplicate gate IDs")
    return rows


def save_gates(store, rows):
    blocks = []
    for row in rows:
        keys = ["Status", "Question", "Options", "Default"]
        if row["Status"] == "resolved":
            keys.append("Answer")
        blocks.append(f"## {row['id']}\n\n" + "\n".join(f"- {key}: {row[key]}" for key in keys))
    atomic_write(store / "gates.md", "# Gates\n\n" + "\n\n".join(blocks) + "\n")


def standing(store):
    rows = []
    for line in (store / "preferences.md").read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        match = re.fullmatch(r"([1-9]\d*)\. (.+)", line)
        if not match or int(match[1]) != len(rows) + 1:
            raise StoreError("preferences.md has malformed numbering")
        rows.append({"number": int(match[1]), "line": match[2]})
    return rows


def pointers(directory):
    result = []
    for path in sorted(directory.glob("*.tsv")):
        values = path.read_text(encoding="utf-8").removesuffix("\n").split("\t")
        if len(values) != 5 or any("\n" in value or "\r" in value for value in values):
            raise StoreError(f"inbox pointer {path.name} is malformed")
        result.append(dict(zip(POINTER_FIELDS, values)))
    return result


def markdown_table(fields, rows):
    def escape(value):
        return str(value).replace("\\", "\\\\").replace("|", "\\|")
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    lines.extend("| " + " | ".join(escape(row.get(field, "")) for field in fields) + " |" for row in rows)
    return "\n".join(lines) if rows else "(none)"


def changes(previous, current):
    if previous is None:
        return "first render"
    if not isinstance(previous, dict):
        return "first render"
    result = []
    for field, label in (("unitStates", "units"), ("ledgerVerdicts", "ledger")):
        before = previous.get(field)
        if not isinstance(before, dict):
            return "first render"
        after = current[field]
        for key in sorted(before.keys() | after.keys()):
            old, new = before.get(key, 0), after.get(key, 0)
            if old != new:
                result.append(f"{label} {key} {old}->{new}")
    if previous.get("frontierGeneration") != current["frontierGeneration"]:
        result.append(f"frontier generation {previous.get('frontierGeneration')}->{current['frontierGeneration']}")
    if previous.get("openGateIds") != current["openGateIds"]:
        result.append(f"open gates: {','.join(current['openGateIds']) or 'none'}")
    return "; ".join(result) or "no derived changes"


def render_status(store):
    units = read_table(store / "units.tsv", UNIT_FIELDS)
    ledger = read_table(store / "ledger.tsv", LEDGER_FIELDS)
    current = frontier(store)
    gates = read_gates(store)
    summary = {"unitStates": counts(units, "state"), "ledgerVerdicts": counts(ledger, "verdict"),
               "frontierGeneration": current["generation"],
               "openGateIds": sorted(row["id"] for row in gates if row["Status"] == "open")}
    path = store / "status.md"
    previous = None
    if path.exists():
        match = re.search(r"<!-- orch-summary (.+) -->", path.read_text(encoding="utf-8"))
        if match:
            try:
                previous = json.loads(match[1])
            except ValueError:
                pass
    changed = changes(previous, summary)
    sections = [("Units", UNIT_FIELDS, units), ("Verification ledger", LEDGER_FIELDS, ledger),
                ("Frontier", ("pr", "branches", "sha", "state"), current["prs"]),
                ("Gates", ("id", "Status", "Question", "Options", "Default", "Answer"), gates)]
    text = f"# Orchestrate status\n\nGenerated: {now()}\n\n"
    text += "\n\n".join(f"## {name}\n\n{markdown_table(fields, rows)}" for name, fields, rows in sections)
    text += f"\n\n<!-- orch-summary {json.dumps(summary)} -->\n"
    atomic_write(path, text)
    return {"units": units, "ledger": ledger, "frontier": current, "gates": gates,
            "summary": summary, "changed": changed}


def operate(args, store):
    if args.command == "init":
        for name, text in (("units.tsv", "\t".join(UNIT_FIELDS) + "\n"),
                           ("ledger.tsv", "\t".join(LEDGER_FIELDS) + "\n"),
                           ("gates.md", ""), ("preferences.md", ""), ("frontier.json", "{}\n")):
            if not (store / name).exists():
                atomic_write(store / name, text)
        (store / "inbox").mkdir(exist_ok=True)
        (store / "inbox-claimed").mkdir(exist_ok=True)
        return {"store": str(store)}
    if not (store / "units.tsv").exists():
        raise StoreError(f"store is not initialized at {store}; run orch init")
    if args.command == "unit":
        rows = read_table(store / "units.tsv", UNIT_FIELDS)
        if args.action in ("add", "set", "get"):
            unit_id = required(args.id, "unit id")
            row = next((row for row in rows if row["id"] == unit_id), None)
            if args.action == "add":
                if row is not None:
                    raise StoreError(f"unit {unit_id} already exists")
                row = dict.fromkeys(UNIT_FIELDS, "")
                row.update(id=unit_id, track=required(args.track, "track"), state="pending",
                           brief=cell(args.brief or ""))
                rows.append(row)
            elif row is None:
                raise Missing(f"unit {unit_id} not found")
            if args.action == "set":
                for key in ("state", "branch", "pr", "sha"):
                    value = getattr(args, key)
                    if value is not None:
                        row[key] = required(value, key)
            if args.action != "get":
                write_table(store / "units.tsv", UNIT_FIELDS, rows)
            return row
        if args.action == "counts":
            return counts(rows, "state")
        return [row for row in rows if (args.state is None or row["state"] == cell(args.state))
                and (args.track is None or row["track"] == cell(args.track))]
    if args.command == "ledger":
        rows = read_table(store / "ledger.tsv", LEDGER_FIELDS)
        if args.action == "summary":
            return counts(rows, "verdict")
        sha = required(args.sha, "SHA")
        row = next((row for row in rows if row["pr"] == str(args.pr) and row["sha"] == sha), None)
        if args.action == "check":
            if row is None:
                return {"pr": str(args.pr), "sha": sha, "verdict": "NOT-VERIFIED"}
            return row
        value = {"pr": str(args.pr), "sha": sha, "verdict": args.verdict,
                 "evidence": required(args.evidence, "evidence"), "verifier": cell(args.verifier or ""), "ts": now()}
        if row is not None:
            rows.remove(row)
        rows.append(value)
        write_table(store / "ledger.tsv", LEDGER_FIELDS, rows)
        return value
    if args.command == "inbox":
        inbox, claimed = store / "inbox", store / "inbox-claimed"
        inbox.mkdir(exist_ok=True)
        claimed.mkdir(exist_ok=True)
        batches = sorted(path for path in claimed.iterdir() if path.is_dir())
        if any(not re.fullmatch(r"[0-9a-f]{32}", path.name) for path in batches):
            raise StoreError("inbox-claimed contains an invalid batch directory")
        if args.action == "push":
            row = {"ts": now(), "agent": required(args.agent, "agent"), "unit": required(args.unit, "unit"),
                   "status": required(args.status, "status"), "report": cell(args.report or "")}
            filename = uuid4().hex + ".tsv"
            atomic_write(inbox / filename, "\t".join(cell(row[key]) for key in POINTER_FIELDS) + "\n")
            return {"pointer": row, "filename": filename}
        if args.action == "ack":
            if not re.fullmatch(r"[0-9a-f]{32}", args.batch):
                raise StoreError("invalid inbox batch ID")
            batch = claimed / args.batch
            if batch.exists():
                shutil.rmtree(batch)
            return {"batch": args.batch, "acknowledged": True}
        if args.action == "drain" and not args.peek:
            if len(batches) > 1:
                raise StoreError("multiple unacknowledged batches; reconcile them before draining")
            if batches:
                return {"batch": batches[0].name, "pointers": pointers(batches[0])}
            pending = pointers(inbox)
            if not pending:
                return {"batch": None, "pointers": []}
            batch = uuid4().hex
            os.replace(inbox, claimed / batch)
            inbox.mkdir()
            return {"batch": batch, "pointers": pending}
        pending = [row for directory in batches + [inbox] for row in pointers(directory)]
        return len(pending) if args.action == "count" else pending
    if args.command == "gate":
        rows = read_gates(store)
        if args.action == "list":
            return [row for row in rows if row["Status"] == "open"]
        gate_id = required(args.id, "gate id")
        if "## " in gate_id:
            raise StoreError("gate ID cannot contain a heading delimiter")
        row = next((row for row in rows if row["id"] == gate_id), None)
        if args.action == "park":
            value = {"id": gate_id, "Status": "open", "Question": required(args.question, "question"),
                     "Options": required(args.options, "options"), "Default": required(args.default, "default")}
            if row is not None:
                rows.remove(row)
            rows.append(value)
            row = value
        else:
            if row is None:
                raise Missing(f"gate {gate_id} not found")
            row.update(Status="resolved", Answer=required(args.answer, "answer"))
        save_gates(store, rows)
        return row
    if args.command == "standing":
        rows = standing(store)
        if args.action == "show":
            return rows
        row = {"number": len(rows) + 1, "line": required(args.line, "standing order")}
        rows.append(row)
        atomic_write(store / "preferences.md", "".join(f"{row['number']}. {row['line']}\n" for row in rows))
        return row
    if args.command == "frontier":
        old = frontier(store)
        if args.action == "show":
            return old
        repo_arg = args.repo or os.environ.get("ORCH_REPO")
        if not repo_arg or not Path(repo_arg).is_dir():
            raise StoreError("set --repo <existing repository dir> or ORCH_REPO")
        expected = args.prs if args.prs is not None else [row["pr"] for row in old["prs"]]
        if not expected:
            raise StoreError("set --prs <bottom-up PR list> to declare the stack scope")
        discovered = resolve_frontier(Path(repo_arg).resolve(), expected)
        if old.get("repository") and old["repository"] != discovered["repository"]:
            raise StoreError("repository does not match the saved frontier; use the correct store")
        rows = discovered["prs"]
        value = {**discovered, "generation": old["generation"] + 1,
                 "lowestUnmerged": next((row["pr"] for row in rows if row["state"] != "MERGED"), None)}
        atomic_write(store / "frontier.json", json.dumps(value, indent=2) + "\n")
        return value
    return render_status(store)


def positive_integer(value):
    if not re.fullmatch(r"[1-9]\d*", value):
        raise argparse.ArgumentTypeError("must be a positive integer")
    return int(value)


def pr_list(value):
    parts = [positive_integer(part) for part in value.split(",")]
    if len(set(parts)) != len(parts):
        raise argparse.ArgumentTypeError("--prs must not contain duplicates")
    return parts


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--store", default=os.environ.get("ORCH_STORE"))
    result.add_argument("--json", action="store_true")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("status")
    for command, actions in (("unit", ("add", "set", "get", "list", "counts")),
                             ("ledger", ("record", "check", "summary")),
                             ("inbox", ("push", "drain", "count", "peek", "ack")),
                             ("gate", ("park", "list", "resolve")),
                             ("frontier", ("set", "show")), ("standing", ("show", "add"))):
        children = commands.add_parser(command).add_subparsers(dest="action", required=True)
        for action in actions:
            item = children.add_parser(action)
            if command == "unit":
                if action in ("add", "set", "get"):
                    item.add_argument("id")
                if action in ("add", "list"):
                    item.add_argument("--track", required=action == "add")
                if action == "add":
                    item.add_argument("--brief")
                if action in ("set", "list"):
                    item.add_argument("--state", required=action == "set")
                if action == "set":
                    item.add_argument("--branch")
                    item.add_argument("--pr", type=positive_integer)
                    item.add_argument("--sha")
            elif command == "ledger" and action in ("record", "check"):
                item.add_argument("pr", type=positive_integer)
                item.add_argument("sha")
                if action == "record":
                    item.add_argument("verdict", choices=VERDICTS)
                    item.add_argument("--evidence", required=True)
                    item.add_argument("--verifier")
            elif command == "inbox":
                if action == "push":
                    for field in ("agent", "unit", "status"):
                        item.add_argument(field)
                    item.add_argument("--report")
                if action == "drain":
                    item.add_argument("--peek", action="store_true")
                if action == "ack":
                    item.add_argument("batch")
            elif command == "gate" and action != "list":
                item.add_argument("id")
                for field in (("question", "options", "default") if action == "park" else ("answer",)):
                    item.add_argument("--" + field, required=True)
            elif command == "frontier" and action == "set":
                item.add_argument("--repo")
                item.add_argument("--prs", type=pr_list)
            elif command == "standing" and action == "add":
                item.add_argument("line")
    return result


def compact(value):
    if isinstance(value, dict) and "summary" in value:
        summary = value["summary"]
        return (f"counts: units={len(value['units'])}; states={json.dumps(summary['unitStates'])}; "
                f"ledger={json.dumps(summary['ledgerVerdicts'])}\nchanged: {value['changed']}\n"
                f"gates open: {len(summary['openGateIds'])}")
    if isinstance(value, dict) and "pointers" in value:
        rows = [f"batch={value['batch'] or 'none'}"]
        rows.extend("\t".join(row[key] for key in POINTER_FIELDS) for row in value["pointers"])
        return "\n".join(rows)
    if isinstance(value, list):
        visible = value[:4]
        text = "\n".join(json.dumps(row) for row in visible) or "(none)"
        return text + (f"\n... {len(value) - 4} more; use --json" if len(value) > 4 else "")
    return json.dumps(value)


def main(argv=None):
    try:
        raw = list(sys.argv[1:] if argv is None else argv)
        global_args, rest = [], []
        index = 0
        while index < len(raw):
            argument = raw[index]
            if argument == "--json" or argument.startswith("--store="):
                global_args.append(argument)
            elif argument == "--store":
                global_args.extend(raw[index:index + 2])
                index += 1
            else:
                rest.append(argument)
            index += 1
        args = parser().parse_args(global_args + rest)
        if not args.store or not args.store.strip():
            raise StoreError("set --store <dir> or ORCH_STORE")
        store = Path(args.store).resolve()
        if args.command != "init" and not store.is_dir():
            raise StoreError(f"store is not initialized at {store}; run orch init")
        with locked(store):
            value = operate(args, store)
        print(json.dumps(value, indent=2) if args.json else compact(value))
        return 2 if isinstance(value, dict) and value.get("verdict") == "NOT-VERIFIED" else 0
    except Missing as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (StoreError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
