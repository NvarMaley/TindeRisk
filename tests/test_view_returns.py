import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import pytest

from src.view_returns import estimate_relative_q, monthly_view_outcomes


def test_monthly_outcomes_skip_entry_return_incomplete_month_and_cutoff():
    sessions = mcal.get_calendar("NYSE").valid_days("2018-01-01", "2018-03-31", tz=None)
    daily = pd.DataFrame({"XLF": .001, "XLE": .003}, index=sessions)
    daily.loc[sessions[0], "XLE"] = .5
    daily = daily.drop(pd.Timestamp("2018-02-28"))
    p = pd.DataFrame({"XLE": [1.0], "XLF": [-1.0]}, index=["sector_spread"])
    months = pd.period_range("2018-01", periods=3, freq="M")
    outcomes = monthly_view_outcomes(dict.fromkeys(months, p), daily, before_month="2018-03")
    assert outcomes.index.tolist() == [months[0]]
    assert outcomes["sector_spread"].item() == pytest.approx(.002)


def test_q_filters_unstable_views_and_excludes_entire_final_test_month():
    months = pd.period_range("2014-01", periods=38, freq="M")
    history = pd.DataFrame(
        {"stable": [0.0001] * 24 + [0.0002] * 12 + [1., 2.],
         "unstable": [0.0001] * 24 + [-0.0002] * 12 + [1., 2.]},
        index=months,
    )
    p = pd.DataFrame({"XLE": [1., -1.], "XLF": [-1., 1.]}, index=["stable", "unstable"])
    dates = dict(validation_start="2016-01", final_test_start="2017-01-15",
                 decision_date="2017-02-01")
    active, q, report = estimate_relative_q(p, history, **dates)
    assert active.index.tolist() == q.index.tolist() == ["stable"]
    assert q.loc["stable"] == pytest.approx(.0336)
    assert report["status"].to_dict() == {"stable": "active", "unstable": "unstable"}
    assert report.loc["stable", "validation_months"] == 12
    history.loc["2017-01":] = -100
    pd.testing.assert_series_equal(estimate_relative_q(p, history, **dates)[1], q)


def test_q_removes_view_if_its_frozen_training_mean_cannot_beat_zero():
    months = pd.period_range("2014-01", periods=36, freq="M")
    p = pd.DataFrame({"XLE": [1.], "XLF": [-1.]}, index=["sector_spread"])
    history = pd.DataFrame({"sector_spread": np.repeat([.01, .0001], [24, 12])}, index=months)
    active, q, report = estimate_relative_q(
        p, history, validation_start="2016-01", final_test_start="2017-02", decision_date="2017-01-31",
    )
    assert active.empty and q.empty
    assert report["status"].item() == "unstable"


def test_unset_test_boundary_and_open_holding_month_leave_q_empty():
    months = pd.period_range("2014-01", periods=36, freq="M")
    p = pd.DataFrame({"XLE": [1.], "XLF": [-1.]}, index=["sector_spread"])
    history = pd.DataFrame({"sector_spread": .0001}, index=months)
    for boundary, status in [(None, "final_test_boundary_missing"), ("2017-01", "insufficient_history")]:
        active, q, report = estimate_relative_q(
            p, history, validation_start="2016-01", final_test_start=boundary, decision_date="2016-12-31",
        )
        assert active.shape == (0, 2) and q.empty
        assert report["status"].item() == status
