"""Chronology, funded execution and registered forecast fallbacks."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/experiments"))
from controls import blocks, walk_predictions
from models import garch_risk, macro_fit
from portfolio import posterior_weight, trade


class ExperimentTests(unittest.TestCase):
    def test_purged_ridge_and_unknown_label(self):
        rng = np.random.default_rng(503)
        x = rng.normal(size=(64, 2))
        y = 0.1 * x[:, 0] + rng.normal(size=len(x))
        tab = pd.DataFrame(x, columns=["T10Y2Y", "BAA10Y"])
        tab["target"] = y
        point, n = macro_fit(tab.iloc[:49], tab.iloc[50], "ridge")
        path = walk_predictions(x, y)
        self.assertEqual(n, 49)
        self.assertAlmostEqual(point, path[50, 2])
        y[49:] = 10000
        x[51:] = -9999
        np.testing.assert_allclose(path[50], walk_predictions(x, y)[50])
        tab.loc[50, "target"] = np.nan
        self.assertEqual(point, macro_fit(tab.iloc[:49], tab.iloc[50], "ridge")[0])
        row = tab.iloc[50].copy()
        row["T10Y2Y"] = np.nan
        self.assertTrue(np.isnan(macro_fit(tab.iloc[:49], row, "ridge")[0]))

    def test_funding_and_posterior(self):
        new, cash, traded, fee = trade(
            np.array([60.0, 40.0]), 0.0, np.array([0.4, 0.6]), 0.01
        )
        self.assertAlmostEqual(sum(new) + cash + fee, 100)
        self.assertAlmostEqual(traded, abs(new - np.array([60.0, 40.0])).sum())
        self.assertGreaterEqual(cash, 0.0)
        cov = np.array([[0.004, 0.001], [0.001, 0.0016]])
        a, te = posterior_weight(cov, 1, 1e12)
        np.testing.assert_allclose(a, [0.5, 0.5], atol=1e-10)
        self.assertLess(te, 1e-10)
        for view in [-1, 0, 1]:
            w, te = posterior_weight(cov, view)
            self.assertAlmostEqual(w.sum(), 1)
            self.assertLessEqual(te, 0.02000000001)
            self.assertGreaterEqual(w.min(), 0.0)

    def test_garch_on_contiguous_fixture(self):
        rng = np.random.default_rng(502)
        eps = rng.standard_t(8, 900) * np.sqrt(6 / 8)
        returns = np.zeros(len(eps))
        var = 0.0001
        for j in range(1, len(eps)):
            var = 0.000003 + 0.09 * returns[j - 1] ** 2 + 0.88 * var
            returns[j] = np.sqrt(var) * eps[j]
        v, diagnostics = garch_risk(pd.Series(returns[-756:]), 20)
        self.assertGreater(v, 0)
        self.assertEqual(diagnostics["convergence"], 0)
        self.assertGreater(diagnostics["nu"], 2)
        self.assertTrue(np.isnan(blocks([np.nan, 1, np.nan], 3)).all())

    def test_release(self):
        d = ROOT / "research/experiments/results"
        for name, checksum in json.loads((d / "manifest.json").read_text()).items():
            self.assertEqual(
                hashlib.sha256((d / name).read_bytes()).hexdigest(), checksum
            )
        f = pd.read_parquet(d / "forecasts.parquet")
        r = f[f.phase == "historical replay"]
        macro = r[r.study.isin(["H03", "H04"]) & r.point.notna()]
        self.assertTrue((macro.train_last < macro.origin).all())
        self.assertTrue((macro.end > macro.origin).all())
        g = r[r.arm == "GARCH-t"].sort_values("origin")
        base = r[r.arm == "rolling 63"].sort_values("origin")
        np.testing.assert_allclose(g.deployed_point, base.point, equal_nan=True)
        self.assertEqual(g.point.count(), 0)
        self.assertEqual(len(g), 82)
        gate = pd.read_parquet(d / "stock_eligibility.parquet")
        self.assertFalse(gate.input_ready.any())
        b = pd.read_parquet(d / "black_litterman.parquet")
        self.assertTrue(b[b.view_direction == 0].target_aapl.eq(0.5).all())
        self.assertLessEqual(b.achieved_te.max(), 0.0200000001)
        a = pd.read_parquet(d / "allocations.parquet")
        h = a.query("study=='H07' and phase=='historical replay' and cost_bp==10")
        self.assertTrue(h.groupby("arm").withdrawal.sum().eq(15000).all())
        self.assertTrue(h.reserve.ge(0).all())


if __name__ == "__main__":
    unittest.main()
