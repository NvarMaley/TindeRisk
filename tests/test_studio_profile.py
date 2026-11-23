"""Calibrated bands, protective constraints, and feed eligibility of the client studio."""

import json
import os
import unittest
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from riskmatch_v2.matching.mandate import MARKET_DAY
from riskmatch_v2.studio import dispatch
from riskmatch_v2.studio_allocation import candidates
from riskmatch_v2.studio_live import live_value
from riskmatch_v2.studio_profile import calibrate, deck, intake

FACTS = {
    "capital": 50000,
    "protected": 15000,
    "expense": 0,
    "loss": 15000,
    "goal": 55000,
    "due": "2030-10-30",
}
BASE = {
    "C01",
    "G00",
    "T01",
    "G01",
    "G03",
    "L00",
    "L01",
    "L02",
    "L03",
    "L04",
    "D01",
    "D03",
    "H01",
    "S01",
}


def answers(yes):
    a = {}
    while pending := [x["id"] for x in deck(a)[0] if x["id"] not in a]:
        k = pending[0]
        a[k] = "yes" if k in yes else "no"
    return a


class Calibration(unittest.TestCase):
    def test_answered_review_prompts_survive_a_resolved_difference(self):
        baseline = answers(BASE)
        cases = (
            ("T03", "yes", baseline, {"T01": "no"}),
            (
                "G04",
                "no",
                baseline | {"G01": "gamble", "G02": "certain"},
                {"G01": "certain"},
            ),
            ("L05", "yes", baseline | {"L02": "no", "L04": "no"}, {"L01": "no"}),
        )
        for prompt, answer, original, revision in cases:
            with self.subTest(prompt=prompt):
                unanswered = {
                    key: value for key, value in original.items() if key != prompt
                }
                self.assertIn(prompt, {card["id"] for card in deck(unanswered)[0]})
                revised = unanswered | revision
                self.assertNotIn(prompt, {card["id"] for card in deck(revised)[0]})
                active, kept = deck(revised | {prompt: answer})
                self.assertIn(prompt, {card["id"] for card in active})
                self.assertEqual(kept[prompt], answer)
                for key in revision:
                    self.assertEqual(kept[key], revision[key])

    def test_behavior_and_capacity_are_distinct(self):
        m, p = calibrate(intake(FACTS), answers(BASE))
        self.assertEqual(
            (p["score"], p["band"], p["low"], p["high"]), (44, "Moderate", 0.08, 0.12)
        )
        self.assertEqual((m["capital_chf"], m["reserve_chf"]), (35000, 15000))
        m, p = calibrate(intake(FACTS | {"loss": 0}), answers(BASE))
        self.assertEqual((p["score"], m["mode"], m["high"]), (44, "minimum", 0))
        m, p = calibrate(intake(FACTS), answers({"C01", "G00", "T01"}))
        self.assertEqual((p["score"], m["low"], m["high"]), (100, 0.2, None))

    def test_reserve_interest_is_separate_from_investable_cash(self):
        old = FACTS | {"loss": 0, "expense": 5000, "expense_date": "2028-10-30"}
        base = intake(old)
        facts = intake(old | {"reserve_rate": 1})
        due = date.fromisoformat(old["due"])
        years = (due - date.fromisoformat(MARKET_DAY)).days / 365.25
        after_spending = (due - date.fromisoformat(old["expense_date"])).days / 365.25
        self.assertAlmostEqual(
            facts["reserve_at_goal_chf"],
            15000 * 1.01**years - 5000 * 1.01**after_spending,
        )
        self.assertEqual(facts["capital_chf"], 35000)
        self.assertEqual(base["reserve_at_goal_chf"], 10000)
        policy, _ = calibrate(facts, answers(BASE))
        plan = next(p for p in candidates(policy) if p["valid"])
        self.assertAlmostEqual(
            plan["goal_value_chf"], 35000 + facts["reserve_at_goal_chf"]
        )
        self.assertEqual(plan["reserve_rate"], 0.01)
        with self.assertRaisesRegex(ValueError, "Set aside more cash"):
            intake(old | {"expense": 15000, "reserve_rate": -1})

    def test_named_choices_and_review_are_preserved(self):
        legacy = answers(BASE)
        named = legacy | {
            "G01": "certain",
            "G02": "gamble",
            "G03": "certain",
            "D01": "reduce",
        }
        _, previously = calibrate(intake(FACTS), legacy)
        _, reduced = calibrate(intake(FACTS), named)
        self.assertEqual(reduced["score"], previously["score"])
        self.assertIn("discomfort", reduced["readings"][0]["detail"])
        cards, active = deck(named | {"D01": "review", "D06": "yes"})
        self.assertNotIn("D03", active)
        self.assertIn("D06", {card["id"] for card in cards})
        _, reviewed = calibrate(intake(FACTS), active)
        self.assertIsNone(reviewed["domains"]["Holding through discomfort"])
        self.assertIn("goal is still reachable", reviewed["readings"][0]["detail"])
        self.assertEqual(
            next(c for c in reviewed["evidence"] if c["id"] == "D01")["answer"],
            "review",
        )

    def test_comparisons_keep_the_score_and_limit_new_searches(self):
        baseline = answers(BASE)
        facts = intake(FACTS)
        _, old = calibrate(facts, baseline)
        cards, _ = deck(baseline, portfolio_check=True)
        self.assertEqual([card["id"] for card in cards[-2:]], ["V01", "V02"])
        for selections, ceiling, status in (
            (("wider", "lower"), 0.08, "Consistent with the score"),
            (("wider", "wider"), 0.12, "Different from the score"),
            (("lower", "wider"), 0.04, "Needs confirmation"),
            (("skip", "wider"), 0.04, "Needs confirmation"),
            (("wider", "skip"), 0.08, "Needs confirmation"),
            (("lower", "lower"), 0.04, "Different from the score"),
            (("wider", "neither"), 0, "Cash only"),
        ):
            with self.subTest(selections=selections):
                policy, profile = calibrate(
                    facts,
                    baseline | dict(zip(("V01", "V02"), selections, strict=True)),
                    portfolio_check=True,
                )
                self.assertEqual(profile["score"], old["score"])
                self.assertEqual(profile["domains"], old["domains"])
                self.assertEqual(profile["portfolio_check"]["status"], status)
                self.assertEqual((policy["low"], policy["high"]), (0, ceiling))
                self.assertEqual(
                    policy["loss_capacity_chf"], facts["loss_capacity_chf"]
                )
        cautious, _ = calibrate(
            facts, baseline | {"V01": "lower", "V02": "lower"}, portfolio_check=True
        )
        offers = [plan for plan in candidates(cautious) if plan["valid"]]
        self.assertTrue(offers)
        self.assertTrue(all(plan["vol"] <= 0.04 + 1e-8 for plan in offers))
        policy, profile = calibrate(
            intake(FACTS | {"loss": 0}),
            baseline | {"V01": "wider", "V02": "wider"},
            portfolio_check=True,
        )
        self.assertEqual(policy["mode"], "minimum")
        self.assertEqual(profile["portfolio_check"]["allocation_ceiling"], 0)

    def test_portfolio_choices_bound_aversion_independently_of_score(self):
        baseline = answers(BASE)
        facts = intake(FACTS)
        mixed = baseline | {"V01": "wider", "V02": "lower", "V04": "lower"}
        _, profile = calibrate(facts, mixed, derived=True)
        self.assertEqual(profile["score"], 44)
        self.assertEqual(
            [row["id"] for row in profile["aversion"]["evidence"]], ["V01", "V02"]
        )
        self.assertAlmostEqual(profile["aversion"]["gamma_low"], 5 / 3)
        self.assertAlmostEqual(profile["aversion"]["gamma_high"], 25 / 6)
        cautious = baseline | {"V01": "lower", "V02": "lower", "V03": "lower"}
        _, profile = calibrate(facts, cautious, derived=True)
        self.assertAlmostEqual(profile["aversion"]["gamma_low"], 25 / 3)
        self.assertIsNone(profile["aversion"]["gamma_high"])
        self.assertEqual(profile["score"], 44)

        _, different_score = calibrate(
            facts,
            answers({"C01", "G00", "T01"}) | {"V01": "wider", "V02": "lower"},
            derived=True,
        )
        self.assertEqual(different_score["score"], 100)
        self.assertEqual(different_score["aversion"]["gamma_low"], 5 / 3)

        for choices, state in (
            ({"V01": "lower", "V02": "wider"}, "needs_confirmation"),
            ({"V01": "skip", "V02": "wider"}, "needs_confirmation"),
            ({"V01": "wider", "V02": "neither"}, "cash_preferred"),
        ):
            with self.subTest(choices=choices):
                _, profile = calibrate(facts, baseline | choices, derived=True)
                self.assertEqual(profile["aversion"]["state"], state)
                self.assertIsNone(profile["aversion"]["gamma_high"])

    def test_portfolio_choices_derive_and_constrain_the_live_matches(self):
        baseline = answers(BASE) | {"V01": "wider", "V02": "lower"}
        with TemporaryDirectory() as folder:
            root = Path(folder)
            saved = dispatch(
                "calibrate",
                {"facts": FACTS, "answers": baseline, "derive_volatility": True},
                root,
            )
            account = {"token": saved["token"], "version": saved["version"]}
            profile = saved["profile"]
            zone = profile["volatility_zone"]
            self.assertEqual(zone["state"], "estimated")
            self.assertGreater(zone["high"], zone["low"])
            self.assertGreater(zone["low"], 0)
            self.assertLessEqual(zone["high"], 1)
            restored = dispatch("resume", account, root)["profile"]
            self.assertEqual(restored["volatility_zone"], zone)
            self.assertEqual(restored["aversion"], profile["aversion"])

            bundle = dispatch("candidates", account, root)
            self.assertEqual(bundle["volatility_zone"], zone)
            matches = {p["id"]: p for p in bundle["plans"] if p["valid"]}
            self.assertIn("preference", matches)
            self.assertIn("cash", matches)
            self.assertTrue(
                all(
                    p["vol"] <= zone["high"] + 1e-8
                    and p["tested_loss_chf"] <= FACTS["loss"] + 0.01
                    for p in matches.values()
                )
            )
            plan = dispatch(
                "blend",
                account | {"ids": ["preference"], "revision": bundle["revision"]},
                root,
            )["plan"]
            self.assertEqual(plan, matches["preference"])

            revised = dispatch(
                "calibrate",
                account
                | {
                    "facts": FACTS | {"loss": 0},
                    "answers": baseline,
                    "derive_volatility": True,
                },
                root,
            )
            self.assertEqual(revised["profile"]["score"], profile["score"])
            self.assertEqual(revised["profile"]["volatility_zone"]["high"], 0)
            self.assertEqual(
                revised["profile"]["volatility_zone"]["state"], "cash_capacity"
            )

    def test_insufficient_and_uncovered_evidence(self):
        m, p = calibrate(intake(FACTS), answers(set()))
        self.assertIsNone(p["score"])
        self.assertTrue(m["blocked_reason"])
        m, p = calibrate(
            intake(FACTS | {"mandatory": "Screen every indirect coal holding"}),
            answers(BASE),
        )
        self.assertIn("verified coverage", m["blocked_reason"])
        with self.assertRaises(ValueError):
            calibrate(intake(FACTS), {})
        with self.assertRaises(ValueError):
            intake(FACTS | {"expense": 2000, "expense_date": "2032-02-01"})

    def test_cash_only_match_and_account_revision(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            result = dispatch(
                "calibrate",
                {"facts": FACTS | {"loss": 0}, "answers": answers(BASE)},
                root,
            )
            token = {"token": result["token"], "version": result["version"]}
            choices = dispatch("candidates", token, root)
            self.assertEqual(
                [x["id"] for x in choices["plans"] if x["valid"]], ["cash"]
            )
            request = token | {"ids": ["cash"], "revision": choices["revision"]}
            proposal = dispatch("draft", request, root)
            self.assertEqual(dispatch("export", token, root)["flows"], [])
            result = dispatch("confirm", token | {"draft": proposal["draft"]}, root)
            again = dispatch("confirm", token | {"draft": proposal["draft"]}, root)
            self.assertEqual(again["version"], result["version"])
            self.assertEqual(len(dispatch("export", token, root)["flows"]), 1)
            self.assertEqual(result["tracking"]["positions"], 0)
            self.assertEqual(result["tracking"]["cash"], 35000)
            later = dispatch(
                "advance", token | {"day": result["tracking"]["day"]}, root
            )
            self.assertEqual(len(later["history"]), 2)
            with self.assertRaisesRegex(ValueError, "account changed"):
                dispatch("blend", request, root)


class LiveMarks(unittest.TestCase):
    def test_market_hours_quotes_fx_and_scope(self):
        now = datetime(2026, 11, 23, 19, 10, tzinfo=UTC)
        acct = {"cash": 100, "holdings": {"SPY": 2}}
        row = {
            "at": now.isoformat(),
            "value": 50,
            "currency": "USD",
            "unit": "ledger_unit",
        }
        feed = {
            "mode": "realtime",
            "display_authorized": True,
            "source": "Fictional feed test",
            "securities": {"SPY": row},
            "usd_chf": {"value": 0.9, "at": row["at"]},
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "feed.json"

            def check(payload, time=now):
                path.write_text(json.dumps(payload))
                return live_value(acct, path=path, now=time)

            self.assertEqual(check(feed)["value"], 190)
            self.assertFalse(check(feed, now + timedelta(minutes=2))["live"])
            self.assertFalse(check(feed | {"usd_chf": {}})["live"])
            self.assertFalse(check(feed | {"securities": {}})["live"])
            self.assertFalse(check(feed | {"display_authorized": False})["live"])
            self.assertFalse(check(feed, now + timedelta(days=5))["live"])
            with patch.dict(os.environ, {"RISKMATCH_LIVE_MARKS": ""}):
                self.assertFalse(live_value(acct)["live"])
