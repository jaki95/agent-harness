import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adoption_decisions import make_proposal, remember_comments, render_proposal, replay


def item(key, *, decision="adopt", depends=(), **extra):
    return {"key": key, "revision": "a" * 40, "evidence": "b" * 64, "decision": decision,
            "behavior": "Adopt the upstream check", "preserve": "Keep local configuration",
            "verify": "Exercise the configured path", "why": "The upstream check finds stale metadata",
            "depends": list(depends), **extra}


def publish(previous, candidates, comment_id):
    return {**make_proposal(previous, candidates), "comment_id": comment_id}


def comment(number, body, login="maintainer", **extra):
    return {"id": number, "user": {"login": login, "type": "User"}, "body": body,
            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z", **extra}


class ProposalTests(unittest.TestCase):
    def test_numbers_and_version_survive_reorder_and_disappearance(self):
        first = publish(None, [item("b"), item("a")], 10)
        unchanged = make_proposal(first, [item("a"), item("b")])
        self.assertEqual(unchanged["version"], 1)
        self.assertEqual(unchanged["items"], first["items"])
        second = publish(first, [item("a"), item("c")], 20)
        third = make_proposal(second, [item("b"), item("c")])
        self.assertEqual(third["numbers"], {"a": 1, "b": 2, "c": 3})
        self.assertEqual([r["id"] for r in third["items"]], [2, 3])
        self.assertEqual(third["version"], 3)

    def test_invalid_items_cannot_overwrite_a_number(self):
        for candidates in ([item("one"), item("one")], [item("one", decision="maybe")],
                           [item("one", evidence="")], [item("one", depends=[False])]):
            with self.subTest(candidates=candidates), self.assertRaises(ValueError):
                make_proposal(None, candidates)

    def test_changed_dependency_invalidates_transitive_approval_only(self):
        candidates = [item("a"), item("b", depends=["a"]), item("c", depends=["b"]), item("d")]
        first = publish(None, candidates, 10)
        candidates[0]["preserve"] = "Retain the other adapter"
        second = publish(first, candidates, 20)
        events = [comment(12, "approve P1"), comment(25, "approve P1 item 3")]
        state = replay([first, second], events, "maintainer")
        self.assertEqual(state["groups"], {"12": [4]})
        self.assertIn("changed", state["responses"]["25"])
        self.assertEqual(state["statuses"]["3"], "pending")

    def test_evidence_paths_and_source_links_are_available_in_the_proposal(self):
        source = "https://github.com/owner/repo/compare/old...new"
        proposal = make_proposal(None, [item("one", source_url=source, evidence_paths=["skills/test/SKILL.md"]),
                                       item("two", source_url="https://example.invalid/path")])
        text = render_proposal(proposal)
        self.assertIn(f"[Upstream change]({source})", text)
        self.assertIn("skills/test/SKILL.md", text)
        self.assertNotIn("example.invalid", text)

    def test_render_includes_requested_decisions_and_evidence(self):
        p = make_proposal(None, [item("a"), item("b", depends=["a"], behavior="Preserve | wording\n</details>")])
        result = render_proposal(p)
        for text in ("Proposal P1", "approve P1 item 1", "Depends on: item 1", "Keep local configuration",
                     "Exercise the configured path", "Preserve &#124; wording &lt;/details&gt;", "Upstream revision"):
            self.assertIn(text, result)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.history = [publish(None, [item("a"), item("b"), item("c", depends=["b"])], 10)]

    def run_replay(self, events, **options):
        return replay(self.history, events, "maintainer", **options)

    def test_only_original_standalone_owner_command_authorizes_work(self):
        events = [comment(9, "approve P1"), comment(11, "approve P1", "outsider"),
                  comment(12, "approve P1", updated_at="2026-01-02T01:00:00Z"),
                  comment(13, "approve P1", user={"login": "maintainer", "type": "Bot"}),
                  comment(14, "> approve P1"), comment(15, "approve P1\nWhy is this needed?"),
                  comment(16, "looks good"), comment(17, "approve P1 item 1", login="MAINTAINER")]
        state = self.run_replay(events[::-1] + [events[-1]])
        self.assertEqual(state["groups"], {"17": [1]})
        self.assertEqual([c["id"] for c in state["discussion"]], [14, 15, 16])

    def test_hold_in_same_pr_removes_dependants_and_survives_restart(self):
        events = [comment(12, "approve P1 items 1,2,3"), comment(13, "hold P1 item 2")]
        state = self.run_replay(events)
        self.assertEqual(state["groups"], {"12": [1]})
        self.assertEqual(state["statuses"], {"1": "approved", "2": "held", "3": "held"})
        self.assertEqual(self.run_replay(list(reversed(events))), state)
        self.assertEqual(self.run_replay(events + [comment(14, "approve P1")])["groups"], {"12": [1]})

    def test_explicit_hold_persists_across_a_changed_proposal_until_selected(self):
        before = self.history[0]
        after = publish(before, [item("a", revision="f" * 40), item("b")], 22)
        commands = [comment(11, "hold P1 item 1"), comment(25, "approve P2")]
        state = replay([before, after], commands, "maintainer")
        self.assertEqual(state["groups"], {"25": [2]})
        self.assertEqual(state["statuses"]["1"], "held")
        state = replay([before, after], commands + [comment(26, "approve P2 item 1")], "maintainer")
        self.assertEqual(state["groups"]["26"], [1])

    def test_repeat_approval_reuses_group_and_new_scope_never_coopts_its_items(self):
        state = self.run_replay([comment(11, "approve P1 item 2"), comment(12, "approve P1 items 1,2"),
                                 comment(13, "approve P1 item 1")])
        self.assertEqual(state["groups"], {"11": [2], "12": [1]})
        self.assertIn("already approved", state["responses"]["13"])

    def test_missing_approval_blocks_entire_selection(self):
        state = self.run_replay([comment(12, "approve P1 items 1,3")])
        self.assertEqual(state["groups"], {})
        self.assertIn("items 2", state["responses"]["12"])
        self.assertEqual(state["statuses"]["1"], "pending")

    def test_separate_approved_dependency_is_awaited_until_verified_merge(self):
        events = [comment(11, "approve P1 item 2"), comment(12, "approve P1 items 1,3")]
        state = self.run_replay(events)
        self.assertEqual(state["waiting"], {"12": [1, 3]})
        self.assertEqual(state["groups"], {"11": [2], "12": []})
        digest = self.history[0]["items"][1]["digest"]
        merged = self.run_replay(events, merged={digest: "https://example.invalid/merged"})
        self.assertEqual(merged["groups"]["12"], [1, 3])
        self.assertEqual(merged["statuses"]["2"], "merged")

    def test_confirmed_merged_prerequisite_leaving_queue_preserves_approved_child(self):
        before = self.history[0]
        merged = {before["items"][1]["digest"]: 27}
        child = [item("a"), item("c", depends=["b"])]
        after = {**make_proposal(before, child, merged=merged), "comment_id": 30}
        self.assertEqual(before["items"][2]["digest"], after["items"][1]["digest"])
        events = [comment(11, "approve P1 item 2"), comment(12, "approve P1 item 3")]
        state = replay([before, after], events, "maintainer", merged=merged)
        self.assertEqual(state["groups"]["12"], [3])
        state = replay([before, after], events + [comment(35, "hold P1 items 2,3")], "maintainer", merged=merged)
        self.assertEqual(state["groups"]["12"], [])
        self.assertIn("already merged", state["responses"]["35"])

    def test_disappearing_unconfirmed_dependency_blocks_child_and_invalidates_approval(self):
        before = self.history[0]
        after = {**make_proposal(before, [item("c", depends=["b"])]), "comment_id": 30}
        self.assertNotEqual(before["items"][2]["digest"], after["items"][0]["digest"])
        state = replay([before, after], [comment(11, "approve P1"), comment(31, "approve P2")], "maintainer")
        self.assertEqual(state["groups"]["11"], [])
        self.assertIn("unavailable dependencies", state["responses"]["31"])

    def test_durable_original_comments_survive_edits_deletion_and_retries(self):
        approved, held = comment(11, "approve P1"), comment(12, "hold P1 item 2")
        recorded = remember_comments({}, [approved, held], "maintainer")
        changed = comment(12, "approve P1", updated_at="2026-03-23T04:00:00Z")
        app = comment(13, "approve P1 item 2", performed_via_github_app={"id": 7})
        later = remember_comments(recorded, [changed, app], "maintainer")
        self.assertEqual(recorded, later)
        state = self.run_replay(list(later.values()))
        self.assertEqual(state["groups"], {"11": [1]})
        self.assertFalse(remember_comments({}, [changed, app], "maintainer"))

    def test_other_items_keep_old_approval_and_commands_cannot_bind_future_version(self):
        before = [comment(12, "approve P2 item 1"), comment(13, "approve P1 items 1,2")]
        second = publish(self.history[0], [item("a", revision="f" * 40), item("b"), item("c", depends=["b"])], 20)
        self.history.append(second)
        state = self.run_replay(before + [comment(25, "hold P1 item 2")])
        self.assertIn("Unknown proposal", state["responses"]["12"])
        self.assertEqual(state["groups"], {"13": []})

    def test_defer_revisit_and_partial_approval_with_unavailable_evidence(self):
        self.history = [publish(None, [item("a", decision="blocked"), item("b"), item("c")], 10)]
        commands = [comment(11, "defer P1 item 2 because a project trial is pending"), comment(12, "approve P1")]
        deferred = self.run_replay(commands)
        self.assertEqual(deferred["statuses"]["2"], "deferred")
        self.assertEqual(deferred["defer_reasons"], {"2": "a project trial is pending"})
        state = self.run_replay(commands + [comment(13, "revisit item 2")])
        self.assertEqual(state["groups"], {"12": [3]})
        self.assertEqual(state["statuses"], {"1": "blocked", "2": "pending", "3": "approved"})
        self.assertEqual([r["id"] for r in state["revisit"]], [13])

    def test_merges_are_preserved_and_hold_reports_it_would_require_revert(self):
        digest = self.history[0]["items"][0]["digest"]
        state = self.run_replay([comment(11, "hold P1 item 1")], merged={digest: 27})
        self.assertEqual(state["statuses"]["1"], "merged")
        self.assertIn("revert", state["responses"]["11"])

    def test_hold_across_merged_and_unmerged_items_still_stops_pending_work(self):
        digest = self.history[0]["items"][0]["digest"]
        state = self.run_replay([comment(11, "approve P1"), comment(12, "hold P1")], merged={digest: 27})
        self.assertEqual(state["statuses"], {"1": "merged", "2": "held", "3": "held"})
        self.assertEqual(state["groups"]["11"], [])
        self.assertIn("revert", state["responses"]["12"])

    def test_cyclic_or_missing_dependencies_do_not_authorize_unrelated_selected_items(self):
        for deps in (["a"], ["outside"]):
            history = [publish(None, [item("a", depends=deps), item("b")], 10)]
            state = replay(history, [comment(12, "approve P1")], "maintainer")
            self.assertFalse(state["groups"])
            self.assertIn("dependencies", state["responses"]["12"])
            state = replay(history, [comment(13, "approve P1 item 2")], "maintainer")
            self.assertEqual(state["groups"], {"13": [2]})

    def test_invalid_history_and_conflicting_duplicates_stop_replay(self):
        bad = copy.deepcopy(self.history[0])
        bad.update(version=3, comment_id=19)
        with self.assertRaises(ValueError):
            replay(self.history + [bad], [], "maintainer")
        with self.assertRaises(ValueError):
            self.run_replay([comment(13, "approve P1"), comment(13, "hold P1")])
