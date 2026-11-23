import json
import unittest
from pathlib import Path

import numpy as np

from riskmatch_v2.matching.engine import CASH, Market, engine_replay


class MatchEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Market(public_only=True)
        cls.account = {
            "day": cls.m.day,
            "cash": 35000.0,
            "value": 35000.0,
            "holdings": {},
        }
        cls.mandate = {
            "low": 0.0,
            "high": 0.12,
            "goal_date": "2029-10-30",
            "goal_chf": 50000.0,
        }
        cls.parts = {"Return": 0.6, "Diversification": 0.4}

    def test_parameter_pack_reconstructs_archived_section_six(self):
        source = json.loads(Path("reports/univers-complet/resultats.json").read_text())
        self.assertEqual(self.m.universe, 3322)
        for name, w in self.m.options.items():
            if name == CASH:
                continue
            self.assertAlmostEqual(
                self.m._variance(w), source["cards"][name]["variance"], places=8
            )
            self.assertAlmostEqual(
                w @ self.m.mu[:, 0] - 0.001 * w.sum(),
                source["cards"][name]["net"],
                places=8,
            )

    def test_budget_exposure_and_euler(self):
        d = self.m.plan(self.parts, self.mandate, self.account)
        self.assertTrue(d["valid"])
        self.assertTrue(all(int(n) == n and n > 0 for n in d["targets"].values()))
        self.assertAlmostEqual(sum(d["weights"].values()), 1.0)
        self.assertAlmostEqual(sum(d["classes"].values()), 1.0)
        self.assertAlmostEqual(sum(d["euler"].values()), d["vol"])
        self.assertAlmostEqual(sum(d["concentration"].values()), d["hhi"])
        self.assertAlmostEqual(
            sum(p["chf"] for p in d["lines"]) + d["cash_chf"] + d["fee_chf"],
            self.account["value"],
        )
        rho = np.array([list(z.values()) for z in d["correlations"].values()])
        np.testing.assert_allclose(rho, rho.T)
        np.testing.assert_allclose(np.diag(rho), 1.0)

    def test_hard_constraints_and_cap(self):
        for policy in [
            {"blocked_reason": "Unknown issuer coverage"},
            {"mode": "minimum"},
            {"loss_capacity_chf": {"low": 10, "high": 15}},
            {"excluded_ids": ["unresolved"]},
            {"low": 0.35, "high": 0.45},
        ]:
            self.assertFalse(
                self.m.plan(self.parts, self.mandate | policy, self.account)["valid"]
            )
        cash = self.m.plan(
            {CASH: 1.0}, self.mandate | {"mode": "minimum", "high": 0}, self.account
        )
        self.assertTrue(cash["valid"])
        self.assertEqual(cash["vol"], 0)
        lower = self.m.plan(self.parts, self.mandate | {"high": 0.04}, self.account)
        self.assertTrue(lower["valid"])
        self.assertLessEqual(lower["vol"], 0.04)

    def test_goal_expired_since_initial_authorization(self):
        revised = self.mandate | {"goal_date": self.m.day}
        plan = self.m.plan(self.parts, revised, self.account)
        self.assertFalse(plan["valid"])
        self.assertIn("future goal date", plan["reason"])

    def test_stale_restriction_and_bills(self):
        p = self.m.plan(self.parts, self.mandate, self.account)
        s = p["lines"][0]["id"]
        quotes = self.m.quotes(self.m.day)
        quotes[s]["fx_at"] = "2026-10-29T20:00:00+00:00"
        self.assertFalse(
            self.m.plan(self.parts, self.mandate, self.account | {"quotes": quotes})[
                "valid"
            ]
        )
        self.assertFalse(
            self.m.plan(self.parts, self.mandate, self.account | {"settled_cash": 3.0})[
                "valid"
            ]
        )
        early = {
            "date": "2027-10-30",
            "currency": "CHF",
            "direction": "contribution",
            "certainty": "confirmed",
            "low": 5000.0,
            "high": 5000.0,
        }
        late = dict(early, date="2029-10-30")

        def scenario(flow):
            return self.m.plan(
                self.parts,
                self.mandate | {"savings_chf": 5000.0, "flows": [flow]},
                self.account,
            )

        self.assertGreater(
            scenario(early)["goal_value_chf"], scenario(late)["goal_value_chf"]
        )
        self.assertLess(
            scenario(early)["goal_required"], scenario(late)["goal_required"]
        )

    def test_blended_revision_from_changed_holdings(self):
        replay = engine_replay(public_only=True)
        self.assertEqual(replay["held"]["fee_chf"], 0.0)
        self.assertLess(
            replay["revision"]["oil_abs_chf"], replay["held"]["oil_abs_chf"]
        )
        self.assertAlmostEqual(
            replay["after_fee_improvement_chf"],
            replay["oil_shock_improvement_chf"] - replay["revision"]["fee_chf"],
        )
        self.assertEqual(replay["notices"]["quiet"], [])
        self.assertIn(
            "Scheduled withdrawal approaching", replay["notices"]["near_expense"]
        )
        self.assertFalse(replay["outside_band"]["valid"])
        self.assertLess(replay["changed_plans"]["Lower risk cap"]["vol"], 0.06)
        self.assertTrue(all(row["valid"] for row in replay["suggested"].values()))

    def test_optimized_grid_checks_actual_rounded_baskets(self):
        names = list(self.parts)
        exact = []
        for i in range(1, 10):
            parts = dict(zip(names, [i / 10, (10 - i) / 10]))
            p = self.m.plan(parts, self.mandate, self.account)
            exact.append(p["net"] / p["vol"])
        best = self.m.suggest(names, "Sharpe", self.mandate, self.account)
        p = self.m.plan(best, self.mandate, self.account)
        self.assertAlmostEqual(p["net"] / p["vol"], max(exact))
