"""Section 3: declared annual volatility, CHF stress examples and consent."""
from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256
from importlib.resources import files
import json
from math import isfinite

from .interview import Facts, cash_events

POLICY = json.loads(files("riskmatch_v2").joinpath("questionnaire/risque.json").read_text())


def percentage(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        raise ValueError("Enter a positive or zero numerical percentage.")
    return float(Decimal(str(value)) / 100)


def request(mode, basis, *, ceiling_pct=None, low_pct=None, high_pct=None, band=None):
    if mode not in ("minimum", "cap", "target_band", "unknown") or basis not in ("investment sleeve", "household"):
        raise ValueError("Type of request or unknown plate.")
    low = high = None
    open_top = False
    if mode == "cap" and all(x is None for x in (band, low_pct, high_pct)):
        high = percentage(ceiling_pct)
    elif mode == "target_band" and ceiling_pct is None:
        if band is None:
            low, high = percentage(low_pct), percentage(high_pct)
            if high < low:
                raise ValueError("The high bound precedes the low bound.")
        else:
            if basis != "investment sleeve" or low_pct is not None or high_pct is not None:
                raise ValueError("The named slices are on the investment sleeve in CHF.")
            item = next((b for b in POLICY["bands"] if b["label"] == band), None)
            if item is None:
                raise ValueError("Unknown range.")
            low, high, open_top = item["low"], item["high"], True
    elif mode not in ("minimum", "unknown") or any(x is not None for x in (ceiling_pct, low_pct, high_pct, band)):
        raise ValueError("Incoherent points with demand.")
    return dict(mode=mode, basis=basis, low=low, high=high, high_exclusive=open_top,
                unit="decimal", period="year", currency="CHF", band=band)


def centered_target(basis, center_pct, margin_pp):
    percentage(center_pct)
    percentage(margin_pp)
    center, width = Decimal(str(center_pct)), Decimal(str(margin_pp))
    return request("target_band", basis, low_pct=float(center-width), high_pct=float(center+width))


def band_at(decimal):
    if isinstance(decimal, bool) or not isfinite(decimal) or decimal < 0:
        raise ValueError("Invalid decimal volatility.")
    return next(b["label"] for b in reversed(POLICY["bands"]) if decimal >= b["low"])


def suggested(portrait):
    goal = portrait["goal"]
    pref = goal["risk_request"] or {}
    basis = pref.get("basis", "investment sleeve")
    mode = pref.get("mode")
    bounds = goal["risk_bounds_pct"] or {}
    if mode == "cap" and "max" in bounds:
        return request(mode, basis, ceiling_pct=bounds["max"]), "P02/P03 · declared ceiling."
    if mode == "target_band" and "low" in bounds and "high" in bounds:
        return request(mode, basis, low_pct=bounds["low"], high_pct=bounds["high"]), "P02/P04 · Declared band."
    if mode == "minimum":
        return request(mode, basis), "P02 · minimum risk search."
    if not mode and portrait["behaviour"].get("D03") == "yes":
        return request("minimum", basis), "D03 · stability preference. The minimum is a lead to discuss."
    return request("unknown", basis), "P02–P04 · digital application missing or incomplete."


def interval(low, high):
    return dict(low=low, high=high)


def loss_examples(portrait):
    cap = portrait["facts"]["capital_chf"]
    budget = portrait["liquidity"]
    pocket, reserve = budget["investable_chf"], budget["reserve_chf"]
    if not pocket or not cap or not reserve:
        return []
    rows = []
    for stress in POLICY["stresses"]:
        shock = stress["loss_fraction"]
        loss = interval(pocket["low"] * shock, pocket["high"] * shock)
        # The portion invested increases with capital and decreases with the reserve.
        household = None
        if cap["low"] > 0:
            household = interval(shock * max(0, cap["low"]-reserve["high"]) / cap["low"],
                                 shock * max(0, cap["high"]-reserve["low"]) / cap["high"])
        rows.append(dict(**stress, loss_chf=loss, household_fraction=household,
                         pocket_fraction=shock if pocket["low"] > 0 else None))
    return rows


def dated_cash(portrait, as_of):
    facts = Facts(**portrait["facts"])
    events, issues = cash_events(facts, as_of)
    pocket = portrait["liquidity"]["investable_chf"]
    if issues or not facts.capital_chf or not pocket:
        return []
    # Invest the smallest available pocket in both paths. Isolate operating cash.
    low, high = (facts.capital_chf[k] - pocket["low"] for k in ("low","high"))
    rows = [dict(date=as_of.isoformat(), phase="before flow", cash_chf=interval(low,high))]
    for day, (out_low, out_high, in_high, in_low) in sorted(events.items()):
        low -= out_high
        high -= out_low
        if out_high:
            rows.append(dict(date=day.isoformat(), phase="After withdrawals", cash_chf=interval(low, high)))
        low += in_low
        high += in_high
        if in_high:
            rows.append(dict(date=day.isoformat(), phase="after input", cash_chf=interval(low, high)))
    return rows


@dataclass(frozen=True)
class CertifiedMaximum:
    """A proven bound for this portrait, decision date and dated investment universe."""
    decimal: float
    basis: str
    as_of: str
    portrait_version: int
    evidence: str
    portrait_digest: str


def portrait_digest(snapshot):
    inputs = {k: snapshot[k] for k in ("as_of", "bank", "answers", "portrait")}
    return sha256(json.dumps(inputs, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def feasibility(choice, snapshot, certificate):
    if certificate is None:
        return "to be tested"
    if (certificate.basis != choice["basis"] or certificate.as_of != snapshot["as_of"]
            or certificate.portrait_version != snapshot.get("portrait_version", snapshot["version"])
            or certificate.portrait_digest != portrait_digest(snapshot) or not certificate.evidence.strip()):
        return "to be tested"
    maximum = certificate.decimal
    if isinstance(maximum, bool) or not isfinite(maximum) or maximum < 0:
        raise ValueError("Invalid feasibility base.")
    if choice["mode"] == "target_band" and choice["low"] > maximum:
        return "target out of range"
    return "to be tested"


def validate_choice(choice):
    if (choice.get("unit"), choice.get("period"), choice.get("currency")) != ("decimal", "year", "CHF"):
        raise ValueError("The demand must be in annual decimal volatility in CHF.")
    if choice.get("mode") not in ("minimum", "cap", "target_band", "unknown") or choice.get("basis") not in ("household", "investment sleeve"):
        raise ValueError("Demand for unknown risk.")
    low, high = choice["low"], choice["high"]
    for value in (low, high):
        if value is not None and (not isinstance(value, (float, int)) or isinstance(value, bool)
                                  or not isfinite(value) or value < 0):
            raise ValueError("Invalid decimal point.")
    if choice["band"] is not None:
        expected = request("target_band", choice["basis"], band=choice["band"])
        if choice != expected:
            raise ValueError("The named slice and its bounds do not match.")
    elif choice["high_exclusive"] or (choice["mode"] == "target_band"
                                      and (low is None or high is None or low > high)):
        raise ValueError("Customized band invalid.")
    elif choice["mode"] == "cap" and (low is not None or high is None):
        raise ValueError("Invalid ceiling.")
    elif choice["mode"] in ("minimum", "unknown") and (low is not None or high is not None):
        raise ValueError("This application has no limits.")


def assess(snapshot, choice, *, accept, bills, comfort, certificate=None):
    validate_choice(choice)
    if not isinstance(accept, bool) or bills not in ("yes","no","unknown") or comfort not in ("yes","no","unknown"):
        raise ValueError("Unknown confirmation response.")
    portrait = snapshot["portrait"]
    budget = portrait["liquidity"]
    pocket, reserve = budget["investable_chf"], budget["reserve_chf"]
    as_of = date.fromisoformat(snapshot["as_of"])
    stresses = loss_examples(portrait)
    issues = list(budget["issues"])
    reasons = []
    limits = portrait["facts"]["capacity_loss_chf"]
    if pocket and pocket["high"] == 0:
        issues.append("F01/F03 · no investment investment sleeve.")
    if reserve and (reserve["low"] != reserve["high"] or pocket and pocket["low"] != pocket["high"]):
        issues.append("F01/F03 · amount to be protected or invested.")
    if pocket and pocket["high"] > 0 and not limits:
        issues.append("F04 · financial loss capacity to be specified.")
    high_demand = choice["low"] if choice["mode"] == "target_band" else None
    # For an exact household/pocket budget, translate volatility assuming fixed nominal CHF cash.
    cap = portrait["facts"]["capital_chf"]
    share = None
    if cap and pocket and cap["low"] == cap["high"] > 0 and pocket["low"] == pocket["high"]:
        share = pocket["low"] / cap["low"]
    pocket_level = high_demand
    if choice["basis"] == "household":
        pocket_level = high_demand / share if high_demand is not None and share else None
    high_request = pocket_level is not None and pocket_level >= POLICY["bands"][-1]["low"]
    equivalent = None
    if share and choice["mode"] in ("cap", "target_band"):
        multiplier = share if choice["basis"] == "investment sleeve" else 1 / share
        equivalent = dict(basis="household" if choice["basis"] == "investment sleeve" else "investment sleeve",
                          low=choice["low"] * multiplier if choice["low"] is not None else None,
                          high=choice["high"] * multiplier if choice["high"] is not None else None,
                          high_exclusive=choice["high_exclusive"])
    end_year = as_of.replace(year=as_of.year + 1, day=min(as_of.day, monthrange(as_of.year+1, as_of.month)[1]))
    if high_request:
        goal_date = (portrait["goal"]["amount"] or {}).get("date")
        if goal_date and as_of.isoformat() <= goal_date <= end_year.isoformat():
            issues.append(f"F05 · Objective {goal_date}in the first year. Specify the amount to be protected.")
        for flow in portrait["facts"]["flows"] or []:
            when = flow["date"]
            if flow["direction"] != "withdrawal" or not when or when < snapshot["as_of"]:
                continue
            horizon = portrait["facts"]["horizon"]
            detail = f"{when} ({flow['low']:g}–{flow['high']:g} {flow['currency']})"
            if horizon and when <= horizon:
                reasons.append(f"F03 · withdrawal from the protective horizon on {detail}.")
            elif when <= end_year.isoformat():
                issues.append(f"F02/F03 · near withdrawal after the protected horizon on {detail}. See the cover again.")
    if bills != "yes":
        issues.append("Scenarios · Coverage of expenses to be clarified.")
    if comfort != "yes":
        issues.append("Scenarios · acceptance of the decrease to be clarified.")
    if portrait["behaviour"].get("D02") == "yes" and not any(f["direction"] == "withdrawal" for f in portrait["facts"]["flows"] or []):
        issues.append("D02/F03 · expenditure mentioned to be reported.")
    if high_request and portrait["behaviour"].get("D03") == "yes":
        reasons.append("D03 · a 15% decrease prompted you to sell out of discomfort.")
    capacity_alert = limits and any(s["loss_chf"]["high"] > limits["low"] for s in stresses)
    if capacity_alert:
        reasons.append(f"F04 · Declared difficulty threshold between {limits['low']:g} et {limits['high']:g} CHF. This threshold remains applicable.")
    if high_request and capacity_alert:
        issues.append("F04 · the illustrated loss exceeds the declared difficulty threshold. Review the application or specify F04.")
    if choice["mode"] == "unknown" or not accept:
        state = "pending confirmation"
    elif issues:
        state = "to be clarified"
    else:
        state = "confirmed for study"
    possible = "no investment capital" if pocket and pocket["high"] == 0 else feasibility(choice, snapshot, certificate)
    if possible == "target out of range" and state == "confirmed for study":
        state = "target out of range"
    initial, reason = suggested(portrait)
    alternative = None
    if high_request and (capacity_alert or comfort == "no" or possible == "target out of range"):
        alternative = dict(choice=request("minimum", choice["basis"]),
                           reason="Compare the minimum risk taking into account the reserve and the limits expressed.")
    return dict(ready_for_feasibility=state == "confirmed for study", ranking_authorized=False,
                alternative=alternative, feasibility_certificate=asdict(certificate) if certificate else None,
                declared_risk=portrait["goal"]["risk_request"], declared_bounds_pct=portrait["goal"]["risk_bounds_pct"],
                capacity_loss_chf=limits, policy=POLICY["version"], portrait_version=snapshot.get("portrait_version", snapshot["version"]),
                initial=initial, suggestion_reason=reason, choice=choice, accepted=accept,
                bills=bills, comfort=comfort, state=state, reasons=reasons, issues=issues, feasibility=possible,
                equivalent=equivalent, household_invested_share=share, reserve_chf=reserve, investable_chf=pocket,
                stresses=stresses, dated_cash=dated_cash(portrait, as_of), allocation_authorized=False)
