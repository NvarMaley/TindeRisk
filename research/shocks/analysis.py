"""Shock definitions, dated sensitivities and CHF holding attribution."""

import numpy as np
import pandas as pd

ASSETS = ["SPY", "IEF", "GLD"]
FACTORS = ["equity", "nominal", "breakeven"]
TERMS = ["intercept", *FACTORS]
MIXES = {"Equal weight": np.ones(3) / 3, "60/40": np.array([0.6, 0.4, 0.0])}
EPISODES = {
    "2020 Q1": ("2020-01-01", "2020-03-31"),
    "2022": ("2022-01-01", "2022-12-31"),
    "March 2023": ("2023-03-01", "2023-03-31"),
}


def bp(value):
    return value / 10_000


SHOCKS = {
    "Equity fall": (-0.10, 0.0, 0.0, 0.0),
    "Nominal yield rise": (0.0, bp(100), 0.0, 0.0),
    "Breakeven rise": (0.0, 0.0, bp(50), 0.0),
    "USD depreciation": (0.0, 0.0, 0.0, -0.05),
    "Joint shock": (-0.10, bp(100), bp(50), -0.05),
}


def matched(frame):
    return frame[[*ASSETS, *FACTORS, "fx"]].notna().all(axis=1)


def fit(frame, minimum):
    """Multivariate OLS, with per-asset HAC intervals preserving gaps on the venue grid."""
    valid = matched(frame).to_numpy()
    n = int(valid.sum())
    if n < minimum:
        raise ValueError(f"Only {n} matched sessions, need {minimum}")
    x = np.column_stack((np.ones(n), frame.loc[valid, FACTORS]))
    y = frame.loc[valid, ASSETS].to_numpy()
    beta, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    if rank < len(TERMS):
        raise ValueError("Rank-deficient factor design")
    residual = y - x @ beta
    bread = np.linalg.inv(x.T @ x)
    se = np.zeros_like(beta)
    for i in range(len(ASSETS)):
        scores = np.zeros((len(frame), len(TERMS)))
        scores[valid] = x * residual[:, i, None]
        meat = scores.T @ scores
        for lag in range(1, min(6, len(frame))):
            cross = scores[lag:].T @ scores[:-lag]
            meat += (1 - lag / 6) * (cross + cross.T)
        se[:, i] = np.sqrt(
            np.maximum(np.diag(bread @ meat @ bread) * n / (n - rank), 0)
        )
    # SPY is the equity factor itself; enforce its known identity exactly.
    if not np.array_equal(x[:, 1], y[:, 0]):
        raise ValueError("Equity factor differs from SPY")
    beta[:, 0] = [0.0, 1.0, 0.0, 0.0]
    se[:, 0] = 0.0
    return beta, se, n


def training_window(frame, cutoff):
    return frame.loc[frame.index < cutoff].tail(252)


def scenarios(beta):
    """Reconcile weighted channel contributions against independent CHF revaluation."""
    rows = []
    totals = []
    for name, shock in SHOCKS.items():
        delta = np.array(shock[:3])
        fx = shock[3]
        channels = delta[:, None] * beta[1:]
        local = channels.sum(axis=0)
        asset_gross = (1 + delta @ beta[1:]) * (1 + fx)
        for mix, weights in {**MIXES, "CHF cash": np.zeros(3)}.items():
            cash_weight = 1.0 if mix == "CHF cash" else 0.0
            direct = cash_weight + weights @ asset_gross - 1
            contributions = []
            for i, asset in enumerate(ASSETS):
                w = weights[i]
                components = w * np.r_[channels[:, i], fx, local[i] * fx]
                row = dict(zip([*FACTORS, "fx", "interaction"], components))
                contribution = components.sum()
                rows.append(
                    dict(
                        scenario=name,
                        mix=mix,
                        asset=asset,
                        weight=w,
                        **row,
                        contribution=contribution,
                    )
                )
                contributions.append(contribution)
            if cash_weight:
                rows.append(
                    {
                        "scenario": name,
                        "mix": mix,
                        "asset": "CHF cash",
                        "weight": 1.0,
                        "equity": 0.0,
                        "nominal": 0.0,
                        "breakeven": 0.0,
                        "fx": 0.0,
                        "interaction": 0.0,
                        "contribution": 0.0,
                    }
                )
            error = sum(contributions) - direct
            if abs(error) > 1e-12:
                raise ValueError("Scenario contributions do not reconcile")
            totals.append(
                {
                    "scenario": name,
                    "mix": mix,
                    "portfolio_return": direct,
                    "interaction": weights @ (local * fx),
                    "reconciliation_error": error,
                }
            )
    return rows, totals


def episode_return(frame, start, end, weights):
    """Daily rebalancing in USD, followed by translation using the two endpoint fixings."""
    window = frame.loc[start:end]
    prior = frame.loc[frame.index < window.index[0]].iloc[-1]
    usd = window[ASSETS] @ weights
    if usd.isna().any() or pd.isna(prior.fixing) or pd.isna(window.fixing.iloc[-1]):
        return np.nan
    return (1 + usd).prod() * window.fixing.iloc[-1] / prior.fixing - 1
