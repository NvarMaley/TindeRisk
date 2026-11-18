import numpy as np
import pandas as pd
import pytest

from src.audit_data import audit_asset_sentiment, audit_market_bundle, audit_prices
from src.data_loader import validate_sentiment_firm_daily


@pytest.fixture
def bundle():
    dates = pd.to_datetime(["2024-07-02", "2024-07-03", "2024-07-05"])
    prices = pd.DataFrame({"SPY": [100., 101., 102.]}, index=dates)
    returns = prices.pct_change(fill_method=None).iloc[1:]
    rf = pd.DataFrame({"rf_daily": [0.001, 0.001]}, index=returns.index)
    return {"prices": prices, "returns": returns,
            "log_returns": np.log(prices).diff().iloc[1:], "rf_daily": rf,
            "excess_returns": returns.sub(rf.rf_daily, axis=0),
            "macro": pd.DataFrame({"VIXCLS": [3., 3.1]}, index=returns.index)}


def test_coherent_bundle_passes(bundle):
    assert audit_market_bundle(bundle, ["SPY"], ["VIXCLS"])["missing_sessions"] == 0


@pytest.mark.parametrize("artifact", ["returns", "log_returns", "excess_returns"])
def test_corrupted_arithmetic_fails(bundle, artifact):
    bundle[artifact].iloc[0, 0] += 0.1
    with pytest.raises(AssertionError):
        audit_market_bundle(bundle, ["SPY"], ["VIXCLS"])


@pytest.mark.parametrize("artifact", ["rf_daily", "macro"])
def test_calendar_misalignment_fails(bundle, artifact):
    bundle[artifact] = bundle[artifact].iloc[1:]
    with pytest.raises(ValueError):
        audit_market_bundle(bundle, ["SPY"], ["VIXCLS"])


def test_missing_configured_asset_fails(bundle):
    with pytest.raises(ValueError, match="universe"):
        audit_market_bundle(bundle, ["SPY", "IEF"], ["VIXCLS"])


@pytest.mark.parametrize("value", [np.nan, np.inf, 0., -10.])
def test_invalid_price_fails(bundle, value):
    bundle["prices"].iloc[0, 0] = value
    with pytest.raises(ValueError, match="finite"):
        audit_prices(bundle["prices"])


def test_duplicate_and_unsorted_prices_fail(bundle):
    prices = bundle["prices"]
    for broken in [pd.concat([prices, prices.iloc[[0]]]), prices.iloc[::-1]]:
        with pytest.raises(ValueError, match="unique and sorted"):
            audit_prices(broken)


@pytest.fixture
def sentiment():
    return pd.DataFrame({"asset": ["XLK", "XLK"],
                         "date": pd.to_datetime(["2024-07-02", "2024-07-05"]),
                         "available_date": pd.to_datetime(["2024-07-03", "2024-07-08"]),
                         "Nbullish": [3, 0], "Nbearish": [1, 0],
                         "N": [5, 2], "polarity": [0.5, np.nan]})


def test_sentiment_gaps_are_reported_not_zero_filled(sentiment):
    before = sentiment.copy(deep=True)
    report = audit_asset_sentiment(sentiment, ["XLK"])
    assert report["coverage"]["XLK"]["sessions_without_observation"] == 1
    assert report["coverage"]["XLK"]["undefined_polarity_rows"] == 1
    pd.testing.assert_frame_equal(sentiment, before)


def test_same_day_sentiment_is_rejected(sentiment):
    sentiment.loc[0, "available_date"] = sentiment.loc[0, "date"]
    with pytest.raises(ValueError, match="availability"):
        audit_asset_sentiment(sentiment, ["XLK"])


def test_sentiment_missing_asset_or_schema_fails(sentiment):
    with pytest.raises(ValueError, match="cover"):
        audit_asset_sentiment(sentiment, ["XLK", "XLF"])
    with pytest.raises(ValueError, match="schema"):
        audit_asset_sentiment(sentiment.drop(columns="N"), ["XLK"])


@pytest.mark.parametrize("column,value", [("N", np.inf), ("Nbullish", 1.5), ("Nbearish", -1), ("polarity", 0.1)])
def test_invalid_sentiment_counts_or_polarity_fail(sentiment, column, value):
    frame = sentiment.rename(columns={"asset": "ticker"}).astype({column: float})
    frame.loc[0, column] = value
    with pytest.raises(ValueError):
        validate_sentiment_firm_daily(frame)


def test_missing_column_and_duplicate_sentiment_fail(sentiment):
    frame = sentiment.rename(columns={"asset": "ticker"})
    with pytest.raises(ValueError, match="missing columns"):
        validate_sentiment_firm_daily(frame.drop(columns="N"))
    with pytest.raises(ValueError, match="duplicate"):
        validate_sentiment_firm_daily(pd.concat([frame, frame.iloc[[0]]]))
