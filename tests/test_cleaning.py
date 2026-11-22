import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from cleaning.availability import eligible_session, exact_vintage_price
from cleaning.markets import cash_accrual, schedule
from cleaning.samples import fill_action
from cleaning.timing import asof, next_session_open


class PointInTime(unittest.TestCase):
    def test_later_release_and_revision_leave_earlier_signal_and_weight_unchanged(self):
        times = pd.to_datetime(["2024-07-03 17:00", "2024-07-05 20:00"], utc=True)
        decisions = pd.DataFrame({"decision_at": times})
        history = pd.DataFrame(
            {
                "available_at": pd.to_datetime(["2024-07-02 14:00"], utc=True),
                "value": [1.0],
            }
        )
        changes = pd.DataFrame(
            {
                "available_at": pd.to_datetime(
                    ["2024-07-03 17:01", "2024-07-05 20:00"], utc=True
                ),
                "value": [-1.0, 2.0],
            }
        )
        before = asof(decisions, history)
        after = asof(decisions, pd.concat([history, changes]))
        self.assertEqual(after.value.tolist(), [1.0, -1.0])
        weight = lambda signal: 0.6 if signal > 0 else 0.4
        self.assertEqual(weight(before.value.iloc[0]), weight(after.value.iloc[0]))
        cal = schedule("XNAS")
        self.assertEqual(cal.close.loc["2024-07-03"], times[0])
        self.assertEqual(
            next_session_open(["2024-07-03"], cal)[0], pd.Timestamp("2024-07-05 13:30Z")
        )
        self.assertEqual(cal.open.loc["2024-12-02"].hour, 14)

    def test_future_split_and_corrected_quote_do_not_change_historical_units(self):
        session = pd.Timestamp("2024-07-02")
        times = pd.to_datetime(["2024-07-02 20:01", "2024-07-10 20:01"], utc=True)
        decisions = pd.DataFrame(
            {"asset": "FICT", "session": session, "decision_at": times}
        )
        quotes = pd.DataFrame(
            {
                "asset": "FICT",
                "session": session,
                "known_at": times - pd.Timedelta(seconds=30),
                "price": [100.0, 50.0],
            }
        )
        original = exact_vintage_price(decisions, quotes.iloc[:1])
        changed = exact_vintage_price(decisions, quotes)
        self.assertEqual((changed.price > 75).tolist(), [True, False])
        self.assertEqual((1000 // changed.price).tolist(), [10.0, 20.0])
        self.assertEqual(original.price.iloc[0], changed.price.iloc[0])
        missing = exact_vintage_price(decisions, quotes.iloc[1:])
        self.assertTrue(pd.isna(missing.price.iloc[0]))

    def test_missing_quote_defers_and_does_not_spend_cash(self):
        dates = pd.date_range("2024-01-02", periods=3)
        prices = pd.DataFrame(
            {"A": [100.0, 101.0, 102.0], "B": [None, 20.0, 20.0]}, index=dates
        )
        fx = pd.Series([0.9, None, 0.91], index=dates)
        self.assertIn("hold", fill_action(prices.iloc[0].min(skipna=False), fx.iloc[0]))
        self.assertEqual(eligible_session(prices, fx), dates[-1])
        self.assertTrue(pd.isna(eligible_session(prices.iloc[:2], fx)))

    def test_currency_and_discount_bill_identities(self):
        usd_chf = [0.90, 0.882]
        foreign_quote = [1 / x for x in usd_chf]
        gross = 1.05 * usd_chf[1] / usd_chf[0]
        self.assertAlmostEqual(gross - 1, 0.029)
        self.assertAlmostEqual(1.05 * foreign_quote[0] / foreign_quote[1], gross)
        rate = cash_accrual(pd.Series([4.0]), pd.Series([91])).iloc[0]
        self.assertAlmostEqual(rate, 1 / (1 - 0.04 * 91 / 360) - 1)


if __name__ == "__main__":
    unittest.main()
