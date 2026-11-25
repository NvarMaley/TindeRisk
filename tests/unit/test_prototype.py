import unittest
import numpy as np
from riskmatch.prototype import ClientProfile, cards, score, candidates, synthetic_returns


class PrototypeTests(unittest.TestCase):
    def test_cards(self):
        self.assertEqual(len(cards()), 30)
        self.assertEqual(len({c["id"] for c in cards()}), 30)
        self.assertTrue(all(set(c["fr"]) == {"block", "a", "b"} for c in cards()))

    def test_score(self):
        self.assertEqual(score({c["id"]: "dislike" for c in cards()})["score"], 30)
        self.assertEqual(score({c["id"]: "like" for c in cards()})["score"], 1)
        self.assertIsNone(score({})["score"])

    def test_filter(self):
        for p in candidates(ClientProfile(10000, 10, .1)):
            self.assertAlmostEqual(sum(p["weights"].values()), 1)
            self.assertLessEqual(p["stress_loss"], .1)
        self.assertEqual([p["name"] for p in candidates(ClientProfile(100, 1, 0))], ["Cash"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            ClientProfile(-100, 2, .2)

    def test_reproducibility(self):
        np.testing.assert_array_equal(synthetic_returns(), synthetic_returns())
