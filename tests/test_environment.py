import unittest

import numpy as np
import pandas as pd

from riskmatch_v2.environment.measurement import allocate
from riskmatch_v2.environment.study import (
    decision,
    intensity_comparison,
    profile,
    summarize,
)
from riskmatch_v2.library.controls import exposure


class EnvironmentalMandateTests(unittest.TestCase):
    def test_ownership_conservation_and_invalid_schedules(self):
        facilities = pd.DataFrame(
            {"id": [1, 2, 3, 4, 5], "tonnes": [200.0, 100.0, 100.0, 50.0, 20.0]}
        )
        owners = pd.DataFrame(
            [
                (1, "First", 60),
                (1, "Second", 40),
                (2, "First", 90),
                (3, "Second", 50),
                (3, "Second", 50),
                (4, None, 100),
            ],
            columns=["id", "parent", "share"],
        )
        valid = allocate(facilities, owners)
        self.assertEqual(valid.attributed.tolist(), [120, 80])
        self.assertEqual(set(valid.id), {1})

    def test_dated_indirect_ban_and_unknown(self):
        holdings = pd.DataFrame(
            [
                ("Fund", "2026-10-20", "2026-11-01", "X", 0.4),
                ("Fund", "2026-10-20", "2026-11-01", None, 0.6),
            ],
            columns=["fund", "day", "available", "issuer", "weight"],
        )
        weights = {"Fund": 0.5, "Treasury": 0.5}
        identities = {"Treasury": "US-TREASURY"}
        future = exposure(weights, holdings, identities, "2026-10-30T23:00Z")
        for action, status in [
            ("suspend", "suspended"),
            ("flag and compare", "unverified comparison only"),
            ("ask for clarification", "clarification required"),
        ]:
            self.assertEqual(decision(future, {"X"}, "mandatory", action), status)
        known = exposure(weights, holdings, identities, "2026-11-02T00:00Z")
        row = profile(known, {"X": 50.0}, {"X"})
        self.assertAlmostEqual(row["forbidden"], 0.2)
        self.assertAlmostEqual(row["covered"], 0.2)
        self.assertAlmostEqual(row["unknown_gross"], 0.3)
        self.assertEqual(
            decision(known, {"X"}, "soft", "flag and compare"),
            "preference not satisfied",
        )
        self.assertEqual(
            decision(known, {"X"}, "mandatory", "flag and compare"), "excluded"
        )

    def test_unrated_is_distinct_from_measured_zero_and_cash(self):
        raw = {"issuers": {"X": 1.0}, "unknown_net": 0.0, "unknown_gross": 0.0}

        def result(measures):
            rows = pd.DataFrame([profile(raw, measures, set())])
            return summarize(rows, np.array([0.6]))

        unknown, zero = result({}), result({"X": 0.0})
        self.assertIsNone(unknown["intensity"])
        self.assertEqual(zero["intensity"], 0.0)
        self.assertEqual(zero["covered"], 0.6)
        self.assertEqual(
            intensity_comparison(unknown, zero, 0.1), "No comparable measurement"
        )
        self.assertEqual(intensity_comparison(zero, zero, 0), "Same allocation")
        self.assertEqual(
            intensity_comparison(zero, dict(zero, covered=0.5), 0.1),
            "Partial or unequal coverage",
        )
