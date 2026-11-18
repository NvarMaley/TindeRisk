import numpy as np
import pandas as pd
import pytest

from src.data_loader import (
    aggregate_sentiment_to_assets,
    apply_publication_lag,
    clean_market_data,
    transform_macro_series,
    validate_sentiment_firm_daily,
)


def _sentiment_frame():
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "AAPL"],
            "date": pd.to_datetime(["2020-01-03", "2020-01-03", "2020-01-06"]),
            "Nbullish": [3, 2, 0],
            "Nbearish": [1, 2, 0],
            "N": [5, 4, 2],
            "polarity": [0.5, 0.0, np.nan],
            "available_date": pd.to_datetime(["2020-01-06", "2020-01-06", "2020-01-07"]),
        }
    )


def test_sentiment_contract_rejects_duplicates_and_impossible_counts():
    frame = _sentiment_frame().drop(columns="available_date")
    validate_sentiment_firm_daily(frame)

    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_sentiment_firm_daily(duplicate)

    impossible = frame.copy()
    impossible.loc[0, "Nbullish"] = 10
    with pytest.raises(ValueError, match="cannot exceed"):
        validate_sentiment_firm_daily(impossible)


def test_sentiment_aggregation_preserves_counts_and_availability():
    result = aggregate_sentiment_to_assets(
        _sentiment_frame(), {"AAPL": "XLK", "MSFT": "XLK"}
    )

    first = result.iloc[0]
    assert first["asset"] == "XLK"
    assert first["available_date"] == pd.Timestamp("2020-01-06")
    assert first["Nbullish"] == 5
    assert first["Nbearish"] == 3
    assert first["N"] == 9
    assert first["polarity"] == pytest.approx(0.25)
    assert np.isnan(result.iloc[1]["polarity"])


def test_publication_lags_prevent_look_ahead():
    daily = pd.Series([1.0], index=pd.to_datetime(["2024-01-05"]))
    monthly = pd.Series([2.0], index=pd.to_datetime(["2024-01-01"]))

    assert apply_publication_lag(daily, monthly=False).index[0] == pd.Timestamp("2024-01-08")
    assert apply_publication_lag(monthly, monthly=True).index[0] == pd.Timestamp("2024-02-29")


def test_macro_transformations_use_observation_order():
    monthly = pd.Series(range(100, 113), index=pd.date_range("2023-01-01", periods=13, freq="MS"))
    assert transform_macro_series(monthly, "yoy").iloc[0] == pytest.approx(0.12)
    assert transform_macro_series(monthly, "diff12").iloc[0] == pytest.approx(12)
    with pytest.raises(ValueError, match="unknown"):
        transform_macro_series(monthly, "mystery")


def test_clean_market_data_uses_complete_prices_and_aligns_risk_free():
    dates = pd.date_range("2024-01-02", periods=4, freq="B")
    prices = pd.DataFrame(
        {"XLK": [100.0, 101.0, np.nan, 103.0], "IEF": [90.0, 90.5, 91.0, 91.5]},
        index=dates,
    )
    rf = pd.Series([5.0, 5.1], index=dates[[0, 2]])

    result = clean_market_data(prices, rf)

    assert len(result["prices"]) == 3
    assert len(result["returns"]) == 2
    assert result["returns"].notna().all().all()
    assert result["rf_daily"].notna().all().all()
    pd.testing.assert_frame_equal(
        result["excess_returns"],
        result["returns"].sub(result["rf_daily"]["rf_daily"], axis=0),
    )
