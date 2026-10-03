#!/usr/bin/env python3
"""Validate owned skill structure and provenance using only the standard library."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HEADER = re.compile(r'\A---\nname: ([^\n]+)\ndescription: ("[^\n]*")\n---\n')


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def check_skill(skill):
    errors = []
    if not NAME.fullmatch(skill.name):
        errors.append("directory name must be lowercase kebab-case")
    contents = {}
    for filename in ("SKILL.md", "provenance.json", "evaluations.md"):
        try:
            contents[filename] = (skill / filename).read_text(encoding="utf-8")
            if not contents[filename].strip():
                errors.append(f"{filename} must not be empty")
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {filename}: {exc}")

    if "SKILL.md" in contents:
        header = HEADER.match(contents["SKILL.md"])
        if not header:
            errors.append("SKILL.md must use the frontmatter format in templates/skill")
        else:
            if header[1] != skill.name:
                errors.append("frontmatter name must match the skill directory")
            try:
                if not nonempty(json.loads(header[2])):
                    errors.append("description must be nonempty")
            except json.JSONDecodeError:
                errors.append("description must be a JSON-quoted string")
            if not contents["SKILL.md"][header.end():].strip():
                errors.append("SKILL.md must contain instructions after the frontmatter")

    if "provenance.json" in contents:
        try:
            provenance = json.loads(contents["provenance.json"])
        except json.JSONDecodeError as exc:
            errors.append(f"invalid provenance.json: {exc}")
        else:
            errors.extend(check_provenance(provenance, skill))
    return errors


def check_provenance(record, skill):
    if not isinstance(record, dict):
        return ["provenance.json must contain an object"]
    errors = []
    origin = record.get("origin")
    if origin not in ("original", "adapted"):
        errors.append("origin must be original or adapted")
    if not nonempty(record.get("adaptation_summary")):
        errors.append("adaptation_summary must be nonempty")
    reviewed = record.get("reviewed_on")
    try:
        if not isinstance(reviewed, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed):
            raise ValueError
        if date.fromisoformat(reviewed) > date.today():
            errors.append("reviewed_on must not be in the future")
    except ValueError:
        errors.append("reviewed_on must be a valid YYYY-MM-DD date")
    upstream = record.get("upstream")
    if not isinstance(upstream, list):
        return errors + ["upstream must be a list"]
    if origin == "adapted" and not upstream:
        errors.append("adapted skills must record at least one upstream source")
    if origin == "original" and upstream:
        errors.append("skills with upstream sources must use origin adapted")
    for index, source in enumerate(upstream, 1):
        prefix = f"upstream source {index}"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("url", "revision", "license", "license_file"):
            if not nonempty(source.get(field)):
                errors.append(f"{prefix}: {field} must be nonempty")
        if nonempty(source.get("url")):
            try:
                url = urlparse(source["url"])
                valid_url = url.scheme in ("https", "http") and bool(url.netloc)
            except ValueError:
                valid_url = False
            if not valid_url:
                errors.append(f"{prefix}: url must be an HTTP(S) URL")
        if nonempty(source.get("license_file")):
            notice = Path(source["license_file"])
            resolved = (skill / notice).resolve()
            if notice.is_absolute() or not resolved.is_relative_to(skill.resolve()):
                errors.append(f"{prefix}: license_file must stay inside the skill directory")
            elif not resolved.is_file() or resolved.stat().st_size == 0:
                errors.append(f"{prefix}: license_file must point to a nonempty file")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, default=ROOT / "skills")
    args = parser.parse_args()
    if not args.skills_dir.is_dir():
        print(f"FAIL: skills directory does not exist: {args.skills_dir}", file=sys.stderr)
        return 1
    count = 0
    failures = []
    for entry in sorted(args.skills_dir.iterdir()):
        if entry.name == ".gitkeep":
            continue
        if entry.is_symlink() or not entry.is_dir():
            failures.append(f"{entry.name}: expected a skill directory, not a file or symlink")
            continue
        count += 1
        failures.extend(f"{entry.name}: {error}" for error in check_skill(entry))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"OK: {count} skill(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
