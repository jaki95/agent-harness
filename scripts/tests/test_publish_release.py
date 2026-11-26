"""Exercise the publisher with a disposable Git remote and a local release service."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


PUBLISH = Path(__file__).resolve().parents[1] / "publish_release.sh"
TAG = "v0.1.0"
REPO = "fixture/harness"

GH = """#!/usr/bin/env python3
import json, os, subprocess, sys
from pathlib import Path

root = Path(os.environ["RELEASE_FIXTURE"])
record = root / "release"
args = sys.argv[1:]
mode = os.environ.get("GH_FIXTURE_MODE")
with (root / "calls").open("a") as log:
    log.write(json.dumps(args) + "\\n")
if args[:2] == ["api", "--paginate"]:
    assert args[2:4] == ["repos/fixture/harness/releases?per_page=100", "--jq"]
    assert 'select(.tag_name == "v0.1.0")' in args[4]
    if mode == "unavailable":
        sys.exit(1)
    if record.exists():
        print(record.read_text())
elif args[:2] == ["api", "repos/fixture/harness/releases/tags/v0.1.0"]:
    assert args[2:] == ["--jq", "[.draft, .prerelease] | @tsv"]
    if not record.exists():
        sys.exit(1)
    first_read = root / "first_read"
    if mode == "delayed" and not first_read.exists():
        first_read.touch()
        sys.exit(1)
    print(record.read_text())
elif args[:2] == ["release", "create"]:
    assert args[2:] == ["v0.1.0", "--repo", "fixture/harness", "--verify-tag",
                        "--title", "v0.1.0", "--notes-file", str(root / "notes")]
    assert not record.exists()
    if mode == "interrupted":
        sys.exit(1)
    (root / "published_notes").write_bytes(Path(args[-1]).read_bytes())
    record.write_text("false\\tfalse")
    if mode == "retarget":
        subprocess.run(["git", "--git-dir", str(root / "origin"), "update-ref",
                        "refs/tags/v0.1.0", os.environ["EARLIER_SHA"]], check=True)
    if mode == "response-lost":
        sys.exit(1)
else:
    raise AssertionError(args)
"""


class PublishReleaseTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git("init", "--bare", "origin")
        self.git("init", "work")
        self.git("-C", "work", "config", "user.email", "fixture@example.invalid")
        self.git("-C", "work", "config", "user.name", "Fixture")
        self.git("-C", "work", "remote", "add", "origin", str(self.root / "origin"))
        self.git("-C", "work", "commit", "--allow-empty", "-m", "earlier")
        self.earlier = self.git("-C", "work", "rev-parse", "HEAD")
        self.git("-C", "work", "commit", "--allow-empty", "-m", "release")
        self.head = self.git("-C", "work", "rev-parse", "HEAD")
        (self.root / "gh").write_text(GH)
        (self.root / "gh").chmod(0o755)
        self.notes = self.root / "notes"
        self.notes.write_text("### Changes\n\n- Preserve notes with UTF-8: café.\n")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True,
                              text=True).stdout.strip()

    def publish(self, mode="", status=0, sha=None):
        env = {**os.environ, "PATH": str(self.root) + os.pathsep + os.environ["PATH"],
               "GH_REPO": REPO, "GH_FIXTURE_MODE": mode, "RELEASE_FIXTURE": str(self.root),
               "EARLIER_SHA": self.earlier}
        result = subprocess.run(["bash", str(PUBLISH), TAG, sha or self.head, str(self.notes)],
                                cwd=self.root / "work", env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def creates(self):
        return sum(json.loads(line)[:2] == ["release", "create"]
                   for line in (self.root / "calls").read_text().splitlines())

    def test_new_release_targets_checked_head_and_replay_is_quiet(self):
        self.git("-C", "work", "tag", "-a", "other", "-m", "not part of release")
        self.git("-C", "work", "config", "push.followTags", "true")
        self.publish("response-lost")
        self.publish()
        self.assertEqual(self.git("--git-dir=origin", "tag"), TAG)
        self.assertEqual(self.git("--git-dir=origin", "rev-parse", TAG), self.head)
        self.assertEqual(self.creates(), 1)
        self.assertEqual((self.root / "published_notes").read_bytes(), self.notes.read_bytes())

    def test_retry_finishes_release_after_interruption(self):
        self.publish("interrupted", status=1)
        self.assertEqual(self.git("--git-dir=origin", "rev-parse", TAG), self.head)
        self.assertFalse((self.root / "release").exists())
        self.publish()
        self.assertTrue((self.root / "release").exists())

    def test_waits_for_release_to_be_readable_by_tag(self):
        self.publish("delayed")
        self.assertTrue((self.root / "first_read").exists())
        self.assertEqual(self.creates(), 1)
        self.assertEqual(self.git("--git-dir=origin", "rev-parse", TAG), self.head)

    def test_existing_annotated_tag_at_same_commit_preserves_tag_object(self):
        self.git("-C", "work", "tag", "-a", TAG, "-m", "annotated")
        self.git("-C", "work", "push", "origin", "refs/tags/" + TAG)
        tag_object = self.git("--git-dir=origin", "rev-parse", TAG)
        self.publish()
        self.assertEqual(self.git("--git-dir=origin", "rev-parse", TAG), tag_object)
        self.assertNotEqual(tag_object, self.head)

    def test_conflicting_remote_tag_does_not_move(self):
        self.git("-C", "work", "push", "origin", self.earlier + ":refs/tags/" + TAG)
        self.publish(status=1)
        self.assertFalse((self.root / "calls").exists())
        self.assertEqual(self.git("--git-dir=origin", "rev-parse", TAG), self.earlier)

    def test_draft_prerelease_and_tagless_release_are_preserved(self):
        for state in ("true\tfalse", "false\ttrue", "false\tfalse"):
            with self.subTest(state=state):
                (self.root / "release").write_text(state)
                self.publish(status=1)
                self.assertEqual(self.git("--git-dir=origin", "tag"), "")
                self.assertEqual(self.creates(), 0)
                self.assertEqual((self.root / "release").read_text(), state)

    def test_ref_change_during_creation_is_reported(self):
        self.publish("retarget", status=1)
        self.assertEqual(self.git("--git-dir=origin", "rev-parse", TAG), self.earlier)
        self.assertEqual(self.creates(), 1)

    def test_read_failure_or_wrong_checkout_cannot_publish(self):
        self.publish(sha=self.earlier, status=1)
        self.assertFalse((self.root / "calls").exists())
        self.publish("unavailable", status=1)
        self.assertEqual(self.git("--git-dir=origin", "tag"), "")
        self.assertEqual(self.creates(), 0)
