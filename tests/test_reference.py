from datetime import date
from math import prod
import unittest

from riskmatch_v2.reference import common_windows, compatibility, replay, study


class ReferenceTest(unittest.TestCase):
    def setUp(self):
        self.days = [date(2024, 12, 31), date(2025, 1, 31)]
        self.weights = {"A": 0.6, "B": 0.4}
        self.panel = {"A": dict(zip(self.days, [1.0, -0.5])), "B": dict.fromkeys(self.days, 0.0)}

    def test_drift_and_calendar(self):
        held = replay(self.panel, self.days, self.weights, "hold", 100, 0)
        annual = replay(self.panel, self.days, self.weights, "annual", 100, 0)
        self.assertAlmostEqual(held[1].traded_chf, 0)
        self.assertAlmostEqual(held[1].closing_chf, 100)
        self.assertAlmostEqual(annual[1].traded_chf, 48)
        self.assertAlmostEqual(annual[1].closing_chf, 112)

    def test_two_sided_fees_and_funded_entry(self):
        first, second = replay(self.panel, self.days, self.weights, "annual", 100, 100)
        self.assertAlmostEqual(first.fees_chf, 100 - 100 / 1.01)
        # A is sold and B bought. The two legs differ by the fees paid.
        bought_a = 60 / 1.01
        bought_b = 40 / 1.01
        opening = 2 * bought_a + bought_b
        after_fees = (opening - 0.01 * (2 * bought_a - bought_b)) / (1 - 0.002)
        self.assertAlmostEqual(second.fees_chf, opening - after_fees)
        self.assertAlmostEqual(second.closing_chf, 0.7 * after_fees)
        self.assertAlmostEqual(prod(1 + r.net_return for r in [first, second]), second.closing_chf / 100)

    def test_unshared_dates_restart_from_cash(self):
        last = date(2025, 3, 31)
        self.panel["A"].update({date(2025, 2, 28): 0.2, last: 0.0})
        self.panel["B"][last] = 0.0
        self.assertEqual(common_windows(self.panel, self.weights), [self.days, [last]])
        settings = dict(base_chf=100, cost_bps=10, weights=self.weights, mandates={}, cash_monthly_return=0)
        rows, ledger = study(self.panel, settings)
        self.assertEqual([r["months"] for r in rows], [2, 2, 2, 1, 1, 1])
        self.assertTrue(all(r["opening_chf"] == 100 for r in ledger if r["date"] == str(last)))
        self.assertTrue(all(r["traded_chf"] == r["fees_chf"] == 0 for r in ledger if r["mode"] == "cash"))
        with self.assertRaisesRegex(ValueError, "consecutive"):
            replay(self.panel, self.days + [last], self.weights, "hold", 100, 0)

    def test_mandate_states_do_not_imply_suitability(self):
        m = {"allowed": ["A"], "confirmed": True, "max_volatility": 0.10}
        self.assertEqual(compatibility(m, {"A"}, 0.10)["status"], "compatible with tested criteria")
        self.assertEqual(compatibility(m, {"A"}, 0.11)["status"], "outside mandate")
        self.assertEqual(compatibility(m, {"B"}, 0.01)["status"], "outside mandate")
        self.assertEqual(compatibility(m, {"A"}, None)["status"], "undetermined")
        self.assertEqual(compatibility(m | {"oil_limit": 1}, {"A"}, 0.01)["status"], "undetermined")
        self.assertEqual(compatibility({}, {"A"}, 0.01)["status"], "undetermined")
