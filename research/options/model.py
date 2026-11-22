"""Household scoring, joint market paths and dated spending capacity in CHF."""

from itertools import combinations

import numpy as np
import pandas as pd

ASSETS = ["SPY", "IEF", "GLD"]
WEIGHTS = ["w0", "w1", "w2"]
CAPITAL, SLEEVE, RESERVE = 50000.0, 35000.0, 15000.0
FEE = 0.001
TOL = 1e-9


def eligible(rows, cap):
    """Admit only financed options with the specified mandate and current risk estimate."""
    cols = rows[WEIGHTS]
    return rows.loc[
        np.isclose(rows.cap, cap)
        & rows.status.isin(["optimal", "optimal_inaccurate", "reference", "exact cash"])
        & (rows.residual <= 2e-7)
        & np.isclose(rows.reserve_chf, RESERVE)
        & np.isclose(rows.investable_chf, SLEEVE)
        & np.isclose(rows.fee, FEE * cols.sum(axis=1), rtol=0, atol=2e-7)
        & (rows.vol <= cap + 2e-7)
        & (rows.cash >= -2e-7)
        & (cols.min(axis=1) >= -2e-7)
        & (cols.max(axis=1) <= 0.6 + 2e-7)
        & (cols.sum(axis=1) <= 0.9 + 2e-7)
        & ((rows.cash + rows.fee + cols.sum(axis=1) - 1).abs() <= 2e-7)
    ].copy()


def comparison(dmean, dvar, profile):
    low, high = profile["low"], profile["high"]
    if (
        profile["status"] != "bounded"
        or high is None
        or not np.isfinite([low, high]).all()
        or low < 0
        or high < low
    ):
        return {
            "result": "unresolved",
            "left": np.nan,
            "right": np.nan,
            "crossover": np.nan,
        }
    left, right = dmean - low * dvar / 2, dmean - high * dvar / 2
    cross = 2 * dmean / dvar if abs(dvar) > 1e-15 else np.nan
    if max(abs(left), abs(right)) <= TOL:
        status = "numerical tie"
    elif min(left, right) > TOL:
        status = "first throughout"
    elif max(left, right) < -TOL:
        status = "second throughout"
    elif min(left, right) < -TOL and max(left, right) > TOL:
        status = "crossover"
    else:
        status = "tie at endpoint"
    return {
        "result": status,
        "left": left,
        "right": right,
        "crossover": cross if low <= cross <= high else np.nan,
    }


def pairs(rows, profile, fraction):
    for a, b in combinations(rows.itertuples(), 2):
        yield dict(
            first=a.arm,
            second=b.arm,
            **comparison(
                fraction * (a.net_mean - b.net_mean),
                fraction**2 * (a.vol**2 - b.vol**2),
                profile,
            ),
        )


def monthly_levels(market):
    selected = market[market.asset.isin(ASSETS)]
    usd = selected.pivot(index="session", columns="asset", values="adjusted_usd")[
        ASSETS
    ]
    fx = selected[selected.asset == "SPY"].set_index("session").chf_per_usd
    daily = usd.assign(FX=fx).sort_index()
    rows = []
    for month, g in daily.groupby(daily.index.to_period("M")):
        valid = g.tail(5).where(g.tail(5) > 0).dropna()
        if valid.empty:
            rows.append({"month": month, "mark": pd.NaT})
        else:
            rows.append(
                dict(month=month, mark=valid.index[-1], **valid.iloc[-1].to_dict())
            )
    monthly = pd.DataFrame(rows).set_index("month")
    monthly = monthly.reindex(
        pd.period_range(monthly.index.min(), monthly.index.max(), freq="M")
    )
    gross = monthly[ASSETS + ["FX"]] / monthly[ASSETS + ["FX"]].shift()
    return daily, monthly, gross


def year_blocks(gross, years=10, n=2000, seed=6202):
    values = gross.to_numpy()
    starts = np.array(
        [i for i in range(len(values) - 11) if np.isfinite(values[i : i + 12]).all()]
    )
    if not len(starts):
        raise ValueError("No complete joint 12-month blocks")
    picks = np.random.default_rng(seed).choice(starts, (n, years))
    # Holdings are constant within each year, deposits stay in CHF until review.
    # The product is identical to marking every ETF and FX position each month.
    by_start = np.zeros((len(values), 3))
    for i in starts:
        year = values[i : i + 12].prod(axis=0)
        by_start[i] = year[:3] * year[3]
    return by_start[picks], picks, starts


def simulate(gross, w, monthly_saving):
    w = np.asarray(w, float)
    n, years, _ = gross.shape
    holdings = np.zeros((n, 3))
    cash = np.full(n, SLEEVE)
    paths = []
    for y in range(years):
        before = holdings.sum(axis=1) + cash
        target = before[:, None] * w
        fee = np.abs(target - holdings).sum(axis=1) * FEE
        cash = before - target.sum(axis=1) - fee
        if cash.min() < -0.01:
            raise ValueError("Unfunded rebalance")
        holdings = target * gross[:, y, :]
        cash = cash + 12 * monthly_saving
        market_value = holdings.sum(axis=1)
        saleable = cash + market_value * (1 - FEE)
        paths.append(
            {
                "terminal": saleable,
                "cash": cash.copy(),
                "securities": market_value,
                "fee": fee,
                "withdrawal_resources": RESERVE + saleable if y == 0 else None,
            }
        )
    return paths


def gap_stats(terminal, target):
    gaps = np.maximum(target - terminal, 0)
    misses = gaps > 1e-6
    return {
        "paths": len(terminal),
        "gap_frequency": misses.mean(),
        "mean_gap_chf": gaps.mean(),
        "mean_gap_when_short_chf": gaps[misses].mean() if misses.any() else 0.0,
        "p10_chf": np.quantile(terminal, 0.1),
        "median_chf": np.median(terminal),
        "p90_chf": np.quantile(terminal, 0.9),
    }


def reverse(cash, securities, due, saleable=True):
    tradable = securities * (1 - FEE) if saleable else 0.0
    at_start = cash + tradable
    if at_start < due - 1e-7:
        status = "already short"
        boundary = np.nan
    elif cash > due + 1e-7:
        status = "no reachable shortfall"
        boundary = np.nan
    elif abs(cash - due) <= 1e-7:
        status = "exact at total loss" if tradable > 0 else "exact throughout"
        boundary = 1.0 if tradable > 0 else np.nan
    else:
        status = "boundary"
        boundary = np.clip((at_start - due) / tradable, 0, 1)
    return {
        "status": status,
        "loss_boundary": boundary,
        "resources_at_zero_loss": at_start,
        "resources_at_total_loss": cash,
        "initial_shortfall": max(due - at_start, 0),
    }


def flat_adjustments(w):
    def ending(years, deposit):
        return simulate(np.ones((1, years, 3)), w, deposit)[-1]["terminal"][0]

    target = 65000 * 1.02**8
    from scipy.optimize import brentq

    needed = brentq(lambda s: ending(8, s) - target, 0, 2000)
    cashflows = simulate(np.ones((1, 50, 3)), w, 100)
    first = next(
        (i for i, p in enumerate(cashflows, 1) if p["terminal"][0] >= 65000 * 1.02**i),
        None,
    )
    return {
        "monthly_chf_needed": needed,
        "first_year_within_50": first,
        "affordable_real_target": ending(8, 100) / 1.02**8,
    }
