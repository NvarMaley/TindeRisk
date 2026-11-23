import json
from datetime import date
from pathlib import Path
from unittest import TestCase

from riskmatch_v2.interview import (
    BANK, CARDS, SKIP, Interview, derive, matches, read_version, route, validated,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "reports/02-questionnaire/cas.json").read_text())
TODAY = date.fromisoformat(CASES["as_of"])
BASE = CASES["common"]


def replay(supplied):
    interview = Interview(TODAY)
    for key in CARDS:
        if key in route(interview.answers):
            interview.record(key, supplied.get(key, SKIP))
    return interview


class InterviewTest(TestCase):
    def test_routes_and_bank(self):
        self.assertEqual(len(CARDS), len(BANK["cards"]))
        reachable = set()
        earlier = set()
        for key, c in CARDS.items():
            self.assertTrue(all(c[k] for k in ("text","family","effect","rationale","alternative")))
            for clause in c["when"]:
                for condition in clause:
                    if not condition.startswith("@"):
                        parent, allowed = condition.split("=")
                        root, _, child = parent.partition(".")
                        self.assertIn(root, earlier)
                        parent_card = CARDS[root]
                        if child:
                            spec = next(f for f in parent_card["fields"] if f["id"] == child)
                            self.assertIn(allowed, spec["options"])
                        else:
                            self.assertIn(allowed, [*parent_card["options"], SKIP])
                    else:
                        matches(condition,{})
            earlier.add(key)
        for case in CASES["cases"]:
            reachable.update(replay(BASE | case["answers"]).answers)
        for choice in ("yes","no",SKIP):
            reachable.update(replay({k:choice for k in CARDS if CARDS[k]["kind"]=="binary"}).answers)
        self.assertEqual(reachable,set(CARDS))

    def test_historical_choice_labels_and_free_text(self):
        original = {"scope": "énergie", "priority": "haute", "strength": "impérative", "missing": "suspendre"}
        restored = validated(CARDS["P07"], [original])[0]
        self.assertEqual(restored, {"scope": "énergie", "priority": "high", "strength": "mandatory", "missing": "suspend"})
        self.assertEqual(original["priority"], "haute")

    def test_published_card_guide_matches_bank(self):
        guide = (ROOT / "reports/02-questionnaire/CARDS.md").read_text()
        self.assertIn(BANK["version"], guide)
        for key, card in CARDS.items():
            row = next(line for line in guide.splitlines() if line.startswith(f"| {key} · "))
            for content in (card["text"], card["effect"], *card.get("options", {}).values()):
                self.assertIn(content, row)

    def test_independent_cases(self):
        for case in CASES["cases"]:
            with self.subTest(case=case["name"]):
                iv = replay(BASE | case["answers"])
                p = iv.confirm()["portrait"]
                self.assertEqual(p["aversion"]["state"],case["phi"])
                self.assertEqual(p["sale_motives"],[case["reason"]] if case["reason"] else [])
                if case["answers"].get("F03") != SKIP:
                    self.assertEqual(p["liquidity"]["investable_chf"],dict(low=35000,high=35000))
                else:
                    self.assertIsNone(p["liquidity"]["reserve_chf"])
                for key in case["answers"]:
                    self.assertIn(key,iv.answers)

    def test_numerical_bounds_and_sensitivity(self):
        p = derive({"C01":"yes","G00":"yes","G01":"yes","G02":"no","T01":"no","G03":SKIP}, TODAY)["aversion"]
        self.assertAlmostEqual(p["low"],8/3)
        self.assertAlmostEqual(p["high"],40/9)
        self.assertEqual(set(p["without"]),{"G01","G02"})
        self.assertIsNone(p["without"]["G01"]["low"])
        self.assertIsNone(p["without"]["G02"]["high"])
        self.assertEqual(derive({"C01":"yes","G00":"no","G01":"yes"}, TODAY)["aversion"]["state"], "insufficient")
        hi = derive({"C01":"yes","G00":"yes","G01":"no"},TODAY)["aversion"]
        self.assertAlmostEqual(hi["high"],8/3)
        self.assertIsNone(hi["low"])
        self.assertEqual(derive({"G01":"yes","C01":SKIP},TODAY)["aversion"]["state"],"insufficient")
        self.assertTrue(derive(BASE | CASES["cases"][4]["answers"],TODAY)["declared_discrepancy"])
        self.assertTrue(derive(BASE | CASES["cases"][5]["answers"],TODAY)["repeated_framing"])

    def test_cash_timing_and_uncertainty(self):
        flow = BASE["F03"][0]
        def budget(*flows):
            return derive(BASE | {"F03":list(flows)}, TODAY)["liquidity"]
        inflow = flow | {"direction":"contribution","low":3000,"high":3000}
        self.assertEqual(budget(flow,inflow)["reserve_chf"]["high"],15000)
        self.assertEqual(budget(flow,inflow | {"date":"2026-12-01"})["reserve_chf"]["high"],12000)
        self.assertEqual(budget(flow,inflow | {"date":"2026-12-01","certainty":"uncertain"})["reserve_chf"]["high"],15000)
        self.assertEqual(budget(flow | {"date":"2028-04-10"})["reserve_chf"]["high"],0)
        self.assertEqual(budget(flow | {"certainty":"uncertain","high":18000})["investable_chf"],dict(low=32000,high=50000))
        self.assertEqual(budget(flow | {"low":70000,"high":70000})["shortfall_chf"]["low"],20000)
        for change in ({"date":None},{"currency":"USD"},{"date":"2025-03-31"}):
            self.assertIsNone(budget(flow | change)["investable_chf"])
        self.assertEqual(budget()["reserve_chf"],dict(low=0,high=0))

    def test_version_corrections_and_pruning(self):
        iv = replay(BASE | CASES["cases"][0]["answers"])
        old = iv.confirm()
        self.assertEqual(old, iv.confirm())
        iv.record("D01","no")
        self.assertFalse(iv.confirmed)
        self.assertNotIn("D02",iv.answers)
        iv.record("D05",SKIP)
        iv.record("F03",[BASE["F03"][0] | {"low":22000,"high":22000}])
        new = iv.confirm()
        self.assertEqual(new["portrait"]["liquidity"]["investable_chf"]["low"],28000)
        self.assertEqual(read_version(json.dumps(old))["portrait"]["liquidity"]["investable_chf"]["low"],35000)
        self.assertEqual(new["version"],2)
        iv.record("P02",BASE["P02"] | {"mode":"minimum","basis":"investment sleeve"})
        self.assertNotIn("P03",iv.answers)
        self.assertIsNone(derive(iv.answers,TODAY)["goal"]["risk_bounds_pct"])
        iv.record("C01","no")
        self.assertNotIn("G01",iv.answers)
        with self.assertRaises(ValueError):
            iv.confirm()
        with self.assertRaises(ValueError):
            iv.record("D02","yes")

    def test_hard_soft_preferences_and_unknowns(self):
        hard, soft = [replay(BASE | c["answers"]).confirm()["portrait"] for c in CASES["cases"][1:3]]
        self.assertEqual(hard["aversion"],soft["aversion"])
        self.assertEqual(hard["mandatory_checks"],[{"card":"P07","scope":"exclude thermal coal"}])
        self.assertFalse(soft["mandatory_checks"])
        self.assertEqual(soft["preferences"]["P08"][0]["strength"],"soft")
        self.assertEqual(derive({},TODAY)["preferences"]["P08"],None)
        self.assertEqual(derive(BASE,TODAY)["preferences"]["P08"],[])

    def test_invalid_answers(self):
        for val in ({"low":4,"high":2},{"low":float("nan"),"high":3},{"low":True,"high":1}):
            with self.assertRaises(ValueError):
                validated(CARDS["F01"],val)
        with self.assertRaises(ValueError):
            validated(CARDS["C01"],"invalid")
        with self.assertRaises(ValueError):
            read_version('{"schema": 7}')
