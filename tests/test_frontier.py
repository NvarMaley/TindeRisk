"""Independent checks of the section 6.1 feasibility, inference and funded accounting."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.frontier.engine import Frontier, Limits, moments, risky_mix
from research.frontier.run import (
    HERE,
    WEIGHTS,
    dual_checks,
    funding,
    paired_fill,
    prior_check,
    reserve,
    screen,
)


class FrontierTests(unittest.TestCase):
    def setUp(self):
        self.cov = np.diag([0.04, 0.01])
        self.mu = np.array([0.09, 0.04])
        self.limits = Limits(single=1, usd=1, fee=0)

    def test_analytic_grid_dual_and_zero_radius(self):
        for v in [self.cov / 50, self.cov]:
            f = Frontier(self.mu, self.cov, v, [1, 1], self.limits)
            row = f.solve(0.06, 0)
            x = np.linalg.solve(self.cov, self.mu)
            expected = 0.06 * x / np.sqrt(x @ self.cov @ x)
            np.testing.assert_allclose([row["w0"], row["w1"]], expected, atol=3e-6)
            grid = np.arange(0, 1.001, 0.001)
            a, b = np.meshgrid(grid, grid)
            admissible = (a + b <= 1) & (0.04 * a * a + 0.01 * b * b <= 0.06**2)
            best = (0.09 * a + 0.04 * b)[admissible].max()
            self.assertLess(abs(row["net_mean"] - best), 0.00014)
        check = dual_checks()
        self.assertLess(check.max_error.max(), 1e-5)
        self.assertLess(check.iloc[-1].dual, 1e-6)

    def test_risk_parity_minimum_variance_and_prior(self):
        np.testing.assert_allclose(
            risky_mix(self.cov, [1, 1], True), [1 / 3, 2 / 3], atol=1e-8
        )
        np.testing.assert_allclose(
            risky_mix(self.cov, [1, 1], False), [0.2, 0.8], atol=1e-7
        )
        capped = risky_mix(self.cov, [1, 1], False, 2 / 3)
        np.testing.assert_allclose(capped, [1 / 3, 2 / 3], atol=1e-7)
        rows = prior_check(np.diag([0.04, 0.01, 0.09]))
        self.assertLess(rows[0]["max_deviation"], 1e-12)
        self.assertLess(rows[1]["max_deviation"], 1e-6)

    def test_budget_with_initial_and_drifted_holdings(self):
        for initial in [[0.0, 0.0], [0.55, 0.4]]:
            m = Frontier(
                self.mu,
                self.cov,
                self.cov / 30,
                [False, True],
                Limits(usd=1, single=1, fee=0.01),
                initial,
            )
            for r in [m.solve(0.12, 0), m.reference("equal weight", 0.12)]:
                self.assertIn(r["status"], ["optimal", "reference"])
                w = np.array([r["w0"], r["w1"]])
                fee = 0.01 * np.abs(w - initial).sum()
                self.assertAlmostEqual(r["fee"], fee)
                cash = 1 - np.sum(initial) - np.sum(w - initial) - fee
                self.assertAlmostEqual(cash, r["cash"])
                self.assertGreaterEqual(cash, -1e-7)
                self.assertAlmostEqual(r["w0"], 0)
            sold = m.solve(0, 0)
            self.assertAlmostEqual(sold["cash"], 1 - 0.01 * sum(initial))

    def test_infeasibility_and_quote_timing(self):
        f = Frontier(self.mu, self.cov, self.cov / 40, [0, 0], Limits(minimum=0.1))
        self.assertIn("infeasible", f.solve(0.1, 1)["status"])
        t = pd.bdate_range("2022-01-01", periods=78)
        prices = pd.DataFrame(100.0, index=t, columns=["SPY", "IEF", "GLD"])
        prices.loc[t[62], "IEF"] = np.nan
        gate = screen(prices, t[62], excluded=["GLD"])
        self.assertEqual(gate.eligible.tolist(), [True, False, False])
        prices.loc[t[63], "GLD"] = np.nan
        prices.loc[t[64] :, "SPY"] = 110
        fill, mark, r = paired_fill(prices, t[62], t[-1])
        self.assertEqual(fill, t[64])
        self.assertEqual(mark, t[-1])
        self.assertAlmostEqual(r.SPY, 0)
        b = reserve(t[62], t[-1])
        row = pd.Series(
            {"w0": 0.5, "w1": 0.0, "w2": 0.0, "cash": 0.4995, "fee": 0.0005}
        )
        out = funding(row, b, np.array([0.1, 0, 0]))
        self.assertAlmostEqual(out["end_after_payment"], 35000 + 1750 - 17.5)
        self.assertEqual(out["payment"], 15000)
        self.assertEqual(reserve(t[0], t[-1], 10000)["shortfall"], 5000)

    def test_joint_bootstrap_and_coverage(self):
        rng = np.random.default_rng(6)
        a = rng.normal(size=756)
        inputs = np.column_stack([a, a * 2, -a])
        inputs[3, 0] = np.nan
        mu, cov, error = moments(inputs, rng, 99)
        self.assertAlmostEqual(mu[1], 2 * mu[0])
        self.assertAlmostEqual(cov[1, 1], 4 * cov[0, 0])
        self.assertAlmostEqual(error[0, 2], -error[0, 0])
        self.assertGreaterEqual(np.linalg.eigvalsh(error).min(), -1e-10)

    def test_release(self):
        d = HERE / "results"
        for name, checksum in json.loads((d / "manifest.json").read_text()).items():
            self.assertEqual(
                hashlib.sha256((d / name).read_bytes()).hexdigest(), checksum
            )
        a = pd.read_csv(d / "frontiers.csv")
        self.assertEqual(len(a), 8 * 5 * 8)
        self.assertTrue((a.residual <= 2e-7).all())
        np.testing.assert_allclose(a[WEIGHTS].sum(axis=1) + a.cash + a.fee, 1)
        self.assertLess(a.query("arm=='60/40'").tracking_error_vs_fixed.max(), 1e-10)
        self.assertEqual(
            pd.read_csv(d / "dispersion.csv").attempted.unique().tolist(), [99]
        )
        diag = json.loads((d / "training.json").read_text())
        self.assertTrue(all(row["last"] < row["origin"] for row in diag))
        h = pd.read_csv(d / "realized.csv")
        self.assertTrue((h.fill > h.origin).all())
        self.assertTrue((h.mark <= h.due).all())
        self.assertTrue((h.shortfall == 0).all())


if __name__ == "__main__":
    unittest.main()
