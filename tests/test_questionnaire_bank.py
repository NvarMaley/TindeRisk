"""Checks for the extended research deck and its adaptive paths."""

import unittest
from itertools import product

from riskmatch_v2 import questionnaire_bank as bank


def replay(overrides, **route):
    answers = {}
    while card := bank.next_card(answers, **route)[0]:
        if card.id in answers:
            raise AssertionError("A replay showed the same card twice.")
        answers[card.id] = overrides.get(card.id, "yes")
    return bank.assess(answers, **route)


class QuestionnaireBankTests(unittest.TestCase):
    def test_bank_is_distinct_and_every_ordered_level_can_be_selected(self):
        cards = bank.pilot.BANK + bank.FOLLOW_UPS
        self.assertEqual(len(cards), 126)
        self.assertEqual(len({card.id for card in cards}), 126)
        self.assertEqual(len({card.text for card in cards}), 126)
        for ladders, increasing in (
            (bank.PORTFOLIO, True),
            (bank.DECLINES, False),
            (bank.LOSSES, True),
        ):
            for ladder in ladders:
                reached = set()
                for replies in product(("yes", "no"), repeat=3):
                    answers = {}
                    for card, answer in zip(
                        bank._offers(answers, ladder, increasing=increasing), replies
                    ):
                        reached.add(card.id)
                        answers[card.id] = answer
                self.assertEqual(reached, {card.id for card in ladder.prompts})

    def test_relaunches_are_targeted_and_keep_anchor_scores(self):
        report = replay({"D02": "no"}, form=3, horizon=1)
        self.assertIn("R12", report["follow_ups"])
        self.assertTrue(any(key.startswith("P2") for key in report["follow_ups"]))
        self.assertEqual(report["scores"]["maintien"], 50)
        self.assertEqual(
            bank.pilot.assess(report["active_answers"])["willingness"],
            report["willingness"],
        )

    def test_explicit_options_preserve_action_and_operate_ladders(self):
        report = replay(
            {"D01": "review", "G01": "certain", "G02": "certain", "P52": "portfolio_a"}
        )
        self.assertIn("revois le plan", report["decisions"]["D01"])
        self.assertIsNone(report["scores"]["maintien"])
        self.assertEqual(report["follow_ups"]["P52"]["answer"], "no")
        self.assertIn("portefeuille A", report["follow_ups"]["P52"]["decision"])

    def test_partial_understanding_and_card_limits(self):
        report = replay({"C01": "skip", "C02": "no"})
        self.assertIsNone(report["willingness"])
        self.assertEqual(
            {key for key in report["follow_ups"] if key.startswith("CX")},
            {"CX01", "CX06"},
        )
        self.assertFalse(any(key.startswith("P") for key in report["follow_ups"]))
        at_limit = replay({}, limit=8)
        self.assertEqual(at_limit["extended_count"], 8)
        self.assertEqual(at_limit["status"], "limite_atteinte")
        self.assertIsNone(at_limit["next"])
        with self.assertRaises(ValueError):
            bank.next_card({}, limit=41)
