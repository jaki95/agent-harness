"""Verify cleanup advice using actual disposable Git worktrees; never delete user trees."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "skills/harness/scripts/worktree-audit.py"
audit = types.ModuleType("harness_worktree_audit")
exec(compile(SCRIPT.read_text(), str(SCRIPT), "exec"), audit.__dict__)


class WorktreeAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repository with spaces "
        self.repo.mkdir()
        self.git(self.repo, "init", "-b", "main")
        self.git(self.repo, "config", "user.name", "Audit fixture")
        self.git(self.repo, "config", "user.email", "fixture@example.invalid")
        (self.repo / "tracked.txt").write_text("baseline\n")
        (self.repo / ".gitignore").write_text("ignored-cache/\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "Baseline")
        self.worktree = self.root / "candidate tree with spaces"
        self.git(self.repo, "worktree", "add", "-b", "candidate", str(self.worktree))
        self.usage = self.root / "usage.json"

    def git(self, repo, *args):
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def receipt(self, **changes):
        row = {"path": str(self.worktree), "head": self.git(self.worktree, "rev-parse", "HEAD"),
               "owned": True, "active": False, "pinned": False, "abandoned": False,
               "evidence": "Current host inventory includes this owner and all delegated worktrees."}
        row.update(changes)
        self.usage.write_text(json.dumps({"repository": str(self.repo), "complete": True, "worktrees": [row]}))

    def row(self, use_receipt=True, github=False, sizes=False):
        result = audit.audit(self.repo, "main", self.usage if use_receipt else None, github, sizes)
        return next(row for row in result["worktrees"] if row["path"] == str(self.worktree))

    def test_clean_merged_owned_inactive_worktree_is_only_a_candidate(self):
        self.receipt()
        row = self.row(sizes=True)
        self.assertEqual(row["bucket"], "eligible-for-confirmation")
        self.assertTrue(row["merged"])
        self.assertIsInstance(row["size_bytes"], int)
        self.assertEqual(row["path"], str(self.worktree))
        self.assertTrue(self.worktree.exists())
        self.assertTrue(self.repo.exists())

    def test_unknown_stale_incomplete_or_unowned_usage_is_held(self):
        self.assertIn("unknown-or-stale-usage", self.row(use_receipt=False)["reasons"])
        self.receipt(head="0" * 40)
        self.assertIn("unknown-or-stale-usage", self.row()["reasons"])
        self.receipt(owned=False)
        self.assertIn("ownership-not-confirmed", self.row()["reasons"])
        value = json.loads(self.usage.read_text())
        value["complete"] = False
        self.usage.write_text(json.dumps(value))
        self.assertIn("unknown-or-stale-usage", self.row()["reasons"])

    def test_pinned_and_active_receipts_override_merge_evidence(self):
        for field in ("pinned", "active"):
            with self.subTest(field=field):
                self.receipt(**{field: True})
                self.assertIn("in-use-or-pinned", self.row()["reasons"])

    def test_tracked_untracked_and_ignored_files_are_preserved(self):
        self.receipt()
        (self.worktree / "tracked.txt").write_text("work in progress\n")
        (self.worktree / "untracked notes.txt").write_text("keep these notes\n")
        (self.worktree / "ignored-cache").mkdir()
        (self.worktree / "ignored-cache/data.txt").write_text("not known to be disposable\n")
        row = self.row()
        self.assertEqual(row["tracked"][0]["path"], "tracked.txt")
        self.assertEqual(row["untracked"], ["untracked notes.txt"])
        self.assertEqual(row["ignored"], ["ignored-cache/"])
        self.assertEqual(row["bucket"], "hold")
        self.assertTrue((self.worktree / "ignored-cache/data.txt").exists())

    def test_closed_pr_does_not_prove_merge(self):
        (self.worktree / "new.txt").write_text("unmerged work\n")
        self.git(self.worktree, "add", "new.txt")
        self.git(self.worktree, "commit", "-m", "Unmerged change")
        self.receipt()
        head = self.git(self.worktree, "rev-parse", "HEAD")
        with patch.object(audit, "github_prs", return_value=[{"number": 10, "state": "CLOSED", "headRefOid": head}]):
            row = self.row(github=True)
        self.assertFalse(row["merged"])
        self.assertIn("merge-or-abandonment-not-confirmed", row["reasons"])

    def test_squash_merge_evidence_requires_the_exact_current_head(self):
        (self.worktree / "new.txt").write_text("squashed change\n")
        self.git(self.worktree, "add", "new.txt")
        self.git(self.worktree, "commit", "-m", "Change")
        self.receipt()
        head = self.git(self.worktree, "rev-parse", "HEAD")
        with patch.object(audit, "github_prs", return_value=[{"number": 10, "state": "MERGED", "headRefOid": head}]):
            self.assertEqual(self.row(github=True)["bucket"], "eligible-for-confirmation")
        with patch.object(audit, "github_prs", return_value=[{"number": 10, "state": "MERGED", "headRefOid": "0" * 40}]):
            self.assertFalse(self.row(github=True)["merged"])

    def test_open_pr_and_failed_pr_lookup_hold_the_candidate(self):
        self.receipt()
        with patch.object(audit, "github_prs", return_value=[{"number": 10, "state": "OPEN"}]):
            self.assertIn("open-pr", self.row(github=True)["reasons"])
        with patch.object(audit, "github_prs", side_effect=audit.AuditError("access denied")):
            self.assertIn("incomplete-metadata", self.row(github=True)["reasons"])

    def test_abandonment_is_explicit_and_primary_or_locked_trees_are_held(self):
        (self.worktree / "new.txt").write_text("abandoned work\n")
        self.git(self.worktree, "add", "new.txt")
        self.git(self.worktree, "commit", "-m", "Abandoned change")
        self.receipt(abandoned=True)
        self.assertEqual(self.row()["bucket"], "eligible-for-confirmation")
        self.git(self.repo, "worktree", "lock", str(self.worktree))
        self.assertIn("locked-worktree", self.row()["reasons"])
        rows = audit.audit(self.repo, "main", self.usage)["worktrees"]
        self.assertIn("primary-worktree", next(row for row in rows if row["path"] == str(self.repo))["reasons"])

    def test_rename_and_newline_filenames_survive_status_parsing(self):
        self.receipt()
        self.git(self.worktree, "mv", "tracked.txt", "renamed file.txt")
        (self.worktree / "notes\nwith newline.txt").write_text("keep\n")
        row = self.row()
        self.assertEqual(row["tracked"][0]["path"], "renamed file.txt")
        self.assertEqual(row["tracked"][0]["original_path"], "tracked.txt")
        self.assertEqual(row["untracked"], ["notes\nwith newline.txt"])

    def test_wrong_repository_receipt_is_rejected(self):
        self.receipt()
        value = json.loads(self.usage.read_text())
        value["repository"] = str(self.root)
        self.usage.write_text(json.dumps(value))
        with self.assertRaisesRegex(audit.AuditError, "this repository"):
            self.row()

    def test_invocation_worktree_is_held_even_with_inactive_receipt(self):
        self.receipt()
        value = json.loads(self.usage.read_text())
        value["repository"] = str(self.worktree)
        self.usage.write_text(json.dumps(value))
        rows = audit.audit(self.worktree, "main", self.usage)["worktrees"]
        row = next(row for row in rows if row["path"] == str(self.worktree))
        self.assertIn("invocation-worktree", row["reasons"])

    def test_cli_audit_does_not_change_git_metadata_or_files(self):
        before = {path: path.read_bytes() for path in (self.worktree / ".git", self.repo / ".git/config",
                                                     self.repo / ".git/index", self.worktree / "tracked.txt")}
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo), "--base", "main"],
                                cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["worktrees"]), 2)
        for path, contents in before.items():
            self.assertEqual(path.read_bytes(), contents)


if __name__ == "__main__":
    unittest.main()
