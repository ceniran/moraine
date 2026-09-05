import unittest

from moraine.core_projection import build_core_projection
from moraine.episodes import build_episode_candidates
from moraine.temporal import is_current, is_valid_at, validate_validity


class TemporalTests(unittest.TestCase):
    def test_half_open_validity_window(self):
        row = {"state": "active", "valid_from": "2026-01-01T00:00:00Z", "valid_to": "2026-02-01T00:00:00Z"}
        self.assertTrue(is_valid_at(row, "2026-01-15T00:00:00Z"))
        self.assertFalse(is_valid_at(row, "2026-02-01T00:00:00Z"))
        self.assertFalse(is_current({**row, "state": "superseded"}, "2026-01-15T00:00:00Z"))

    def test_rejects_invalid_window(self):
        with self.assertRaises(ValueError):
            validate_validity({"valid_from": "2026-02-01T00:00:00Z", "valid_to": "2026-01-01T00:00:00Z"})


class EpisodeTests(unittest.TestCase):
    def test_groups_only_same_source_scope_inside_window(self):
        base = {"source": {"type": "conversation", "ref": "session:a"}, "workspace": "personal", "project_id": "moraine"}
        rows = [
            {**base, "id": "a", "created_at": "2026-09-05T01:00:00Z"},
            {**base, "id": "b", "created_at": "2026-09-05T01:40:00Z"},
            {**base, "id": "c", "created_at": "2026-09-05T03:00:00Z"},
            {**base, "id": "d", "created_at": "2026-09-05T01:20:00Z", "project_id": "dwell"},
        ]
        result = build_episode_candidates(rows, window_minutes=60)
        self.assertEqual([row["member_ids"] for row in result], [["d"], ["a", "b"], ["c"]])
        self.assertTrue(all(row["status"] == "pending_review" and not row["persisted"] for row in result))

    def test_requires_identity_and_time(self):
        with self.assertRaises(ValueError):
            build_episode_candidates([{"created_at": "2026-09-05T01:00:00Z"}])
        with self.assertRaises(ValueError):
            build_episode_candidates([{"id": "a", "source": {"type": "conversation", "ref": "session:a"}}])
        with self.assertRaises(ValueError):
            build_episode_candidates([{"id": "a", "created_at": "2026-09-05T01:00:00Z"}])


class CoreProjectionTests(unittest.TestCase):
    def test_only_explicit_current_records_enter_budget(self):
        records = [
            {"id": "identity", "title": "Name", "content": "Cairn", "state": "active", "importance": 0.9,
             "moraine_governance": {"core_presence": "always"}},
            {"id": "high-but-not-selected", "title": "Event", "content": "Not always", "state": "active", "importance": 1.0},
            {"id": "expired", "title": "Old", "content": "Old fact", "state": "active", "importance": 1.0,
             "valid_to": "2026-01-01T00:00:00Z", "moraine_governance": {"core_presence": "always"}},
        ]
        result = build_core_projection(records, now="2026-09-05T00:00:00Z", max_chars=100)
        self.assertEqual(result["source_ids"], ["identity"])
        self.assertIn("Cairn", result["text"])
        self.assertFalse(result["persisted"])

    def test_never_silently_truncates_a_block(self):
        row = {"id": "a", "title": "Long", "content": "x" * 100, "state": "active",
               "moraine_governance": {"core_presence": "always"}}
        result = build_core_projection([row], now="2026-09-05T00:00:00Z", max_chars=20)
        self.assertEqual(result["text"], "")
        self.assertEqual(result["skipped_ids"], ["a"])


if __name__ == "__main__":
    unittest.main()
