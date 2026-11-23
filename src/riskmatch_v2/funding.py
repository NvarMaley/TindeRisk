"""Dated funding requirements and paired, whole-lot portfolio scenarios in CHF."""

import itertools
from datetime import date
from math import expm1, isfinite, log1p

import numpy as np
import pandas as pd
from scipy.optimize import brentq


def years(start, end):
    return (date.fromisoformat(end) - date.fromisoformat(start)).days / 365.25


def required_return(start, end, capital, reserve, flows, goal, *, inflation=0.0):
    """Annual net sleeve rate under ACT/365.25; protected cash earns zero.

    The search covers -99% to +1000% annually. Partition at stationary points
    of the discounted cash-flow sum to detect multiple and tangent roots.
    """
    horizon = years(start, end)
    if (
        horizon <= 0
        or not all(map(isfinite, (capital, reserve, goal, inflation)))
        or min(capital, reserve, goal) < 0
        or inflation <= -1
    ):
        raise ValueError("Invalid capital, goal, reserve, inflation or horizon")
    if reserve > capital:
        return {"status": "reserve exceeds capital", "rates": []}
    balance = reserve
    cash_events = [(0.0, capital - reserve)]
    amounts = {0.0: capital - reserve}
    for day, signed in sorted(flows, key=lambda row: (row[0], row[1])):
        t = years(start, day)
        if not 0 < t <= horizon or not isfinite(signed):
            raise ValueError("Flow outside the plan or non-finite amount")
        protected_payment = min(balance, max(0, -signed))
        balance -= protected_payment
        cash_events.append((t, signed + protected_payment))
        amounts[t] = amounts.get(t, 0) + signed + protected_payment
    terminal = goal * (1 + inflation) ** horizon
    amounts[horizon] = amounts.get(horizon, 0) + balance - terminal
    pairs = [(t, v) for t, v in sorted(amounts.items()) if v]
    if not pairs:
        return {"status": "any rate satisfies the equation", "rates": []}

    def roots(times, coeff, lo, hi):
        times = times - times[0]
        coeff = coeff / np.max(np.abs(coeff))
        if len(coeff) == 1 or np.all(coeff > 0) or np.all(coeff < 0):
            return []

        def value(x):
            exponent = -times * x
            discount = np.exp(exponent - exponent.max())
            return float((coeff @ discount) / (np.abs(coeff) @ discount))

        critical = roots(times[1:], -times[1:] * coeff[1:], lo, hi)
        boundaries = [lo, *critical, hi]
        found = [x for x in boundaries if abs(value(x)) < 1e-12]
        for left, right in itertools.pairwise(boundaries):
            if (
                value(left) * value(right) < 0
                and left not in found
                and right not in found
            ):
                found.append(brentq(value, left, right, xtol=1e-13))
        return sorted(found)

    t, c = np.array(pairs).T
    rates = [expm1(x) for x in roots(t, c, log1p(-0.99), log1p(10.0))]
    state = (
        "unique"
        if len(rates) == 1
        else "multiple roots"
        if rates
        else "no root in search range"
    )
    # A mathematical root that needs an interim loan is not a feasible funding plan.
    if len(rates) == 1:
        event_t, event_c = np.array(cash_events).T
        discounted = np.cumsum(event_c * np.exp(-event_t * log1p(rates[0])))
        if (discounted < -1e-6).any():
            state = "unique root requires interim borrowing"
    return {"status": state, "rates": rates, "nominal_goal_chf": terminal}


def block_draws(frame, length, horizon, paths, seed):
    """A sampled month is shared by every holding, currency leg and strategy."""
    months = pd.PeriodIndex(frame.index, freq="M")
    if (
        months.has_duplicates
        or not months.is_monotonic_increasing
        or min(length, horizon, paths) < 1
    ):
        raise ValueError("Expected ordered unique months and positive dimensions")
    data = frame.to_numpy(dtype=float)
    valid = np.isfinite(data).all(axis=1) & (data >= -1).all(axis=1)
    starts = [
        i
        for i in range(len(frame) - length + 1)
        if valid[i : i + length].all()
        and months[i + length - 1].ordinal - months[i].ordinal == length - 1
    ]
    if not starts:
        return starts, None
    n = paths if len(starts) > 1 else 1
    rng = np.random.default_rng(seed)
    selected = rng.choice(starts, size=(n, (horizon + length - 1) // length))
    indices = (selected[:, :, None] + np.arange(length)).reshape(n, -1)
    return starts, indices[:, :horizon]


def sale_values(returns, draws, cost_basis, fees):
    """Liquidation proceeds from initial whole lots, with total distributions reinvested."""
    values = np.broadcast_to(cost_basis, (len(draws), len(cost_basis))).copy()
    proceeds = np.empty((len(draws), draws.shape[1]))
    for month in range(draws.shape[1]):
        values *= 1 + returns[draws[:, month]]
        proceeds[:, month] = values @ (1 - fees)
    return proceeds


def funding_paths(proceeds, cash_chf, outflows, inflows, goal):
    """Sell the entire sleeve if cash is insufficient. Carry unpaid bills as arrears.

    Each month: value holdings, pay outstanding and new bills, receive contributions,
    settle remaining arrears, then value closing wealth net of exit costs.
    """
    n, months = proceeds.shape
    if (
        min(n, months) == 0
        or not np.isfinite([cash_chf, goal, *inflows, *outflows]).all()
        or len(inflows) != months
        or len(outflows) != months
        or not np.isfinite(proceeds).all()
        or (proceeds < 0).any()
        or min(cash_chf, goal, *inflows, *outflows) < 0
    ):
        raise ValueError("Invalid funding paths or cash schedule")
    cash = np.full(n, float(cash_chf))
    held = np.ones(n, dtype=bool)
    arrears = np.zeros(n)
    first = np.zeros(n, dtype=int)
    recovery = first.copy()
    first_gap = np.zeros(n)
    for i in range(months):
        arrears += outflows[i]
        sell = held & (cash + 1e-8 < arrears)
        cash[sell] += proceeds[sell, i]
        held[sell] = False
        paid = np.minimum(cash, arrears)
        cash -= paid
        arrears -= paid
        missed = (first == 0) & (arrears > 1e-7)
        first[missed] = i + 1
        first_gap[missed] = arrears[missed]
        cash += inflows[i]
        paid = np.minimum(cash, arrears)
        arrears -= paid
        cash -= paid
        recovered = (first > 0) & (recovery == 0) & (arrears < 1e-7)
        recovery[recovered] = i + 1
    terminal = cash + held * proceeds[:, -1] - arrears
    gap = np.maximum(goal - terminal, 0)
    return pd.DataFrame(
        {
            "first_missed_month": first,
            "first_gap_chf": first_gap,
            "first_recovery_month": recovery,
            "terminal_chf": terminal,
            "terminal_gap_chf": gap,
            "all_goals_met": (first == 0) & (gap <= 1e-7),
        }
    )
