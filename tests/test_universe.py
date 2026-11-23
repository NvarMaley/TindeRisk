import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from riskmatch.demo import allocations, mandate
from riskmatch.monitor import create, advance, history, snapshot
from riskmatch.reviews import prepare, revise, respond, shadows
from riskmatch.universe import ASSETS
from research.universe.comparison import compare


class Universe(unittest.TestCase):
    def test_registered_holdings_and_execution(self):
        d = ROOT / "research/universe/results"
        latest = pd.read_csv(d / "frontier/latest.csv")
        fitted = json.loads((d / "frontier/training.json").read_text())
        self.assertEqual(np.array(fitted[-1]["covariance"]).shape, (13, 13))
        self.assertTrue(all(r["last"] < r["origin"] for r in fitted))
        holdings = latest[[a + "_chf" for a in ASSETS]].sum(axis=1)
        np.testing.assert_allclose(
            holdings + latest.sleeve_cash_chf + latest.fee_chf, 35000, atol=0.01
        )
        r = latest.query("arm=='robust' and cap==.08").iloc[0]
        self.assertGreater(r.XLU_chf, 100)
        c = pd.read_csv(d / "execution/cohorts.csv")
        self.assertEqual(len(c), 462)
        self.assertEqual(c.shortfall.max(), 0)
        x = compare(d / "execution/cohorts.csv")
        np.testing.assert_allclose(
            x.gain, pd.read_csv(d / "client_value.csv").gain, atol=1e-10
        )

    def test_last_etf_reaches_monitor_and_review(self):
        w = [0.0] * 13
        w[-1] = 0.35
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.db"
            t = create(w, 0.08, "last ETF", True, path)
            s, _ = history(t, path)
            self.assertEqual(s["assets"][-1], "XLU")
            self.assertAlmostEqual(snapshot(s)["wealth"], 50000 - 12.25)
            advance(t, 0, path)
            revise(t, 1, 45000, "2026-11-30", 0.08, path)
            r = prepare(t, path=path)
            self.assertEqual(r["status"], "proposal")
            self.assertEqual(respond(t, r["review_id"], "accept", path), "accept")
            advance(t, 1, path)
            self.assertEqual(prepare(t, path=path)["status"], "suspended")
            advance(t, 2, path)
            self.assertTrue(shadows(history(t, path)[1]))
        for w, _, _ in allocations(0.08, ["XLU"]).values():
            self.assertEqual(w[-1], 0)

    def test_actual_intake_allocation(self):
        app = AppTest.from_file(
            str(ROOT / "app/pages/1_Portfolio_options.py"), default_timeout=25
        )
        d = mandate()
        d.update(capital="75000", exclusions="GLD, XLK")
        app.session_state["mandate"] = d
        app.run()
        app.checkbox(key="use_intake_allocation").set_value(True).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("60,000.00" in x.value for x in app.markdown))
        rows = app.table[0].value.set_index("ETF")
        self.assertEqual(len(rows), 13)
        self.assertTrue((rows.loc[["GLD", "XLK"], "Allocation CHF"] == 0).all())
        app.multiselect[0].set_value(["XLE"]).run()
        self.assertEqual(
            app.table[0].value.set_index("ETF").loc["XLE", "Allocation CHF"], 0
        )


if __name__ == "__main__":
    unittest.main()
