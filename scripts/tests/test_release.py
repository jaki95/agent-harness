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

    def run_check(self, version="v0.1.0"):
        return subprocess.run([sys.executable, str(CHECK), version, "--root", str(self.root)],
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

    def test_valid_owned_skill_can_be_released(self):
        skill = self.root / "skills/example"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            '---\nname: example\ndescription: "A fixture skill."\n---\nDo the fixture task.\n',
            encoding="utf-8")
        self.write_index({"example": {
            "maintenance_notes": "Independent fixture.",
            "reviewed_on": date.today().isoformat(), "sources": [],
        }})
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("v0.1.0 is ready", result.stdout)
        self.assertFalse((self.root / ".git").exists())

    def test_invalid_harness_cannot_be_released(self):
        self.write_index({"missing": {}})
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no runtime skill", result.stderr)


if __name__ == "__main__":
    unittest.main()
