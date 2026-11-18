import pytest

from src.fixed_profile import assess_financial_capacity


BASE = {"F01": "ge_10y", "F02": "none", "F03": "ge_6m", "F04": "no_payment"}


@pytest.mark.parametrize("key,choice,ceiling", [
    ("F01", "lt_2y", .05),
    ("F02", "25_to_lt_50pct", .06),
    ("F03", "1_to_lt_3m", .06),
    ("F04", "lt_5pct", .03),
])
def test_each_capacity_factor_can_set_the_limit(key, choice, ceiling):
    result = assess_financial_capacity({**BASE, key: choice})
    assert result.volatility == ceiling
    assert result.binding_items == (key,)
    assert result.caps[key] == ceiling
    assert not result.clarification_items


def test_capacity_preserves_tied_limits_and_separate_clarifications():
    result = assess_financial_capacity({**BASE, "F02": "unsure", "F03": "lt_1m",
                                       "F05": "increase_risk"})
    assert result.volatility == .04
    assert result.binding_items == ("F02", "F03")
    assert result.clarification_items == ("F02",)
    assert set(result.caps) == set(BASE)


@pytest.mark.parametrize("bad", [{"F02": ["none"]}, {"F02": "invalid"}, {}])
def test_missing_or_invalid_capacity_answers_fail(bad):
    unchecked = {key: value for key, value in BASE.items() if key != "F02"}
    with pytest.raises(ValueError, match="F02"):
        assess_financial_capacity({**unchecked, **bad})
