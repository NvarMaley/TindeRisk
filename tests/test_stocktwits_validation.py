import numpy as np
import pandas as pd
import pytest

from src.stocktwits_validation import high_low_spread, spread_summary


def test_missing_prices_do_not_change_the_selected_signal_legs():
    monthly = pd.DataFrame({
        "asset": ["XLE", "XLK", "XLF"], "available_month": pd.PeriodIndex(["2019-12"] * 3, freq="M"),
        "polarity": [.7, .2, -.4],
    })
    prices = pd.DataFrame({"XLE": [100., np.nan], "XLK": [100., 110.], "XLF": [100., 95.]},
                          index=pd.to_datetime(["2020-01-02", "2020-01-31"]))
    result = high_low_spread(monthly, prices, before_month="2020-02").iloc[0]
    assert (result["high_asset"], result["low_asset"], result["status"]) == ("XLE", "XLF", "unpriced")
    assert np.isnan(result["spread"])
    assert result["covered_sectors"] == 3


def test_spreads_skip_ties_and_the_excluded_month():
    monthly = pd.DataFrame({
        "asset": ["XLE", "XLF"] * 3,
        "available_month": pd.PeriodIndex(["2019-12"] * 2 + ["2020-01"] * 2 + ["2020-02"] * 2, freq="M"),
        "polarity": [.5, -.2, .3, .3, -.2, .4],
    })
    prices = pd.DataFrame({"XLE": [100., 121.], "XLF": [100., 110.]},
                          index=pd.to_datetime(["2020-01-02", "2020-01-31"]))
    result = high_low_spread(monthly, prices, before_month="2020-03")
    assert result["status"].tolist() == ["priced", "tied_extremes"]
    assert result["spread"].iloc[0] == pytest.approx(.11)
    summary = spread_summary(result, "2020-02")
    assert summary["priced_months"].tolist() == [1, 0]
    assert np.isnan(summary.loc["validation", "mean_spread"])
