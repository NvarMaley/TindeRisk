import numpy as np
import pandas as pd
import pytest

from src.ln7 import (
    abnormal_returns, check_aapl_ar_reference, check_spy_reference, event_paths,
    ln7_reference_returns, reconstruct_events,
)


def test_spy_reference_uses_the_previous_close_and_reports_missing_dates(tmp_path):
    path = tmp_path / "adjusted.csv"
    pd.DataFrame({"date": ["2009-12-31", "2010-01-04"], "SPY": [100, 101.696]}).to_csv(
        path, index=False
    )
    result = check_spy_reference(path)
    assert result["matches"].tolist() == [True, False, False, False, False]
    assert result["reproduced"].iloc[0] == pytest.approx(0.016960)


def test_aapl_reference_uses_prior_close_and_reports_incomplete_coverage():
    closes = pd.DataFrame({
        "AAPL": [100., 110., 121., 144.], "SPY": [100., 102., 101., 110.],
    }, index=pd.to_datetime(["2009-12-31", "2010-01-04", "2010-06-01", "2011-01-03"]))
    returns = ln7_reference_returns(closes)
    initial_apple = returns.loc[returns["ticker"].eq("AAPL"), "daily_return"].iloc[0]
    assert initial_apple == pytest.approx(.10)
    comparison = check_aapl_ar_reference(returns)
    assert len(comparison) == 5 and comparison["calculated_ar"].count() == 1
    expected = (comparison["calculated_ar"].iloc[0] - comparison["lab_ar"].iloc[0]) * 10_000
    assert comparison["difference_bps"].iloc[0] == pytest.approx(expected)
    assert not comparison["matches_at_6dp"].any()


def test_abnormal_return_respects_ticker_and_lab_window():
    dates = ["2009-12-31", "2010-06-01", "2010-12-31", "2011-01-03", "2011-01-04"]
    prices = pd.DataFrame({
        "ticker": ["SPY"] * 5 + ["AAPL"] * 5, "date": dates * 2,
        "daily_return": [0.01, 0.02, -0.03, 0.04, 0.05, 8, 0.05, -0.05, 0.09, 10],
    })
    returns = abnormal_returns(prices.sample(frac=1, random_state=1))
    apple = returns.loc[returns["ticker"].eq("AAPL"), "AR"].reset_index(drop=True)
    assert apple.iloc[:3].isna().all()
    assert apple.iloc[3] == pytest.approx(0, abs=1e-12)
    assert abs(apple.iloc[4]) > 1


def test_reconstruction_finds_volume_spike_and_classifies_abnormal_polarity():
    market = np.tile([-0.2, 0.3, 0.5, -0.4], 10)
    polarity = 0.1 + 0.5 * market
    polarity[35] += 0.2
    index = np.arange(len(market))
    messages = pd.DataFrame({
        "ticker": "AAPL", "date": pd.date_range("2010-12-20", periods=len(market)),
        "Polarity": polarity, "market_polarity": market, "N": 100 + index % 5,
        "Nbullish": 30, "Nbearish": 10, "total_vol_tweet": 1000 + 25 * (index % 7),
        "businessday": True,
    })
    messages.loc[35, "N"] = 1100
    panel = reconstruct_events(messages)
    assert panel.loc[35, "event_type"] == "Good"
    assert panel.loc[35, "AP"] == pytest.approx(0.2)
    assert panel.loc[35, "count_polarity"] == pytest.approx(0.5)


def test_event_paths_sum_in_session_order_and_reject_missing_residuals():
    panel = pd.DataFrame({
        "ticker": "AAPL", "date": pd.date_range("2011-01-06", periods=4),
        "market_return": [0.02, 0.01, np.nan, 0.02],
        "businessday": [True, True, False, True],
        "event_type": [None, "Good", None, None],
        "AR": [0.1, 0.2, 999, -0.1], "AP": [0.01, 0.1, 999, 0.2],
    })
    result = event_paths(panel, radius=1)
    assert result["relative_session"].tolist() == [-1, 0, 1]
    assert result["CAR"].tolist() == pytest.approx([0.1, 0.3, 0.2])
    assert result["CAP"].tolist() == pytest.approx([0.01, 0.11, 0.31])
    panel.loc[3, "AP"] = np.nan
    assert event_paths(panel, radius=1).empty
