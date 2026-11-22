from datetime import date, timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from riskmatch.intake import amount, evaluate, funding_rate

START = date(2027, 1, 1)
END = START + timedelta(days=730)


def flow(kind, days, value, confirmed=True):
    return dict(
        kind=kind, day=START + timedelta(days=days), amount=value, confirmed=confirmed
    )


def example():
    return dict(
        start=START,
        end=END,
        currency="CHF",
        capital="50000",
        buffer="0",
        target="35000",
        basis="Future amount",
        desired="5",
        goal_list="Complete",
        bill_list="Complete",
        flows=[flow("withdrawal", 730, "15000")],
    )


class Intake(unittest.TestCase):
    def test_answers(self):
        self.assertEqual(
            [amount(a).state for a in ["", "?", "pass", "0"]],
            ["missing", "unknown", "declined", "known"],
        )
        for raw in ["-1", "150..100", "NaN", "inf", "? .. 1"]:
            with self.assertRaises(ValueError):
                amount(raw)
        self.assertEqual(amount("-2..5", percent=True).low, -2)
        with self.assertRaises(ValueError):
            amount("-100", percent=True)

    def test_funding_invariant(self):
        d = example()
        a = evaluate(d)
        self.assertEqual(
            [a["capacity"][0][k] for k in ("protected", "investable")], [15000, 35000]
        )
        self.assertAlmostEqual(a["rates"][0]["rate"], 0)
        self.assertEqual(
            a["capacity"], evaluate(dict(d, desired="15", tolerance=1))["capacity"]
        )
        deposit = flow("bill funding", 400, "5000")
        d["flows"].append(deposit)
        self.assertEqual(evaluate(d)["capacity"][0]["required"], 10000)
        d["flows"][0] = flow("withdrawal", 300, "15000")
        self.assertEqual(evaluate(d)["capacity"][0]["required"], 15000)

    def test_ranges_and_stress(self):
        d = example()
        d.update(
            buffer="2000",
            flows=[
                flow("withdrawal", 10, "10000..15000"),
                flow("withdrawal", 10, "5000"),
                flow("bill funding", 10, "17000"),
            ],
        )
        r = evaluate(d)
        self.assertEqual([c["investable"] for c in r["capacity"]], [48000, 45000])
        self.assertEqual(r["delayed"]["required"], 22000)
        d["capital"] = "10000"
        self.assertEqual(
            evaluate(d)["delayed"]["first_shortfall"],
            (START + timedelta(days=10)).isoformat(),
        )
        self.assertEqual(evaluate(d)["delayed"]["shortfall"], 12000)

    def test_opening_and_shortfall(self):
        d = example()
        d["flows"] = [flow("withdrawal", 0, "15000"), flow("bill funding", 0, "15000")]
        self.assertEqual(evaluate(d)["capacity"][0]["required"], 0)
        d["flows"][1]["confirmed"] = False
        d["buffer"] = "40000"
        r = evaluate(d)
        self.assertEqual(r["capacity"][0]["investable"], 0)
        self.assertEqual(r["capacity"][0]["shortfall"], 5000)
        self.assertEqual(r["capacity"][0]["first_shortfall"], START.isoformat())
        self.assertEqual(r["rates"][0]["status"], "withdrawal funding shortfall")

    def test_rates(self):
        d = example()
        d["target"] = "35000"
        d["basis"] = "Today's purchasing power"
        d["inflation"] = "2..4"
        r = evaluate(d)
        for case, want in zip(r["rates"], [0.02, 0.04]):
            self.assertAlmostEqual(case["rate"], want)
            self.assertAlmostEqual(case["terminal"], case["target"])
        result = funding_rate(
            START, END, 100, [(START + timedelta(days=365), 10), (END, 5)], 137
        )
        self.assertAlmostEqual(result["rate"], 0.1)
        self.assertEqual(
            funding_rate(START, END, 0, [(END, 10)], 10)["status"], "any rate"
        )
        self.assertEqual(funding_rate(START, END, 0, [], 10)["status"], "no solution")
        self.assertEqual(
            funding_rate(START, END, 100, [(END, 10)], 9)["status"], "no finite rate"
        )

    def test_unknown_and_invalid_dates(self):
        d = example()
        self.assertIsNone(evaluate(dict(d, buffer="pass"))["capacity"])
        self.assertIsNone(evaluate(dict(d, target="?"))["rates"])
        self.assertIsNotNone(evaluate(dict(d, target="?"))["capacity"])
        self.assertIsNone(evaluate(dict(d, bill_list="Unknown"))["capacity"])
        self.assertIn("end", evaluate(dict(d, end=START))["issues"])
        d["flows"] = [flow("withdrawal", 731, "1")]
        self.assertIn("Flow 1 date", evaluate(d)["issues"])
        d["flows"][0]["day"] = None
        self.assertIsNone(evaluate(d)["capacity"])


if __name__ == "__main__":
    unittest.main()
