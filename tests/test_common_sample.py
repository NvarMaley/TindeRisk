import numpy as np
import pandas as pd
import pytest

from src.build_common_sample import select_common_dates, sentiment_arrivals


def test_warmup_is_strictly_prior_and_incomplete_session_excluded():
    dates = pd.bdate_range("2020-01-01", periods=6)
    returns = pd.DataFrame({"ETF": [0.01] * 6}, index=dates)
    rf = returns * 0.01
    result = select_common_dates(returns, rf, start=dates[0], end=None,
                                 window_days=3, completed_dates=dates[:-1])
    pd.testing.assert_index_equal(result, dates[3:5])


def test_missing_market_input_is_not_silently_dropped():
    dates = pd.bdate_range("2020-01-01", periods=6)
    returns = pd.DataFrame({"ETF": [0.01] * 6}, index=dates)
    rf = returns * 0.01
    returns.iloc[1, 0] = np.nan
    with pytest.raises(ValueError, match="complete"):
        select_common_dates(returns, rf, start=dates[0], end=None,
                            window_days=3, completed_dates=dates)


def test_sentiment_counts_aggregate_by_availability_without_filling():
    # Friday and weekend messages all become usable on Monday.
    sentiment = pd.DataFrame({"asset": ["ETF", "ETF", "ETF"],
        "available_date": pd.to_datetime(["2024-07-08", "2024-07-08", "2024-07-10"]),
        "Nbullish": [3, 0, 0], "Nbearish": [1, 2, 0], "N": [4, 2, 5]})
    dates = pd.bdate_range("2024-07-05", periods=4)
    result = sentiment_arrivals(sentiment, dates, ["ETF"])
    assert np.isnan(result["sentiment_polarity"].loc["2024-07-05", "ETF"])
    assert result["sentiment_polarity"].loc["2024-07-08", "ETF"] == 0
    assert result["sentiment_messages"].loc["2024-07-08", "ETF"] == 6
    assert not result["sentiment_observed"].loc["2024-07-09", "ETF"]
    assert result["sentiment_observed"].loc["2024-07-10", "ETF"]
    assert not result["sentiment_labelled"].loc["2024-07-10", "ETF"]


def test_configured_period_bounds_are_preserved():
    dates = pd.bdate_range("2020-01-01", periods=6)
    returns = pd.DataFrame({"ETF": [0.01] * 6}, index=dates)
    result = select_common_dates(returns, returns * 0, start=dates[3], end=dates[4],
                                 window_days=2, completed_dates=dates)
    pd.testing.assert_index_equal(result, dates[3:5])


def test_stocktwits_cutoff_excludes_later_arrivals_without_dropping_market_dates():
    dates = pd.bdate_range("2020-03-31", periods=3)
    sentiment = pd.DataFrame({
        "asset": "ETF", "date": pd.to_datetime(["2020-03-30", "2020-03-31", "2020-04-01"]),
        "available_date": dates, "Nbullish": 3, "Nbearish": 1, "N": 4,
    })
    result = sentiment_arrivals(sentiment, dates, ["ETF"], coverage_end="2020-03-31")
    for frame in result.values():
        pd.testing.assert_index_equal(frame.index, dates)
    assert result["sentiment_polarity"]["ETF"].iloc[0] == .5
    assert result["sentiment_polarity"]["ETF"].iloc[1:].isna().all()
    assert not result["sentiment_labelled"]["ETF"].iloc[1:].any()
