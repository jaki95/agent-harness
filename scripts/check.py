#!/usr/bin/env python3
"""Validate runtime skills and the separate maintenance index; no network access."""

import argparse
from datetime import date
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
COMMIT = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
HEADER = re.compile(r'\A---\nname: ([^\n]+)\ndescription: ([^\n]+)\n((?:[a-z][a-z-]*: [^\n]+\n)*)---\n')
BOOLEAN_FIELDS = {"disable-model-invocation", "mode"}
STRING_FIELDS = {"icon", "color", "reminder"}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def relative_path(value):
    return (nonempty(value) and not value.startswith("/") and "\\" not in value
            and not re.match(r"[A-Za-z]:", value)
            and ".." not in PurePosixPath(value).parts)


def check_text(path):
    try:
        text = path.read_text(encoding="utf-8")
        return text, [] if text.strip() else [f"{path.name} must not be empty"]
    except (OSError, UnicodeError) as exc:
        return "", [f"cannot read {path.name}: {exc}"]


def check_skill(skill):
    text, errors = check_text(skill / "SKILL.md")
    header = HEADER.match(text)
    if not header:
        errors.append("SKILL.md must use the frontmatter format in templates/skill")
    else:
        if header[1] != skill.name:
            errors.append("frontmatter name must match the skill directory")
        description = header[2]
        if description.startswith('"'):
            try:
                if not nonempty(json.loads(description)):
                    errors.append("description must be nonempty")
            except json.JSONDecodeError:
                errors.append("description must be a valid JSON-quoted string")
        elif (not description[0].isalpha()
              or description.strip().lower() in ("true", "false", "null", "yes", "no", "on", "off")
              or re.search(r":(?:\s|$)|(?:^|\s)#", description)):
            errors.append("description must be plain text or a JSON-quoted string")
        seen = set()
        for line in header[3].splitlines():
            key, value = line.split(": ", 1)
            if key in seen:
                errors.append(f"duplicate frontmatter field: {key}")
            seen.add(key)
            if key in BOOLEAN_FIELDS:
                if value not in ("true", "false"):
                    errors.append(f"{key} must be true or false")
            elif key in STRING_FIELDS:
                try:
                    if not nonempty(json.loads(value)):
                        raise ValueError
                except (ValueError, TypeError):
                    errors.append(f"{key} must be a nonempty JSON-quoted string")
            else:
                errors.append(f"unsupported frontmatter field: {key}")
        if not text[header.end():].strip():
            errors.append("SKILL.md must contain instructions after the frontmatter")
    for reserved in ("provenance.json", "evaluations.md", "registry", "reviews"):
        if (skill / reserved).exists():
            errors.append(f"{reserved} belongs outside the runtime skill directory")
    return errors


def check_source(source):
    if not isinstance(source, dict):
        return ["source must be an object"]
    errors = []
    if not nonempty(source.get("id")) or not NAME.fullmatch(source["id"]):
        errors.append("id must be lowercase kebab-case")
    relationship = source.get("relationship")
    if relationship not in ("adapted", "inspired"):
        errors.append("relationship must be adapted or inspired")
    try:
        url = urlparse(source.get("repository") or "")
        valid_url = url.scheme in ("http", "https") and bool(url.netloc)
    except (ValueError, AttributeError, TypeError):
        valid_url = False
    if not valid_url:
        errors.append("repository must be an HTTP(S) URL")
    if not nonempty(source.get("ref")):
        errors.append("ref must be nonempty")
    paths = source.get("paths")
    if not isinstance(paths, list) or not paths or not all(relative_path(p) for p in paths):
        errors.append("paths must be a nonempty list of repository-relative paths")
    for field in ("baseline_revision", "last_reviewed_revision", "last_incorporated_revision"):
        revision = source.get(field)
        if field == "last_incorporated_revision" and relationship == "inspired" and revision is None:
            continue
        if not nonempty(revision) or not COMMIT.fullmatch(revision):
            errors.append(f"{field} must be a full Git commit ID")
    return errors


def check_record(record):
    if not isinstance(record, dict):
        return ["registry entry must contain an object"]
    errors = []
    if not nonempty(record.get("maintenance_notes")):
        errors.append("maintenance_notes must be nonempty")
    reviewed = record.get("reviewed_on")
    try:
        if not isinstance(reviewed, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed):
            raise ValueError
        if date.fromisoformat(reviewed) > date.today():
            errors.append("reviewed_on must not be in the future")
    except ValueError:
        errors.append("reviewed_on must be a valid YYYY-MM-DD date")
    sources = record.get("sources")
    if not isinstance(sources, list):
        return errors + ["sources must be a list"]
    ids = set()
    for index, source in enumerate(sources, 1):
        errors.extend(f"source {index}: {error}" for error in check_source(source))
        if isinstance(source, dict) and nonempty(source.get("id")):
            if source["id"] in ids:
                errors.append(f"source {index}: duplicate source id {source['id']}")
            ids.add(source["id"])
    return errors


def load_index(root):
    text, errors = check_text(root / "registry" / "skills.json")
    if errors:
        return {}, errors
    try:
        index = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, [f"invalid registry JSON: {exc}"]
    if not isinstance(index, dict):
        return {}, ["registry must contain an object"]
    if type(index.get("schema_version")) is not int or index["schema_version"] != 1:
        errors.append("registry schema_version must be 1")
    skills = index.get("skills")
    if not isinstance(skills, dict):
        return {}, errors + ["registry skills must contain an object"]
    return skills, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="harness repository root")
    root = parser.parse_args().root.resolve()
    index, failures = load_index(root)
    skills = root / "skills"
    names = set()
    if not skills.is_dir():
        failures.append("skills directory does not exist")
    else:
        for entry in sorted(skills.iterdir()):
            if entry.name == ".gitkeep":
                continue
            if entry.is_symlink() or not entry.is_dir() or not NAME.fullmatch(entry.name):
                failures.append(f"{entry.name}: expected a lowercase kebab-case skill directory")
                continue
            names.add(entry.name)
            failures.extend(f"{entry.name}: {error}" for error in check_skill(entry))
            if entry.name not in index:
                failures.append(f"{entry.name}: missing registry entry")
            _, errors = check_text(root / "evaluations" / f"{entry.name}.md")
            failures.extend(f"{entry.name}: {error}" for error in errors)
    for name, record in index.items():
        if not NAME.fullmatch(name):
            failures.append(f"registry key {name!r} must be lowercase kebab-case")
        if name not in names:
            failures.append(f"{name}: registry entry has no runtime skill")
        failures.extend(f"{name}: {error}" for error in check_record(record))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"OK: {len(names)} skill(s) and maintenance index validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
