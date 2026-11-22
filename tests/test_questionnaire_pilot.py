from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "research")]
from riskmatch import interview as engine
from questionnaire_pilot import IDS, freeze, participant, summarize
from simulate_interview import economic_choice, simulate, witnesses


class PilotTests(unittest.TestCase):
    def route(self, reverse=False, mirrored=False, swap_sides=False):
        # Lab manipulation: keep the same semantic preferences but swap the endorsed alternative.
        # Even when the two options exchange positions, right continues to endorse the statement.
        cards = deepcopy(engine.CARDS)
        order = [engine.CORE[0], *reversed(engine.CORE[1:])] if reverse else engine.CORE
        log = []
        with patch.object(engine, "CORE", order), patch.dict(engine.CARDS, cards):
            for c in cards.values():
                if c["effect"] == "bound" and mirrored:
                    m = c["answers"]
                    m["yes"], m["no"] = m["no"], m["yes"]
            while pool := engine.eligible(engine.current(log), 7):
                i = pool[0]
                card = cards[i]
                if card["effect"] == "bound":
                    choice = economic_choice(card, 2.1)
                    display = ["gamble", "sure"] if swap_sides else ["sure", "gamble"]
                    selected_position = display.index(choice)
                    endorsed_position = display.index(card["answers"]["yes"])
                    response = "yes" if selected_position == endorsed_position else "no"
                else:
                    response = "yes" if i == "C01" else "no"
                self.assertTrue(engine.submit(log, i, response, "fixture", len(log), 7))
            r = engine.report(engine.current(log))
            return log, (r["low"], r["high"], r["used"], set(r["sensitive"]))

    def test_display_order_and_endorsement(self):
        base = self.route()[1]
        for order, mirror in [(True, False), (False, True), (True, True)]:
            for swapped in (True, False):
                self.assertEqual(base, self.route(order, mirror, swapped)[1])

    def test_future_answers_and_sealed_core(self):
        log, _ = self.route()
        end = next(i for i, e in enumerate(log, 1) if e["id"] == engine.CORE[-1])
        prefix = deepcopy(log[:end])
        snapshot = freeze(prefix)
        self.assertEqual(freeze(log)["core"], snapshot["core"])
        engine.rewind(log, "C03")
        self.assertTrue(engine.submit(log, "C03", "pass", "test", len(log), 7))
        self.assertEqual(freeze(log)["core"], snapshot["core"])
        self.assertEqual(prefix, log[:end])
        self.assertEqual(freeze(prefix), snapshot)

    def test_separate_validation_and_duplicate_events(self):
        log, _ = self.route()
        frozen = freeze(log)
        self.assertTrue(set(IDS).isdisjoint(engine.CARDS))
        for answer in ["sure", "gamble", "unsure", None]:
            participant("example", frozen, {i: answer for i in IDS})
            self.assertEqual(freeze(log), frozen)
        log = []
        self.assertFalse(engine.submit(log, IDS[0], "yes", "test", 0))
        self.assertTrue(engine.submit(log, "C01", "yes", "test", 0))
        self.assertFalse(engine.submit(log, "C01", "yes", "test", 0))
        self.assertEqual(len(log), 1)

    def test_abstention_and_attrition(self):
        preds = dict.fromkeys(IDS, "sure")
        sim = {"core": preds, "adaptive": preds}
        a = participant("one", sim, dict.fromkeys(IDS, "sure"))
        b = participant("two", sim, {})
        s = summarize([a, b])
        self.assertEqual(s["core"]["verified_people"], 1)
        self.assertEqual(s["core"]["agreement"], 1)
        self.assertEqual(s["core"]["all_assigned_bounds"], [0.5, 1])
        self.assertEqual(s["paired_agreement_gain"]["participants"], 1)
        empty = participant("three", freeze([]), {})
        self.assertEqual(empty["core"]["coverage"], 0)
        self.assertIsNone(empty["paired_agreement_gain"])
        with self.assertRaises(ValueError):
            summarize([a, a])

    def test_branch_witnesses_and_seed(self):
        routes = witnesses()
        for card, route in zip(engine.CARDS, routes, strict=True):
            self.assertIn(card, route)
        self.assertEqual(simulate("random", 2, 2), simulate("random", 2, 2))
        self.assertTrue(simulate("early stop", 2, 2)["stopped"])


if __name__ == "__main__":
    unittest.main()
