"""Card answers must reach the portfolio engine through explicit, versioned consent."""

import unittest
from pathlib import Path

from riskmatch_v2.matching.mandate import MARKET_DAY, example_profile, mandate, restore
from riskmatch_v2.risk_review import request


class ConfirmedMandateTests(unittest.TestCase):
    def setUp(self):
        self.iv = example_profile(Path(__file__).resolve().parents[1])
        self.choice = request("cap", "investment sleeve", ceiling_pct=12)

    def approve(self):
        self.iv.confirm()
        self.iv.save_risk(self.choice, accept=True, bills="yes", comfort="yes")
        return mandate(self.iv, MARKET_DAY)

    def test_profile_requires_two_confirmations_and_round_trips(self):
        with self.assertRaises(ValueError):
            mandate(self.iv, MARKET_DAY)
        self.iv.confirm()
        with self.assertRaises(ValueError):
            mandate(self.iv, MARKET_DAY)
        result = self.approve()
        self.assertEqual(result["blocked_reason"], "")
        self.assertEqual(result["capital_chf"], 35000)
        self.assertEqual(result["reserve_at_goal_chf"], 0)
        self.assertEqual(result["goal_chf"], 50000)
        self.assertEqual(result["high"], 0.12)
        self.assertEqual(mandate(restore(self.iv.versions), MARKET_DAY), result)

    def test_edited_reserve_needs_new_consent_and_cash_reconciliation(self):
        old = self.approve()
        self.iv.record(
            "F03", [self.iv.answers["F03"][0] | {"low": 20000, "high": 20000}]
        )
        with self.assertRaises(ValueError):
            mandate(self.iv, MARKET_DAY)
        revised = self.approve()
        self.assertEqual(revised["capital_chf"], 30000)
        self.assertIn(
            "funded sleeve",
            mandate(self.iv, MARKET_DAY, old["capital_chf"])["blocked_reason"],
        )

    def test_unknown_exclusion_suspends_matching(self):
        self.iv.record("P07", "skip")
        self.assertIn("P07", self.approve()["blocked_reason"])
