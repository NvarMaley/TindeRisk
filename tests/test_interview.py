from collections import Counter
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from riskmatch.interview import (
    CARDS,
    CORE,
    current,
    eligible,
    report,
    rewind,
    submit,
    threshold,
)
from riskmatch.intake import evaluate


def walk(overrides=None, phi=3, form=0):
    log = []
    while pool := eligible(current(log), form):
        i = pool[0]
        c = CARDS[i]
        action = (overrides or {}).get(i)
        if action is None and c["effect"] == "bound":
            want = "sure" if phi >= threshold(c) else "gamble"
            action = next(a for a, v in c["answers"].items() if v == want)
        if action is None:
            action = "yes" if i == "C01" else "no"
        assert submit(log, i, action, "button", len(log), form)
        assert len(log) <= 25
    return log


class Interview(unittest.TestCase):
    def test_blueprint_and_scoring_key(self):
        self.assertEqual(len(CARDS), 60)
        self.assertEqual(set(CORE), {i for i, c in CARDS.items() if c["core"]})
        self.assertEqual(
            Counter(CARDS[i]["family"] for i in CORE),
            Counter(
                {
                    "practice": 1,
                    "self-description": 1,
                    "tradeoff": 5,
                    "loss comparison": 4,
                    "decline": 2,
                    "flexibility": 1,
                    "monitoring": 1,
                }
            ),
        )
        for c in CARDS.values():
            self.assertEqual(c["answers"]["pass"], "unsure")
            if c["effect"] == "bound":
                self.assertGreater(threshold(c), 0)
                self.assertEqual(
                    c["answers"]["yes"],
                    "sure" if "guaranteed" in c["statement"] else "gamble",
                )
                self.assertEqual(
                    {c["answers"]["yes"], c["answers"]["no"]}, {"sure", "gamble"}
                )

    def test_bounds_and_boundaries(self):
        c = CARDS["C03"]
        self.assertAlmostEqual(threshold(c), 8 / 3)
        for changes in [
            dict(outcomes=[1000, 1000]),
            dict(certain=1200),
            dict(certain=1060),
            dict(certain=1050),
        ]:
            self.assertIsNone(threshold(dict(c, **changes)))
        with self.assertRaises(ValueError):
            threshold(dict(c, probabilities=[0.5, 0.7]))
        a = {"C01": "yes", "C03": "yes", "C05": "no"}
        self.assertEqual(report(a)["status"], "conflict")
        self.assertEqual(report({"C01": "yes", "C03": "pass"})["used"], 0)
        self.assertEqual(report({"C01": "yes", "C03": "yes"})["sensitive"], ["C03"])

    def test_practice_and_corrections(self):
        log = []
        self.assertTrue(submit(log, "C01", "pass", "keyboard", 0))
        self.assertFalse(submit(log, "C01", "pass", "keyboard", 0))
        self.assertTrue(submit(log, "P01", "yes", "touch", 1))
        self.assertEqual(eligible(current(log)), [])
        self.assertFalse(report(current(log))["understood"])
        rewind(log, "P01")
        self.assertTrue(submit(log, "P01", "no", "mouse", 3))
        self.assertEqual(eligible(current(log)), ["C02"])
        rewind(log, "C01")
        self.assertEqual(current(log), {})
        self.assertFalse(submit(log, "C01", "no", "touch", 0))
        self.assertEqual(len(log), 5)

    def test_branches_and_risk_cap(self):
        for form in range(20):
            log = walk({"C12": "yes", "B01": "yes", "B02": "yes"}, form=form)
            answers = current(log)
            r = report(answers)
            self.assertTrue(r["liquidity"] and r["discomfort"])
            self.assertLessEqual(sum(i.startswith("T") for i in answers), 2)
            self.assertTrue(set(CORE) <= answers.keys())
            self.assertEqual(eligible(answers, form), [])
            rewind(log, "C12")
            while pool := eligible(current(log), form):
                submit(log, pool[0], "pass", "keyboard", len(log), form)
            self.assertFalse(report(current(log))["liquidity"])
        # A wide unresolved interval includes the illustrative crossover; a probe can refine it.
        core = {i: "pass" for i in CORE}
        core.update(C01="yes", C05="yes")
        t = [i for i in eligible(core) if i.startswith("T")]
        self.assertTrue(t)
        for i in t:
            self.assertGreater(threshold(CARDS[i]), report(core)["low"])
        # Once the illustrative ranking is invariant, no extra numerical probe is needed.
        core["C03"] = "yes"
        self.assertFalse(any(i.startswith("T") for i in eligible(core)))

    def test_consequential_clarification_and_loss_pairs(self):
        a = {i: "pass" for i in CORE}
        a.update(C01="yes", C03="yes", C08="no", C09="no", C10="yes", C11="yes")
        self.assertTrue({"B14", "B15"} <= set(eligible(a)))
        a["B15"] = "yes"
        a["B14"] = "pass"
        self.assertEqual(report(a)["used"], 1)
        self.assertFalse(report(a)["confirmed_loss"])
        a["B14"] = "yes"
        self.assertTrue(report(a)["confirmed_loss"])
        for k in ("C02", "C15", "B01"):
            self.assertEqual(
                report(dict(a, **{k: "yes"}))["options"], report(a)["options"]
            )

    def test_report_and_cash_are_independent(self):
        d = dict(
            start=date(2027, 1, 1),
            end=date(2030, 1, 1),
            currency="CHF",
            capital="50000",
            buffer="0",
            bill_list="Complete",
            goal_list="Complete",
            flows=[
                dict(
                    kind="withdrawal",
                    day=date(2029, 1, 1),
                    amount="10000..15000",
                    confirmed=True,
                )
            ],
        )
        capacity = evaluate(d)["capacity"]
        self.assertEqual([x["investable"] for x in capacity], [40000, 35000])
        self.assertEqual(
            evaluate(dict(d, age=70, desired="20", tolerance=8))["capacity"], capacity
        )
        for method in ["touch", "mouse", "keyboard"]:
            log = []
            submit(log, "C01", "yes", method, 0)
            self.assertEqual(report(current(log)), report({"C01": "yes"}))


if __name__ == "__main__":
    unittest.main()
