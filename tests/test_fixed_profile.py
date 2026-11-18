import json

import pytest

from src.fixed_profile import CAPACITY_RULES, TOLERANCE_POINTS, score_fixed_profile
from src.paths import ROOT


@pytest.fixture
def answers():
    return {
        "F01": "ge_10y", "F02": "none", "F03": "ge_6m", "F04": "no_payment",
        "F05": "increase_risk", "F06": "ge_20pct", "F07": "larger_swings",
        "F08": ["funds"], "F09": "can_decline", "F10": "gain_25",
        "F11": "growth", "F12": ["none"], "F13": "disallow", "F14": "standard",
    }


def test_every_scored_answer_has_a_rule_and_higher_capacity_never_lowers_cap():
    bank = json.loads((ROOT / "questions/fixed_mvp.json").read_text())
    for question in bank["questions"]:
        key = question["id"]
        if question["dimension"] not in {"capacity", "tolerance"}:
            continue
        rules = CAPACITY_RULES if question["dimension"] == "capacity" else TOLERANCE_POINTS
        assert set(rules[key]) == {option["id"] for option in question["options"]}
    for key, safer_order in {
        "F01": ["lt_2y", "2_to_lt_5y", "5_to_lt_10y", "ge_10y"],
        "F02": ["ge_50pct", "25_to_lt_50pct", "gt_0_to_lt_25pct", "none"],
        "F03": ["lt_1m", "1_to_lt_3m", "3_to_lt_6m", "ge_6m"],
        "F04": ["lt_5pct", "5_to_lt_10pct", "10_to_lt_20pct", "ge_20pct", "no_payment"],
    }.items():
        caps = [CAPACITY_RULES[key][option] for option in safer_order]
        assert caps == sorted(caps)


def test_capacity_caps_tolerance_and_knowledge_and_goals_are_independent(answers):
    high = score_fixed_profile(answers, reference_sharpe=.35)
    assert high.tolerance_score == 1
    assert high.risk_aversion == 2.5
    assert high.tolerance_volatility == pytest.approx(.14)
    assert high.band.key == "aggressive"
    assert high.reference_within_limit

    answers.update(F01="2_to_lt_5y", F09="must_rise", F11="income")
    result = score_fixed_profile(answers, reference_sharpe=.35)
    assert result.tolerance_volatility == pytest.approx(.14)
    assert result.capacity_volatility == result.effective_volatility == .08
    assert result.binding_capacity_items == ("F01",)
    assert result.band.key == "balanced"
    assert result.reference_within_limit


def test_uncertainty_and_presets_above_limit_are_flagged(answers):
    answers.update(F02="unsure", F05="unsure", F12=["unsure"])
    result = score_fixed_profile(answers, reference_sharpe=.35)
    assert result.clarification_items == ("F02", "F05", "F12")
    assert result.tolerance_score == pytest.approx(2 / 3)
    assert result.capacity_volatility == .04
    assert result.band.key == "conservative"
    assert not result.reference_within_limit

    answers.update(F02="none", F05="increase_risk", F12=["none"], F03="lt_1m")
    reserve_limit = score_fixed_profile(answers, reference_sharpe=.35)
    assert not reserve_limit.clarification_items
    assert reserve_limit.band.key == "conservative"
    assert not reserve_limit.reference_within_limit

    answers["F04"] = "lt_5pct"
    below_range = score_fixed_profile(answers, reference_sharpe=.35)
    assert below_range.effective_volatility == .03
    assert below_range.band is None
    assert not below_range.reference_within_limit


@pytest.mark.parametrize("key,value", [("F05", "unknown"), ("F08", ["funds", "funds"]),
                                       ("F12", ["energy", "none"]), ("F13", ["disallow"])])
def test_invalid_answers_are_rejected(answers, key, value):
    answers[key] = value
    with pytest.raises(ValueError, match=key):
        score_fixed_profile(answers, reference_sharpe=.35)


def test_missing_answer_is_rejected(answers):
    del answers["F01"]
    with pytest.raises(ValueError, match="missing=.*F01"):
        score_fixed_profile(answers, reference_sharpe=.35)
