#!/usr/bin/env python3
"""Bounded hourly audit registration receipts. Requires Python 3.10+."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from uuid import uuid4

sys.dont_write_bytecode = True
from orch import StoreError, atomic_write, locked


LIMIT = 65536
CADENCE = 3600
CHECKPOINT_LISTS = ("units", "owners", "published_heads", "findings", "evidence",
                    "next_actions", "unresolved_gates")
CAPABILITIES = ("durable", "exact_lookup", "idempotent_ensure", "scoped_cancel", "readback")
QUEUE_FILES = ("standing-orders.md", "units.tsv", "ledger.tsv", "gates.md",
               "preferences.md", "frontier.json")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StoreError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def digest(value):
    return hashlib.sha256(value).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("timezone missing")
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise StoreError("timestamp must be ISO 8601 with a timezone") from exc


def iso(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path, limit=LIMIT):
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise StoreError(f"{path} exceeds {limit} bytes")
        return json.loads(data, object_pairs_hook=unique_object)
    except (OSError, ValueError, UnicodeError) as exc:
        raise StoreError(f"cannot read JSON from {path}: {exc}") from exc


def checkpoint(path):
    value = read_json(path)
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise StoreError("checkpoint requires schema_version 1")
    for field in ("program", "repo", "authorization", "resume"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise StoreError(f"checkpoint requires nonempty {field}")
    for field in CHECKPOINT_LISTS:
        if not isinstance(value.get(field), list):
            raise StoreError(f"checkpoint requires {field} list")
    for owner in value["owners"]:
        if (not isinstance(owner, dict) or not isinstance(owner.get("id"), str)
                or not owner["id"].strip() or not isinstance(owner.get("scope"), list)
                or not all(isinstance(item, str) and item.strip() for item in owner["scope"])):
            raise StoreError("checkpoint owners require id and scope list")
    return value


def adapter(path):
    value = read_json(path)
    if (not isinstance(value, dict) or value.get("schema_version") != 1
            or not isinstance(value.get("argv"), list) or not value["argv"]
            or not all(isinstance(item, str) and item and "\0" not in item for item in value["argv"])
            or type(value.get("timeout_seconds")) not in (int, float)
            or not 1 <= value["timeout_seconds"] <= 30):
        raise StoreError("adapter requires schema_version 1, argv, and timeout_seconds from 1 through 30")
    return value


def queue_snapshot(store):
    paths = [store / name for name in QUEUE_FILES]
    for name in ("inbox", "inbox-claimed"):
        inbox = store / name
        if inbox.exists():
            paths.extend(sorted(path for path in inbox.rglob("*") if path.is_file()))
    result = {}
    total = 0
    for path in paths:
        if not path.exists():
            continue
        with path.open("rb") as stream:
            data = stream.read(LIMIT + 1)
        total += len(data)
        if len(data) > LIMIT or total > 4 * LIMIT:
            raise StoreError("queue snapshot exceeds the bounded checkpoint size")
        result[str(path.relative_to(store))] = {"sha256": digest(data), "contents": data.decode("utf-8")}
    return result


def save(path, receipt):
    atomic_write(path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def call_host(receipt, path, operation, registration_id=None):
    pending = receipt.get("pending")
    operation_id = (pending["operation_id"] if pending and pending["operation"] == operation else str(uuid4()))
    request = {"schema_version": 1, "operation": operation, "operation_id": operation_id,
               "program_key": receipt["program_key"], "target": receipt["target"],
               "cadence_seconds": CADENCE}
    if registration_id is not None:
        request["registration_id"] = registration_id
    if operation in ("ensure", "cancel"):
        receipt["pending"] = {"operation": operation, "operation_id": operation_id,
                              "registration_id": registration_id}
        save(path, receipt)
    command = receipt["adapter"]
    output = [b"", b""]
    exceeded = threading.Event()
    with tempfile.TemporaryFile() as input_stream:
        input_stream.write(encode(request))
        input_stream.seek(0)
        deadline = time.monotonic() + command["timeout_seconds"]
        process = subprocess.Popen(command["argv"], stdin=input_stream, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=receipt["target"]["store"],
                                   start_new_session=os.name != "nt")
        def kill():
            if os.name == "nt":
                process.kill()
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        def capture(index, stream):
            output[index] = stream.read(LIMIT + 1)
            if len(output[index]) > LIMIT:
                exceeded.set()
                kill()
            stream.close()
        readers = [threading.Thread(target=capture, args=(index, stream), daemon=True)
                   for index, stream in enumerate((process.stdout, process.stderr))]
        for reader in readers:
            reader.start()
        failure = None
        try:
            process.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            failure = "host adapter timed out"
            kill()
            process.wait(timeout=1)
        for reader in readers:
            reader.join(timeout=max(0, deadline - time.monotonic()))
        if any(reader.is_alive() for reader in readers):
            failure = "host adapter left output pipes open"
            kill()
            for reader in readers:
                reader.join(timeout=0.2)
        if exceeded.is_set() or sum(map(len, output)) > LIMIT:
            failure = "host adapter response exceeds bounded size"
        raw = {"request": request, "operation": operation, "operation_id": operation_id,
               "stdout": output[0][:LIMIT].decode("utf-8", errors="replace"),
               "stderr": output[1][:LIMIT].decode("utf-8", errors="replace"),
               "exit_code": process.returncode, "error": failure}
        directory = path.parent / "audit-host-responses"
        directory.mkdir(exist_ok=True)
        response_path = directory / f"{uuid4()}.json"
        save(response_path, raw)
        receipt["host_responses"].append({"operation": operation, "operation_id": operation_id,
                                          "path": str(response_path), "sha256": digest(response_path.read_bytes())})
        receipt["host_responses"] = receipt["host_responses"][-20:]
        save(path, receipt)
        if failure or process.returncode:
            raise StoreError(failure or f"host adapter exited {process.returncode}")
        try:
            value = json.loads(output[0], object_pairs_hook=unique_object)
        except (ValueError, UnicodeError) as exc:
            raise StoreError("host adapter returned malformed JSON") from exc
        if not isinstance(value, dict):
            raise StoreError("host adapter response must be an object")
        return value


def registration(value, receipt):
    rows = value.get("registrations")
    if not isinstance(rows, list) or len(rows) > 1:
        raise StoreError("host lookup is malformed or ambiguous")
    if not rows:
        return None
    row = rows[0]
    if (not isinstance(row, dict) or not isinstance(row.get("registration_id"), str)
            or not row["registration_id"] or row.get("program_key") != receipt["program_key"]
            or row.get("target") != receipt["target"] or row.get("cadence_seconds") != CADENCE
            or row.get("status") not in ("enabled", "disabled")):
        raise StoreError("host registration ownership, target, status, or hourly cadence mismatch")
    if receipt.get("registration_id") not in (None, row["registration_id"]):
        raise StoreError("host registration identifier changed")
    return row


def reconcile(receipt, path, allow_ensure):
    stopped = receipt["desired"] == "stopped"
    receipt["registration_status"] = "cancellation-unconfirmed" if stopped else "unconfirmed"
    if receipt["adapter"] is None:
        receipt["registration_status"] = "stopped" if stopped else "unavailable"
        receipt["error"] = "Unattended continuation is unavailable. No supported host adapter was supplied."
        return
    discovery = call_host(receipt, path, "discover")
    if discovery.get("supported") is False:
        receipt["registration_status"] = "cancellation-unconfirmed" if stopped else "unavailable"
        receipt["error"] = "Unattended continuation is unavailable. The adapter reports no durable host capability."
        return
    if (discovery.get("supported") is not True
            or not isinstance(discovery.get("capabilities"), dict)
            or any(discovery["capabilities"].get(key) is not True for key in CAPABILITIES)):
        raise StoreError("host cannot prove all required durable scheduling capabilities")
    row = registration(discovery, receipt)
    if stopped:
        if row is None:
            receipt.update(registration_status="stopped", pending=None, error=None)
            return
        receipt["registration_id"] = row["registration_id"]
        row = registration(call_host(receipt, path, "readback", row["registration_id"]), receipt)
        if row and row["status"] == "enabled":
            call_host(receipt, path, "cancel", row["registration_id"])
            row = registration(call_host(receipt, path, "readback", row["registration_id"]), receipt)
        if row and row["status"] == "enabled":
            raise StoreError("host cancellation is unconfirmed")
        receipt.update(registration_status="stopped", pending=None, error=None)
        return
    if row is None:
        if receipt.get("registration_id") or not allow_ensure:
            raise StoreError("previous registration disappeared; unattended continuation is unconfirmed")
        call_host(receipt, path, "ensure")
    else:
        receipt["registration_id"] = row["registration_id"]
        if row["status"] == "disabled" and allow_ensure:
            call_host(receipt, path, "ensure", row["registration_id"])
    row = registration(call_host(receipt, path, "readback", receipt.get("registration_id")), receipt)
    if row is None:
        raise StoreError("host readback does not prove a registration")
    receipt.update(registration_id=row["registration_id"],
                   registration_status="armed" if row["status"] == "enabled" else "suspended",
                   pending=None, error=None)


def next_due(receipt):
    last = receipt["last_completed_audit"]
    return timestamp(last["due_at"]) + timedelta(seconds=CADENCE) if last else timestamp(receipt["first_due_at"])


def view(receipt, moment, current=None, notify=False):
    due = next_due(receipt)
    return {"schema_version": 1, "program_key": receipt["program_key"], "desired": receipt["desired"],
            "registration_id": receipt["registration_id"], "registration_status": receipt["registration_status"],
            "registration_observed_at": receipt["registration_observed_at"],
            "last_completed_audit": receipt["last_completed_audit"], "next_expected_audit": iso(due),
            "overdue_seconds": max(0, int((moment - due).total_seconds())) if receipt["desired"] == "active" else 0,
            "error": receipt["error"], "pending": receipt["pending"], "notify": notify,
            "checkpoint": receipt["checkpoint"], "checkpoint_sha256": receipt["checkpoint_sha256"],
            "current_queue_files": current,
            "recovery_hold": bool(receipt["checkpoint"]["metadata"]["unresolved_gates"])
                or (current is not None and current.get("gates.md") != receipt["checkpoint"]["queue_files"].get("gates.md"))}


def notification(receipt, moment, current=None):
    value = {key: receipt[key] for key in ("desired", "registration_status", "error")}
    value["gates_sha256"] = digest(encode(current.get("gates.md"))) if current is not None else receipt.get("gates_sha256")
    receipt["gates_sha256"] = value["gates_sha256"]
    value["overdue"] = receipt["desired"] == "active" and moment > next_due(receipt)
    value["report"] = receipt.get("last_report", {"progress": [], "failures": [], "required_actions": []})
    fingerprint = digest(encode(value))
    changed = fingerprint != receipt.get("notification_sha256")
    receipt["notification_sha256"] = fingerprint
    return changed


def complete(receipt, args, moment):
    report = read_json(args.report)
    if not isinstance(report, dict) or any(not isinstance(report.get(key), list)
                                         for key in ("progress", "failures", "required_actions")):
        raise StoreError("audit report requires progress, failures, and required_actions lists")
    with args.evidence.open("rb") as stream:
        evidence = stream.read(LIMIT + 1)
    if not evidence or len(evidence) > LIMIT:
        raise StoreError("audit evidence must be nonempty and bounded")
    due = iso(timestamp(args.due_at))
    item = {"delivery_id": args.delivery_id, "due_at": due, "report": report,
            "evidence": {"path": str(args.evidence.resolve()), "sha256": digest(evidence),
                         "contents": evidence.decode("utf-8")}}
    directory = Path(receipt["target"]["store"]) / "audit-completions"
    completion_path = directory / (digest(args.delivery_id.encode()) + ".json")
    prior = read_json(completion_path, 4 * 1024 * 1024) if completion_path.exists() else None
    if prior:
        if any(prior[key] != item[key] for key in item):
            raise StoreError("replayed delivery differs from its completed receipt")
        if receipt["last_completed_audit"] and timestamp(due) < next_due(receipt):
            return False
    if receipt["desired"] == "stopped":
        raise StoreError("stopped programs cannot complete a new audit")
    if not args.delivery_id.strip() or timestamp(due) != next_due(receipt) or timestamp(due) > moment:
        raise StoreError("audit must cover the next due occurrence at or before completion")
    item["completed_at"] = prior["completed_at"] if prior else iso(moment)
    directory.mkdir(exist_ok=True)
    if not prior:
        save(completion_path, item)
    receipt["last_completed_audit"] = {key: item[key] for key in ("delivery_id", "due_at", "completed_at")}
    receipt["last_completed_audit"]["receipt_path"] = str(completion_path)
    receipt["last_completed_audit"]["evidence"] = {key: item["evidence"][key] for key in ("path", "sha256")}
    receipt["last_report"] = report
    return notification(receipt, moment)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--store", type=Path, required=True)
    result.add_argument("--now", help="explicit UTC clock for deterministic replay")
    commands = result.add_subparsers(dest="command", required=True)
    ensure = commands.add_parser("ensure")
    ensure.add_argument("--checkpoint", type=Path, required=True)
    ensure.add_argument("--adapter", type=Path)
    for command in ("status", "pickup", "stop"):
        commands.add_parser(command)
    done = commands.add_parser("complete")
    done.add_argument("--delivery-id", required=True)
    done.add_argument("--due-at", required=True)
    done.add_argument("--evidence", type=Path, required=True)
    done.add_argument("--report", type=Path, required=True)
    return result


def main(arguments=None):
    args = parser().parse_args(arguments)
    store = args.store.resolve()
    path = store / "audit-registration.json"
    try:
        moment = timestamp(args.now) if args.now else datetime.now(timezone.utc)
        if args.command == "status":
            print(json.dumps(view(read_json(path, 4 * 1024 * 1024), moment, queue_snapshot(store)), sort_keys=True))
            return 0
        with locked(store):
            receipt = read_json(path, 4 * 1024 * 1024) if path.exists() else None
            if args.command == "ensure":
                snapshot = checkpoint(args.checkpoint)
                command = adapter(args.adapter) if args.adapter else None
                target = {"repo": snapshot["repo"], "store": str(store), "checkpoint": str(path)}
                program_key = "harness-audit:" + digest(encode({"program": snapshot["program"],
                                                              "repo": snapshot["repo"], "store": str(store)}))
                if receipt:
                    if (receipt["program_key"] != program_key or receipt["target"] != target
                            or receipt["adapter"] != command):
                        raise StoreError("existing program, target, or adapter changed; use its frozen pickup packet")
                    original = receipt["checkpoint"]
                    if any(original["metadata"][key] != snapshot[key] for key in ("authorization", "unresolved_gates")):
                        raise StoreError("frozen authorization or unresolved gates changed; start a separately authorized program")
                    packet = {"metadata": snapshot, "queue_files": queue_snapshot(store)}
                    if "gates.md" in original["queue_files"]:
                        packet["queue_files"]["gates.md"] = original["queue_files"]["gates.md"]
                    receipt["checkpoint"] = packet
                    receipt["checkpoint_sha256"] = digest(encode(packet))
                    save(path, receipt)
                else:
                    packet = {"metadata": snapshot, "queue_files": queue_snapshot(store)}
                    receipt = {"schema_version": 1, "program_key": program_key, "target": target,
                               "adapter": command, "desired": "active", "checkpoint": packet,
                               "checkpoint_sha256": digest(encode(packet)),
                               "first_due_at": iso(moment + timedelta(seconds=CADENCE)),
                               "registration_id": None, "registration_status": "unconfirmed",
                               "registration_observed_at": None, "pending": None, "error": None,
                               "host_responses": [], "last_completed_audit": None}
                    save(path, receipt)
            if receipt is None:
                raise StoreError("audit receipt missing; run ensure with a complete checkpoint")
            if args.command == "complete":
                notify = complete(receipt, args, moment)
                save(path, receipt)
                print(json.dumps(view(receipt, moment, notify=notify), sort_keys=True))
                return 0
            if args.command == "stop":
                receipt["desired"] = "stopped"
                receipt["registration_status"] = "cancellation-unconfirmed"
                save(path, receipt)
            failure = None
            try:
                reconcile(receipt, path, allow_ensure=args.command == "ensure")
                receipt["registration_observed_at"] = iso(moment)
            except (StoreError, OSError) as exc:
                receipt["error"] = str(exc)
                failure = str(exc)
            current = queue_snapshot(store)
            notify = notification(receipt, moment, current)
            save(path, receipt)
            print(json.dumps(view(receipt, moment, current, notify), sort_keys=True))
            return 1 if failure else 0
    except (StoreError, OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
