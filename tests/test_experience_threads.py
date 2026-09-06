import unittest

from moraine.experience_threads import build_experience_thread_candidate


class ExperienceThreadTests(unittest.TestCase):
    @staticmethod
    def row(memory_id, created_at, *, workspace="personal", source_ref=None):
        return {
            "id": memory_id,
            "workspace": workspace,
            "created_at": created_at,
            "source": {"type": "game", "ref": source_ref or f"werewolf:{memory_id}"},
        }

    def test_orders_explicit_members_and_keeps_sources(self):
        rows = [
            self.row("later", "2026-09-02T10:00:00Z"),
            self.row("first", "2026-09-01T10:00:00Z"),
        ]
        result = build_experience_thread_candidate(
            rows,
            thread_id="werewolf.action-timing",
            title="Werewolf action timing",
            workspace="personal",
        )
        self.assertEqual(result["member_ids"], ["first", "later"])
        self.assertEqual(result["points"][0]["source"], {"type": "game", "ref": "werewolf:first"})
        self.assertFalse(result["membership_inferred"])
        self.assertTrue(result["requires_review"])
        self.assertEqual(result["writes"], [])
        self.assertFalse(result["persisted"])

    def test_builds_source_linked_pending_summary(self):
        result = build_experience_thread_candidate(
            [self.row("a", "2026-09-01T10:00:00Z"), self.row("b", "2026-09-02T10:00:00Z")],
            thread_id="werewolf.action-timing",
            title="Werewolf action timing",
            workspace="personal",
            summary_draft={
                "revision": 2,
                "previous_revision": 1,
                "text": "Wait for decisive replies before locking an action.",
                "source_ids": ["b", "a"],
                "unresolved": ["Needs another wolf-game check", ""],
                "revisit_when": ["A later game contradicts this rule"],
            },
        )
        summary = result["summary_draft"]
        self.assertEqual(summary["status"], "pending_review")
        self.assertEqual(summary["source_ids"], ["b", "a"])
        self.assertEqual(summary["unresolved"], ["Needs another wolf-game check"])
        self.assertFalse(summary["persisted"])

    def test_rejects_missing_identity_scope_source_or_time(self):
        base = self.row("a", "2026-09-01T10:00:00Z")
        cases = [
            {**base, "id": ""},
            {**base, "workspace": "other"},
            {**base, "source": {}},
            {**base, "created_at": ""},
        ]
        for row in cases:
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    build_experience_thread_candidate(
                        [row], thread_id="thread", title="Thread", workspace="personal"
                    )

    def test_rejects_empty_or_duplicate_members(self):
        with self.assertRaises(ValueError):
            build_experience_thread_candidate([], thread_id="thread", title="Thread", workspace="personal")
        row = self.row("a", "2026-09-01T10:00:00Z")
        with self.assertRaises(ValueError):
            build_experience_thread_candidate([row, row], thread_id="thread", title="Thread", workspace="personal")

    def test_summary_must_cite_members_and_follow_revision_chain(self):
        row = self.row("a", "2026-09-01T10:00:00Z")
        invalid_summaries = [
            {"revision": 1, "text": "Summary", "source_ids": ["missing"]},
            {"revision": 1, "previous_revision": 1, "text": "Summary", "source_ids": ["a"]},
            {"revision": 3, "previous_revision": 1, "text": "Summary", "source_ids": ["a"]},
            {"revision": 1, "text": "", "source_ids": ["a"]},
            {"revision": 1, "text": "Summary", "source_ids": []},
            {"revision": 1, "text": "Summary", "source_ids": "a"},
            {"revision": 1, "text": "Summary", "source_ids": ["a"], "unresolved": "question"},
            {"revision": True, "text": "Summary", "source_ids": ["a"]},
        ]
        for summary in invalid_summaries:
            with self.subTest(summary=summary):
                with self.assertRaises(ValueError):
                    build_experience_thread_candidate(
                        [row], thread_id="thread", title="Thread", workspace="personal",
                        summary_draft=summary,
                    )

    def test_does_not_mutate_input(self):
        rows = [self.row("a", "2026-09-01T10:00:00Z")]
        snapshot = [{**rows[0], "source": dict(rows[0]["source"])}]
        build_experience_thread_candidate(
            rows, thread_id="thread", title="Thread", workspace="personal"
        )
        self.assertEqual(rows, snapshot)


if __name__ == "__main__":
    unittest.main()
