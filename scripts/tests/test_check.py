"""Exercise runtime/maintenance boundaries using temporary harness repositories."""

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
        for directory in ("skills", "registry", "evaluations", "reviews"):
            (self.root / directory).mkdir()
        self.index = {"schema_version": 1, "skills": {}}
        self.write_index()

    def write_index(self):
        (self.root / "registry/skills.json").write_text(json.dumps(self.index), encoding="utf-8")

    def run_check(self):
        return subprocess.run(
            [sys.executable, str(CHECKER), "--root", str(self.root)],
            cwd=self.root / "reviews", capture_output=True, text=True, check=False,
        )

    def assert_passes(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_fails(self, expected):
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def add_skill(self, sources=None):
        skill = self.root / "skills/example-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            '---\nname: example-skill\ndescription: "Use for an example task."\n---\n'
            "# Example\nPerform the task and verify the result.\n", encoding="utf-8",
        )
        (self.root / "evaluations/example-skill.md").write_text(
            "# Cases\nConcrete manual cases.\n", encoding="utf-8",
        )
        self.index["skills"]["example-skill"] = {
            "maintenance_notes": "Customized for portable use.",
            "reviewed_on": date.today().isoformat(),
            "sources": [] if sources is None else sources,
        }
        self.write_index()
        return skill

    def source(self, relationship="adapted"):
        return {
            "id": "example-source", "relationship": relationship,
            "repository": "https://example.com/skills.git", "ref": "main",
            "paths": ["skills/example/"],
            "baseline_revision": "a" * 40,
            "last_reviewed_revision": "b" * 40,
            "last_incorporated_revision": "a" * 40 if relationship == "adapted" else None,
        }

    def test_empty_scaffold_passes(self):
        (self.root / "skills/.gitkeep").touch()
        self.assert_passes()

    def test_original_skill_with_external_metadata_passes_from_another_directory(self):
        self.add_skill()
        self.assert_passes()

    def test_adaptation_with_separate_reviewed_and_incorporated_revisions_passes(self):
        self.add_skill([self.source()])
        self.assert_passes()

    def test_inspiration_without_copied_material_passes(self):
        self.add_skill([self.source("inspired")])
        self.assert_passes()

    def test_multiple_sources_pass(self):
        adapted = self.source()
        inspired = self.source("inspired")
        inspired["id"] = "another-source"
        self.add_skill([adapted, inspired])
        self.assert_passes()

    def test_duplicate_source_ids_fail(self):
        self.add_skill([self.source(), self.source("inspired")])
        self.assert_fails("duplicate source id")

    def test_runtime_skill_without_registry_entry_fails(self):
        self.add_skill()
        self.index["skills"].clear()
        self.write_index()
        self.assert_fails("missing registry entry")

    def test_orphan_registry_entry_fails(self):
        self.add_skill().rename(self.root / "reviews/removed-skill")
        self.assert_fails("registry entry has no runtime skill")

    def test_runtime_maintenance_metadata_fails(self):
        skill = self.add_skill()
        for filename in ("provenance.json", "evaluations.md"):
            (skill / filename).write_text("Maintenance data", encoding="utf-8")
        self.assert_fails("belongs outside the runtime skill directory")

    def test_moving_ref_cannot_be_used_as_a_revision(self):
        source = self.source()
        source["last_reviewed_revision"] = "main"
        self.add_skill([source])
        self.assert_fails("last_reviewed_revision must be a full Git commit ID")

    def test_missing_external_evaluations_and_mismatched_name_fail(self):
        skill = self.add_skill()
        (self.root / "evaluations/example-skill.md").unlink()
        path = skill / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "name: example-skill", "name: other-skill"), encoding="utf-8")
        self.assert_fails("cannot read example-skill.md")
        self.assert_fails("name must match")

    def test_malformed_registry_fails_without_traceback(self):
        (self.root / "registry/skills.json").write_text("[]", encoding="utf-8")
        self.assert_fails("registry must contain an object")

    def test_malformed_source_values_fail_without_traceback(self):
        source = self.source()
        source["repository"] = ["invalid"]
        source["paths"] = [1]
        self.add_skill([source])
        self.assert_fails("repository must be an HTTP(S) URL")
        self.assert_fails("paths must be a nonempty list")


if __name__ == "__main__":
    unittest.main()
