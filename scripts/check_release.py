#!/usr/bin/env python3
"""Check a proposed release without creating tags or publishing anything."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="new tag in vMAJOR.MINOR.PATCH form")
    parser.add_argument("--root", type=Path, default=ROOT)
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
    print(f"OK: {args.version} is ready for release with {count} skill(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
