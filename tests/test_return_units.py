import numpy as np
import pandas as pd
import pytest

from src.check_return_units import check_return_units
from src.descriptive import descriptive_statistics


@pytest.fixture
def daily_inputs():
    dates = pd.bdate_range("2020-01-01", periods=20)
    simple = pd.DataFrame({"A": [.02, -.02] * 10, "B": [.01, -.01] * 10}, index=dates)
    cash = pd.Series([.0001, .0003] * 10, index=dates)
    return simple, np.log1p(simple), simple.sub(cash, axis=0), cash


def test_annual_variance_volatility_and_geometric_return(daily_inputs):
    simple, _, _, cash = daily_inputs
    result = check_return_units(*daily_inputs)
    # The daily portfolio alternates +1.5% and -1.5% at constant weights.
    expected_variance = 252 * 20 * .015**2 / 19
    assert result["equal_weight_annual_variance"] == pytest.approx(expected_variance)
    assert result["equal_weight_annual_volatility"] == pytest.approx(expected_variance**.5)
    stats = descriptive_statistics(simple, cash)
    assert simple["A"].mean() * 252 == 0
    assert stats.at["A", "ann_return"] == pytest.approx((1 - .02**2)**126 - 1)
    assert stats.at["A", "sharpe"] == pytest.approx(-.0002 * 252 / (252 * 20 * .02**2 / 19)**.5)


@pytest.mark.parametrize("corruption", ["simple_as_log", "annual_cash", "reversed_labels"])
def test_audit_rejects_unit_and_alignment_errors(daily_inputs, corruption):
    simple, log, excess, cash = daily_inputs
    if corruption == "simple_as_log":
        log = simple
    elif corruption == "annual_cash":
        cash = cash * 252
    else:
        excess = excess[["B", "A"]]
    match = {"simple_as_log": "simple/log", "annual_cash": "simple/excess",
             "reversed_labels": "align"}[corruption]
    with pytest.raises((AssertionError, ValueError), match=match):
        check_return_units(simple, log, excess, cash)
