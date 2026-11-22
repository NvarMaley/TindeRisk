"""Section 4.2 shock arithmetic, timing, episode coverage and release checks."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/shocks"))
from analysis import ASSETS, bp, episode_return, fit, scenarios, training_window


class ShockTests(unittest.TestCase):
    def test_cash_interaction_and_basis_points(self):
        self.assertEqual(bp(100), 0.01)
        # SPY tracks equity, IEF has sensitivity -7 to nominal yield, GLD +2 to breakeven.
        b = np.array(
            [[0.25, 0.25, 0.25], [1.0, 0.0, 0.0], [0.0, -7.0, 0.0], [0.0, 0.0, 2.0]]
        )
        rows, totals = scenarios(b)
        summary = pd.DataFrame(totals).set_index(["scenario", "mix"])
        self.assertAlmostEqual(
            summary.loc[("Joint shock", "60/40"), "portfolio_return"],
            (0.6 * 0.9 + 0.4 * 0.93) * 0.95 - 1,
        )
        self.assertAlmostEqual(
            summary.loc[("Joint shock", "60/40"), "interaction"], 0.0044
        )
        self.assertTrue(
            summary.xs("CHF cash", level="mix").portfolio_return.eq(0).all()
        )
        self.assertAlmostEqual(
            summary.loc[("Nominal yield rise", "Equal weight"), "portfolio_return"],
            -0.07 / 3,
        )
        parts = pd.DataFrame(rows).groupby(["scenario", "mix"]).contribution.sum()
        np.testing.assert_allclose(
            parts, summary.portfolio_return.reindex(parts.index), atol=1e-12
        )

    def test_fit_and_cutoff(self):
        rng = np.random.default_rng(42)
        days = pd.bdate_range("2022-01-03", periods=260)
        x = rng.normal(size=(260, 3)) * 0.01
        frame = pd.DataFrame(x, index=days, columns=["equity", "nominal", "breakeven"])
        frame["SPY"] = x[:, 0]
        frame["IEF"] = 0.001 - 7 * x[:, 1]
        frame["GLD"] = 0.5 * x[:, 0] + 2 * x[:, 2]
        frame["fx"] = 0.0
        frame.loc[days[30], "nominal"] = np.nan
        cutoff = days[-3]
        train = training_window(frame, cutoff)
        b, se, n = fit(train, 200)
        self.assertEqual((len(train), n, train.index[-1]), (252, 251, days[-4]))
        np.testing.assert_allclose(
            b, [[0, 0.001, 0], [1, 0, 0.5], [0, -7, 0], [0, 0, 2]], atol=1e-12
        )
        self.assertTrue((se >= 0).all())
        frame.loc[cutoff:, "IEF"] = -1.0
        np.testing.assert_array_equal(fit(training_window(frame, cutoff), 200)[0], b)
        with self.assertRaises(ValueError):
            fit(train.iloc[:20], 200)
        with self.assertRaises(ValueError):
            fit(train.assign(breakeven=train.nominal), 200)

    def test_episode_gaps(self):
        dates = pd.bdate_range("2020-01-01", periods=3)
        frame = pd.DataFrame({a: [np.nan, 0.1, -0.1] for a in ASSETS}, index=dates)
        frame["fixing"] = [1.0, np.nan, 0.9]
        self.assertAlmostEqual(
            episode_return(frame, dates[1], dates[2], np.ones(3) / 3), -0.109
        )
        frame.loc[dates[0], "fixing"] = np.nan
        self.assertTrue(
            np.isnan(episode_return(frame, dates[1], dates[2], np.ones(3) / 3))
        )

    def test_release_reconciliation(self):
        d = ROOT / "research/shocks/results"
        for name, digest in json.loads((d / "manifest.json").read_text()).items():
            self.assertEqual(
                hashlib.sha256((d / name).read_bytes()).hexdigest(), digest
            )
        ledger = pd.read_parquet(d / "historical_attribution.parquet")
        self.assertTrue((ledger.cutoff < ledger.session).all())
        self.assertEqual(len(ledger), 2 * 1717)
        np.testing.assert_allclose(
            ledger.explained + ledger.residual,
            ledger.actual,
            equal_nan=True,
            atol=1e-12,
        )
        exposures = pd.read_csv(d / "rolling_exposures.csv")
        self.assertTrue((exposures["last"] < exposures.cutoff).all())
        s = pd.read_csv(d / "scenarios.csv")
        self.assertEqual(len(s), 83 * 5 * 3)
        self.assertLess(s.reconciliation_error.abs().max(), 1e-12)
        held = (
            pd.read_csv(d / "scenario_holdings.csv")
            .groupby(["cutoff", "scenario", "mix"])
            .contribution.sum()
        )
        np.testing.assert_allclose(
            held,
            s.set_index(["cutoff", "scenario", "mix"]).portfolio_return.reindex(
                held.index
            ),
            atol=1e-12,
        )


if __name__ == "__main__":
    unittest.main()
