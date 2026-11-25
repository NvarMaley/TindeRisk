"""Versioned, simulation-only client mandate and deterministic feasibility checks."""

from datetime import date, timedelta
from math import exp, isfinite
from calendar import monthrange

from scipy.optimize import brentq

SCHEMA_VERSION = "2.0.0"
CURRENCIES = {"USD", "CHF"}
OBJECTIVES = {
    "OBJ01": "Capital Preservation", "OBJ02": "Income", "OBJ03": "Conservative",
    "OBJ04": "Balanced", "OBJ05": "Growth", "OBJ06": "Aggressive Growth",
    "OBJ07": "Inflation Protection", "OBJ08": "Absolute Return",
    "OBJ09": "Liability-Driven (LDI)", "OBJ10": "Goal-Based", "OBJ11": "Capital Protection",
}
KNOWLEDGE = {"none", "basic", "advanced"}
EXPERIENCE = {"none", "limited", "experienced"}
ASSETS = {"equity", "treasury", "reit", "cash", "futures", "commodity_etp"}
LIMITS = ("stress_loss", "loss_budget", "volatility", "max_asset_weight", "max_issuer_weight",
          "max_sector_weight", "max_turnover", "max_cost", "min_liquidity", "gross_limit", "net_min", "net_max")


def number(value, field, *, minimum=0, maximum=None, optional=False):
    """Strict JSON number contract; null means unavailable, not zero."""
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"invalid_field:{field}")
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"invalid_field:{field}")
    return float(value)


def day(value, field):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError(f"invalid_field:{field}") from None


def choice(value, allowed, field):
    if value not in allowed:
        raise ValueError(f"invalid_field:{field}")
    return value


def boolean(value, field):
    if type(value) is not bool:
        raise ValueError(f"invalid_field:{field}")
    return value


def years_between(start, end):
    return (end - start).days / 365.25


def add_month(start, months):
    year, index = divmod(start.year * 12 + start.month - 1 + months, 12)
    return date(year, index + 1, min(start.day, monthrange(year, index + 1)[1]))


def convert(amount, source, target, chf_per_usd):
    """Convert using one explicit CHF-per-USD scenario, not a forecast."""
    if source == target:
        return amount
    if chf_per_usd is None or chf_per_usd <= 0:
        raise ValueError("fx_required")
    return amount * chf_per_usd if source == "USD" else amount / chf_per_usd


def required_return(initial, flows, start, end, target):
    """Annual nominal effective return for dated flows; no market forecast.

    Positive flows are deposits, negative flows are withdrawals. A single
    sign change in chronological cash flows implies at most one root. Do not
    select one of potentially multiple IRRs for non-conventional cash flows.
    """
    if initial <= 0 or end <= start or target < 0:
        return {"status": "unavailable", "annual_return": None}
    grouped = {start: initial, end: -target}
    for when, amount in flows:
        if start < when <= end:
            grouped[when] = grouped.get(when, 0) + amount
    dated = [(years_between(start, d), a) for d, a in sorted(grouped.items()) if abs(a) > 1e-10]
    signs = [a > 0 for _, a in dated]
    changes = sum(a != b for a, b in zip(signs, signs[1:]))
    if not changes:
        return {"status": "no_unique_root", "annual_return": None}
    if changes != 1:
        return {"status": "ambiguous_cash_flows", "annual_return": None}
    # Discount to the start date; scale by the greatest exponential to avoid overflow.
    def npv(log_rate):
        powers = [-log_rate * t for t, _ in dated]
        scale = max(powers)
        return sum(a * exp(p - scale) for p, (_, a) in zip(powers, dated))

    lo, hi = -20.0, 20.0
    if npv(lo) * npv(hi) > 0:
        return {"status": "root_outside_range", "annual_return": None}
    root = brentq(npv, lo, hi, xtol=1e-12)
    balance, previous = 0.0, 0.0
    for time, amount in dated:
        balance = balance * exp(root * (time - previous)) + amount
        if time < dated[-1][0] and balance < -max(1e-6, initial * 1e-9):
            return {"status": "requires_interim_borrowing", "annual_return": None}
        previous = time
    return {"status": "calculated", "annual_return": exp(root) - 1}


