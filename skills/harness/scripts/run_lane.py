#!/usr/bin/env python3
"""Run one cooperative verification lane with private state and owned groups."""

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import Mapping


@dataclass(frozen=True)
class LaneSpec:
    checkout: Path
    expected_head: str
    temp_root: Path
    argv: tuple[str, ...]
    deadline_seconds: float
    public_env: Mapping[str, str] = field(default_factory=dict)
    secret_env: Mapping[str, str] = field(default_factory=dict)
    receipt: Path | None = None


@dataclass(frozen=True)
class LaneResult:
    receipt_path: Path | None
    outcome: str
    returncode: int | None
    cleanup: str
    reason: str


class LaneFailure(Exception):
    def __init__(self, reason, outcome="environment_failed"):
        self.reason = reason
        self.outcome = outcome


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    parent: int
    group: int
    session: int
    state: str
    started: int


def inventory():
    result = {}
    try:
        for entry in Path("/proc").iterdir():
            if not entry.name.isdecimal():
                continue
            try:
                raw = (entry / "stat").read_text()
            except (FileNotFoundError, ProcessLookupError):
                continue
            fields = raw.rsplit(")", 1)[1].split()
            result[int(entry.name)] = ProcessIdentity(
                int(entry.name), int(fields[1]), int(fields[2]),
                int(fields[3]), fields[0], int(fields[19]),
            )
    except (OSError, ValueError, IndexError):
        raise LaneFailure("process_inventory_unavailable") from None
    return result


class Owner:
    cleanup_allowance = 1.0
    term_grace = 0.2

    def __init__(self, root, environment, deadline):
        self.root = root
        self.environment = environment
        self.deadline = deadline
        self.cancelled = None
        self.commands = []

    def cancel(self, signum, frame):
        self.cancelled = signal.Signals(signum).name

    def check_budget(self):
        if self.cancelled:
            raise LaneFailure("interrupted", "cancelled")
        if time.monotonic() >= self.deadline:
            raise LaneFailure("deadline_reached", "timed_out")

    def run(self, argv, cwd, name):
        self.check_budget()
        command = {
            "phase": name, "argv": list(argv), "returncode": None,
            "trigger": "exited", "cleanup": "incomplete", "signals": [],
            "residual_zombies": [], "escaped_observed": [],
        }
        self.commands.append(command)
        started = time.monotonic()
        seen = {}
        child = None
        with (self.root / f"{name}.stdout").open("wb") as output, (self.root / f"{name}.stderr").open("wb") as errors:
            try:
                child = subprocess.Popen(
                    argv, cwd=cwd, env=self.environment, stdin=subprocess.DEVNULL,
                    stdout=output, stderr=errors, start_new_session=True,
                )
                command["leader"] = child.pid
                while True:
                    rows = inventory()
                    self._observe(rows, child.pid, seen)
                    if self.cancelled:
                        command["trigger"] = "cancelled"
                        break
                    if time.monotonic() >= self.deadline:
                        command["trigger"] = "timed_out"
                        break
                    observed = os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    if observed is not None:
                        break
                    time.sleep(0.02)
            except LaneFailure:
                command["trigger"] = "inventory_failed"
            except OSError:
                command["trigger"] = "spawn_failed" if child is None else "observation_failed"
            finally:
                command["execution_seconds"] = time.monotonic() - started
                if child is not None:
                    self._cleanup(child, command, seen)
                else:
                    command["cleanup"] = "not_started"
        if command["cleanup"] == "incomplete":
            raise LaneFailure("cleanup_incomplete", command["trigger"] if command["trigger"] in {"timed_out", "cancelled"} else "environment_failed")
        if command["trigger"] in {"cancelled", "timed_out"}:
            raise LaneFailure(command["trigger"], command["trigger"])
        if command["trigger"] != "exited":
            raise LaneFailure(command["trigger"])
        with (self.root / f"{name}.stdout").open("rb") as output:
            return command["returncode"], output.read(16384)

    @staticmethod
    def _observe(rows, leader, seen):
        owned = {leader}
        changed = True
        while changed:
            changed = False
            for row in rows.values():
                if row.parent in owned and row.pid not in owned:
                    owned.add(row.pid)
                    changed = True
        for row in rows.values():
            if row.pid in owned or row.group == leader:
                seen[(row.pid, row.started)] = row

    def _cleanup(self, child, command, seen):
        started = time.monotonic()
        end = started + self.cleanup_allowance
        inventory_ok = command["trigger"] != "inventory_failed"

        def send(sig):
            nonlocal inventory_ok
            record = {"signal": signal.Signals(sig).name, "result": "sent"}
            try:
                os.killpg(child.pid, sig)
            except ProcessLookupError:
                record["result"] = "absent"
            except OSError:
                record["result"] = "denied"
                inventory_ok = False
            command["signals"].append(record)

        def inspect():
            nonlocal inventory_ok
            try:
                rows = inventory()
                self._observe(rows, child.pid, seen)
                members = [row for row in rows.values() if row.group == child.pid]
                command["residual_zombies"] = [row.pid for row in members if row.state == "Z" and row.pid != child.pid]
                escapes = [row.pid for row in rows.values() if (row.pid, row.started) in seen and row.group != child.pid and row.state != "Z"]
                command["escaped_observed"] = escapes
                return [row for row in members if row.state != "Z"], escapes
            except LaneFailure:
                inventory_ok = False
                return None, []

        # The unreaped direct child reserves its group identity until the last signal.
        send(signal.SIGTERM)
        term_end = min(end, started + self.term_grace)
        live, escaped = inspect()
        while (live is None or live) and time.monotonic() < term_end:
            time.sleep(0.02)
            live, escaped = inspect()
        if live is None or live:
            send(signal.SIGKILL)
        live, escaped = inspect()
        while (live is None or live) and time.monotonic() < end:
            time.sleep(0.02)
            live, escaped = inspect()
        try:
            command["returncode"] = child.wait(timeout=max(0.01, end - time.monotonic()))
        except subprocess.TimeoutExpired:
            inventory_ok = False
        live, escaped = inspect()
        command["cleanup"] = "complete" if inventory_ok and live == [] and not escaped else "incomplete"
        command["cleanup_seconds"] = time.monotonic() - started


