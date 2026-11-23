import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from riskmatch_v2.market_import import build, monthly_returns, read_fx


class TestMarketImport(unittest.TestCase):
    def test_chf_conversion_and_incomplete_month(self):
        jan, feb, mar = map(date.fromisoformat, ["2025-01-31", "2025-02-28", "2025-03-03"])
        values = monthly_returns({jan: 100, feb: 110, mar: 115}, {jan: 0.90, feb: 0.81, mar: 1})
        self.assertEqual(list(values), [feb])
        self.assertAlmostEqual(values[feb], -0.01)

    def test_no_stale_fx_or_multi_month_returns(self):
        dates = list(map(date.fromisoformat, ["2024-12-31", "2025-01-31", "2025-02-28",
                                              "2025-04-30", "2025-05-30", "2025-06-02"]))
        prices = dict.fromkeys(dates, 100)
        rates = dict.fromkeys(dates, 0.90)
        rates[dates[1]] = None
        self.assertEqual(monthly_returns(prices, rates), {dates[4]: 0.0})

    def test_invalid_fx_structure(self):
        for raw in [b"date,DEXSZUS\n", b"observation_date,DEXSZUS\n2025-01-31,1\n2025-01-31,1\n"]:
            with self.assertRaises(ValueError):
                read_fx(raw)

    def test_unapproved_revision_rejected(self):
        with TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "fx.csv").write_bytes(b"revision")
            lock = {"sources": [{"series": "DEXSZUS", "file": "fx.csv", "sha256": "0" * 64}]}
            with self.assertRaisesRegex(ValueError, "Checksum"):
                build(lock, raw)
