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
