from copy import deepcopy
from dataclasses import replace
from datetime import date
import json
from math import nextafter, inf
from pathlib import Path
from unittest import TestCase

from riskmatch_v2.interview import CARDS, Interview, SKIP, read_version, route
from riskmatch_v2.risk_review import CertifiedMaximum, POLICY, assess, band_at, centered_target, portrait_digest, request, suggested

ROOT = Path(__file__).resolve().parents[1]
SEEDS = json.loads((ROOT / "reports/02-questionnaire/cas.json").read_text())


def interview(**updates):
    answers = SEEDS["common"] | SEEDS["cases"][0]["answers"] | updates
    session = Interview(date.fromisoformat(SEEDS["as_of"]))
    for k in CARDS:
        if k in route(session.answers):
            session.record(k, answers.get(k, SKIP))
    session.confirm()
    return session


def review(session, selection=None, **options):
    return assess(session.versions[-1], selection or request("minimum","investment sleeve"),
                  **(dict(accept=True, bills="yes", comfort="yes") | options))


class RiskReviewTest(TestCase):
    def test_half_open_bands_and_custom_units(self):
        labels = [b["label"] for b in POLICY["bands"]]
        for i, cutoff in enumerate((.04,.08,.12,.20), 1):
            self.assertEqual(band_at(nextafter(cutoff,-inf)),labels[i-1])
            self.assertEqual(band_at(cutoff),labels[i])
            self.assertEqual(band_at(nextafter(cutoff,inf)),labels[i])
        self.assertEqual(band_at(0), labels[0])
        for value in [35,40,100,125]:
            self.assertEqual(request("cap","investment sleeve",ceiling_pct=value)["high"],value/100)
        target = request("target_band","investment sleeve",low_pct=6,high_pct=10)
        self.assertEqual((target["low"],target["high"],target["high_exclusive"]),(.06,.1,False))
        self.assertEqual(centered_target("investment sleeve",40,2)["low"],.38)
        self.assertEqual(centered_target("investment sleeve",40,2)["high"],.42)
        self.assertIsNone(request("target_band","investment sleeve",band=labels[-1])["high"])

    def test_invalid_bounds_modes_and_units(self):
        for value in (-1, "40 %", float("nan"), True, float("inf")):
            with self.assertRaises(ValueError):
                request("cap","investment sleeve",ceiling_pct=value)
        for params in [dict(low_pct=10,high_pct=6),dict(band="Not applicable"), dict(band="Moderate", low_pct=8)]:
            with self.assertRaises(ValueError):
                request("target_band","investment sleeve",**params)
        with self.assertRaises(ValueError):
            centered_target("investment sleeve",1,2)
        with self.assertRaises(ValueError):
            request("minimum","investment sleeve",ceiling_pct=2)
        for alteration in (dict(unit="pct"),dict(high=-.2),dict(high=float("nan")),dict(low=.1)):
            with self.assertRaises(ValueError):
                review(interview(),request("cap","investment sleeve",ceiling_pct=40) | alteration)

    def test_acknowledgment_and_distinct_modes(self):
        session = interview(F04={"low":15000,"high":15000})
        for choice in [request("minimum","investment sleeve"),request("cap","investment sleeve",ceiling_pct=40),
                       centered_target("investment sleeve",40,2)]:
            self.assertTrue(review(session, choice)["ready_for_feasibility"])
            self.assertFalse(review(session,choice,accept=False)["ready_for_feasibility"])
        undecided = review(session,request("unknown","household"),accept=False)
        self.assertEqual(undecided["state"], "pending confirmation")
        self.assertFalse(undecided["ranking_authorized"])
        self.assertEqual(undecided["initial"]["high"], .12)
        self.assertEqual(review(session,centered_target("investment sleeve",40,2))["feasibility"],"to be tested")

    def test_documented_market_bound_can_only_exclude(self):
        session = interview(F04={"low":15000,"high":15000})
        cert = CertifiedMaximum(.18,"investment sleeve",SEEDS["as_of"],1,"fictitious analytical case",portrait_digest(session.versions[-1]))
        opts = dict(certificate=cert)
        target = centered_target("investment sleeve",40,2)
        self.assertEqual(review(session,target,**opts)["state"],"target out of range")
        self.assertEqual(review(session,request("cap","investment sleeve",ceiling_pct=40),**opts)["feasibility"],"to be tested")
        for stale in [replace(cert,basis="household"), replace(cert,as_of="2025-01-01"), replace(cert,portrait_version=2), replace(cert,portrait_digest="other customer")]:
            self.assertEqual(review(session,target,certificate=stale)["feasibility"],"to be tested")

    def test_same_shock_two_bases_and_cash_calendar(self):
        session = interview()
        r = review(session)
        a,b = r["stresses"]
        self.assertEqual(a["months"],1)
        self.assertAlmostEqual(a["household_fraction"]["low"],.07)
        self.assertEqual(a["loss_chf"],{"low":3500,"high":3500})
        self.assertAlmostEqual(b["loss_chf"]["high"],7000)
        self.assertEqual(r["dated_cash"][-1],{"date":"2027-03-31","phase":"After withdrawals","cash_chf":{"low":0,"high":0}})
        self.assertEqual(r["dated_cash"][0]["cash_chf"]["low"],15000)
        self.assertEqual(r["household_invested_share"],.7)
        self.assertTrue(review(session, request("target_band","household",low_pct=15,high_pct=17))["issues"])

    def test_same_request_on_different_bases_and_near_term_liabilities(self):
        session = interview()
        cap = request("cap", "investment sleeve", ceiling_pct=40)
        converted = review(session,cap)["equivalent"]
        self.assertAlmostEqual(converted["high"],.28)
        self.assertEqual(converted["basis"],"household")
        target = centered_target("household",28,1.4)
        converted = review(session,target)["equivalent"]
        self.assertAlmostEqual(converted["low"],.38)
        self.assertAlmostEqual(converted["high"],.42)
        near = interview(F02={"date":"2027-01-01"}, F05=SEEDS["common"]["F05"] | {"date":"2027-09-01"})
        decision = review(near,target)
        self.assertTrue(any("F05" in m for m in decision["issues"]))
        self.assertTrue(any("F02/F03" in m for m in decision["issues"]))
        self.assertFalse(decision["ready_for_feasibility"])

    def test_conflicts_do_not_change_declared_limits(self):
        session=interview(D03="yes")
        target=centered_target("investment sleeve",40,2)
        r=review(session,target,comfort="no")
        self.assertEqual(r["state"],"to be clarified")
        self.assertEqual(r["choice"],target)
        self.assertEqual(r["alternative"]["choice"]["mode"],"minimum")
        self.assertTrue(any("2027-03-31" in m for m in r["reasons"]))
        self.assertTrue(any("D03" in m for m in r["reasons"]))
        self.assertTrue(any("F04" in m for m in r["issues"]))
        self.assertEqual(r["reserve_chf"]["low"],15000)
        self.assertFalse(r["ready_for_feasibility"])

    def test_uncertain_expense_empty_pocket_and_missing_inputs(self):
        base=SEEDS["common"]["F03"][0]
        original=review(interview())
        approx=review(interview(F03=[base | {"low":10000,"high":20000,"certainty":"uncertain"}]))
        self.assertEqual(approx["investable_chf"],{"low":30000,"high":50000})
        self.assertEqual(approx["stresses"][0]["loss_chf"],{"low":3000,"high":5000})
        self.assertEqual(approx["dated_cash"][-1]["cash_chf"],{"low":0,"high":20000})
        self.assertFalse(approx["ready_for_feasibility"])
        self.assertEqual(original["initial"],approx["initial"])
        for cap in [0,15000]:
            empty=review(interview(F01={"low":cap,"high":cap}))
            self.assertEqual(empty["feasibility"],"no investment capital")
            self.assertIsNone(empty["stresses"][0]["pocket_fraction"])
            self.assertEqual(empty["stresses"][0]["household_fraction"] is None, cap==0)
        missing=review(interview(F03=SKIP))
        self.assertEqual(missing["stresses"],[])
        self.assertFalse(missing["ready_for_feasibility"])

    def test_version_and_invalidation(self):
        session=interview()
        portrait=deepcopy(session.versions[0])
        risk=request("cap","investment sleeve",ceiling_pct=10)
        kwargs=dict(accept=True,bills="yes",comfort="yes")
        first=session.save_risk(risk,**kwargs)
        self.assertEqual(first,session.save_risk(risk,**kwargs))
        self.assertEqual(first["portrait_version"],1)
        self.assertEqual(read_version(json.dumps(first))["schema"],2)
        self.assertEqual(read_version(json.dumps(portrait))["schema"],1)
        session.record("F03",[])
        with self.assertRaises(ValueError):
            session.save_risk(risk,**kwargs)
        updated=session.confirm()
        self.assertNotIn("risk_review", updated)
        self.assertEqual(session.versions[0],portrait)
        self.assertEqual(session.versions[1]["risk_review"]["investable_chf"]["low"],35000)
        revised=session.save_risk(risk,**kwargs)
        self.assertEqual(revised["portrait_version"],updated["version"])
        self.assertEqual(revised["risk_review"]["investable_chf"]["low"],50000)

    def test_undeclared_does_not_become_a_numeric_band(self):
        consent=interview(P02=SKIP,D03="yes")
        r, reason=suggested(consent.versions[0]["portrait"])
        self.assertEqual(r["mode"],"minimum")
        self.assertIn("D03",reason)
        self.assertEqual(suggested(interview(P02=SKIP).versions[0]["portrait"])[0]["mode"],"unknown")