def validate_mandate(payload):
    """Validate, normalize and analyze a fictional profile without persisting it."""
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid_schema")
    if not boolean(payload.get("consent"), "consent"):
        raise ValueError("consent_required")
    currency = choice(payload.get("currency"), CURRENCIES, "currency")
    start = day(payload.get("as_of"), "as_of")
    end = day(payload.get("horizon_date"), "horizon_date")
    if end <= start or years_between(start, end) > 100:
        raise ValueError("invalid_horizon")
    fx = number(payload.get("chf_per_usd"), "chf_per_usd", minimum=0.000001, optional=True)
    inflation = number(payload.get("inflation"), "inflation", minimum=-0.99, maximum=1, optional=True)
    fields = ("capital", "cash", "investments", "other_assets", "debt", "reserve", "income_monthly",
              "spending_monthly", "contribution_monthly", "withdrawal_monthly", "loss_capacity_amount")
    values = {field: number(payload.get(field), field, maximum=1e15) for field in fields}
    if values["capital"] <= 0:
        raise ValueError("capital_positive")
    if values["reserve"] > values["cash"]:
        raise ValueError("reserve_exceeds_cash")
    liquid_wealth = values["cash"] + values["investments"] - values["reserve"]
    wealth = values["cash"] + values["investments"] + values["other_assets"] - values["debt"]
    surplus = values["income_monthly"] - values["spending_monthly"]
    warnings, conflicts = [], []
    if values["capital"] > liquid_wealth:
        conflicts.append("capital_exceeds_investable_wealth")
    if values["contribution_monthly"] > max(surplus, 0):
        conflicts.append("contribution_exceeds_surplus")
    if surplus < 0 and values["withdrawal_monthly"] < -surplus:
        conflicts.append("unfunded_monthly_deficit")
    if wealth < 0:
        warnings.append("negative_net_worth")

    raw_flows = payload.get("dated_flows")
    if not isinstance(raw_flows, list) or len(raw_flows) > 120:
        raise ValueError("invalid_field:dated_flows")
    dated = []
    for row in raw_flows:
        if not isinstance(row, dict):
            raise ValueError("invalid_field:dated_flows")
        when = day(row.get("date"), "flow_date")
        if not start < when <= end:
            raise ValueError("flow_outside_horizon")
        kind = choice(row.get("kind"), {"contribution", "withdrawal", "liability"}, "flow_kind")
        amount = number(row.get("amount"), "flow_amount", minimum=0.01, maximum=1e15)
        dated.append((when, amount if kind == "contribution" else -amount))
    recurring = []
    withdrawals = [d for d, a in dated if a < 0]
    for m in range(1, 1201):
        when = add_month(start, m)
        if when > end:
            break
        recurring.append((when, values["contribution_monthly"] - values["withdrawal_monthly"]))
        if values["withdrawal_monthly"] > 0:
            withdrawals.append(when)
    flows = sorted(dated + recurring)

    raw_goals = payload.get("goals")
    if not isinstance(raw_goals, list) or not 1 <= len(raw_goals) <= 11:
        raise ValueError("invalid_field:goals")
    goal_results, goal_flows = [], []
    for i, goal in enumerate(raw_goals):
        if not isinstance(goal, dict):
            raise ValueError("invalid_field:goals")
        objective = choice(goal.get("objective_id"), OBJECTIVES, "objective_id")
        due = day(goal.get("due_date"), "goal_due_date")
        if not start < due <= end:
            raise ValueError("goal_outside_horizon")
        priority = number(goal.get("priority"), "priority", minimum=1, maximum=5)
        if not priority.is_integer():
            raise ValueError("invalid_field:priority")
        penalty = number(goal.get("shortfall_penalty"), "shortfall_penalty", maximum=1000)
        target = number(goal.get("amount"), "goal_amount", minimum=0.01, maximum=1e15, optional=True)
        fund = boolean(goal.get("funding"), "funding")
        goal_currency = choice(goal.get("currency"), CURRENCIES, "goal_currency")
        basis = choice(goal.get("basis"), {"nominal", "real"}, "goal_basis")
        if fund and target is None:
            raise ValueError("funding_requires_amount")
        if objective in {"OBJ09", "OBJ10"} and not fund:
            raise ValueError("dated_goal_requires_funding")
        if objective == "OBJ02" and fund:
            raise ValueError("income_use_withdrawals")
        nominal = None
        result = {"status": "preference_only", "annual_return": None}
        if target is not None:
            if basis == "real" and inflation is None:
                raise ValueError("inflation_required")
            nominal = convert(target, goal_currency, currency, fx)
            if basis == "real":
                nominal *= (1 + inflation) ** years_between(start, due)
            if not isfinite(nominal):
                raise ValueError("invalid_field:goal_amount")
            if objective != "OBJ02":
                result = required_return(values["capital"], flows, start, due, nominal)
            else:
                result = {"status": "income_not_terminal", "annual_return": None}
        if fund:
            goal_flows.append((due, -nominal))
            withdrawals.append(due)
        zero_return_assets = values["capital"] + sum(a for when, a in flows if when <= due)
        goal_results.append({"goal_index": i, "objective_id": objective, "due_date": due.isoformat(),
                             "target_nominal_base": nominal, "funding": fund, "priority": int(priority),
                             "shortfall_penalty": penalty, "required_return": result,
                             "zero_return_gap": max(0, nominal - zero_return_assets)
                             if nominal is not None and objective != "OBJ02" else None})
    total_priority = sum(g["priority"] for g in goal_results)
    for goal in goal_results:
        goal["priority_weight"] = goal["priority"] / total_priority

    raw_constraints = payload.get("constraints")
    if not isinstance(raw_constraints, dict):
        raise ValueError("invalid_field:constraints")
    limits = {}
    for key in LIMITS:
        minimum = -10 if key == "net_min" else 0
        maximum = 10 if key in {"gross_limit", "net_min", "net_max", "max_turnover"} else 1
        limit = raw_constraints.get(key)
        if not isinstance(limit, dict):
            raise ValueError(f"invalid_field:{key}")
        value = number(limit.get("value"), key, minimum=minimum, maximum=maximum, optional=True)
        mode = choice(limit.get("mode"), {"hard", "soft"}, key)
        limits[key] = {"value": value, "mode": mode}
    for key in ("stress_loss", "loss_budget"):
        if limits[key]["value"] is None or limits[key]["mode"] != "hard":
            raise ValueError("required_hard_risk_limit")
    permissions = {key: boolean(raw_constraints.get(key), key) for key in
                   ("allow_short", "allow_leverage", "allow_derivatives")}
    allowed = raw_constraints.get("allowed_assets")
    if not isinstance(allowed, list) or not allowed or not set(allowed) <= ASSETS:
        raise ValueError("invalid_field:allowed_assets")
    knowledge = payload.get("knowledge")
    experience = payload.get("experience")
    if not isinstance(knowledge, dict) or not isinstance(experience, dict):
        raise ValueError("invalid_field:knowledge")
    for key in ("equity", "treasury", "futures", "leverage", "short"):
        choice(knowledge.get(key), KNOWLEDGE, key)
        choice(experience.get(key), EXPERIENCE, key)
    for permission, instrument in (("allow_short", "short"), ("allow_leverage", "leverage"),
                                   ("allow_derivatives", "futures")):
        if permissions[permission] and knowledge[instrument] == "none":
            conflicts.append(f"knowledge_required:{instrument}")
        if permissions[permission] and experience[instrument] == "none":
            conflicts.append(f"experience_required:{instrument}")
    if "futures" in allowed and not permissions["allow_derivatives"]:
        conflicts.append("derivatives_permission_required")
    if limits["net_min"]["value"] is not None and limits["net_max"]["value"] is not None:
        if limits["net_min"]["value"] > limits["net_max"]["value"]:
            conflicts.append("net_bounds_conflict")
    if not permissions["allow_leverage"] and limits["gross_limit"]["value"] is not None:
        if limits["gross_limit"]["value"] < 1:
            conflicts.append("gross_limit_below_funded_budget")
    for key in ("esg_exclusions", "tax_assumption", "fx_hedge"):
        value = raw_constraints.get(key)
        if not isinstance(value, str) or len(value) > 240:
            raise ValueError(f"invalid_field:{key}")
    choice(raw_constraints["fx_hedge"], {"none", "partial", "full", "undecided"}, "fx_hedge")
    choice(raw_constraints["tax_assumption"], {"not_modeled", "pre_tax", "after_tax_required"}, "tax_assumption")

    # Cash-flow feasibility at zero return, including funding goals; not an expected-return model.
    schedule = {}
    for when, amount in flows + goal_flows:
        schedule[when] = schedule.get(when, 0) + amount
    balance, min_balance = values["capital"], values["capital"]
    near_term_min_balance = balance
    for when, amount in sorted(schedule.items()):
        balance += amount
        min_balance = min(min_balance, balance)
        if when <= min(end, add_month(start, 12)):
            near_term_min_balance = min(near_term_min_balance, balance)
    if min_balance < 0:
        warnings.append("zero_return_funding_gap")
    if goal_flows:
        combined = required_return(values["capital"], flows + goal_flows, start, end, 0)
    else:
        combined = {"status": "no_funding_goals", "annual_return": None}
    # Loss capacity is explicitly self-declared and capped by available financial resources.
    # No behavioral score, expected return or risk tolerance is inferred here.
    capacity = min(values["loss_capacity_amount"], values["capital"], max(0, liquid_wealth),
                   max(0, near_term_min_balance))
    effective_stress = min(limits["stress_loss"]["value"], limits["loss_budget"]["value"],
                           capacity / values["capital"])
    if effective_stress < limits["stress_loss"]["value"]:
        warnings.append("stress_capped_by_capacity")
    warnings.append("market_feasibility_not_evaluated")
    # Legacy USD candidates do not evaluate the full mandate, so do not represent them as suitable.
    demo_reasons = []
    if currency != "USD":
        demo_reasons.append("demo_usd_only")
    if any(limits[k]["value"] is not None and limits[k]["mode"] == "hard" for k in LIMITS
           if k not in {"stress_loss", "loss_budget"}):
        demo_reasons.append("demo_hard_constraints_unmodeled")
    if set(allowed) != {"equity", "treasury", "reit", "cash"} or raw_constraints["esg_exclusions"].strip():
        demo_reasons.append("demo_universe_restrictions_unmodeled")
    if raw_constraints["tax_assumption"] == "after_tax_required" or raw_constraints["fx_hedge"] in {"partial", "full"}:
        demo_reasons.append("demo_tax_fx_unmodeled")
    personalized_reasons = []
    if currency != "USD":
        personalized_reasons.append("demo_usd_only")
    supported = {"stress_loss", "loss_budget", "volatility", "max_asset_weight",
                 "gross_limit", "net_min", "net_max"}
    if any(limits[k]["value"] is not None and limits[k]["mode"] == "hard"
           for k in LIMITS if k not in supported):
        personalized_reasons.append("demo_hard_constraints_unmodeled")
    if (raw_constraints["esg_exclusions"].strip() or
            raw_constraints["tax_assumption"] == "after_tax_required" or
            raw_constraints["fx_hedge"] in {"partial", "full"}):
        personalized_reasons.append("demo_tax_fx_unmodeled")
    hard = lambda k: limits[k]["mode"] == "hard" and limits[k]["value"] is not None
    if ((hard("gross_limit") and limits["gross_limit"]["value"] < 1) or
            (hard("net_min") and limits["net_min"]["value"] > 1) or
            (hard("net_max") and limits["net_max"]["value"] < 1)):
        personalized_reasons.append("funded_budget_infeasible")
    if any(limits[k]["mode"] == "soft" and limits[k]["value"] is not None
           for k in LIMITS if k not in {"volatility", "max_asset_weight"}):
        warnings.append("soft_constraints_unmodeled")
    return {
        "schema_version": SCHEMA_VERSION, "status": "conflicts" if conflicts else "structurally_valid",
        "currency": currency, "as_of": start.isoformat(), "horizon_date": end.isoformat(),
        "horizon_years": years_between(start, end), "net_worth": wealth, "investable_wealth": liquid_wealth,
        "monthly_surplus": surplus, "next_withdrawal": min(withdrawals).isoformat() if withdrawals else None,
        "loss_capacity_amount": capacity, "effective_stress_limit": effective_stress,
        "near_term_liquidity_cushion": near_term_min_balance,
        "zero_return_min_balance": min_balance, "zero_return_terminal_balance": balance,
        "goals": goal_results, "combined_required_return": combined,
        "conflicts": conflicts, "warnings": warnings, "demo_reasons": demo_reasons,
        "demo_eligible": not conflicts and not demo_reasons,
        "personalized_eligible": not conflicts and not personalized_reasons,
        "personalized_reasons": personalized_reasons,
        "risk_willingness": "not_measured", "risk_required": "not_estimated",
    }
