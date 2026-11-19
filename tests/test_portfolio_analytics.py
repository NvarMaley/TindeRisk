import numpy as np
import pandas as pd
import pytest

from src.optim import vol
from src.portfolio_analytics import information_ratio, risk_breakdown, risky_weight_herfindahl


def test_risk_analytics_keep_signed_euler_contributions_and_cash_neutral_concentration():
    weights = pd.Series({"A": .1, "B": .5})
    covariance = pd.DataFrame([[.04, -.016], [-.016, .01]], index=weights.index, columns=weights.index)
    risk = risk_breakdown(weights, covariance)
    assert risk.loc["A", "risk_contribution"] < 0
    assert risk["risk_contribution"].sum() == pytest.approx(vol(weights, covariance))
    assert risk["risk_share"].sum() == pytest.approx(1)
    assert risky_weight_herfindahl(weights) == pytest.approx(26 / 36)
    assert risky_weight_herfindahl(weights / 2) == pytest.approx(26 / 36)
    cash = risk_breakdown(weights * 0, covariance)
    assert cash["risk_contribution"].eq(0).all()
    assert cash["risk_share"].isna().all()


def test_information_ratio_uses_realized_active_returns_on_identical_dates():
    dates = pd.bdate_range("2020-01-02", periods=4)
    benchmark = pd.Series([.01, .02, -.01, 0], index=dates)
    active = pd.Series([.01, -.01, .02, .02], index=dates)
    assert information_ratio(benchmark + active, benchmark) == pytest.approx(
        np.sqrt(252) * active.mean() / active.std(ddof=1)
    )
    assert np.isnan(information_ratio(benchmark, benchmark))
    with pytest.raises(ValueError, match="aligned"):
        information_ratio(benchmark, benchmark.iloc[::-1])
