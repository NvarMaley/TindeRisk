import numpy as np
import pandas as pd
import pytest

from src.backtest import aligned_strategy_returns, audit_strategy_calendar


def test_common_comparison_does_not_silently_intersect_or_drop_missing_dates():
    dates = pd.date_range("2020-04-01", periods=3, freq="B", name="date")
    streams = {
        "classic": pd.Series([.01, .03], index=dates[[0, 2]]),
        "benchmark_60_40": pd.Series([0., np.nan, .02], index=dates),
    }
    strategies = ["classic", "erc", "benchmark_60_40"]
    audit = audit_strategy_calendar(streams, dates, strategies)
    assert audit["status"].tolist() == ["incomplete", "absent", "incomplete"]
    assert audit["missing_sessions"].tolist() == [1, 3, 0]
    assert audit["invalid_returns"].tolist() == [0, 0, 1]
    with pytest.raises(ValueError, match="classic, erc, benchmark_60_40"):
        aligned_strategy_returns(streams, dates, strategies)


def test_extra_history_is_reported_and_kept_out_of_the_fixed_comparison():
    extended = pd.date_range("2020-04-01", periods=6, freq="B", name="date")
    common = extended[1:-1]
    streams = {
        "erc": pd.Series(np.arange(6) / 100, index=extended),
        "classic": pd.Series(.02, index=common),
    }
    strategies = ["classic", "erc"]
    audit = audit_strategy_calendar(streams, common, strategies)
    assert audit["outside_sessions"].to_dict() == {"classic": 0, "erc": 2}
    report = aligned_strategy_returns(streams, common, strategies)
    assert report.columns.tolist() == strategies
    pd.testing.assert_index_equal(report.index, common)
    pd.testing.assert_series_equal(report["erc"], streams["erc"].loc[common].rename("erc"))
    assert len(streams["erc"]) == len(extended)


def test_duplicate_dates_are_rejected_before_comparing_returns():
    dates = pd.date_range("2020-04-01", periods=3, freq="B")
    with pytest.raises(ValueError, match="unique session dates"):
        audit_strategy_calendar({"erc": pd.Series(.03, index=dates.repeat(2))}, dates, ["erc"])
