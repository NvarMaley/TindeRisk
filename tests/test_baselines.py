import numpy as np
import pandas as pd
import pytest

from src.baselines import (
    apply_monthly_targets, benchmark_60_40_weights, minimum_variance_weights, monthly_decision_closes,
    simulate_monthly_targets,
)


def test_minimum_variance_with_binding_cap():
    # The unconstrained inverse-variance allocation to A would be 75%.
    cov = pd.DataFrame(np.diag([1., 4., 6.]), index=list("ABC"), columns=list("ABC"))
    expected = pd.Series([.5, .3, .2], index=cov.columns)
    pd.testing.assert_series_equal(minimum_variance_weights(cov, .5), expected, atol=1e-7)
    pd.testing.assert_series_equal(minimum_variance_weights(cov * 252, .5), expected, atol=1e-7)
    with pytest.raises(ValueError, match="infeasible"):
        minimum_variance_weights(cov, .30)


def test_holdings_drift_and_close_rebalance_only_applies_next_session():
    dates = pd.to_datetime(["2020-01-29", "2020-01-30", "2020-01-31", "2020-02-03"])
    returns = pd.DataFrame({"A": [.2, .1, -.1], "B": [0., 0., .2]}, index=dates[1:])
    targets = pd.DataFrame({"A": [.5, 0.], "B": [.5, 1.]}, index=dates[[0, 2]])
    result = apply_monthly_targets(returns, targets)
    np.testing.assert_allclose(result["wealth"], [1.10, 1.16, 1.392])
    np.testing.assert_allclose(result["gross_return"], [.1, .06 / 1.1, .2])
    with pytest.raises(ValueError, match="precede"):
        apply_monthly_targets(returns, targets.set_axis(dates[[1, 2]]))


def test_60_40_uses_nyse_month_end_targets_and_skips_the_final_close():
    sessions = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-03"])
    targets = monthly_decision_closes(sessions)
    assert targets.tolist() == pd.to_datetime(["2019-12-31", "2020-01-31"]).tolist()
    assert monthly_decision_closes(sessions[:2]).tolist() == [pd.Timestamp("2019-12-31")]
    pd.testing.assert_series_equal(benchmark_60_40_weights(), pd.Series({"SPY": .6, "IEF": .4}))
    with pytest.raises(ValueError, match="all scheduled NYSE sessions"):
        monthly_decision_closes(sessions[[0, 2]])


def test_small_rebalance_is_skipped_unless_drift_would_exceed_the_cap():
    dates = pd.to_datetime(["2019-12-31", "2020-01-31", "2020-02-03"])
    returns = pd.DataFrame({"A": [.04, 0.], "B": [0., .1]}, index=dates[1:])
    targets = pd.DataFrame(.5, index=dates[:2], columns=returns.columns)
    skipped = simulate_monthly_targets(returns, targets, min_turnover=.05, cost_bps=10.)
    forced = simulate_monthly_targets(returns, targets, min_turnover=.05, cost_bps=10., max_weight=.5)
    assert skipped.turnover.eq(0).all()
    turnover = 2 * (.52 / 1.02 - .5)
    assert forced.turnover.iat[0] == pytest.approx(turnover)
    assert forced.net_wealth.iat[0] == pytest.approx(1.02 * (1 - .001 * turnover))
    assert forced.gross_return.iat[1] == pytest.approx(.05)
    assert skipped.gross_return.iat[1] < forced.gross_return.iat[1]
    no_cost = simulate_monthly_targets(returns, targets)
    pd.testing.assert_series_equal(no_cost.net_wealth, no_cost.wealth, check_names=False)
