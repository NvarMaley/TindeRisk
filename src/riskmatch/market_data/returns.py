"""Return conventions shared by research, analytics and simulation."""
from datetime import date
from math import exp, expm1, fsum, isfinite, log1p, prod
from pathlib import Path
import hashlib
import json


def _finite(*values):
    if not all(isfinite(v) for v in values):
        raise ValueError("Non-finite input")


def price_return(previous, current):
    _finite(previous, current)
    if previous <= 0 or current < 0:
        raise ValueError("Invalid price")
    return current / previous - 1


def log_return(value):
    _finite(value)
    if value < -1:
        raise ValueError("Return below -100%")
    return log1p(value) if value > -1 else None


def total_return(previous, current, *, split=1.0, distribution=0.0):
    """Split ratio is new shares per old share; distribution is per old share."""
    _finite(previous, current, split, distribution)
    if previous <= 0 or current < 0 or split <= 0 or distribution < 0:
        raise ValueError("Invalid corporate action or price")
    return (current * split + distribution) / previous - 1


def compound(values):
    values = tuple(values)
    if not values or any(v is None or not isfinite(v) or v < -1 for v in values):
        raise ValueError("Complete valid return window required")
    return prod(1 + v for v in values) - 1


def means(values, periods_per_year):
    values = tuple(values)
    growth = 1 + compound(values)
    if periods_per_year <= 0:
        raise ValueError("Invalid frequency")
    return {"arithmetic": fsum(values)/len(values),
            "geometric": growth**(1/len(values))-1,
            "annualized_geometric": growth**(periods_per_year/len(values))-1}


def aggregate_periods(observed, expected_dates, frequency):
    """Require every expected session in each group; return None for incomplete groups."""
    if frequency not in ("daily","weekly","monthly"):
        raise ValueError("Unsupported frequency")
    groups = {}
    for day in sorted(set(expected_dates)):
        key = day if frequency == "daily" else (
            day.isocalendar()[:2] if frequency == "weekly" else (day.year, day.month))
        groups.setdefault(key, []).append(day)
    return {key: compound([observed[day] for day in days])
            if all(day in observed and observed[day] is not None for day in days) else None
            for key, days in groups.items()}


def fx_return(local_return, previous_fx, current_fx, *, inverse=False):
    _finite(local_return, previous_fx, current_fx)
    if local_return < -1 or min(previous_fx,current_fx) <= 0:
        raise ValueError("Invalid FX or local return")
    ratio = previous_fx/current_fx if inverse else current_fx/previous_fx
    return (1+local_return)*ratio-1


def real_return(nominal, inflation):
    _finite(nominal,inflation)
    if nominal < -1 or inflation <= -1:
        raise ValueError("Invalid nominal return or inflation")
    return (1+nominal)/(1+inflation)-1


def cash_accrual(rate, start, end, *, basis=360):
    _finite(rate)
    if basis not in (360,365) or end < start:
        raise ValueError("Invalid day count")
    result = rate * (end-start).days/basis
    if result <= -1:
        raise ValueError("Invalid accrued cash return")
    return result


def excess_return(asset_return, benchmark_return):
    _finite(asset_return, benchmark_return)
    if min(asset_return,benchmark_return)<-1:
        raise ValueError("Invalid return")
    return asset_return-benchmark_return


def bond_return(previous_clean, current_clean, previous_accrued, current_accrued, cash_paid=0.0):
    """All prices and cash flows are per identical face value and currency."""
    _finite(previous_clean,current_clean,previous_accrued,current_accrued,cash_paid)
    if min(previous_clean,current_clean,previous_accrued,current_accrued,cash_paid)<0:
        raise ValueError("Invalid bond values")
    return total_return(previous_clean+previous_accrued,current_clean+current_accrued,distribution=cash_paid)


def futures_pnl(previous_settlement, current_settlement, multiplier, contracts):
    _finite(previous_settlement,current_settlement,multiplier,contracts)
    if multiplier <= 0:
        raise ValueError("Invalid multiplier")
    return (current_settlement-previous_settlement)*multiplier*contracts


def tips_return(previous_clean_real, current_clean_real, previous_accrued_real,
                current_accrued_real, previous_ratio, current_ratio, cash_paid_usd=0.0):
    _finite(previous_ratio,current_ratio)
    if min(previous_ratio,current_ratio)<=0:
        raise ValueError("Invalid index ratio")
    return bond_return(previous_clean_real*previous_ratio,current_clean_real*current_ratio,
                       previous_accrued_real*previous_ratio,current_accrued_real*current_ratio,cash_paid_usd)


def time_weighted_return(nav, flows):
    """NAV after end-of-period external flows, contributions positive."""
    nav, flows = tuple(nav), tuple(flows)
    if not flows or len(nav)!=len(flows)+1:
        raise ValueError("Expected initial NAV and one flow per period")
    return compound(price_return(a,b-flow) for a,b,flow in zip(nav[:-1],nav[1:],flows))


def money_weighted_return(cashflows):
    """Annual XIRR for conventional dated investor cash flows; reject ambiguous signs."""
    cashflows = sorted(cashflows)
    grouped = {}
    for day, amount in cashflows:
        _finite(amount)
        grouped[day] = grouped.get(day,0)+amount
    items = [(day,amount) for day,amount in grouped.items() if amount]
    if len(items)<2 or items[0][1]>=0 or items[-1][1]<=0:
        raise ValueError("Expected negative initial and positive terminal cash flows")
    if sum((a[1]>0)!=(b[1]>0) for a,b in zip(items,items[1:])) != 1:
        raise ValueError("Ambiguous non-conventional cash flows")
    times = [((day-items[0][0]).days/365,amount) for day,amount in items]
    def npv(log_rate):
        shift=max(-log_rate*t for t,_ in times)
        return fsum(amount*exp(-log_rate*t-shift) for t,amount in times)
    lo,hi=-20.0,20.0
    if npv(lo)*npv(hi)>0:
        raise ValueError("IRR outside supported range")
    for _ in range(100):
        mid=(lo+hi)/2
        if npv(mid)>0:
            lo=mid
        else:
            hi=mid
    return expm1((lo+hi)/2)


def returns_report(root, as_of: date):
    base=Path(root)/"data/processed/returns"
    unavailable={"schema":"returns-v1","approved":False,"datasets":[],"reason":"returns_unavailable"}
    try:
        report=json.loads((base/"report.json").read_text())
        source=json.loads((Path(root)/"data/processed/pit/report.json").read_text())
        if report["snapshot_id"]!=source["snapshot_id"] or date.fromisoformat(report["built_at"][:10])>as_of:
            return unavailable
        identifier=hashlib.sha256(json.dumps([report["snapshot_id"],report["datasets"]],sort_keys=True).encode()).hexdigest()
        if identifier!=report["return_id"]:
            return unavailable
        for row in report["datasets"]:
            name=row["dataset"]
            if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in name):
                return unavailable
            with (base/identifier/f"{name}.parquet").open("rb") as stream:
                if hashlib.file_digest(stream,"sha256").hexdigest()!=row["file_hash"]:
                    return unavailable
        return report | {"approved":False}
    except (OSError,ValueError,TypeError,KeyError):
        return unavailable
