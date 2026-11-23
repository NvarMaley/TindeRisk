from importlib.util import find_spec
from types import SimpleNamespace
from unittest import TestCase, skipUnless


@skipUnless(
    all(
        find_spec(m)
        for m in ("numpy", "pandas", "duckdb", "cvxpy", "sklearn", "pyarrow")
    ),
    "Catalogue options and feasibility required",
)
class UniverseTest(TestCase):
    def test_otc_continuation_requires_observed_volume_and_no_unhandled_event(self):
        import json
        import pandas as pd
        from riskmatch_v2.universe.replay_evidence import observed_quotes

        timestamps = [
            int(pd.Timestamp(day, tz="UTC").timestamp())
            for day in ("2017-12-19 21:00", "2017-12-20 21:00")
        ]
        chart = {
            "meta": {
                "symbol": "PFBX",
                "currency": "USD",
                "exchangeName": "OQX",
                "instrumentType": "EQUITY",
            },
            "timestamp": timestamps,
            "indicators": {"quote": [{"close": [12.25, 12.60], "volume": [0, 45000]}]},
        }

        def raw():
            return json.dumps({"chart": {"result": [chart]}})

        self.assertEqual(observed_quotes(raw()).index.tolist(), ["2017-12-20"])
        chart["events"] = {"dividends": {"1": {"date": timestamps[0]}}}
        with self.assertRaisesRegex(ValueError, "Corporate action"):
            observed_quotes(raw())

    def test_coupon_boundary_and_dirty_price(self):
        import pandas as pd

        from riskmatch_v2.universe.treasury import accrual

        days = pd.to_datetime(["2024-08-14", "2024-08-15", "2024-08-16"])
        interest, cash = accrual(days, "2024-02-15", "2034-02-15", 4.0)
        self.assertGreater(interest.iloc[0], 1.98)
        self.assertEqual(interest.iloc[1], 0)
        self.assertAlmostEqual(cash.iloc[1], 2.0)
        self.assertAlmostEqual(interest.iloc[2], 2 / 184)
        self.assertLess(abs((100 + cash.iloc[1]) / (100 + interest.iloc[0]) - 1), 0.001)

    def test_vectorized_factor_risk_matches_existing(self):
        import numpy as np
        import pandas as pd

        from riskmatch_v2.feasibility.inputs import factors
        from riskmatch_v2.universe.model import moments

        rng = np.random.default_rng(42)
        x = rng.normal(0, 0.01, (420, 5))
        x[::8, 3] = np.nan
        cols = ["SPY", "IEF", "GLD", "stock", "bond"]
        df = pd.DataFrame(x, columns=cols)
        names, mu, root, _ = factors(df, cols[:3], 252)
        got, mat, _ = moments(x, x[:, :3])
        np.testing.assert_allclose(got, mu)
        np.testing.assert_allclose(
            (root.T @ root).toarray(), (mat.T @ mat).toarray(), atol=1e-10
        )

    def test_ledger_coupon_and_halt(self):
        import numpy as np
        import pandas as pd

        from riskmatch_v2.universe.replay import run

        days = np.array(
            [
                "2025-01-02",
                "2025-01-03",
                "2025-01-06",
                "2025-01-07",
                "2025-01-08",
                "2025-01-09",
                "2025-01-10",
                "2025-01-13",
                "2025-01-14",
            ]
        )
        price = np.full((len(days), 2), 100.0)
        price[3:, 0] = np.nan
        r = np.zeros_like(price)
        r[3:, 0] = np.nan
        r[2, 1] = 0.02
        coupon = np.zeros((len(days), 1))
        coupon[2, 0] = 2
        panel = SimpleNamespace(
            names=pd.Index(["SPY", "UST:test"]),
            funds=["SPY"],
            stock0=2,
            dindex=pd.Index(days),
            days=days,
            fx=np.ones(len(days)),
            close=price,
            usd=r,
            coupons=coupon,
            exits={},
        )
        out, rows, orders = run(
            panel,
            {days[0]: {"SPY": 0.4, "UST:test": 0.4}},
            {"market": days[-1], "pocket": 1000},
            fee=0,
            capture=True,
        )
        self.assertAlmostEqual(rows.coupon.sum(), 8.0)
        self.assertAlmostEqual(out["final"], 1008.0)
        self.assertIsNone(out["cagr"])
        self.assertEqual(out["unresolved"], ["SPY"])
        self.assertEqual(set(orders.execution), {days[1]})
        self.assertLess(out["max_residual"], 1e-6)

    def test_risk_bound_and_minimum_variance_mix(self):
        import numpy as np

        from riskmatch_v2.feasibility.engine import Problem
        from riskmatch_v2.universe.model import blend_search, broad_frontier

        p = Problem(
            names=("A", "B"),
            mu=[0.1, 0.1],
            root=np.diag([0.2, 0.1]),
            lo=[0, 0],
            hi=[1, 1],
            current=[0, 0],
            fees=[0, 0],
            groups={},
        )
        mix = blend_search([p], np.eye(2), criterion="Minimum risk", low=0, high=0.21)
        np.testing.assert_allclose(mix["parts"], [0.2, 0.8], atol=1e-5)
        result = broad_frontier(p, high=0.05)
        expected = 0.1 * 0.05 / np.sqrt(0.008)
        self.assertEqual(result["status"], "optimal")
        self.assertAlmostEqual(result["candidate"]["net"], expected, places=6)
        self.assertGreaterEqual(result["upper_net"] + 1e-8, expected)
        self.assertLess(result["gap"], 1e-5)
        self.assertEqual(broad_frontier(p, low=0.21, high=0.22)["status"], "impossible")

    def test_terminal_cash_without_month_end_membership(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        import pandas as pd

        from riskmatch_v2.universe.data import cash_exits

        with TemporaryDirectory() as folder:
            root = Path(folder)

            def dates(values):
                return pd.to_datetime(values).date

            end = dates(["2017-11-16"] * 3)
            pd.DataFrame({"permno": [1, 2, 3], "security_end": end}).to_parquet(
                root / "identifiers.parquet"
            )
            pd.DataFrame(
                {
                    "permno": [1, 2, 2, 3],
                    "ex_date": dates(["2017-11-17"] * 4),
                    "payment_date": dates(["2017-11-16"] * 3 + ["2017-12-15"]),
                    "distribution_type": ["CP", "CP", "SD", "CP"],
                    "payment_type": ["USD", "USD", "STK", "USD"],
                    "share_factor": [-1.0, -1.0, 0.5, -1.0],
                    "dividend": [24.25, 2.0, 0.0, 4.0],
                }
            ).to_parquet(root / "stock_events.parquet")
            daily = pd.DataFrame(
                {"permno": [0], "day": dates(["2017-10-01"]), "usd": [0.0]}
            )
            daily.to_parquet(root / "stock_returns.parquet")
            daily.assign(del_flag="N", exit_payment="N/A", return_flag="NA").to_parquet(
                root / "stock_months.parquet"
            )
            panel = SimpleNamespace(
                dindex=pd.Index(["2017-11-17"]),
                names=pd.Index(["PERMNO:1", "PERMNO:2", "PERMNO:3"]),
                register=pd.DataFrame(columns=["exit_cash_usd"]),
            )
            with patch("riskmatch_v2.universe.data.CAT", root):
                self.assertEqual(
                    cash_exits(panel), {"2017-11-17": {"PERMNO:1": ("cash", 24.25)}}
                )
