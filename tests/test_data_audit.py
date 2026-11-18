import pandas as pd
import pytest

from src.audit_data import audit_prices


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
