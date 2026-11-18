import numpy as np
import pandas as pd
import pytest

from src.signal_validation import (
    ln7_event_rank_tests, matched_forward_returns, monthly_tag_polarity, validate_predictor,
)


def test_forward_month_uses_first_and_last_session_closes_and_skips_partial_month():
    tags = pd.DataFrame({
        "asset": ["XLK", "XLK", "XLK"], "available_date": pd.to_datetime(
            ["2019-12-31", "2019-12-31", "2020-01-02"]
        ),
        "Nbullish": [9, 0, 1], "Nbearish": [0, 1, 0],
    })
    prices = pd.DataFrame({"XLK": [50., 100., 121., 100.], "SPY": [100., 100., 110., 100.]},
                          index=pd.to_datetime(["2019-12-31", "2020-01-02", "2020-01-31", "2020-02-03"]))
    pairs = matched_forward_returns(monthly_tag_polarity(tags), prices, "SPY")
    assert pairs["target_month"].tolist() == [pd.Period("2020-01")]
    assert pairs["relative_return"].item() == pytest.approx(.11)
    assert pairs["polarity"].item() == pytest.approx(.8)


def test_predictor_uses_training_fit_and_ignores_data_after_validation():
    periods = pd.period_range("2010-01", periods=62, freq="M")
    x = np.tile(np.linspace(-.9, .9, 10), 7)[:len(periods)]
    y = .1 * x + .005 * np.sin(np.arange(len(x)))
    y[-2:] = 10000
    pairs = pd.DataFrame({"asset": "XLK", "target_month": periods, "polarity": x, "relative_return": y})
    report = validate_predictor(pairs, "2013-05", "2014-12")
    row = report.iloc[0]
    assert (row["train_months"], row["validation_months"]) == (40, 20)
    assert row["train_slope"] == pytest.approx(.1, abs=.002)
    assert row["huber_mae"] < row["mean_mae"]
    assert row["rank_effect"] == 1

    changed_validation = pairs.copy()
    changed_validation.loc[40:, "relative_return"] *= -1
    changed = validate_predictor(changed_validation, "2013-05", "2014-12").iloc[0]
    assert changed["train_slope"] == row["train_slope"]
    assert changed["validation_slope"] < 0
    assert changed["rank_effect"] == -1


def test_ln7_rank_test_reports_group_sizes_and_signed_effect_at_each_horizon():
    paths = pd.DataFrame({
        "relative_session": [-5] * 10, "event_type": ["Good"] * 5 + ["Neutral"] * 5,
        "CAP": [1.] * 5 + [0.] * 5, "CAR": [0.] * 10,
    })
    report = ln7_event_rank_tests(paths)
    assert len(report) == 18
    comparison = report.query("session == -5 and measure == 'CAP' and first == 'Good' and second == 'Neutral'").iloc[0]
    assert comparison["rank_effect"] == 1
    assert comparison["holm_p"] > comparison["nominal_p"]
    assert report.query("second == 'Bad'")["holm_p"].isna().all()
