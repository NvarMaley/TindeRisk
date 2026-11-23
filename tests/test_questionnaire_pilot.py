"""Check the candidate study before any change to live questionnaire scoring."""

import unittest

from riskmatch_v2.questionnaire_pilot import BANK, assess, count_routes, next_card


def finish(overrides, default="yes"):
    answers = {}
    while (card := next_card(answers)[0]) is not None:
        answers[card.id] = overrides.get(card.id, default)
    return assess(answers)


class QuestionnairePilotTests(unittest.TestCase):
    def test_common_gate_and_longest_route(self):
        short = finish({"C01": "no", "C02": "no", "S01": "no"})
        self.assertEqual(short["shown"], 9)
        self.assertEqual(short["scores"]["comprehension"], 0)
        self.assertIsNone(short["willingness"])
        self.assertFalse({"G01", "L01", "F01"} & short["active_answers"].keys())

        long = finish(
            {"C01": "skip", "C02": "yes", "G01": "no", "G02": "yes", "D02": "no"}
        )
        self.assertEqual(long["shown"], len(BANK))
        self.assertEqual(long["scores"]["maintien"], 50)
        self.assertEqual(long["scores"]["arbitrage"], 33)
        self.assertEqual(long["willingness"], 44)
        self.assertEqual(long["evidence"]["comprehension"], {"answered": 1, "shown": 2})

    def test_conflict_uncertainty_and_descriptive_scores(self):
        report = finish({"G01": "yes", "G02": "no", "D01": "no", "F02": "no"})
        self.assertIsNone(report["willingness"])
        self.assertEqual(report["status"], "a_revoir")
        self.assertIsNone(report["scores"]["arbitrage"])
        self.assertIsNone(report["scores"]["maintien"])
        self.assertEqual(report["scores"]["concordance_cadrage"], 0)

        report = finish(
            {"T02": "no", "G01": "no", "G02": "no", "D01": "no", "D02": "no"}
        )
        self.assertEqual(report["willingness"], 67)
        self.assertEqual(report["status"], "a_confirmer")
        self.assertEqual(report["scores"]["reticence_pertes"], 0)

    def test_routing_ignores_inactive_answers_and_counts_terminal_paths(self):
        card, seen = next_card({"C01": "yes", "C02": "no", "G03": "yes"})
        self.assertEqual(card.id, "T01")
        self.assertEqual(seen, {"C01": "yes"})
        counts = count_routes()
        self.assertEqual(sum(counts.values()), 56_629_125)
        self.assertEqual(set(counts), {9, 10, 11, 14, 15, 16, 17, 18})
