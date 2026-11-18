import numpy as np
import pandas as pd
import pytest

from src.baselines import apply_monthly_targets, minimum_variance_weights


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
