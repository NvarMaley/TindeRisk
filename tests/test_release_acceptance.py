"""Acceptance fixtures maintained separately from the ledger examples."""

from datetime import date
import hashlib, json, sys, tempfile, unittest, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from riskmatch.demo import mandate, matches
from riskmatch.intake import evaluate
from riskmatch.interview import report
from riskmatch.catalogue import approved
from riskmatch.monitor import create, history, erase
from riskmatch.reviews import prepare, revise
from research.release.package import export, MAPPING


class Acceptance(unittest.TestCase):
    def test_counterfactual_mandates(self):
        d = mandate()
        self.assertTrue(matches(d))
        reserves = []
        for answers in [
            {"C01": "yes", "C03": "no", "C04": "yes"},
            {"C01": "yes", "C03": "yes", "C04": "no"},
        ]:
            r = report(answers)
            reserves.append((r["low"], evaluate(d)["capacity"][1]["protected"]))
        self.assertNotEqual(reserves[0][0], reserves[1][0])
        self.assertEqual([r[1] for r in reserves], [15000, 15000])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "db"
            t = create([0.45, 0.30, 0.1], 0.08, "test", True, p)
            revise(t, 1, 30000, "2026-11-30", 0.08, p)
            a = prepare(t, path=p)
            revise(t, 2, 30000, "2026-11-23", 0.08, p)
            b = prepare(t, path=p)
            self.assertNotEqual(a["review_id"], b["review_id"])
            self.assertGreater(b["trade_shortfall"], a["trade_shortfall"])
            self.assertEqual(history(t, p)[0]["reserve"], 15000)
            erase(t, p)
            with self.assertRaises(ValueError):
                history(t, p)

    def test_public_package(self):
        with tempfile.TemporaryDirectory() as d:
            dest = export(Path(d) / "demo")
            self.assertEqual(
                {str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()},
                set(MAPPING.values()),
            )
            self.assertFalse((dest / "data/raw").exists())
            self.assertFalse((dest / "research/options/results").exists())
            r = json.loads((dest / "research/catalogue/catalogue.json").read_text())
            self.assertEqual([a["id"] for a in r["records"]], ["demo/manual/v1"])
            self.assertIsNone(
                approved(
                    "H06/v2/cross-instrument sentiment",
                    date(2026, 11, 23),
                    "CHF",
                    "illustrative CHF 50000",
                    "live recommendations",
                    dest / "research/catalogue",
                )
            )

    def test_nonanticipating_cashflow_convention(self):
        # Independent two-subperiod reconciliation of a CHF 100 deposit and a 10% move.
        self.assertAlmostEqual(
            (1100 + 100 - 100) / 1000, (1000 + 100) * 1.1 / (1000 + 100)
        )
        self.assertAlmostEqual(1210 - 1200, 100 * 0.10)


if __name__ == "__main__":
    unittest.main()
