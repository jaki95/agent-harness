#!/usr/bin/env python3
"""Check a proposed release without creating tags or publishing anything."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def release_notes(changelog, version):
    lines = changelog.read_text(encoding="utf-8").splitlines(keepends=True)
    start = end = None
    fence = ""
    for i, line in enumerate(lines):
        marker = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1].startswith(fence) and not marker[2].strip():
                fence = ""
            continue
        if marker:
            fence = marker[1]
            continue
        if not line.startswith(("## ", "# ")):
            continue
        if start is not None and end is None:
            end = i
        heading = line.rstrip().split()
        if heading[:2] != ["##", version]:
            continue
        if start is not None:
            raise ValueError(f"duplicate release heading for {version}")
        if len(heading) != 4 or heading[2] != "-" or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", heading[3]):
            raise ValueError(f"expected '## {version} - YYYY-MM-DD'")
        date.fromisoformat(heading[3])
        start = i + 1
    if start is None:
        raise ValueError(f"missing '## {version} - YYYY-MM-DD'")
    body = "".join(lines[start:end]).strip("\n")
    if not body.strip():
        raise ValueError(f"empty notes for {version}")
    return body + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="new tag in vMAJOR.MINOR.PATCH form")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--notes-file", type=Path, help="write the validated release notes to this file")
    args = parser.parse_args()
    if not VERSION.fullmatch(args.version):
        print("FAIL: version must use vMAJOR.MINOR.PATCH, without leading zeroes", file=sys.stderr)
        return 1
    root = args.root.resolve()
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check.py"), "--root", str(root)])
    if result.returncode:
        return result.returncode
    index = json.loads((root / "registry/skills.json").read_text(encoding="utf-8"))
    count = len(index["skills"])
    if not count:
        print("FAIL: add at least one owned skill before releasing", file=sys.stderr)
        return 1
    try:
        notes = release_notes(root / "CHANGELOG.md", args.version)
    except (OSError, ValueError) as exc:
        print(f"FAIL: CHANGELOG.md: {exc}", file=sys.stderr)
        return 1
    if args.notes_file:
        try:
            args.notes_file.write_text(notes, encoding="utf-8")
        except OSError as exc:
            print(f"FAIL: cannot write release notes: {exc}", file=sys.stderr)
            return 1
    print(f"OK: {args.version} is ready for release with {count} skill(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
