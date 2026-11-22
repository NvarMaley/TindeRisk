import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.execution.run import intent, fill, replay


class Execution(unittest.TestCase):
    def test_buy_sale_and_cost(self):
        u = np.array([0.0, 2.0])
        q = np.array([110.0, 25.0])
        c = 100
        new, cash, s, n = fill(u, c, np.array([1.0, -2.0]), q, 0.001)
        self.assertAlmostEqual(cash, 100 + 50 - 110 - 0.16)
        self.assertAlmostEqual(new @ q + cash, 150 - 0.16)
        self.assertAlmostEqual(cash, 100 + 2 * (25 * 0.999) - (110 * 1.001))
        np.testing.assert_allclose(intent(u, 100, q, [0.0, 1 / 3]), 0)

    def test_no_future_fill_and_miss(self):
        ix = pd.bdate_range("2020-01-01", periods=8)

        def case(level, name):
            usd = np.full((8, 3), 100.0)
            usd[1:] = level
            return replay(
                ix,
                usd,
                np.ones(8),
                np.ones((8, 3)) * 1e9,
                np.array([0.5, 0, 0]),
                np.eye(3) * 0.01,
                np.zeros(3),
                ix[0] - pd.Timedelta(days=1),
                "fixture",
                "hold",
                name,
            )

        e, m, s = case(120, "zero fee")
        self.assertEqual(m[1]["wealth"], 50000)
        self.assertEqual(
            e[0]["intended_units"], case(80, "zero fee")[0][0]["intended_units"]
        )
        e, m, s = case(120, "miss opening")
        self.assertEqual(e[0]["status"], "expired")
        self.assertEqual(s["net_household_return"], 0)
        self.assertEqual(m[-1]["wealth"], 35000)


if __name__ == "__main__":
    unittest.main()
