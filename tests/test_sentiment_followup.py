"""Check the message timing and independent accounting of the H06 follow-up."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.sentiment_followup.run import fit_activity, posterior_weight, signals


class SentimentFollowup(unittest.TestCase):
    def test_timing_and_missing_messages(self):
        idx = pd.bdate_range("2015-01-01", periods=100)
        rng = np.random.default_rng(606)
        rows = []
        for day in idx:
            for symbol in ["AAPL", "SPY"]:
                up, down = rng.integers(1, 80, size=2)
                rows.append((day, symbol, up, down, up + down + 5))
        counts = pd.DataFrame(
            rows, columns=["session", "ticker", "Nbullish", "Nbearish", "N"]
        )
        prices = pd.DataFrame(index=idx)
        original = signals(prices, counts)
        self.assertTrue(original.iloc[-4].notna().all())
        counts.loc[counts.session >= idx[-4], ["Nbullish", "Nbearish", "N"]] = np.nan
        changed = signals(prices, counts)
        pd.testing.assert_series_equal(
            original.polarity.iloc[:-3], changed.polarity.iloc[:-3]
        )
        pd.testing.assert_series_equal(
            original.activity.iloc[:-2], changed.activity.iloc[:-2]
        )
        self.assertTrue(pd.isna(changed.polarity.iloc[-3]))
        self.assertTrue(pd.isna(changed.activity.iloc[-2]))

    def test_neutral_view_and_known_activity_slope(self):
        cov = np.array([[0.004, 0.001], [0.001, 0.0016]])
        for score in [-0.75, 0, 0.75]:
            w, te = posterior_weight(cov, score, relative_to_prior=True)
            self.assertEqual(np.sign(w[0] - 0.5), np.sign(score))
            self.assertLessEqual(te, 0.0200000001)
        x = np.linspace(-2, 2, 500)
        train = pd.DataFrame(
            {"activity": x, "base": 0.0004, "actual": 0.0004 * 1.1 * np.exp(0.3 * x)}
        )
        ref, scale, b, n = fit_activity(train)
        self.assertAlmostEqual(scale, 1.1, places=6)
        self.assertAlmostEqual(b, 0.3, places=6)
        self.assertEqual(n, 500)
        self.assertGreater(ref, 1.0)
        self.assertIsNone(fit_activity(train.iloc[:251]))

    def test_published_release(self):
        d = ROOT / "research/sentiment_followup/results"
        for name, checksum in json.loads((d / "manifest.json").read_text()).items():
            self.assertEqual(
                hashlib.sha256((d / name).read_bytes()).hexdigest(), checksum
            )
        a = pd.read_parquet(d / "allocation.parquet")
        self.assertTrue((a.signal_cutoff < a.origin).all())
        self.assertTrue((a.origin < a.first_close).all())
        np.testing.assert_allclose(
            a.utility, a.net_return - 2 * a.net_return**2, equal_nan=True
        )
        np.testing.assert_allclose(a.gain, a.utility - a.anchor_utility, equal_nan=True)
        r = pd.read_parquet(d / "daily_risk.parquet")
        valid = r[r.deployed.notna()]
        self.assertTrue((valid.training_last < valid.origin).all())
        self.assertTrue((valid.origin < valid.session).all())
        self.assertTrue((valid.deployed > 0).all())
        no_view = valid[valid.candidate.isna()]
        np.testing.assert_array_equal(no_view.reference, no_view.deployed)


if __name__ == "__main__":
    unittest.main()
