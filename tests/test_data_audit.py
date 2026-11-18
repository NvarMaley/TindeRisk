import pandas as pd
import pytest

from src.audit_data import audit_prices
from src.data_loader import next_market_session


def test_sentiment_availability_skips_holiday_and_weekend():
    dates = pd.to_datetime(["2024-07-03", "2024-07-04", "2024-07-05", "2012-10-26"])
    expected = pd.to_datetime(["2024-07-05", "2024-07-05", "2024-07-08", "2012-10-31"])
    pd.testing.assert_index_equal(next_market_session(dates), expected, check_names=False)


def test_exchange_holiday_is_not_a_gap():
    prices = pd.DataFrame({"SPY": [100., 101.]}, index=pd.to_datetime(["2024-07-03", "2024-07-05"]))
    assert audit_prices(prices)["missing_sessions"] == 0


def test_missing_session_is_rejected():
    prices = pd.DataFrame({"SPY": [100., 101.]}, index=pd.to_datetime(["2024-07-02", "2024-07-05"]))
    with pytest.raises(ValueError, match="calendar mismatch"):
        audit_prices(prices)


def test_outliers_are_reported_not_deleted():
    prices = pd.DataFrame({"SPY": [100., 140.]}, index=pd.to_datetime(["2024-07-03", "2024-07-05"]))
    report = audit_prices(prices)
    assert len(report["outliers_retained_for_review"]) == 1
    assert len(prices) == 2