def _support():
    if os.name != "posix" or not sys.platform.startswith("linux") or threading.current_thread() is not threading.main_thread():
        raise LaneFailure("linux_main_thread_required", "unsupported")
    if not all(hasattr(os, name) for name in ("waitid", "WNOWAIT", "WEXITED", "P_PID", "killpg")):
        raise LaneFailure("process_ownership_unavailable", "unsupported")
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        raise LaneFailure("default_sigchld_required", "unsupported")
    try:
        rows = inventory()
        if os.getpid() not in rows:
            raise LaneFailure("process_inventory_unavailable")
    except LaneFailure:
        raise LaneFailure("process_inventory_unavailable", "unsupported") from None


def _safe_receipt(value, secrets):
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[redacted]")
        return value
    if isinstance(value, dict):
        return {_safe_receipt(key, secrets): _safe_receipt(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_receipt(item, secrets) for item in value]
    return value


def _hooks(path, secrets, execution_seconds):
    events = []
    rejected = 0
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except FileNotFoundError:
        return events, 0
    except OSError:
        return events, 1
    try:
        with os.fdopen(descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                return events, 1
            content = source.read(65537)
        if len(content) > 65536:
            return events, 1
        for line in content.decode().splitlines():
            try:
                event = json.loads(line)
                if not isinstance(event, dict) or any(secret in json.dumps(event, ensure_ascii=False) for secret in secrets):
                    raise ValueError
                if set(event) == {"kind", "id", "elapsed_seconds"} and event["kind"] == "ready":
                    elapsed = event["elapsed_seconds"]
                    if not isinstance(event["id"], str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,80}", event["id"]):
                        raise ValueError
                    if isinstance(elapsed, bool) or not isinstance(elapsed, (float, int)) or not math.isfinite(elapsed) or not 0 <= elapsed <= execution_seconds:
                        raise ValueError
                elif set(event) == {"kind", "module", "file"} and event["kind"] == "import":
                    if not isinstance(event["module"], str) or not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_.]{0,119}", event["module"]):
                        raise ValueError
                    if not isinstance(event["file"], str) or not Path(event["file"]).is_absolute():
                        raise ValueError
                    event["file"] = str(Path(event["file"]).resolve(strict=True))
                else:
                    raise ValueError
                events.append(event)
            except (ValueError, TypeError, OSError):
                rejected += 1
    except (OSError, UnicodeError):
        rejected += 1
    return events, rejected


def run_lane(spec):
    started = time.monotonic()
    deadline = started + spec.deadline_seconds
    root = None
    export = None
    owner = None
    prior_handlers = {}
    secrets = sorted({value for value in spec.secret_env.values() if value}, key=len, reverse=True)
    data = {
        "version": 1, "outcome": "environment_failed", "reason": "invalid_configuration",
        "returncode": None, "cleanup": "not_started", "started_at": datetime.now(timezone.utc).isoformat(),
        "deadline_seconds": spec.deadline_seconds, "cleanup_allowance_seconds": Owner.cleanup_allowance,
        "source": {}, "command": [], "environment_keys": [], "commands": [], "hooks": [],
    }
    try:
        if not math.isfinite(spec.deadline_seconds) or spec.deadline_seconds <= 0:
            raise LaneFailure("invalid_deadline")
        if not spec.argv or any(not isinstance(arg, str) or "\0" in arg for arg in spec.argv) or not spec.argv[0]:
            raise LaneFailure("invalid_command")
        if any(secret in arg for arg in spec.argv for secret in secrets):
            raise LaneFailure("secret_in_command")
        if any(re.search(r"(?i)(?:--(?:password|token|secret|api-key|credential)(?:=|$)|://[^/\s]+:[^/\s]+@)", arg) for arg in spec.argv):
            raise LaneFailure("credential_argument")
        data["requested_command"] = list(spec.argv)
        checkout = Path(spec.checkout).resolve(strict=True)
        temp_root = Path(spec.temp_root).resolve(strict=True)
        if not checkout.is_dir() or not temp_root.is_dir():
            raise LaneFailure("invalid_directory")
        if not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", spec.expected_head):
            raise LaneFailure("invalid_head")
        root = Path(tempfile.mkdtemp(prefix="harness-lane-", dir=temp_root))
        data["run_directory"] = str(root)
        data["source"] = {"checkout": str(checkout), "expected_head": spec.expected_head}
        for directory in ("home", "tmp", "cache", "pip-cache", "pycache"):
            (root / directory).mkdir(mode=0o700)
        environment = {
            "PATH": os.defpath, "HOME": str(root / "home"), "TMPDIR": str(root / "tmp"),
            "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"), "XDG_CACHE_HOME": str(root / "cache"),
            "PIP_CACHE_DIR": str(root / "pip-cache"), "PYTHONPYCACHEPREFIX": str(root / "pycache"),
            "PYTHONNOUSERSITE": "1", "VIRTUAL_ENV": str(root / "venv"),
            "HARNESS_LANE_HOOKS": str(root / "hooks.jsonl"),
        }
        for mapping in (spec.public_env, spec.secret_env):
            for key, value in mapping.items():
                if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or not isinstance(value, str) or "\0" in value:
                    raise LaneFailure("invalid_environment")
                if key in environment or key.startswith(("PYTHON", "PIP_", "XDG_", "GIT_", "LD_", "DYLD_")) or key in {"NODE_OPTIONS", "NODE_PATH", "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"}:
                    raise LaneFailure("reserved_environment")
                environment[key] = value
        data["environment_keys"] = sorted(environment)
        data["environment_paths"] = {key: value for key, value in environment.items() if key in {"HOME", "TMPDIR", "XDG_CACHE_HOME", "PIP_CACHE_DIR", "PYTHONPYCACHEPREFIX", "VIRTUAL_ENV", "HARNESS_LANE_HOOKS"}}
        if spec.receipt is not None:
            candidate = Path(spec.receipt)
            candidate = candidate.parent.resolve(strict=True) / candidate.name
            if candidate.exists() or candidate.is_symlink():
                raise LaneFailure("receipt_exists")
            export = candidate
        _support()
        owner = Owner(root, environment, deadline)
        data["commands"] = owner.commands
        for signum in (signal.SIGINT, signal.SIGTERM):
            prior_handlers[signum] = signal.signal(signum, owner.cancel)
        git = shutil.which("git", path=os.defpath)
        if git is None:
            raise LaneFailure("git_unavailable")

        def source_check(name):
            code, output = owner.run((git, "--no-optional-locks", "-C", str(checkout), "rev-parse", "--show-toplevel", "HEAD"), checkout, name)
            if code != 0:
                raise LaneFailure("source_unavailable")
            try:
                top, head = output.decode().splitlines()
            except (ValueError, UnicodeError):
                raise LaneFailure("source_unavailable") from None
            if Path(top).resolve() != checkout or head != spec.expected_head:
                raise LaneFailure("source_identity_changed")
            data["source"][name] = head
            code, changes = owner.run((git, "--no-optional-locks", "-C", str(checkout), "status", "--porcelain", "--untracked-files=normal"), checkout, name + "_status")
            if code != 0 or changes:
                raise LaneFailure("source_not_clean")

        source_check("source_before")
        code, _ = owner.run((sys.executable, "-m", "venv", "--without-pip", str(root / "venv")), checkout, "setup")
        if code != 0:
            raise LaneFailure("venv_setup_failed")
        environment["PATH"] = str(root / "venv" / "bin") + os.pathsep + os.defpath
        executable = shutil.which(spec.argv[0], path=environment["PATH"])
        if executable is None:
            raise LaneFailure("command_unavailable")
        if re.fullmatch(r"python(?:[0-9]+(?:\.[0-9]+)?)?", Path(executable).name) and Path(executable).absolute().parent != root / "venv" / "bin":
            raise LaneFailure("external_python_interpreter")
        argv = (executable, *spec.argv[1:])
        data["command"] = list(argv)
        data["resolved_executable"] = executable
        data["returncode"], _ = owner.run(argv, checkout, "execution")
        source_check("source_after")
        data["outcome"] = "passed" if data["returncode"] == 0 else "command_failed"
        data["reason"] = "exited"
    except LaneFailure as error:
        data["outcome"] = error.outcome
        data["reason"] = error.reason
    except (OSError, ValueError, TypeError):
        data["reason"] = "boundary_unavailable"
    finally:
        for signum, handler in prior_handlers.items():
            signal.signal(signum, handler)
    if owner:
        execution = next((command for command in owner.commands if command["phase"] == "execution"), None)
        if execution:
            data["returncode"] = execution["returncode"]
        data["cleanup"] = "incomplete" if any(command["cleanup"] == "incomplete" for command in owner.commands) else "complete" if owner.commands else "not_started"
        data["setup_seconds"] = sum(command["execution_seconds"] for command in owner.commands if command["phase"] != "execution")
        data["execution_seconds"] = execution["execution_seconds"] if execution else 0
        data["hooks"], data["rejected_hooks"] = _hooks(root / "hooks.jsonl", secrets, data["execution_seconds"])
    data["total_seconds"] = time.monotonic() - started
    receipt_path = None
    if root:
        try:
            content = json.dumps(_safe_receipt(data, secrets), indent=2, allow_nan=False) + "\n"
            staging = root / "receipt.pending"
            staging.write_text(content)
            receipt_path = root / "receipt.json"
            staging.replace(receipt_path)
            if export is not None:
                with export.open("x") as target:
                    target.write(content)
        except (OSError, ValueError):
            data["outcome"] = "environment_failed"
            data["reason"] = "receipt_write_failed"
            if receipt_path:
                try:
                    receipt_path.write_text(json.dumps(_safe_receipt(data, secrets), indent=2, allow_nan=False) + "\n")
                except (OSError, ValueError):
                    receipt_path = None
    return LaneResult(receipt_path, data["outcome"], data["returncode"], data["cleanup"], data["reason"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--temp-root", type=Path, required=True)
    parser.add_argument("--deadline", type=float, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--env", type=Path, help="JSON environment mapping. Values are excluded from receipts.")
    parser.add_argument("--secret-env", action="append", default=[], metavar="KEY")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        public_env = json.loads(args.env.read_text()) if args.env else {}
        if not isinstance(public_env, dict):
            raise ValueError
        secret_env = {key: os.environ[key] for key in args.secret_env}
    except (OSError, ValueError, KeyError):
        print(json.dumps({"outcome": "environment_failed", "cleanup": "not_started", "reason": "environment_input_unavailable"}))
        return 2
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    result = run_lane(LaneSpec(args.checkout, args.head, args.temp_root, tuple(command), args.deadline, public_env, secret_env, args.receipt))
    print(json.dumps({"outcome": result.outcome, "cleanup": result.cleanup, "returncode": result.returncode, "reason": result.reason, "receipt": str(result.receipt_path) if result.receipt_path else None}))
    return 0 if result.outcome == "passed" and result.cleanup == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
