import unittest
from importlib.util import find_spec
from types import SimpleNamespace


@unittest.skipUnless(
    all(find_spec(x) for x in ("exchange_calendars", "duckdb", "openpyxl")),
    "Catalog dependencies required",
)
class ExtensionTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        import pandas as pd
        from riskmatch_v2.equity_extension.build import ANCHOR, inspect_link

        self.inspect = inspect_link
        self.row = SimpleNamespace(price=100.0, issuer="EXAMPLE INDUSTRIES CORP")
        self.days = pd.bdate_range(end=ANCHOR, periods=32)
        self.returns = pd.Series(np.tile([0.01, -0.01], 16), index=self.days)
        self.prices = pd.DataFrame(dict(close=100.0, usd=self.returns), index=self.days)
        self.meta = dict(symbol="EXA", longName="Example Industries, Inc.")

    def evaluate(self, ids=(), events=()):
        return self.inspect(
            self.row, "EXA", self.meta, self.prices, events, self.returns, set(ids)
        )

    def test_overlap_and_class(self):
        self.assertEqual(self.evaluate(), "ok")
        self.assertNotEqual(self.evaluate(["EXA-B"]), "ok")
        self.prices["usd"] = -self.returns
        self.assertNotEqual(self.evaluate(), "ok")

    def test_split_and_renamed_issuer(self):
        self.prices["close"] = 50.0
        self.assertNotEqual(self.evaluate(), "ok")
        action = dict(kind="splits", day="2026-01-09", numerator=2, denominator=1)
        self.assertEqual(self.evaluate(events=[action]), "ok")
        self.meta["longName"] = "Independent name"
        self.assertNotEqual(self.evaluate(events=[action]), "ok")
        self.assertEqual(self.evaluate(["EXA"], [action]), "ok")

    def test_missing_and_redirect(self):
        self.prices.loc[self.days[:25], "usd"] = float("nan")
        self.assertNotEqual(self.evaluate(), "ok")
        self.meta["symbol"] = "OTHER"
        self.assertEqual(self.evaluate(), "re-directed symbol")
