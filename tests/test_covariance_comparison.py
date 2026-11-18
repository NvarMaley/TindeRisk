import numpy as np
import pandas as pd
import pytest

from src.covariance_comparison import compare_covariances


def test_turnover_after_drift_and_partial_month_scoring():
    dates = pd.to_datetime(["2020-01-24", "2020-01-27", "2020-01-28", "2020-01-29",
                            "2020-01-30", "2020-02-03", "2020-02-04"])
    history = pd.DataFrame({"A": [.02, .01, -.02, .15, .03, -.03, .01],
                            "B": [.01, -.01, .01, 0., .02, .02, -.03]}, index=dates)
    realized = history.iloc[3:]
    closes = dates[[2, 4]]
    month_end = pd.Timestamp("2020-02-28")
    result, weights = compare_covariances(history, realized, closes, month_end, 3, .5)
    first_day = .075
    second_day = (1.15 * .03 + .02) / 2.15
    expected_vol = np.std([first_day, second_day], ddof=1) * np.sqrt(252)
    drifted_a = (1.15 * 1.03) / (1.15 * 1.03 + 1.02)
    expected_turnover = 2 * abs(.5 - drifted_a)

    for estimator in ("sample", "lw_constcorr"):
        rows = result.loc[estimator]
        np.testing.assert_allclose(weights.loc[estimator], .5)
        assert pd.isna(rows.iloc[0].turnover_two_way)
        assert rows.iloc[0].first_session == dates[3]
        assert rows.iloc[0].realized_vol == pytest.approx(expected_vol)
        assert rows.iloc[1].turnover_two_way == pytest.approx(expected_turnover)
        assert not rows.iloc[1].complete_month
        assert pd.isna(rows.iloc[1].vol_error)

    expected_cov = np.cov(history.iloc[:3].to_numpy().T) * 252
    assert result.loc[("sample", closes[0]), "predicted_vol"] == pytest.approx(
        np.sqrt(np.array([.5, .5]) @ expected_cov @ np.array([.5, .5]))
    )
