"""Verify release preflight rejects empty or invalid harnesses without mutations."""

from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECK = Path(__file__).resolve().parents[1] / "check_release.py"


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ("skills", "registry"):
            (self.root / folder).mkdir()
        self.write_index({})

    def write_index(self, skills):
        (self.root / "registry/skills.json").write_text(json.dumps({
            "schema_version": 1, "skills": skills,
        }), encoding="utf-8")

    def run_check(self, version="v0.1.0", *args):
        return subprocess.run([sys.executable, str(CHECK), version, "--root", str(self.root), *args],
                              capture_output=True, text=True, check=False)

    def test_empty_harness_cannot_be_released(self):
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least one owned skill", result.stderr)

    def test_invalid_versions_cannot_reach_release(self):
        for version in ("main", "v01.2.3", "v1.2", "v1.2.3;echo unsafe"):
            with self.subTest(version=version):
                result = self.run_check(version)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("vMAJOR.MINOR.PATCH", result.stderr)

    def write_skill(self):
        skill = self.root / "skills/example"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            '---\nname: example\ndescription: "A fixture skill."\n---\nDo the fixture task.\n',
            encoding="utf-8")
        self.write_index({"example": {
            "maintenance_notes": "Independent fixture.",
            "reviewed_on": date.today().isoformat(), "sources": [],
        }})

    def test_exports_only_the_matching_release_notes(self):
        self.write_skill()
        notes = "### Fixed\n\n- Keep the exact commit.\n\n```md\n## Example heading\n```\n"
        (self.root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## Unreleased\n\n- Pending.\n\n## v0.1.0 - 2026-01-01\n\n"
            + notes + "\n## v0.0.1 - 2025-12-31\n\n- Old.\n", encoding="utf-8")
        output = self.root / "notes.md"
        result = self.run_check("v0.1.0", "--notes-file", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("v0.1.0 is ready", result.stdout)
        self.assertEqual(output.read_text(encoding="utf-8"), notes)
        self.assertFalse((self.root / ".git").exists())

    def test_missing_changelog_blocks_release(self):
        self.write_skill()
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CHANGELOG.md", result.stderr)

    def test_unprepared_or_ambiguous_notes_block_release(self):
        self.write_skill()
        for content in ("## Unreleased\n\n- Pending.\n", "## v0.1.0\n\n- Undated.\n",
                        "## v0.1.0 - 2026-02-30\n\n- Invalid date.\n",
                        "## v0.1.0 - 2026-01-01\n\n## Older\n\n- Not this version.\n",
                        "```md\n## v0.1.0 - 2026-01-01\n\n- Example.\n```\n",
                        "## v0.1.0 - 2026-01-01\n\nFirst.\n## v0.1.0 - 2026-01-02\n\nSecond.\n"):
            with self.subTest(content=content):
                (self.root / "CHANGELOG.md").write_text(content, encoding="utf-8")
                result = self.run_check()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("CHANGELOG.md", result.stderr)

    def test_invalid_harness_cannot_be_released(self):
        self.write_index({"missing": {}})
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no runtime skill", result.stderr)


if __name__ == "__main__":
    unittest.main()
