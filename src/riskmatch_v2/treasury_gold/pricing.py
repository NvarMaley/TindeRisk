"""Regular nominal US coupon bonds per USD 100, using Treasury Appendix B."""

from copy import copy

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar, sunday_to_monday
from scipy.optimize import brentq

# Federal Reserve remains open on a Friday preceding a Saturday fixed holiday.
rules = [copy(rule) for rule in USFederalHolidayCalendar.rules]
for rule in rules:
    if rule.month in (1, 6, 7, 11, 12) and rule.offset is None and rule.observance:
        rule.observance = sunday_to_monday
bank_day = pd.offsets.CustomBusinessDay(calendar=USFederalHolidayCalendar(rules=rules))


def schedule(dated, maturity, coupon):
    first, end = pd.Timestamp(dated), pd.Timestamp(maturity)
    edges = []
    date = end
    while date > first:
        edges.append(date)
        date = end - pd.DateOffset(months=6 * len(edges))
        if end.is_month_end:
            date += pd.offsets.MonthEnd(0)
    if date != first or not edges:
        raise ValueError("Requires a regular semiannual nominal issue")
    period = pd.DatetimeIndex(edges[::-1])
    return pd.DataFrame(
        {
            "start": [first, *period[:-1]],
            "due": period,
            "pay": [bank_day.rollforward(d) for d in period],
            "coupon": float(coupon) / 2,
            "principal": np.where(period == end, 100.0, 0.0),
        }
    )


def remaining(flows, date):
    date = pd.Timestamp(date)
    after = flows.loc[flows.due > date]
    if after.empty or date < after.start.iloc[0]:
        raise ValueError("Valuation outside the issue's accrual period")
    row = after.iloc[0]
    days = (row.due - row.start).days
    elapsed = (date - row.start).days
    return after, (days - elapsed) / days, row.coupon * elapsed / days


def discounted(cash, fraction, y):
    """Simple first fractional period; semiannual compounding thereafter."""
    k = np.arange(len(cash))
    pv = cash / ((1 + fraction * y / 2) * (1 + y / 2) ** k)
    slope = fraction / (2 + fraction * y) + k / (2 + y)
    curvature = slope**2 + (fraction / (2 + fraction * y)) ** 2 + k / (2 + y) ** 2
    return pv.sum(), (pv * slope).sum() / pv.sum(), (pv * curvature).sum() / pv.sum()


def risk(flows, day, clean, cfg):
    later, fraction, accrued = remaining(flows, day)
    dirty = clean + accrued
    cash = (later.coupon + later.principal).to_numpy()
    y = brentq(lambda x: discounted(cash, fraction, x)[0] - dirty, -0.5, 1, xtol=1e-14)

    def price(shock):
        return discounted(cash, fraction, y + shock)[0]

    base, dur, conv = discounted(cash, fraction, y)
    assert abs(base - dirty) < 1e-8
    bp = 1 / 10000
    numerical = (price(-bp) - price(bp)) / (2 * bp * dirty)
    assert abs(numerical - dur) < 1e-4
    d = cfg["parallel_bp"] * bp
    scenarios = {}
    errors = []
    for label, dy, fx in [
        ("Rates up", d, 0),
        ("Rates down", -d, 0),
        ("Spread only", cfg["spread_bp"] * bp, 0),
        ("FX only", 0, cfg["fx_change"]),
        ("Joint", d + cfg["spread_bp"] * bp, cfg["fx_change"]),
    ]:
        local = price(dy) / dirty - 1
        approx = -dur * dy + 0.5 * conv * dy * dy
        scenarios[label] = {
            "local": local,
            "approx_local": approx,
            "fx": fx,
            "interaction": local * fx,
            "chf": (1 + local) * (1 + fx) - 1,
        }
        errors.append(abs(local - approx) * 10000)
    return {
        "clean": clean,
        "dirty": dirty,
        "accrued": accrued,
        "yield": y,
        "duration": dur,
        "convexity": conv,
        "dv01_per_100": dirty * dur * bp,
        "remaining_coupons": len(later),
        "next_coupon": str(later.due.iloc[0].date()),
        "max_approx_error_bp": max(errors),
        "exceeds_tolerance": max(errors) > cfg["approximation_tolerance_bp_of_price"],
    }, scenarios
