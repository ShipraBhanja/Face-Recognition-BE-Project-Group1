import unittest
from unittest.mock import patch

import numpy as np

from app.services.face_matching import (AGE_DB_COSINE_THRESHOLD, COSINE_THRESHOLD,
                                        known_age_gap, looks_like_match, rank_features,
                                        select_top_matches)


class FakeRecognizer:
    def match(self, left, right, _method):
        left = left.reshape(-1)
        right = right.reshape(-1)
        return float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right)))


class FaceMatchingTests(unittest.TestCase):
    def test_rank_features_sorts_highest_similarity_first(self):
        recognizer = FakeRecognizer()
        with patch("app.services.face_matching._load_models", return_value=(None, recognizer)):
            results = rank_features(
                np.array([[1.0, 0.0]], dtype=np.float32),
                [("different", "/d", np.array([[0.0, 1.0]], dtype=np.float32)),
                 ("same direction", "/s", np.array([[1.0, 0.0]], dtype=np.float32))],
            )
        self.assertEqual([row["label"] for row in results], ["same direction", "different"])

    def test_reference_threshold_is_a_boolean_cutoff(self):
        self.assertTrue(looks_like_match(COSINE_THRESHOLD))
        self.assertFalse(looks_like_match(COSINE_THRESHOLD - 0.001))

    def test_age_gap_threshold_uses_explicit_benchmark_cue(self):
        self.assertTrue(looks_like_match(AGE_DB_COSINE_THRESHOLD, AGE_DB_COSINE_THRESHOLD))
        self.assertFalse(looks_like_match(AGE_DB_COSINE_THRESHOLD - 0.001, AGE_DB_COSINE_THRESHOLD))

    def test_age_gap_only_exists_when_both_photo_ages_are_known(self):
        self.assertEqual(known_age_gap(30, 12), 18)
        self.assertIsNone(known_age_gap(None, 12))

    def test_top_k_returns_only_cutoff_matches_in_descending_order(self):
        ranked = [{"score": 0.8}, {"score": 0.3}, {"score": 0.6}]
        self.assertEqual(select_top_matches(ranked, k=1, threshold=0.4), [{"score": 0.8}])
        self.assertEqual(select_top_matches(ranked, k=10, threshold=0.9), [])


if __name__ == "__main__":
    unittest.main()
