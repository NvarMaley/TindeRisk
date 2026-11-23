"""Monthly CHF research references. Each uninterrupted window starts from cash."""

from dataclasses import asdict, dataclass
from math import isclose, isfinite
from statistics import mean

from .catalogue import describe


def common_windows(panel, assets):
    if not assets or any(asset not in panel for asset in assets):
        raise ValueError("Missing history for requested assets")
    dates = sorted(set.intersection(*(set(panel[a]) for a in assets)))
    if not dates:
        raise ValueError("No common date")
    windows = []
    previous = None
    for day in dates:
        month = day.year * 12 + day.month
        if month == previous:
            raise ValueError("Several observations in the same month")
        if previous is None or month != previous + 1:
            windows.append([])
        windows[-1].append(day)
        previous = month
    return windows


@dataclass(frozen=True)
class Month:
    date: str
    opening_chf: float
    traded_chf: float
    fees_chf: float
    pnl_chf: float
    closing_chf: float
    net_return: float


def rebalance(holdings, wealth, weights, rate):
    # Post-fee wealth solves x + rate * sum(|w_i*x - holding_i|) = wealth.
    low, high = 0.0, wealth
    for _ in range(60):
        mid = (low + high) / 2
        volume = sum(abs(mid * w - holdings[a]) for a, w in weights.items())
        if mid + rate * volume > wealth:
            high = mid
        else:
            low = mid
    target = {a: high * w for a, w in weights.items()}
    traded = sum(abs(target[a] - holdings[a]) for a in weights)
    return target, traded


def replay(panel, days, weights, mode, base, bps):
    if mode not in {"annual", "hold"} or not days:
        raise ValueError("Invalid policy or window")
    if (not all(isfinite(w) and w > 0 for w in weights.values())
            or not isclose(sum(weights.values()), 1, rel_tol=0, abs_tol=1e-12)
            or not isfinite(base) or base <= 0 or not 0 <= bps < 10000):
        raise ValueError("Invalid weight, capital or costs")
    holdings = dict.fromkeys(weights, 0.0)
    wealth = base
    rows = []
    previous = None
    for day in days:
        month = day.year * 12 + day.month
        if previous is not None and month != previous + 1:
            raise ValueError("Months of replay must be consecutive")
        traded = 0.0
        if previous is None or (mode == "annual" and day.month == 1):
            holdings, traded = rebalance(holdings, wealth, weights, bps / 10000)
        fees = traded * bps / 10000
        pnl = 0.0
        for a, value in holdings.items():
            gain = value * panel[a][day]
            holdings[a] += gain
            pnl += gain
        closing = sum(holdings.values())
        if not isclose(closing, wealth - fees + pnl, rel_tol=1e-11, abs_tol=1e-10):
            raise ArithmeticError("Difference between positions and flows")
        rows.append(Month(day.isoformat(), wealth, traded, fees, pnl, closing, closing / wealth - 1))
        wealth = closing
        if wealth <= 0:
            raise ValueError("Exhausted capital during replay")
        previous = month
    return rows


def compatibility(mandate, assets, vol):
    """Assess only the explicit constraints in a historical research mandate."""
    reasons = []
    unknown = []
    allowed = mandate.get("allowed")
    if allowed is None:
        unknown.append("permitted universe unspecified")
    elif extra := sorted(set(assets) - set(allowed)):
        reasons.append("Excluded: " + ", ".join(extra))
    for key, sign in (("max_volatility", 1), ("min_volatility", -1)):
        if key in mandate:
            limit = mandate[key]
            if limit is None or vol is None:
                unknown.append("volatility bound unknown")
            elif not isfinite(limit) or limit < 0:
                raise ValueError("Invalid volatility point")
            elif sign * (vol - limit) > 1e-12:
                reasons.append("historical volatility beyond bounds")
    if not mandate.get("confirmed"):
        unknown.append("mandate to be confirmed")
    for field in sorted(mandate.keys() - {"confirmed", "allowed", "max_volatility", "min_volatility"}):
        unknown.append(f"constraint requiring review: {field}")
    state = "outside mandate" if reasons else "undetermined" if unknown else "compatible with tested criteria"
    return {"status": state, "motifs": reasons + unknown}


def study(panel, settings):
    weights = settings["weights"]
    base = settings["base_chf"]
    rate = settings["cost_bps"]
    summaries, ledger = [], []
    for days in common_windows(panel, weights):
        for mode in ("annual", "hold", "cash"):
            assets = {"CHF"} if mode == "cash" else set(weights)
            if mode == "cash":
                cash_panel = {"CHF": dict.fromkeys(days, settings["cash_monthly_return"])}
                rows = replay(cash_panel, days, {"CHF": 1}, "hold", base, 0)
                # The initial balance already consists of CHF.
                rows[0] = Month(**(asdict(rows[0]) | {"traded_chf": 0.0}))
            else:
                rows = replay(panel, days, weights, mode, base, rate)
            returns = [row.net_return for row in rows]
            stats = describe(returns)
            growth = rows[-1].closing_chf / base
            if not isclose(growth, 1 + stats["cumulative_return"], rel_tol=1e-10):
                raise ArithmeticError("Difference between capital and returns")
            summary = dict(start=rows[0].date, end=rows[-1].date, mode=mode,
                           months=len(rows), final_chf=rows[-1].closing_chf,
                           monthly_mean=mean(returns), cagr=growth ** (12 / len(rows)) - 1,
                           cumulative=growth - 1, volatility=stats["annualized_volatility"],
                           traded_chf=sum(r.traded_chf for r in rows), fees_chf=sum(r.fees_chf for r in rows))
            summary["mandates"] = {k: compatibility(m, assets, summary["volatility"])
                                  for k, m in settings["mandates"].items()}
            summaries.append(summary)
            ledger.extend(dict(mode=mode, start=rows[0].date, **asdict(row)) for row in rows)
    return summaries, ledger
