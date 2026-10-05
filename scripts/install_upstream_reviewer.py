#!/usr/bin/env python3
"""Stage a portable reviewer bundle and systemd user units without enabling them."""

import argparse
import os
from pathlib import Path
import shutil
import sys

from monitor_upstream import MonitorError


SCRIPTS = Path(__file__).resolve().parent
BUNDLE = ("review_upstream.py", "monitor_upstream.py", "check.py")
UNIT = "agent-harness-upstream-review"


def quote(value, *, expand_dollar=False):
    value = str(value)
    if any(ord(c) < 32 for c in value):
        raise ValueError("Unit arguments cannot contain control characters")
    value = value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    if expand_dollar:
        value = value.replace("$", "$$")
    return '"' + value + '"'


def render_units(runtime, state, codex, python, gh, *, repository, model=None, effort="high", path=None):
    for value in (runtime, state, codex, python, gh):
        if not Path(value).is_absolute():
            raise ValueError("Runtime, state and executable paths must be absolute")
    import monitor_upstream as monitor
    monitor.GitHub(repository)
    if effort not in ("low", "medium", "high", "xhigh"):
        raise ValueError("Unsupported reasoning effort")
    args = [python, Path(runtime) / "review_upstream.py", "--issue-repo", repository, "--state-dir", state,
            "--codex", codex, "--effort", effort]
    if model:
        args.extend(["--model", model])
    search_path = path or os.environ.get("PATH", os.defpath)
    search_path = ":".join(dict.fromkeys([str(Path(exe).parent) for exe in (codex, gh, python)] + search_path.split(":")))
    service = "\n".join(["[Unit]", "Description=Analyze queued external skill changes with Codex", "",
        "[Service]", "Type=oneshot",
        "Environment=" + quote("PATH=" + search_path), "Environment=" + quote("TMPDIR=" + str(Path(state) / "scratch")),
        "ExecStart=" + " ".join(quote(a, expand_dollar=True) for a in args), "TimeoutStartSec=20min",
        "KillMode=control-group", "UMask=0077", ""])
    timer = "\n".join(["[Unit]", "Description=Check the external skill review queue every fifteen minutes", "",
        "[Timer]", "OnBootSec=2min", "OnCalendar=*:0/15", "Persistent=true", "RandomizedDelaySec=30s",
        "Unit=" + UNIT + ".service", "", "[Install]", "WantedBy=timers.target", ""])
    return service, timer


def stage(runtime, state, units, codex, python, gh, *, repository, model=None, effort="high", source=SCRIPTS):
    service, timer = render_units(runtime, state, codex, python, gh, repository=repository, model=model, effort=effort)
    runtime, state, units = map(Path, (runtime, state, units))
    if not units.is_absolute():
        raise ValueError("Unit directory must be absolute")
    for executable in (codex, python, gh):
        if not Path(executable).is_file() or not os.access(executable, os.X_OK):
            raise ValueError(f"Executable is unavailable: {executable}")
    runtime.mkdir(parents=True, exist_ok=True)
    (state / "scratch").mkdir(parents=True, exist_ok=True)
    units.mkdir(parents=True, exist_ok=True)
    for filename in BUNDLE:
        target = runtime / filename
        if (source / filename).resolve() != target.resolve():
            shutil.copyfile(source / filename, target)
    (units / (UNIT + ".service")).write_text(service)
    (units / (UNIT + ".timer")).write_text(timer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime-dir", "state-dir", "unit-dir", "codex", "gh"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--issue-repo", required=True)
    parser.add_argument("--model")
    parser.add_argument("--effort", choices=("low", "medium", "high", "xhigh"), default="high")
    args = parser.parse_args()
    try:
        stage(args.runtime_dir, args.state_dir, args.unit_dir, args.codex, args.python, args.gh,
              repository=args.issue_repo, model=args.model, effort=args.effort)
        print(f"Reviewer staged at {args.runtime_dir}. Units are not enabled. Run a one-shot review before enabling the timer.")
        return 0
    except (MonitorError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
