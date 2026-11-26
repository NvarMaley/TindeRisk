import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from riskmatch.profiling.mandate import OBJECTIVES, convert, required_return, validate_mandate


@pytest.fixture
def mandate():
    return json.loads((Path(__file__).resolve().parents[2] / "configs/mandate-example.json").read_text())


def test_balance_sheet_and_cash_flows(mandate):
    r = validate_mandate(mandate)
    assert r["status"] == "structurally_valid"
    assert r["net_worth"] == 180000
    assert r["investable_wealth"] == 130000
    assert r["monthly_surplus"] == 2500
    assert r["goals"][0]["zero_return_gap"] == 20000
    assert r["next_withdrawal"] == mandate["goals"][0]["due_date"]
    assert r["goals"][0]["required_return"]["annual_return"] > 0
    assert r["combined_required_return"]["status"] == "calculated"
    assert r["demo_eligible"]


def test_exact_single_and_dated_multiple_returns():
    start = date(2024, 1, 1)
    end = date(2025, 1, 1)
    years = (end-start).days/365.25
    expected = .10
    target = 100 * (1+expected)**years
    assert required_return(100, [], start, end, target)["annual_return"] == pytest.approx(expected)
    mid = start + timedelta(days=183)
    target += 25 * (1+expected)**((end-mid).days/365.25)
    assert required_return(100, [(mid,25)], start, end, target)["annual_return"] == pytest.approx(expected)
    assert required_return(100, [(mid,-50),(mid+timedelta(days=1),50)],start,end,target)["status"] == "ambiguous_cash_flows"


def test_fx_real_values_and_unmodeled_demo(mandate):
    mandate["currency"] = "CHF"
    with pytest.raises(ValueError, match="fx_required"):
        validate_mandate(mandate)
    mandate["chf_per_usd"] = 0.9
    mandate["goals"][0]["basis"] = "real"
    r = validate_mandate(mandate)
    assert convert(100,"USD","CHF",.9) == 90
    assert convert(90,"CHF","USD",.9) == 100
    assert r["goals"][0]["target_nominal_base"] == pytest.approx(240000*.9*1.02**r["horizon_years"])
    assert not r["demo_eligible"] and "demo_usd_only" in r["demo_reasons"]


@pytest.mark.parametrize("field,value,error", [
    ("capital",0,"capital_positive"), ("capital",-1,"invalid_field"),
    ("capital",True,"invalid_field"), ("currency","EUR","invalid_field"),
    ("consent",False,"consent_required"), ("horizon_date","2026-01-01","invalid_horizon"),
    ("reserve",200000,"reserve_exceeds_cash"), ("capital",float("nan"),"invalid_field"),
])
def test_invalid_inputs(mandate,field,value,error):
    mandate[field]=value
    with pytest.raises(ValueError,match=error):
        validate_mandate(mandate)


def test_conflicts_and_financial_capacity(mandate):
    mandate["capital"] = 140000
    mandate["contribution_monthly"] = 3000
    mandate["constraints"]["allow_short"] = True
    mandate["constraints"]["net_min"]["value"] = .8
    mandate["constraints"]["net_max"]["value"] = .4
    r=validate_mandate(mandate)
    assert {"capital_exceeds_investable_wealth","contribution_exceeds_surplus","knowledge_required:short","net_bounds_conflict"} <= set(r["conflicts"])
    assert not r["demo_eligible"]


def test_near_term_withdrawals_and_hard_constraints(mandate):
    mandate["dated_flows"] = [{"date":"2026-12-01","kind":"liability","amount":95000}]
    r=validate_mandate(mandate)
    assert r["next_withdrawal"] == "2026-12-01"
    assert r["loss_capacity_amount"] == 5000
    assert r["effective_stress_limit"] == .05
    mandate["dated_flows"][0]["amount"] = 150000
    r=validate_mandate(mandate)
    assert r["zero_return_min_balance"] < 0
    assert r["effective_stress_limit"] == 0
    mandate["constraints"]["max_cost"]["value"] = .01
    assert not validate_mandate(mandate)["demo_eligible"]


def test_multiple_priorities_and_catalog(mandate):
    assert len(OBJECTIVES)==11
    mandate["goals"].append(dict(mandate["goals"][0],objective_id="OBJ05",amount=None,funding=False,priority=1))
    r=validate_mandate(mandate)
    assert [g["priority_weight"] for g in r["goals"]] == [.75,.25]
    assert r["goals"][1]["required_return"]["status"] == "preference_only"
