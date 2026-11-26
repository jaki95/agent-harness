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


def changelog_sections(changelog):
    lines = changelog.read_text(encoding="utf-8").splitlines(keepends=True)
    heading = []
    start = 0
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
        if heading:
            yield heading, "".join(lines[start:i]).strip("\n")
        heading = line.split()
        start = i + 1
    if heading:
        yield heading, "".join(lines[start:]).strip("\n")


def releases(changelog, *, only=None, allow_incomplete_baseline=False):
    result = {}
    for heading, body in changelog_sections(changelog):
        if len(heading) < 2 or heading[0] != "##":
            continue
        version = heading[1]
        if only is not None and version != only:
            continue
        if not re.match(r"\[?(?:[vV][0-9]|[0-9]+\.)", version):
            continue
        try:
            if not VERSION.fullmatch(version):
                raise ValueError(f"invalid release version {version!r}: expected vMAJOR.MINOR.PATCH")
            if len(heading) != 4 or heading[2] != "-" or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", heading[3]):
                raise ValueError(f"expected '## {version} - YYYY-MM-DD'")
            date.fromisoformat(heading[3])
            if not body.strip():
                raise ValueError(f"empty notes for {version}")
        except ValueError:
            if allow_incomplete_baseline:
                continue
            raise
        if version in result and not allow_incomplete_baseline:
            raise ValueError(f"duplicate release heading for {version}")
        result[version] = body + "\n"
    return result


def release_notes(changelog, version):
    notes = releases(changelog, only=version)
    if version not in notes:
        raise ValueError(f"missing '## {version} - YYYY-MM-DD'")
    return notes[version]


def new_release(previous, current):
    old = releases(previous, allow_incomplete_baseline=True)
    new = releases(current).keys() - old.keys()
    if not new:
        return None
    if len(new) > 1:
        raise ValueError(f"only one new version can be released per push: {', '.join(sorted(new))}")
    version = new.pop()
    numbers = tuple(map(int, version[1:].split(".")))
    if any(numbers <= tuple(map(int, tag[1:].split("."))) for tag in old):
        raise ValueError(f"{version} must be newer than the existing releases")
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="new tag in vMAJOR.MINOR.PATCH form")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--notes-file", type=Path, help="write the validated release notes to this file")
    parser.add_argument("--new-since", type=Path, metavar="CHANGELOG",
                        help="print the version newly prepared since the previous changelog, if any")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.new_since is not None:
        if args.version is not None or args.notes_file is not None:
            parser.error("--new-since cannot be combined with a version or --notes-file")
        try:
            version = new_release(args.new_since, root / "CHANGELOG.md")
        except (OSError, ValueError) as exc:
            print(f"FAIL: CHANGELOG.md: {exc}", file=sys.stderr)
            return 1
        if version:
            print(version)
        return 0
    if args.version is None:
        parser.error("provide a version or --new-since CHANGELOG")
    if not VERSION.fullmatch(args.version):
        print("FAIL: version must use vMAJOR.MINOR.PATCH, without leading zeroes", file=sys.stderr)
        return 1
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
