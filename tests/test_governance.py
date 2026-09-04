import unittest

from moraine.governance import GovernancePolicy, band_for, importance_from_strength, migration_preview, simulate_strengths, suggest_strength


class GovernanceTests(unittest.TestCase):
    def test_hundred_point_round_trip(self):
        self.assertEqual(importance_from_strength(42), 0.42)
        self.assertEqual(suggest_strength({"id": "m1", "kind": "event", "importance": 0.42})["current_strength"], 42)

    def test_kind_is_starting_point_not_forced_high_score(self):
        result = suggest_strength({"id": "m1", "kind": "project", "importance": 0.8})
        self.assertEqual(result["suggested_strength"], 40)
        self.assertEqual(result["difference"], -40)

    def test_protection_and_confirmations_are_explainable(self):
        result = suggest_strength({"id": "m1", "kind": "identity", "memory_decay": {"policy": "protected", "confirmation_count": 15}})
        self.assertEqual(result["suggested_strength"], 93)
        self.assertTrue(result["requires_review"])
        self.assertEqual([reason["signal"] for reason in result["reasons"]], ["kind_default", "explicit_protection", "confirmed_use"])

    def test_simulation_reports_distributions_without_content(self):
        result = simulate_strengths([{"id": "a", "kind": "event", "importance": 0.8, "content": "private"},
                                     {"id": "b", "kind": "decision", "importance": 0.7}])
        self.assertEqual(result["current_distribution"]["core"], 1)
        self.assertEqual(result["suggested_distribution"]["ordinary"], 1)
        self.assertTrue(all("content" not in row for row in result["suggestions"]))

    def test_auto_assign_keeps_sensitive_types_in_review(self):
        result = migration_preview([{"id": "a", "kind": "event"}, {"id": "b", "kind": "relationship", "importance": 0.8}], "auto_assign")
        self.assertFalse(result["persisted"])
        self.assertTrue(result["records"][0]["would_write"])
        self.assertFalse(result["records"][1]["would_write"])

    def test_only_missing_preserves_existing_strength(self):
        result = migration_preview([{"id": "a", "kind": "event", "importance": 0.77}], "auto_assign", only_missing=True)
        self.assertEqual(result["records"][0]["selected_strength"], 77)
        self.assertFalse(result["records"][0]["would_write"])

    def test_custom_policy(self):
        result = suggest_strength({"id": "a", "kind": "event"}, GovernancePolicy(base_strength={"event": 22, "unknown": 10}))
        self.assertEqual(result["suggested_strength"], 22)
        self.assertEqual(band_for(22), "ordinary")


if __name__ == "__main__":
    unittest.main()
