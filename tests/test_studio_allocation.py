"""Regression checks for full-universe custom matches and simulated ledger transitions."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from riskmatch_v2.matching.ledger import Ledger
from riskmatch_v2.studio_allocation import (
    DAYS,
    FEE,
    _data,
    blend,
    candidates,
    compare_goal,
    quotes,
)


class StudioAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = {
            "capital_chf": 35000,
            "reserve_chf": 5000,
            "goal_date": "2031-10-30",
            "goal_chf": 48000,
            "target_return": 0.05,
            "low": 0.06,
            "high": 0.12,
        }
        cls.cards = {c["id"]: c for c in candidates(cls.policy)}
        cls.d = _data()

    def test_full_model_lots_risk_and_dated_signals(self):
        self.assertEqual(len(self.d["index"]), 3322)
        self.assertEqual(
            set(self.cards),
            {"return", "robust", "defensive", "diversified", "reference"},
        )
        for card in self.cards.values():
            self.assertTrue(card["valid"], card["reason"])
            self.assertTrue(
                all(type(n) is int and n > 0 for n in card["targets"].values())
            )
            self.assertEqual(card["eligible"], 3322)
            self.assertAlmostEqual(sum(card["weights"].values()), 1)
            marks = quotes(DAYS[0], card["targets"])
            amount = np.zeros(card["universe"])
            for k, n in card["targets"].items():
                amount[self.d["index"][k]] = n * marks[k]["price"] * marks[k]["fx"]
            self.assertAlmostEqual(amount.sum() * FEE, card["fee_chf"])
            self.assertAlmostEqual(
                amount.sum() + card["cash_chf"] + card["fee_chf"], 35000
            )
            w = amount / (35000 - card["fee_chf"])
            factor = w @ self.d["factor_roots"][0]
            variance = factor @ factor + np.sum((w * self.d["specific_risk"][0]) ** 2)
            self.assertAlmostEqual(variance**0.5, card["vol"])
            self.assertLessEqual(card["vol"], self.policy["high"])
            self.assertGreaterEqual(card["vol"], self.policy["low"])
            self.assertEqual(len(card["signals"]), 5)
            self.assertTrue(all(s["measured_at"] == DAYS[0] for s in card["signals"]))
            self.assertTrue(all(s["weight"] == 0 for s in card["signals"]))
        self.assertGreater(
            self.cards["diversified"]["positions"], self.cards["reference"]["positions"]
        )

    def test_goal_comparison_keeps_the_illustration_out_of_matching(self):
        policy = self.policy | {
            "goal_chf": 130000,
            "low": 0,
            "high": 0.04,
            "loss_capacity_chf": 1000,
        }
        plans = candidates(policy)
        result = compare_goal(policy, plans)
        self.assertEqual(result["desired"], 0.05)
        self.assertGreater(result["required"], result["desired"])
        self.assertGreaterEqual(result["scenario"]["goal_value_chf"], 130000)
        self.assertGreater(result["scenario"]["vol"], policy["high"])
        self.assertGreater(
            result["scenario"]["tested_loss_chf"], policy["loss_capacity_chf"]
        )
        self.assertLessEqual(result["compatible"]["vol"], policy["high"])
        self.assertGreater(result["compatible"]["goal_gap_chf"], 0)
        self.assertIsNone(compare_goal(policy | {"goal_chf": 1e9}, plans)["scenario"])
        with self.assertRaisesRegex(ValueError, "unavailable"):
            blend(policy, ["goal_scenario"])

    def test_issuer_and_measured_intensity_screens(self):
        strict = candidates(
            self.policy | {"exclude_chevron": True, "exclusions": ["AAPL"]}
        )
        self.assertFalse(next(c for c in strict if c["id"] == "reference")["valid"])
        for card in strict:
            self.assertLess(card["eligible"], 3322)
            for symbol in card["targets"]:
                self.assertNotEqual(symbol, "AAPL")
                forbidden, unknown = self.d["carbon"][self.d["index"][symbol], :2]
                self.assertLessEqual(max(forbidden, unknown), 1e-9)
        green = next(
            c
            for c in candidates(self.policy | {"prefer_lower_emissions": True})
            if c["id"] == "carbon"
        )
        self.assertTrue(green["valid"])
        self.assertGreater(green["esg"]["coverage"], 0.0)
        for symbol in green["targets"]:
            self.assertGreaterEqual(
                self.d["carbon"][self.d["index"][symbol], 2], 0.99999
            )
        self.assertTrue(
            all(
                not c["valid"]
                for c in candidates(self.policy | {"exclusions": ["FAKE-TICKER"]})
            )
        )

    def test_capacity_reserve_horizon_and_goal(self):
        constrained = candidates(self.policy | {"loss_capacity_chf": 2000})
        self.assertTrue(any(c["valid"] for c in constrained))
        self.assertFalse(
            next(c for c in constrained if c["id"] == "reference")["valid"]
        )
        self.assertTrue(
            all(c["tested_loss_chf"] <= 2000.01 for c in constrained if c["valid"])
        )
        cash = candidates(self.policy | {"mode": "minimum", "low": 0, "high": 0})[0]
        self.assertEqual(cash["goal_value_chf"], 40000)
        self.assertEqual(cash["goal_gap_chf"], 8000)
        self.assertEqual(cash["targets"], {})
        short = candidates(
            self.policy
            | {"goal_date": "2027-10-30", "mode": "minimum", "low": 0, "high": 0}
        )[0]
        self.assertGreater(short["goal_required"], cash["goal_required"])
        self.assertTrue(
            all(
                not c["valid"]
                for c in candidates(
                    self.policy
                    | {"low": 1.0, "high": 1.2, "allowed_classes": ["Direct Treasury"]}
                )
            )
        )

    def test_combination_checks_sum_and_optimises_among_checked_weights(self):
        keys = ["return", "defensive"]
        for bad in ([], [0.8, 0.4], [-0.1, 1.1], [np.nan, 0.4], {"x": 1.0}):
            with self.assertRaises(ValueError):
                blend(self.policy, keys, bad)
        with self.assertRaises(ValueError):
            blend(self.policy, ["return"], [np.nan])
        fixed = blend(self.policy, keys, [0.4, 0.6])
        self.assertTrue(fixed["valid"])
        self.assertEqual(fixed["parts"], {"return": 0.4, "defensive": 0.6})
        self.assertNotEqual(fixed["targets"], self.cards["return"]["targets"])
        best = blend(self.policy, keys)
        self.assertTrue(best["valid"])
        ratios = []
        for tenth in range(1, 10):
            p = blend(self.policy, keys, [tenth / 10, 1 - tenth / 10])
            if p["valid"]:
                ratios.append(p["net"] / p["vol"])
        self.assertAlmostEqual(best["net"] / best["vol"], max(ratios))

    def test_revision_uses_ledger_units_cash_marks_and_trade_fees(self):
        with TemporaryDirectory() as tmp:
            book = Ledger.create(Path(tmp))
            book.save_mandate(self.policy)
            book.flow(DAYS[0], self.policy["capital_chf"], "opening")
            first = self.cards["reference"]
            book.mark(DAYS[0], quotes(DAYS[0], first["targets"]))
            draft = book.propose(DAYS[0], first["targets"], first["parts"])
            book.confirm(draft, DAYS[0])
            self.assertAlmostEqual(
                sum(t["fee"] for t in book.export()["trades"]), first["fee_chf"]
            )
            book.mark(DAYS[1], quotes(DAYS[1], first["targets"]))
            book.flow(DAYS[1], 1500, "deposit")
            a = book.account(DAYS[1])
            policy = self.policy | {"account": a}
            next_plan = blend(policy, ["return", "defensive"], [0.5, 0.5])
            self.assertTrue(next_plan["valid"])
            self.assertEqual(next_plan["date"], DAYS[1])
            self.assertAlmostEqual(next_plan["capital_chf"], a["value"])
            symbols = set(next_plan["targets"]) | set(first["targets"])
            book.mark(DAYS[1], quotes(DAYS[1], symbols))
            draft = book.propose(DAYS[1], next_plan["targets"], next_plan["parts"])
            book.confirm(draft, DAYS[1])
            actual = book.account(DAYS[1])
            self.assertEqual(actual["holdings"], next_plan["targets"])
            self.assertAlmostEqual(actual["cash"], next_plan["cash_chf"])
            fees = sum(t["fee"] for t in book.export()["trades"] if t["day"] == DAYS[1])
            self.assertAlmostEqual(fees, next_plan["fee_chf"])


if __name__ == "__main__":
    unittest.main()
