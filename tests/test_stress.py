import unittest

import numpy as np
import pandas as pd

from riskmatch_v2.stress.events import path_metrics
from riskmatch_v2.stress.exposures import aggregation
from riskmatch_v2.stress.inputs import FACTORS
from riskmatch_v2.stress.scenarios import attribution, price_case


class StressControls(unittest.TestCase):
    def test_recovery_and_censoring(self):
        ret, draw, sessions, status = path_metrics([0.1, -0.2, 0.26], 2)
        self.assertAlmostEqual(ret, -0.12)
        self.assertAlmostEqual(draw, -0.2)
        self.assertEqual((sessions, status), (1, "Recovered"))
        self.assertEqual(
            path_metrics([-0.1, 0.01, np.nan, 0.2], 1)[3], "Censored at data gap"
        )
        self.assertEqual(path_metrics([-0.1, 0.01], 1)[3], "Censored at horizon")
        self.assertEqual(path_metrics([np.nan, 0.2], 1)[3], "Missing event path")

    def test_cash_flow_repricing(self):
        flat = price_case("2026-10-30", "2028-10-31", 4, 100, 4, 4, 0, 0)
        self.assertAlmostEqual(flat["rate_return"], 0)
        up = price_case("2026-10-30", "2028-10-31", 4, 100, 4, 4, 1, 0)
        self.assertAlmostEqual(
            up["rate_return"], -flat["modified_duration"] / 10000, places=6
        )
        slope = price_case("2026-10-30", "2028-10-31", 4, 100, 4, 4, 50, 25)
        parallel = price_case("2026-10-30", "2028-10-31", 4, 100, 4, 4, 50, 0)
        self.assertLess(parallel["rate_return"], slope["rate_return"])

    def test_attribution_keeps_reserve_and_unknown_weight(self):
        est = pd.DataFrame(
            [("A", "local_USD", k, 0.01 if k == "oil" else 0) for k in FACTORS],
            columns=["id", "variant", "factor", "beta"],
        )
        weights = pd.DataFrame(
            [("Test", "A", 0.6), ("Test", "Missing", 0.3)],
            columns=["option", "id", "weight"],
        )
        bonds = pd.DataFrame(columns=["scenario", "id", "rate_return"])
        _, rows = attribution(
            est,
            bonds,
            weights,
            {
                "scenarios": {"Joint": {"oil": 10, "fx": 0.05}},
                "scenario_budget_chf": 1000,
            },
        )
        row = rows[0]
        self.assertAlmostEqual(row["covered_total_pct"], 9.3)
        self.assertAlmostEqual(row["missing_weight"], 0.3)
        self.assertAlmostEqual(row["chf_cash"], 0.1)
        self.assertAlmostEqual(row["known_fx_all_pct"], 4.5)

    def test_common_sample_identity(self):
        rng = np.random.default_rng(30)
        x = pd.DataFrame(rng.normal(size=(260, 5)), columns=FACTORS)
        y = pd.DataFrame(rng.normal(size=(260, 2)), columns=["A", "B"])
        y.loc[60:65, "A"] = np.nan
        weights = pd.DataFrame(
            [("Test", "A", 0.5), ("Test", "B", 0.3)], columns=["option", "id", "weight"]
        )
        result = aggregation(x, y, weights, {"window": 252, "minimum": 200})[0]
        self.assertEqual(result["common"], 246)
        self.assertLess(result["max_corr_error"], 1e-12)
        self.assertLess(result["max_beta_error"], 1e-12)
