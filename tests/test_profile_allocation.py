import numpy as np
import pandas as pd
import pytest

from src.profile_allocation import allocate_for_profile, allocate_for_risk_band
from src.profiling import RISK_BANDS, risk_target


@pytest.mark.parametrize("capacity,category", [
    (.03, None), (.04, "conservative"), (.059999, "conservative"),
    (.06, "balanced"), (.089999, "balanced"), (.09, "growth"),
    (.119999, "growth"), (.12, "aggressive"), (.15, "aggressive"),
])
def test_capacity_limits_the_target_at_all_borders(capacity, category):
    target = risk_target(1, .35, capacity)
    assert target.effective == capacity
    assert (target.band.key if target.band else None) == category


def test_achieved_volatility_is_recomputed_after_weight_and_leverage_limits():
    weights = pd.Series({"A": .6, "B": .4})
    covariance = pd.DataFrame(np.diag([.01, .01]), index=weights.index, columns=weights.index)
    achieved = allocate_for_profile(weights, covariance, risk_aversion=2.5,
                                    reference_sharpe=.35, capacity=.08,
                                    max_risky_exposure=1.5, max_etf_weight=.35)
    assert achieved.target.effective == .08
    assert achieved.risky_weights["A"] == pytest.approx(.35)
    assert achieved.cash_weight + achieved.risky_weights.sum() == pytest.approx(1)
    assert achieved.achieved_volatility == pytest.approx(np.sqrt(.01 * (.35**2 + (.4*.35/.6)**2)))
    full = allocate_for_profile(weights, covariance, risk_aversion=2.5,
                                reference_sharpe=.35, capacity=.08, max_risky_exposure=1.5)
    assert full.achieved_volatility == pytest.approx(.08)
    assert full.cash_weight < 0
    no_borrowing = allocate_for_profile(weights, covariance, risk_aversion=2.5,
                                        reference_sharpe=.35, capacity=.08)
    assert no_borrowing.cash_weight == pytest.approx(0)
    assert no_borrowing.achieved_volatility < .08


def test_band_allocations_default_to_cash_or_at_most_full_risky_exposure():
    weights = pd.Series({"A": 1.})
    covariance = pd.DataFrame([[.06**2]], index=weights.index, columns=weights.index)
    low = allocate_for_risk_band(weights, covariance, RISK_BANDS[0])
    assert low.allocation.achieved_volatility == pytest.approx(.05)
    assert low.allocation.cash_weight == pytest.approx(1 - .05 / .06)
    high = allocate_for_risk_band(weights, covariance, RISK_BANDS[-1])
    assert high.risky_exposure == pytest.approx(1.)
    assert high.allocation.cash_weight == pytest.approx(0.)
    assert high.target_shortfall == pytest.approx(.08)


def test_band_leverage_is_explicit_and_limited_by_gross_exposure():
    weights = pd.Series({"A": 1.})
    covariance = pd.DataFrame([[.06**2]], index=weights.index, columns=weights.index)
    levered = allocate_for_risk_band(weights, covariance, RISK_BANDS[-1], allow_leverage=True)
    assert levered.risky_exposure == pytest.approx(1.5)
    assert levered.allocation.cash_weight == pytest.approx(-.5)
    assert levered.allocation.achieved_volatility == pytest.approx(.09)
    assert levered.target_shortfall == pytest.approx(.05)
    with pytest.raises(ValueError, match="explicit boolean"):
        allocate_for_risk_band(weights, covariance, RISK_BANDS[-1], allow_leverage="false")
