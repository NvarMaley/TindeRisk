import numpy as np
import pandas as pd
import pytest

from src.view_uncertainty import estimate_omega


P = pd.DataFrame([[1., -1., 0.], [0., 1., -1.]],
                 index=pd.Index(["first", "second"], name="view"), columns=["XLE", "XLF", "XLK"])
SIGMA = pd.DataFrame(np.diag([.02, .01, .03]), index=["XLK", "XLF", "XLE"],
                     columns=["XLK", "XLF", "XLE"])
DIAGNOSTICS = pd.DataFrame({"status": "active", "validation_mse": [1e-7, 0.]},
                           index=["first", "second"])


def test_omega_uses_labelled_covariance_prior_floor_and_annual_error_variance():
    omega = estimate_omega(P, SIGMA, DIAGNOSTICS.iloc[::-1], tau=.05)
    assert omega.index.equals(P.index) and omega.columns.equals(P.index)
    assert omega.loc["first", "first"] == pytest.approx(252**2 * 1e-7)
    assert omega.loc["second", "second"] == pytest.approx(.05 * (.01 + .02))
    assert omega.loc["first", "second"] == 0
    larger = estimate_omega(P, SIGMA, DIAGNOSTICS, tau=.05, error_multiplier=2)
    assert larger.loc["first", "first"] == 2 * omega.loc["first", "first"]
    assert larger.loc["second", "second"] == omega.loc["second", "second"]


def test_omega_is_empty_without_an_active_view_and_rejects_missing_evidence():
    assert estimate_omega(P.iloc[:0], pd.DataFrame(), pd.DataFrame(), tau=.05).shape == (0, 0)
    with pytest.raises(ValueError, match="observed validation MSE"):
        estimate_omega(P, SIGMA, DIAGNOSTICS.iloc[:1], tau=.05)
    with pytest.raises(ValueError, match="observed validation MSE"):
        estimate_omega(P, SIGMA, DIAGNOSTICS.assign(status="unstable"), tau=.05)


def test_omega_rejects_invalid_uncertainty_or_covariance():
    with pytest.raises(ValueError, match="positive and finite"):
        estimate_omega(P, SIGMA, DIAGNOSTICS, tau=.05, error_multiplier=0)
    with pytest.raises(ValueError, match="must cover"):
        estimate_omega(P, SIGMA.drop(columns="XLK"), DIAGNOSTICS, tau=.05)
    with pytest.raises(ValueError, match="positive, finite prior variance"):
        estimate_omega(P, SIGMA * 0, DIAGNOSTICS, tau=.05)
