import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from riskmatch.monitor import create, advance, history, erase, quote_status, UPDATES


class Ledger(unittest.TestCase):
    def test_revisions_flows_and_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "db"
            token = create([0, 0, 0], 0.08, "cash", True, path)
            for i in range(len(UPDATES) - 1):
                self.assertTrue(advance(token, i, path))
            s, e = history(token, path)
            self.assertEqual(s["index"], 1)
            self.assertEqual(e[-1]["flow"], -15000)
            self.assertEqual(e[-1]["wealth"], 35100)
            self.assertEqual(e[2]["status"], "stale FX")
            self.assertEqual(e[2]["last_reliable"], e[1]["time"])
            self.assertEqual(e[4]["supersedes"], "late-fx")
            self.assertEqual(e[5]["status"], "market closed")
            self.assertFalse(advance(token, 0, path))
            erase(token, path)
            with self.assertRaises(ValueError):
                history(token, path)

    def test_fee_and_fx_decomposition(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "db"
            t = create([0.5, 0, 0], 0.08, "fixture", True, path)
            for i in range(7):
                advance(t, i, path)
            _, e = history(t, path)
            self.assertAlmostEqual(e[0]["wealth"], 50000 - 17.5)
            for a, b in zip(e, e[1:]):
                self.assertAlmostEqual(
                    b["wealth"] - a["wealth"], b["market_pnl"] + b["fx_pnl"] + b["flow"]
                )
            self.assertEqual(
                quote_status(dict(UPDATES[0], close=None)), "missing close"
            )


if __name__ == "__main__":
    unittest.main()
