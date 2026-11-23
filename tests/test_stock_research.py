import unittest

import numpy as np
import pandas as pd

from riskmatch_v2.stocks.filings import issuer, next_session
from riskmatch_v2.stocks.universe import round_trip, sector_group


class StockResearchControls(unittest.TestCase):
    def test_both_trade_fees_and_cash(self):
        # 10% cash, 90% invested. Costs apply to the actual entry/exit notionals.
        weights = np.array([0.45, 0.45])
        growth = np.array([1.10, 0.90])
        self.assertAlmostEqual(round_trip(growth, weights, 0.001), 0.9982)
        self.assertAlmostEqual(
            round_trip(np.array([1.2]), np.array([0.9]), 0.001),
            0.1 - 0.0009 + 1.08 * 0.999,
        )
        with self.assertRaises(ValueError):
            round_trip(np.array([1.0]), np.array([1.0]), 0.001)

    def test_filing_calendar_uses_later_date(self):
        dates = pd.Index(["2025-11-07", "2025-11-10", "2025-11-11"])
        time = "2025-11-07T21:42:08Z"
        self.assertEqual(next_session(dates, time, "2025-11-07"), "2025-11-10")
        self.assertEqual(next_session(dates, time, "2025-11-10"), "2025-11-11")
        self.assertIsNone(next_session(dates, time, "2025-11-11"))

    def test_identities_and_sectors(self):
        self.assertEqual(issuer("Veritone, Inc."), issuer("VERITONE INC"))
        self.assertNotEqual(issuer("Acme Holdings Inc."), issuer("Acme Inc."))
        sectors = sector_group(pd.Series(["3714", "5099", None, "9999"]))
        self.assertEqual(
            sectors.tolist(),
            ["Manufacturing", "Wholesale", "Unclassified", "Unclassified"],
        )
