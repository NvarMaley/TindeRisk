"""Regression checks for dated research inputs, estimators and the published register."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "research/experiments")]
from portfolio import EW, boundary_weights

from research.robustness.estimators import (
    filtered_path,
    gap_forecast,
    mean_forecast,
    rescaled_covariance,
)
from research.robustness.filing import characteristics
from research.robustness.run import HERE, mean_inputs, published_curve_inputs


class Robustness(unittest.TestCase):
    def test_missing_innovation_propagates_variance(self):
        path = filtered_path([4.0, -1.0, 0.0], 1, 0.1, 0.9)
        np.testing.assert_allclose(path, [1, 1.3, 1.27, 1.116])
        x = np.random.default_rng(82).normal(0, 0.01, 756)
        x[:37] = np.nan
        variance, info = gap_forecast(x, 21)
        self.assertGreater(variance, 0)
        self.assertEqual(info["observed"], 719)
        x[37] = np.nan
        self.assertTrue(np.isnan(gap_forecast(x, 21)[0]))

    def test_covariance_and_partial_trading(self):
        x = np.random.default_rng(3).normal(size=(756, 3))
        c = rescaled_covariance(x, x[-63:])
        np.testing.assert_allclose(c, c.T)
        np.testing.assert_allclose(np.diag(c), x[-63:].var(axis=0, ddof=1))
        self.assertGreater(np.linalg.eigvalsh(c).min(), 0)
        inside = EW + [0.01, 0, -0.01]
        outside = EW + [0.13, -0.05, -0.08]
        np.testing.assert_allclose(boundary_weights(inside, 0.05), inside)
        w = boundary_weights(outside, 0.05)
        self.assertAlmostEqual(w.sum(), 1)
        self.assertAlmostEqual(abs(w - EW).max(), 0.05)
        self.assertLess(abs(w - outside).sum(), abs(EW - outside).sum())

    def test_forwards_and_weekly_release_lag(self):
        dates = pd.date_range("2022-10-21", "2022-11-09", freq="B")
        cols = [f"SVENY{i:02}" for i in range(1, 6)]
        curve = pd.DataFrame(
            np.tile([1.0, 2.0, 3.0, 4.0, 5.0], (len(dates), 1)), columns=cols
        )
        curve["Date"] = dates
        origins = pd.DatetimeIndex(["2022-11-08", "2022-11-09"])
        forward, observed = published_curve_inputs(origins, curve)
        self.assertEqual(
            observed.tolist(), list(pd.to_datetime(["2022-10-28", "2022-11-04"]))
        )
        np.testing.assert_allclose(forward[0], [0.01, 0.03, 0.05, 0.07, 0.09])
        curve.loc[curve.Date >= origins[0], cols] = 1000
        np.testing.assert_allclose(published_curve_inputs(origins, curve)[0], forward)
        direct, dates_used = mean_inputs(origins[:1], curve, None, "H03")
        self.assertLess(dates_used[0], origins[0])
        np.testing.assert_allclose(direct[0], forward[0])

    def test_restricted_equity_forecast(self):
        x = np.arange(40.0).reshape(-1, 1)
        self.assertAlmostEqual(mean_forecast(x, 50 - x[:, 0], x[-1], "H04"), 30.5)
        self.assertEqual(mean_forecast(x, x[:, 0] - 100, x[-1], "H04"), 0)
        self.assertTrue(np.isnan(mean_forecast(x[:35], x[:35, 0], x[-1], "H04")))

    def test_filing_gate_and_momentum_lag(self):
        f = json.loads((HERE / "inputs/aapl_2023_filing.json").read_text())
        dates = pd.date_range("2022-12-01", periods=12, freq="BME")
        panel = pd.DataFrame(
            {
                "day": dates,
                "permno": 14593,
                "gvkey": "001690",
                "ret": 0.01,
                "cap_thousands": 1e8,
                "best_link_count": 1,
                "common_us": True,
                "market_candidate": True,
            }
        )
        panel.loc[11, "ret"] = 8
        cal = pd.bdate_range("2023-10-01", "2023-11-30")
        for origin in ["2023-10-31", "2023-11-03"]:
            with self.assertRaisesRegex(ValueError, "unavailable"):
                characteristics(f, panel, cal, origin)
        row = characteristics(f, panel, cal, dates[-1])
        self.assertEqual(row["first_allowed_session"], "2023-11-06")
        self.assertAlmostEqual(row["momentum"], 1.01**11 - 1)
        self.assertAlmostEqual(row["gross_profitability"], 169148 / 352583)
        panel.loc[11, "best_link_count"] = 2
        with self.assertRaisesRegex(ValueError, "link"):
            characteristics(f, panel, cal, dates[-1])

    def test_release_integrity_and_decisions(self):
        dest = HERE / "results"
        for name, digest in json.loads((dest / "manifest.json").read_text()).items():
            self.assertEqual(
                hashlib.sha256((dest / name).read_bytes()).hexdigest(), digest
            )
        rows = pd.read_csv(dest / "signal_register.csv")
        self.assertEqual(rows.study.tolist(), [f"H0{i}" for i in range(1, 8)])
        self.assertFalse(rows.admitted.any())
        self.assertEqual(rows.independent_months.sum(), 0)
        self.assertTrue(
            rows[["research_use", "active_reference", "next_gate"]].notna().all().all()
        )
        dates = pd.read_parquet(dest / "monthly.parquet")
        financial = dates[dates.study.isin(["H03", "H04"]) & dates.prediction.notna()]
        self.assertTrue((financial.train_end < financial.origin).all())
        self.assertTrue((financial.source_date < financial.origin).all())
        raw = pd.read_csv(HERE / "inputs/french_portfolios.csv")
        gain = (raw.favorable - raw.middle).groupby(raw.month).mean()
        h5 = dates[dates.study.eq("H05")].set_index("month").sort_index()
        np.testing.assert_allclose(h5.gain, gain.reindex(h5.index))
        self.assertEqual(len(gain), 144)


if __name__ == "__main__":
    unittest.main()
