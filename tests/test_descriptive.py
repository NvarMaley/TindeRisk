"""Section 4.1 regression cases with hand-computable returns and risk."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/descriptive"))
from build import wealth_path
from metrics import (
    attribution,
    coverage,
    forecasts,
    historical_tail,
    horizon_risk,
    underwater,
)


class HistoricalRiskTests(unittest.TestCase):
    def test_compounding_and_fx_gap(self):
        ret = pd.Series([np.nan, 0.10, -0.10])
        usd, chf = wealth_path(ret, pd.Series([1.0, np.nan, 0.9]))
        np.testing.assert_allclose(usd, [100, 110, 99])
        np.testing.assert_allclose(chf, [100, np.nan, 89.1], equal_nan=True)
        self.assertTrue(chf.pct_change(fill_method=None).isna().all())
        self.assertAlmostEqual(np.expm1(np.log1p(ret).sum()), -0.01)
        zero, _ = wealth_path(
            pd.Series([np.nan, -1.0, 0.25]), pd.Series([1.0, 1.0, 1.0])
        )
        self.assertEqual(zero.iloc[-1], 0.0)

    def test_underwater(self):
        w = pd.Series(
            [100, 120, 90, np.nan, 120, 108],
            index=pd.date_range("2020-01-01", periods=6),
        )
        dd, age, episodes = underwater(w)
        self.assertAlmostEqual(dd.min(), -0.25)
        self.assertTrue(pd.isna(age.iloc[3]))
        self.assertEqual(episodes.duration_days.tolist(), [3, 1])
        self.assertEqual(episodes.ongoing.tolist(), [False, True])
        self.assertEqual(episodes.iloc[0].trough, w.index[2])
        self.assertEqual(episodes.iloc[0].recovery, w.index[4])
        flat, _, events = underwater(w.fillna(1) * 0 + 100)
        self.assertTrue(flat.eq(0).all() and events.empty)

    def test_fractional_tail_and_boundary(self):
        losses = [0, 0.02, 0.02, 0.08, np.nan]
        np.testing.assert_allclose(historical_tail(losses, 0.625), [0.02, 0.06])
        np.testing.assert_allclose(historical_tail(losses, 0.75), [0.02, 0.08])

    def test_forecast_timing_and_missing_sessions(self):
        dates = pd.bdate_range("2021-01-04", periods=257)
        returns = pd.Series(-0.01, index=dates)
        returns.iloc[252:] = [-0.5, np.nan, -0.5, -0.01, -0.01]
        ledger = forecasts(returns, dates[251:], 0.95)
        self.assertTrue(pd.isna(ledger.iloc[0]["var"]))
        self.assertEqual(ledger.iloc[1].cutoff_session, dates[251])
        np.testing.assert_allclose(
            ledger.hit, [np.nan, 1, np.nan, 1, 0, 0], equal_nan=True
        )
        check = coverage(ledger, 0.95)
        self.assertEqual(
            (check["verified"], check["breaches"], check["breach_runs"], check["n11"]),
            (4, 2, 2, 0),
        )
        self.assertTrue(np.isnan(check["independence_p"]))
        returns.iloc[:14] = np.nan
        missing = forecasts(returns, dates[252:253], 0.95)
        self.assertEqual(coverage(missing, 0.95)["verified"], 0)

    def test_diversification_and_hedging(self):
        w = np.array([0.8, 0.2])
        diagnostic, parts = attribution(np.full((2, 2), 0.04), w)
        self.assertAlmostEqual(diagnostic["diversification_ratio"], 1.0)
        self.assertIn("singular", diagnostic["status"])
        diagnostic, parts = attribution(np.array([[0.04, -0.018], [-0.018, 0.01]]), w)
        self.assertLess(parts["risk_share"][1], 0)
        self.assertAlmostEqual(sum(parts["vol_component"]), diagnostic["volatility"])
        self.assertAlmostEqual(sum(parts["variance_component"]), diagnostic["variance"])
        for cov in (np.zeros((2, 2)), np.array([[1.0, 2.0], [2.0, 1.0]])):
            self.assertIsNone(attribution(cov, w)[1])

    def test_lagged_risk_and_path_counts(self):
        r = pd.Series(np.expm1([0.03, -0.03, 0.03, np.nan, -0.03]))
        result = horizon_risk(r, 2)
        self.assertAlmostEqual(result["iid_log_sd"], np.sqrt(2) * 0.03)
        self.assertAlmostEqual(result["autocov_log_sd"], 0.0, places=8)
        self.assertEqual(result["complete_paths"], 2)
        self.assertAlmostEqual(result["compounded_simple_sd"], 0.0)


if __name__ == "__main__":
    unittest.main()
