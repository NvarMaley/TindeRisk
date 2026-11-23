import unittest
from importlib.util import find_spec


@unittest.skipUnless(
    find_spec("scipy") and find_spec("pandas"), "Funding study dependencies required"
)
class FundingTests(unittest.TestCase):
    def test_required_rate_real_goal_and_reserve(self):
        from riskmatch_v2.funding import required_return, years

        rate = required_return(
            "2024-01-01",
            "2027-01-01",
            50_000,
            15_000,
            [("2024-06-30", -15_000)],
            50_000,
            inflation=0.02,
        )
        t = years("2024-01-01", "2027-01-01")
        self.assertAlmostEqual(
            rate["rates"][0], (50_000 / 35_000) ** (1 / t) * 1.02 - 1
        )
        self.assertEqual(rate["status"], "unique")
        self.assertEqual(
            required_return("2024-01-01", "2027-01-01", 10, 11, [], 20)["status"],
            "reserve exceeds capital",
        )
        self.assertAlmostEqual(
            required_return("2024-01-01", "2027-01-01", 20, 0, [], 20)["rates"][0], 0
        )

    def test_multiple_tangent_and_absent_roots(self):
        from riskmatch_v2.funding import required_return

        def rates(payment, final):
            return required_return(
                "2021-01-01",
                "2023-01-01",
                100,
                0,
                [("2022-01-01", -payment), ("2023-01-01", final)],
                0,
            )

        self.assertEqual(len(rates(230, 132)["rates"]), 2)
        self.assertEqual(
            rates(200, 100)["status"], "unique root requires interim borrowing"
        )
        self.assertEqual(rates(100, 140)["rates"], [])

    def test_same_day_inflow_cannot_fund_an_earlier_bill_at_the_implied_rate(self):
        from riskmatch_v2.funding import required_return

        result = required_return(
            "2021-01-01",
            "2023-01-01",
            100,
            0,
            [("2022-01-01", -150), ("2022-01-01", 150)],
            100,
        )
        self.assertEqual(result["status"], "unique root requires interim borrowing")

    def test_joint_blocks_never_bridge_gaps(self):
        import numpy as np
        import pandas as pd

        from riskmatch_v2.funding import block_draws

        data = pd.DataFrame(
            {"stock": [0.1, 0.2, 0.3, 0.4], "fund": [0, 0, np.nan, 0]},
            index=["2024-01", "2024-02", "2024-04", "2024-05"],
        )
        starts, draws = block_draws(data, 2, 4, 2000, 42)
        self.assertEqual(starts, [0])
        self.assertEqual(draws.tolist(), [[0, 1, 0, 1]])
        self.assertIsNone(block_draws(data, 3, 4, 2000, 42)[1])

    def test_whole_lot_liquidation_fee_and_no_double_count(self):
        import numpy as np

        from riskmatch_v2.funding import funding_paths, sale_values

        proceeds = sale_values(
            np.array([[0.1], [0.5]]),
            np.array([[0, 1]]),
            np.array([100.0]),
            np.array([0.01]),
        )
        result = funding_paths(proceeds, 0, [120, 0], [0, 50], 30).iloc[0]
        self.assertAlmostEqual(result.first_gap_chf, 11.1)
        self.assertAlmostEqual(result.terminal_chf, 38.9)
        self.assertEqual(result.first_recovery_month, 2)
        self.assertEqual(result.terminal_gap_chf, 0)
        self.assertFalse(result.all_goals_met)

    def test_same_day_bill_precedes_contribution(self):
        import numpy as np

        from riskmatch_v2.funding import funding_paths

        paths = funding_paths(np.zeros((1, 1)), 0, [5000], [7000], 2000)
        self.assertEqual(paths.iloc[0].first_missed_month, 1)
        self.assertEqual(paths.iloc[0].first_recovery_month, 1)
        self.assertEqual(paths.iloc[0].terminal_chf, 2000)
