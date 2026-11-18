import json

import pytest
from jsonschema import Draft202012Validator

from src.paths import ROOT
from src.profile_output import build_profile


@pytest.fixture
def answers():
    return {
        "F01": "2_to_lt_5y", "F02": "none", "F03": "ge_6m", "F04": "no_payment",
        "F05": "increase_risk", "F06": "ge_20pct", "F07": "larger_swings",
        "F08": ["funds"], "F09": "can_decline", "F10": "gain_25", "F11": "growth",
        "F12": ["energy", "gold"], "F13": "disallow", "F14": "cap_25pct",
    }


@pytest.fixture
def validator():
    schema = json.loads((ROOT / "schemas/profile_v1.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_emitted_profile_satisfies_v1_schema_and_retains_constraints(answers, validator):
    profile = build_profile(answers, reference_sharpe=.35)
    json.dumps(profile, allow_nan=False)
    validator.validate(profile)
    assert profile["risk"]["category"] == {
        "id": "balanced", "range": [.06, .09], "reference_volatility": .08,
    }
    assert profile["risk"]["binding_capacity_items"] == ["F01"]
    assert profile["risk"]["reference_check_passed"] is True
    assert profile["constraints"] == {
        "excluded_groups": ["energy", "gold"], "allow_borrowing": False,
        "max_etf_weight": .25,
    }
    answers["F12"].append("treasuries")
    assert profile["answers"]["F12"] == ["energy", "gold"]


def test_unresolved_restrictions_and_below_range_fit_schema(answers, validator):
    answers.update(F04="lt_5pct", F12=["unsure"], F13="unsure", F14="unsure")
    profile = build_profile(answers, reference_sharpe=.35)
    validator.validate(profile)
    assert profile["risk"]["category"] is None
    assert profile["risk"]["reference_check_passed"] is False
    assert profile["risk"]["clarification_items"] == ["F12", "F13", "F14"]
    assert profile["constraints"] == {
        "excluded_groups": None, "allow_borrowing": None, "max_etf_weight": None,
    }

    answers.update(F12=["none"], F13="allow", F14="standard")
    resolved = build_profile(answers, reference_sharpe=.35)
    validator.validate(resolved)
    assert resolved["constraints"] == {
        "excluded_groups": [], "allow_borrowing": True, "max_etf_weight": .35,
    }


def test_v1_rejects_ambiguous_exclusive_choice_and_unknown_version(answers, validator):
    profile = build_profile(answers, reference_sharpe=.35)
    profile["answers"]["F12"] = ["none", "energy"]
    assert not validator.is_valid(profile)
    profile["answers"]["F12"] = ["none"]
    profile["schema_version"] = 2
    assert not validator.is_valid(profile)
