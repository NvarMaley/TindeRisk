import numpy as np
import pandas as pd
import pytest

from src.check_conventions import validate_quote_metadata, verify_adjusted_returns
from src.data_loader import clean_market_data, transform_macro_series


def test_currency_and_timezone_are_checked_not_assumed():
    assert validate_quote_metadata({"currency": "USD", "exchangeTimezoneName": "America/New_York"}, "USD")["currency"] == "USD"
    for metadata in [{}, {"currency": "CHF"}, {"currency": "USD", "exchangeTimezoneName": "Europe/Zurich"}]:
        with pytest.raises(ValueError):
            validate_quote_metadata(metadata, "USD")


def test_adjustment_comparison_accepts_constant_rebasing_not_wrong_returns():
    prices = pd.DataFrame({"ETF": [100., 102., 101.]}, index=pd.date_range("2019-01-02", periods=3))
    verify_adjusted_returns(prices, prices * 0.8)
    broken = prices.copy()
    broken.iloc[1, 0] = 110
    with pytest.raises(AssertionError):
        verify_adjusted_returns(prices, broken)


def test_percent_rate_and_return_units():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
    prices = pd.DataFrame({"ETF": [100., 101.]}, index=dates)
    outputs = clean_market_data(prices, pd.Series([5., 5.], index=dates))
    assert outputs["returns"].iloc[0, 0] == pytest.approx(0.01)
    assert outputs["log_returns"].iloc[0, 0] == pytest.approx(np.log(1.01))
    assert outputs["rf_daily"].iloc[0, 0] == pytest.approx(0.05 / 252)
    assert outputs["excess_returns"].iloc[0, 0] == pytest.approx(0.01 - 0.05 / 252)


def test_inflation_is_decimal_but_unemployment_change_is_percentage_points():
    dates = pd.date_range("2020-01-01", periods=13, freq="MS")
    index = pd.Series([100.] * 12 + [105.], index=dates)
    unemployment = pd.Series([5.] * 12 + [6.], index=dates)
    assert transform_macro_series(index, "yoy").iloc[0] == pytest.approx(0.05)
    assert transform_macro_series(unemployment, "diff12").iloc[0] == pytest.approx(1.)
