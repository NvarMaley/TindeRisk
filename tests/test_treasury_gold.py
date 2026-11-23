import unittest

import pandas as pd

from riskmatch_v2.treasury_gold.access import auction_gate
from riskmatch_v2.treasury_gold.pricing import discounted, remaining, risk, schedule


class TreasuryGoldResearchTests(unittest.TestCase):
    def test_published_reopening_price(self):
        flows = schedule("2023-05-15", "2033-05-15", 3.375)
        rest, f, accrued = remaining(flows, "2023-06-15")
        full, _, _ = discounted((rest.coupon + rest.principal).values, f, 0.03791)
        self.assertAlmostEqual(accrued * 10, 2.84307, places=5)
        self.assertAlmostEqual(full - accrued, 96.583639, places=6)
        self.assertEqual(rest.principal.sum(), 100)
        self.assertEqual(rest.iloc[-1].pay, pd.Timestamp("2033-05-16"))

    def test_zero_coupon_boundary_and_month_end(self):
        flows = schedule("2023-08-31", "2025-08-31", 4.0)
        after, remaining_fraction, accrued = remaining(flows, "2024-02-29")
        self.assertEqual((len(after), remaining_fraction, accrued), (3, 1, 0))
        self.assertEqual(after.due.iloc[0], pd.Timestamp("2024-08-31"))
        self.assertEqual(after.pay.iloc[0], pd.Timestamp("2024-09-03"))
        self.assertEqual(after.pay.iloc[-1], pd.Timestamp("2025-09-02"))
        with self.assertRaises(ValueError):
            remaining(flows, "2025-08-31")

    def test_scenario_returns_and_cash_settlement(self):
        flows = schedule("2023-05-15", "2033-05-15", 3.375)
        cfg = {
            "parallel_bp": 100,
            "spread_bp": 25,
            "fx_change": -0.05,
            "approximation_tolerance_bp_of_price": 5,
        }
        row, cases = risk(flows, "2026-10-30", 92.03125, cfg)
        self.assertGreater(row["dv01_per_100"], 0)
        self.assertGreater(
            cases["Rates down"]["local"], abs(cases["Rates up"]["local"])
        )
        joint = cases["Joint"]
        self.assertAlmostEqual(
            joint["chf"], joint["local"] + joint["fx"] + joint["interaction"]
        )
        self.assertEqual(
            auction_gate(
                1000, 100, 100, 970, [("2023-06-16", 1000)], "2023-06-15", True
            ),
            "Insufficient settled USD",
        )
        self.assertEqual(
            auction_gate(
                1050, 100, 100, 970, [("2023-06-14", 1000)], "2023-06-15", True
            ),
            "Invalid lot",
        )
