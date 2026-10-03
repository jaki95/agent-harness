"""Exercise validation against temporary repositories, without installing skills."""

from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "check.py"


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skills = self.root / "skills"
        self.skills.mkdir()

    def run_check(self):
        return subprocess.run(
            [sys.executable, str(CHECKER), "--skills-dir", str(self.skills)],
            cwd=self.root, capture_output=True, text=True, check=False,
        )

    def add_skill(self, origin="original", upstream=None):
        skill = self.skills / "example-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            '---\nname: example-skill\ndescription: "Use for an example task."\n---\n'
            "# Example\nPerform the task and verify the result.\n", encoding="utf-8",
        )
        (skill / "evaluations.md").write_text("# Cases\nConcrete manual cases.\n", encoding="utf-8")
        (skill / "provenance.json").write_text(json.dumps({
            "origin": origin,
            "upstream": [] if upstream is None else upstream,
            "adaptation_summary": "Customized the workflow for portable use.",
            "reviewed_on": date.today().isoformat(),
        }), encoding="utf-8")
        return skill

    def test_empty_scaffold_passes(self):
        (self.skills / ".gitkeep").touch()
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_original_skill_passes_from_another_directory(self):
        self.add_skill()
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_adaptation_with_retained_license_passes(self):
        skill = self.add_skill("adapted", [{
            "url": "https://example.com/skill", "revision": "v1.0.0",
            "license": "MIT", "license_file": "LICENSE.upstream",
        }])
        (skill / "LICENSE.upstream").write_text("Example retained notice.\n", encoding="utf-8")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_adaptation_without_source_fails(self):
        self.add_skill("adapted")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least one upstream source", result.stderr)

    def test_license_cannot_escape_skill_directory(self):
        (self.skills / "outside-license").write_text("Notice.\n", encoding="utf-8")
        self.add_skill("adapted", [{
            "url": "https://example.com/skill", "revision": "v1.0.0",
            "license": "MIT", "license_file": "../outside-license",
        }])
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must stay inside", result.stderr)

    def test_missing_evaluations_and_mismatched_name_fail(self):
        skill = self.add_skill()
        (skill / "evaluations.md").unlink()
        path = skill / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "name: example-skill", "name: other-skill"), encoding="utf-8")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read evaluations.md", result.stderr)
        self.assertIn("name must match", result.stderr)

    def test_malformed_provenance_fails_without_traceback(self):
        skill = self.add_skill()
        (skill / "provenance.json").write_text("[]", encoding="utf-8")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must contain an object", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
