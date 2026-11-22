"""Independent checks for section 6.2 scoring, timing, spending and choice."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.options.model import (
    ASSETS,
    CAPITAL,
    RESERVE,
    comparison,
    eligible,
    flat_adjustments,
    monthly_levels,
    reverse,
    simulate,
    year_blocks,
)
from research.options.run import HERE, PROFILE, first_month_range


class ClientOptions(unittest.TestCase):
    def test_annual_scores_and_transfer(self):
        p = {"status": "bounded", "low": 2, "high": 5}
        self.assertEqual(comparison(0.02, 0.01, p)["crossover"], 4)
        self.assertEqual(comparison(0, 0, p)["result"], "numerical tie")
        self.assertEqual(comparison(0.01, 0.01, p)["result"], "tie at endpoint")
        self.assertEqual(
            comparison(0.02, 0.01, dict(p, high=None))["result"], "unresolved"
        )
        self.assertEqual(
            comparison(0.02, 0.01, dict(p, status="conflict"))["result"], "unresolved"
        )
        result = comparison(0.7 * 0.02, 0.7**2 * 0.01, p)
        self.assertEqual(result["result"], "first throughout")
        sleeve = comparison(0.02, 0.01, dict(p, low=1.4, high=3.5))
        self.assertAlmostEqual(result["left"], 0.7 * sleeve["left"])
        self.assertAlmostEqual(result["right"], 0.7 * sleeve["right"])
        self.assertAlmostEqual(PROFILE["low"], 8 / 3)
        self.assertAlmostEqual(PROFILE["high"], 40 / 9)

    def test_hard_limits_precede_any_goal(self):
        frame = pd.read_csv(ROOT / "research/frontier/results/latest.csv").query(
            "cap==.08"
        )
        r = frame[frame.arm == "robust"].copy()
        self.assertEqual(len(eligible(r, 0.08)), 1)
        for k, v in [
            ("reserve_chf", 0),
            ("w0", 0.8),
            ("vol", 0.09),
            ("fee", 0),
            ("status", "infeasible"),
            ("cash", -0.1),
        ]:
            bad = r.copy()
            bad[k] = v
            bad["desired"] = 10
            self.assertTrue(eligible(bad, 0.08).empty)
        self.assertTrue(eligible(r, 0.04).empty)

    def test_joint_fx_and_missing_blocks(self):
        dates = pd.bdate_range("2020-01-01", "2022-12-31")
        frame = pd.concat(
            [
                pd.DataFrame(
                    {
                        "session": dates,
                        "asset": a,
                        "adjusted_usd": 10.0,
                        "chf_per_usd": 1.0,
                    }
                )
                for a in ASSETS
            ]
        )
        frame.loc[frame.session >= "2021-01-01", "chf_per_usd"] = 1.1
        frame.loc[
            (frame.asset == "SPY") & (frame.session >= "2021-01-01"), "adjusted_usd"
        ] = 12.0
        _, _, g = monthly_levels(frame)
        self.assertAlmostEqual(g.loc["2021-01", "SPY"] * g.loc["2021-01", "FX"], 1.32)
        g.loc["2021-05", "FX"] = np.nan
        block, picks, starts = year_blocks(g, n=12, years=2)
        for i in starts:
            self.assertTrue(g.iloc[i : i + 12].notna().all().all())
        p = picks[0, 0]
        direct = g.iloc[p : p + 12]
        np.testing.assert_allclose(
            block[0, 0], direct[ASSETS].mul(direct.FX, axis=0).prod()
        )

    def test_range_ignores_future(self):
        ix = pd.period_range("2019-01", periods=50, freq="M")
        g = pd.DataFrame(1.01, index=ix, columns=[*ASSETS, "FX"])
        origin = pd.Timestamp("2022-04-29")
        w = np.array([0.2, 0.3, 0])
        q, n = first_month_range(g, origin, w, 0.0005)
        g.loc["2022-04":] = 25
        np.testing.assert_allclose(first_month_range(g, origin, w, 0.0005)[0], q)
        np.testing.assert_allclose(q, (0.5 * (1.01**2 - 1) - 0.0005) * 0.7)
        self.assertEqual(n, 36)

    def test_dated_cashflows_and_breakeven(self):
        values = np.ones((1, 2, 3))
        values[0, 0, 0] = 1.2
        w = np.array([0.5, 0.0, 0.0])
        rows = simulate(values, w, 100)
        shares = 17500 * 1.2
        cash = 17500 - 17.5 + 1200
        self.assertAlmostEqual(
            rows[0]["withdrawal_resources"][0], 15000 + cash + shares * 0.999
        )
        next_wealth = cash + shares
        second_fee = 0.001 * abs(shares - 0.5 * next_wealth)
        independently = next_wealth - second_fee + 1200 - 0.001 * 0.5 * next_wealth
        self.assertAlmostEqual(rows[1]["terminal"][0], independently)
        cash_paths = simulate(np.ones((2, 8, 3)), np.zeros(3), 100)
        np.testing.assert_allclose(cash_paths[-1]["terminal"], 44600)
        a = flat_adjustments(np.zeros(3))
        self.assertAlmostEqual(a["monthly_chf_needed"], (65000 * 1.02**8 - 35000) / 96)
        self.assertAlmostEqual(a["affordable_real_target"], 44600 / 1.02**8)

    def test_reverse_stress_equality_and_settlement(self):
        r = reverse(15000, 10000, 22000)
        x = r["loss_boundary"]
        self.assertAlmostEqual(15000 + 10000 * (1 - x) * 0.999, 22000)
        self.assertLess(15000 + 10000 * (1 - x - 1e-5) * 0.999, 22000)
        self.assertEqual(reverse(15000, 10000, 22000, False)["initial_shortfall"], 7000)
        self.assertEqual(reverse(15000, 0, 15000)["status"], "exact throughout")
        self.assertEqual(reverse(15000, 10000, 15000)["loss_boundary"], 1)
        self.assertEqual(
            reverse(15100, 10000, 15000)["status"], "no reachable shortfall"
        )

    def test_release_and_denominators(self):
        d = HERE / "results"
        for k, v in json.loads((d / "manifest.json").read_text()).items():
            self.assertEqual(hashlib.sha256((d / k).read_bytes()).hexdigest(), v)
        cards = pd.read_csv(d / "options.csv")
        self.assertEqual(len(cards), 16)
        self.assertTrue(cards.query("arm=='cash'").sharpe.isna().all())
        np.testing.assert_allclose(
            cards.SPY_chf
            + cards.IEF_chf
            + cards.GLD_chf
            + cards.available_sleeve_cash
            + cards.entry_fee_chf
            + RESERVE,
            CAPITAL,
        )
        self.assertEqual(len(pd.read_csv(d / "pairwise.csv")), 2 * 2 * 28)
        g = pd.read_csv(d / "goal_scenarios.csv")
        np.testing.assert_allclose(
            g.mean_gap_chf, g.gap_frequency * g.mean_gap_when_short_chf, atol=1e-7
        )
        self.assertEqual(g.paths.unique().tolist(), [2000])
        self.assertTrue(cards.coverage_count.eq(7).all())


if __name__ == "__main__":
    unittest.main()
