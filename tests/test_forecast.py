import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from riskmatch_v2.forecast.coverage import incremental
from riskmatch_v2.forecast.evaluation import block_ci, funded
from riskmatch_v2.forecast.models import black_litterman, matured, ridge
from riskmatch_v2.forecast.overheating import statistics
from riskmatch_v2.forecast.registry import controlled_estimate
from riskmatch_v2.forecast.sources import asof
from riskmatch_v2.options.scoring import FAMILIES, rank


class ForecastTests(unittest.TestCase):
    def test_late_and_expired_releases(self):
        source = pd.Series([2.0, 9.0], index=["2022-05-04T21:05Z", "2022-05-06T21:05Z"])
        got = asof(
            source, ["2022-05-04T20:00Z", "2022-05-06T20:00Z", "2022-06-10T00:00Z"], 4
        )
        np.testing.assert_allclose(got, [np.nan, 2.0, np.nan], equal_nan=True)

    def test_purge_includes_embargo_and_split(self):
        t = pd.DataFrame(
            {"end": pd.to_datetime(["2020-12-30", "2021-01-03", "2021-01-04"])},
            index=pd.to_datetime(["2020-12-01", "2020-12-20", "2021-01-01"]),
        )
        self.assertEqual(
            list(matured(t, pd.Timestamp("2021-01-04"), "2021-01-01").index),
            list(t.index[:1]),
        )

    def test_zero_view_and_constant_bootstrap(self):
        self.assertEqual(black_litterman(0.01, 0.8, 0.1, np.inf), 0.01)
        self.assertEqual(
            block_ci(np.ones(20), {"bootstrap": {"seed": 1, "draws": 100, "block": 3}}),
            [1.0, 1.0],
        )

    def test_funded_cost_on_entry_and_exit_only(self):
        days = pd.date_range("2020-01-01", periods=4)
        t = pd.DataFrame(
            {"end": days[1:], "hist": [0.00001] * 3, "model": [0.02] * 3},
            index=days[:-1],
        )
        z = funded(t, "model", "return", pd.Series(0.0, index=days))
        self.assertAlmostEqual(z["terminal_chf"] + z["fees_chf"], 35000.0)
        self.assertAlmostEqual(z["fees_chf"], 42.0, delta=0.05)
        self.assertEqual(z["frequency"], 0.0)

    def test_inventory_ridge_matches_train_only_single_security(self):
        rng = np.random.default_rng(45)
        days = pd.date_range("2019-01-01", periods=40)
        x = rng.normal(size=40)
        x[4] = np.nan
        base = np.full(40, 0.01)
        y = 0.02 + 0.01 * rng.normal(size=40)
        inputs = pd.DataFrame(
            {"x": x, "baseline": base, "return": y, "end": days + pd.Timedelta(days=1)},
            index=days,
        )
        cfg = {"min_train": 24, "ridge_alpha": 10, "final_start": "2019-01-31"}
        predicted = incremental(
            x[:, None],
            y[:, None],
            base[:, None],
            days.strftime("%Y-%m-%d").to_numpy(),
            inputs.end.dt.strftime("%Y-%m-%d").to_numpy(),
            cfg,
            False,
        )
        for i in [31, 39]:
            train = matured(inputs, days[i], cfg["final_start"])
            self.assertAlmostEqual(
                predicted[i, 0], ridge(train, inputs.iloc[i], ["x"], "return", True, 10)
            )

    def test_adf_against_direct_ols(self):
        price = np.cumsum(np.random.default_rng(117).normal(size=32))

        def adf(a):
            x = np.c_[np.ones(len(a) - 1), a[:-1]]
            y = np.diff(a)
            b = np.linalg.lstsq(x, y, rcond=None)[0]
            return b[1] / np.sqrt(
                ((y - x @ b) ** 2).sum() / (len(y) - 2) * np.linalg.inv(x.T @ x)[1, 1]
            )

        result = statistics(price[None, :], 16)
        self.assertAlmostEqual(
            result[1][0],
            max(adf(price[i:j]) for j in range(16, 33) for i in range(j - 15)),
        )
        self.assertAlmostEqual(result[2][0], max(adf(price[i:]) for i in range(17)))

    def test_versioned_ranking_refuses_spoof_and_withdrawal(self):
        cfg = json.loads(Path("config/options-6.json").read_text())
        signals = {
            k: {
                "validated": True,
                "target": "CHF return",
                "months": 12,
                "value": 99,
                "evidence": "injected",
                "version": 1,
            }
            for k in FAMILIES
        }
        card = {
            "valid": True,
            "tradable": True,
            "net": 0.07,
            "loss": 0.1,
            "hhi": 0.3,
            "fee": 0.001,
            "cagr": 0.06,
            "drawdown": -0.12,
            "signals": signals,
        }

        def coverage(records):
            return rank({"A": card}, cfg["profiles"]["Goal"], cfg, registry=records)[
                "coverage"
            ]

        entries = [
            {
                "name": k,
                "scope": "A",
                "target": "CHF return",
                "horizon": "12 months",
                "issued": "2026-10-01",
                "expires": "2026-10-31",
                "weight": 0.25,
                "status": "approved",
                "version": 1,
                "score_100": 99,
            }
            for k in FAMILIES
        ]
        self.assertEqual(coverage([]), 90)
        self.assertEqual(coverage(entries), 100)
        self.assertEqual(coverage([dict(x, score_100=1) for x in entries]), 90)
        self.assertEqual(coverage([dict(x, expires="2026-10-29") for x in entries]), 90)
        self.assertEqual(
            coverage(
                entries
                + [dict(entries[0], version=2, issued="2026-10-02", status="withdrawn")]
            ),
            90,
        )
        self.assertEqual(
            controlled_estimate(
                entries, "2026-10-30", "A", "variance", 21, {"macro": 999}, 0.01
            ),
            (0.01, {}),
        )
