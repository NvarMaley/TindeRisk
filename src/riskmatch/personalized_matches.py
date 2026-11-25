"""Mandate-conditioned, funded portfolio construction on the local research universe.

All candidates are reconstructed from the mandate and frozen data. Historical
evaluation uses only information available at the start of each evaluation segment.
"""
from datetime import date
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from threading import Lock

import duckdb
import numpy as np
from scipy.optimize import linprog
from threadpoolctl import threadpool_limits

from riskmatch.backtesting.mandate_replay import replay
from riskmatch.backtesting.walk_models import REGISTRY, SIGNED, fit_models
from riskmatch.optimization.mean_variance_report import aligned, category, regularized_mean
from riskmatch.profiling.mandate import validate_mandate, add_month
from riskmatch.prototype import ClientProfile, metrics
from riskmatch.selection.sleeve_ledger import rebalance_paths
from riskmatch.simulation.stress_report import scenario_matrix
from riskmatch.strategies.alternative_report import macro_signals
from riskmatch.strategies.long_only_report import load_signals, verified_pit

VERSION = "personalized-v3"
AS_OF = date(2026, 11, 25)
KEYS = tuple(k for k in REGISTRY if k not in SIGNED)
LOCK = Lock()


def is_version(value):
    return isinstance(value, str) and value.startswith(VERSION + ":")


def hard_limit(mandate, name, default):
    limit = mandate["constraints"][name]
    return limit["value"] if limit["mode"] == "hard" and limit["value"] is not None else default


@lru_cache(maxsize=1)
def market_data(root):
    assets, intervals, returns, cash, version = aligned(root, AS_OF, "USD", "cohort")
    if len(returns) < 60:
        raise ValueError("Insufficient aligned historical observations")
    first = max(36, int(len(returns) * .4))
    split = int(len(returns) * .75)
    origins = [intervals[first][0], intervals[split][0], intervals[-1][1]]
    signals = load_signals(root, AS_OF, assets, origins, version)
    macro = macro_signals(root, version, origins)
    caps = {}
    pit = verified_pit(root, version)
    with duckdb.connect() as db:
        rows = db.execute(
            "select instrument,observation_date,market_cap_source_units from read_parquet(?) "
            "where observation_date in (select unnest(?)) and market_cap_source_units>0",
            [str(pit / "stock_membership.parquet"), origins]).fetchall()
    for instrument, day, cap in rows:
        caps.setdefault(day, {})[str(instrument)] = float(cap)
    labels = [a["ticker"] for a in assets]
    if len(set(labels)) != len(labels):
        counts = {label: labels.count(label) for label in set(labels)}
        labels = [label if counts[label] == 1 else f"{label} ({a['id']})"
                  for label, a in zip(labels, assets)]
    return assets, intervals, returns, cash, version, first, split, origins, signals, macro, caps, labels


def risk_preferences(mandate, report, aversion):
    """Transparent research calibration; psychological score is not an estimated utility."""
    goals = mandate["goals"]
    defensive = {"OBJ01", "OBJ03", "OBJ11"}
    growth = {"OBJ05", "OBJ06"}
    priority = sum(g["priority"] for g in goals)
    preference = sum(g["priority"] * (int(g["objective_id"] in defensive) -
                     int(g["objective_id"] in growth)) for g in goals) / max(priority, 1)
    willingness = (aversion - 1) / 29
    horizon = report["horizon_years"]
    risk_weight = float(np.clip(.25 + .5 * willingness + .15 * preference
                                + .1 * (1 - min(horizon / 15, 1)), .05, .95))
    return float(1 + 19 * risk_weight**2), risk_weight


def bounds_for(assets, mandate, day, membership):
    allowed = set(mandate["constraints"]["allowed_assets"])
    cap = hard_limit(mandate, "max_asset_weight", 1.)
    upper = np.array([min(cap, .05 if a["category"] == "stock" else .65)
                      if category(a) in allowed and
                      (a["ticker"] not in {"USO", "CPER", "WEAT"} or
                       mandate["constraints"]["allow_derivatives"]) and
                      (a["category"] != "stock" or str(a["instrument"]) in membership.get(day, set()))
                      else 0. for a in assets])
    cash_cap = cap if "cash" in allowed else 0.
    return upper, cash_cap


def valid_weights(weights, upper, shocks, stress_limit, covariance, vol_limit):
    return (np.isfinite(weights).all() and weights.min() >= -1e-8
            and abs(weights.sum() - 1) <= 1e-7 and np.all(weights <= upper + 1e-8)
            and np.min(shocks @ weights) >= -stress_limit - 1e-10
            and float(weights @ covariance @ weights) <= vol_limit**2 + 1e-9)


def defensive_reference(upper, shocks, covariance, stress_limit, vol_limit):
    """Find a funded minimum-worst-stress feasible reference (prefer cash if permitted)."""
    reference = np.zeros(len(upper))
    reference[-1] = min(upper[-1], 1.)
    if valid_weights(reference, upper, shocks, stress_limit, covariance, vol_limit):
        return reference
    n = len(upper)
    # Maximize the least favorable scenario return; the last variable is worst loss.
    fit = linprog(np.r_[np.zeros(n), 1.], A_ub=np.c_[-shocks, -np.ones(len(shocks))],
                  b_ub=np.zeros(len(shocks)), A_eq=[np.r_[np.ones(n), 0.]], b_eq=[1.],
                  bounds=[(0, u) for u in upper] + [(0, stress_limit)], method="highs")
    if not fit.success:
        return None
    reference = fit.x[:-1]
    if valid_weights(reference, upper, shocks, stress_limit, covariance, vol_limit):
        return reference
    # The minimum-stress solution need not minimize covariance risk.
    from riskmatch.optimization.mean_variance import MeanVariance, Constraints
    active = np.flatnonzero(upper > 0)
    lowest = sorted(active, key=lambda i: (covariance[i, i], i))[:64]
    idx = np.array(sorted(set(lowest + np.flatnonzero(reference > 1e-9).tolist())), int)
    linear = [(str(i), shock[idx], -stress_limit, 1.) for i, shock in enumerate(shocks)]
    engine = MeanVariance(np.zeros(len(idx)), covariance[np.ix_(idx, idx)], 0.,
                          Constraints(np.zeros(len(idx)), upper[idx], linear=linear))
    result = engine.solve()
    if result.get("status") != "optimal":
        return None
    reference = np.zeros(n)
    reference[idx] = result["weights"]
    return reference if valid_weights(reference, upper, shocks, stress_limit, covariance, vol_limit) else None


def adapt_target(weights, reference, upper, shocks, stress_limit, covariance, vol_limit):
    """Keep the strategy direction and shrink toward a feasible defensive allocation.

    Convex mixing preserves funded weights and linear limits. A bisection checks
    all modeled shocks and the covariance-based volatility limit.
    """
    if valid_weights(weights, upper, shocks, stress_limit, covariance, vol_limit):
        return weights
    if reference is None:
        return None
    direction = weights - reference
    stress_start = shocks @ reference
    stress_slope = shocks @ direction
    variance_start = reference @ covariance @ reference
    linear = 2 * (reference @ covariance @ direction)
    quadratic = direction @ covariance @ direction
    # On this line segment risk is quadratic and scenario P&L is linear.
    # Compute the coefficients once instead of multiplying a large matrix at every step.
    lo, hi = 0., 1.
    for _ in range(45):
        fraction = (lo + hi) / 2
        trial = reference + fraction * direction
        variance = variance_start + fraction * (linear + fraction * quadratic)
        feasible = (trial.min() >= -1e-8 and np.all(trial <= upper + 1e-8)
                    and np.min(stress_start + fraction * stress_slope) >= -stress_limit - 1e-10
                    and variance <= vol_limit**2 + 1e-9)
        if feasible:
            lo = fraction
        else:
            hi = fraction
    result = reference + max(0., lo - 1e-9) * direction
    return result if valid_weights(result, upper, shocks, stress_limit, covariance, vol_limit) else None


def construct(data, mandate, report, aversion, end, origin):
    from sklearn.covariance import LedoitWolf
    assets, _, returns, cash, _, _, _, _, signals, macro, caps, _ = data
    x, rf = returns[:end], cash[:end]
    upper, cash_cap = bounds_for(assets, mandate, origin, signals[0])
    bounds = np.r_[upper, cash_cap]
    loss = report["effective_stress_limit"]
    vol_limit = hard_limit(mandate, "volatility", 1.)
    lam, risk_weight = risk_preferences(mandate, report, aversion)
    scenarios, _ = scenario_matrix(assets, x, "USD")
    scenarios["margin_liquidity_shock"] = scenarios["margin_liquidity_shock"].copy()
    scenarios["margin_liquidity_shock"][:-1] -= .02
    shock_matrix = np.array(list(scenarios.values()))
    # Cash is modeled with the historical risk-free proxy, zero instantaneous shocks.
    covariance = np.zeros((len(bounds), len(bounds)))
    active = np.flatnonzero(bounds > 0)
    if len(active):
        covariance[np.ix_(active, active)] = LedoitWolf().fit(
            np.column_stack([x, rf])[:, active]).covariance_ * 12
    reference = defensive_reference(bounds, shock_matrix, covariance, loss, vol_limit)
    forecast = None  # identical trailing estimator at historical and current decisions
    fitted = fit_models(KEYS, x[-60:], rf[-60:], assets, upper, origin, signals,
                        optimizer_limit=64, market_caps=caps.get(origin), lam=lam, seed=24,
                        macro=macro.get(origin), forecast=forecast)
    candidates = {}
    diagnostics = {}
    for key, result in fitted.items():
        if result["status"] != "computed":
            diagnostics[key] = result.get("reason", "Model unavailable")
            continue
        w = np.asarray(result["weights"], float)
        w = np.r_[w, max(0., 1 - w.sum())]
        # Vary the preferred risk envelope with willingness, goals and horizon.
        preferred = loss * (1 - .55 * risk_weight)
        selected = adapt_target(w, reference, bounds, shock_matrix, loss, covariance, vol_limit)
        if selected is None:
            diagnostics[key] = "Target breaches a modeled hard constraint"
            continue
        preferred_reference = reference if reference is not None and valid_weights(
            reference, bounds, shock_matrix, preferred, covariance, vol_limit) else None
        if preferred_reference is not None:
            preferred_target = adapt_target(selected, preferred_reference, bounds, shock_matrix,
                                            preferred, covariance, vol_limit)
            if preferred_target is not None:
                selected = preferred_target
        # Numerical cleanup is checked again after normalization.
        selected = np.maximum(selected, 0.)
        selected /= selected.sum()
        if not valid_weights(selected, bounds, shock_matrix, loss, covariance, vol_limit):
            diagnostics[key] = "Numerical constraint residual"
            continue
        candidates[key] = selected
    if reference is not None and valid_weights(reference, bounds, shock_matrix, loss, covariance, vol_limit):
        candidates["defensive_reference"] = reference
        # A directly constrained utility optimizer complements the existing
        # strategy-specific targets and their feasible defensive adjustments.
        from riskmatch.optimization.mean_variance import MeanVariance, Constraints
        active = np.flatnonzero(upper > 0)
        stock = [i for i in active if assets[i]["category"] == "stock"]
        etfs = [i for i in active if assets[i]["category"] != "stock"]
        ranked = sorted(stock, key=lambda i: (
            -caps.get(origin, {}).get(str(assets[i]["instrument"]), 0.), assets[i]["id"]))
        selected = sorted(set(etfs + ranked[:max(0, 64-len(etfs))] +
                              np.flatnonzero(reference > 1e-9).tolist() + [len(upper)]))
        idx = np.array(selected, int)
        if len(idx) > 1 and bounds[idx].sum() >= 1-1e-9:
            mean = np.r_[regularized_mean(x[-60:], forecast if forecast is not None else None),
                         float(np.mean(rf[-60:])*12)]
            preferred = loss * (1-.55*risk_weight)
            effective = preferred if np.min(shock_matrix @ reference) >= -preferred else loss
            linear = [(key, shock[idx], -effective, 1.) for key, shock in scenarios.items()]
            model = MeanVariance(mean[idx], covariance[np.ix_(idx, idx)], mean[-1],
                                 Constraints(np.zeros(len(idx)), bounds[idx], linear=linear))
            result = model.solve(return_weight=1., variance_weight=lam)
            if result.get("status") == "optimal":
                weights = np.zeros(len(bounds))
                weights[idx] = result["weights"]
                adjusted = adapt_target(weights, reference, bounds, shock_matrix,
                                        loss, covariance, vol_limit)
                if adjusted is not None:
                    adjusted = np.maximum(adjusted, 0.)
                    adjusted /= adjusted.sum()
                    if valid_weights(adjusted, bounds, shock_matrix, loss, covariance, vol_limit):
                        candidates["constrained_utility"] = adjusted
            if "constrained_utility" not in candidates:
                diagnostics["constrained_utility"] = result.get("reason", "Constrained solve unavailable")
    for key in ("defensive_reference", "constrained_utility"):
        if key not in candidates:
            diagnostics.setdefault(key, "No feasible defensive reference or funded optimization subset")
    return candidates, diagnostics, scenarios, covariance, int(np.count_nonzero(upper)), lam, risk_weight


def fingerprint(mandate, aversion, data_version, style="000"):
    payload = json.dumps([VERSION, data_version, mandate, aversion], sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    return f"{VERSION}:{aversion}:{style}:{hashlib.sha256(payload.encode()).hexdigest()}"


def objective_fit(goal, lam):
    """Normalize each supported objective on a fixed research scale."""
    metrics = goal["metrics"]
    kind = goal["objective_id"]
    growth = lambda value: float(np.clip((value + .05) / .20, 0., 1.)) if value is not None else None
    if kind in {"OBJ01", "OBJ11"}:
        value = 1 - metrics["nominal_capital_loss_probability"]
    elif kind == "OBJ02":
        value = metrics["withdrawal_coverage"]
    elif kind == "OBJ03":
        value = 1 - metrics["loss_budget_breach_probability"]
    elif kind == "OBJ04":
        value = growth(metrics["market_cagr"] - .5 * lam * metrics["annual_cagr_dispersion"]**2)
    elif kind in {"OBJ05", "OBJ06"}:
        value = growth(metrics["market_cagr"])
    elif kind == "OBJ07":
        value = growth(metrics["real_market_cagr"])
    elif kind == "OBJ08":
        value = growth(metrics["cash_excess_cagr"])
    else:
        value = goal["probability"]
    if goal["probability"] is not None and kind not in {"OBJ09", "OBJ10"}:
        value = goal["probability"] if value is None else .5 * (value + goal["probability"])
    if goal["normalized_shortfall"] is not None and value is not None:
        value *= 1 - min(1., goal["normalized_shortfall"] * goal["penalty"])
    return None if value is None else float(np.clip(value, 0., 1.))


def run(root, mandate, aversion=None, style="000"):
    if not isinstance(style, str) or len(style) != 3 or any(c not in "012" for c in style):
        raise ValueError("Invalid preference profile")
    if aversion is None:
        raise ValueError("scoreUnavailable")
    if type(aversion) is not int or not 1 <= aversion <= 30:
        raise ValueError("Invalid discovery score")
    report = validate_mandate(mandate)
    if not report["personalized_eligible"] or mandate["as_of"] < str(AS_OF):
        raise ValueError("demoUnavailable")
    encoded = json.dumps(mandate, sort_keys=True, separators=(",", ":"), allow_nan=False)
    with LOCK, threadpool_limits(limits=1):
        return _run(Path(root).resolve(), encoded, aversion, style)


@lru_cache(maxsize=8)
def _run(root, encoded, aversion, style):
    mandate = json.loads(encoded)
    report = validate_mandate(mandate)
    data = market_data(root)
    assets, intervals, x, rf, data_version, first, split, origins, _, _, _, labels = data
    history, failures = replay(root, data, mandate, report, aversion, construct, AS_OF)
    current, unavailable, scenarios, covariance, eligible_count, lam, risk_weight = construct(
        data, mandate, report, aversion, len(x), origins[2])
    assets_with_cash = labels + ["USD cash"]
    date_rows = intervals[first:]
    shared = history.keys() & current.keys()
    benchmark = "defensive_reference" if "defensive_reference" in shared else next(iter(sorted(shared)), None)
    reference = np.array(history[benchmark]["returns"]) if benchmark else np.array([])
    from riskmatch.analytics.factor_report import factor_report
    from riskmatch.analytics.forecast_batch import batch_report
    input_version = hashlib.sha256(json.dumps([
        data_version, factor_report(root, AS_OF).get("run_id"), batch_report(root, AS_OF).get("run_id")
    ], sort_keys=True).encode()).hexdigest()
    version = fingerprint(mandate, aversion, input_version, style)
    from riskmatch.analytics.objectives import evaluate, bootstrap_indices
    start = date.fromisoformat(report["as_of"])
    end = date.fromisoformat(report["horizon_date"])
    months = 1
    while add_month(start, months) < end:
        months += 1
    if months > 600:
        raise ValueError("Research scenario horizon exceeds 50 years")
    indices = bootstrap_indices(split-first, months, paths=256, block=6, seed=25)
    cash_paths = rf[first:split][indices]
    half = (split-first)//2
    windows = [bootstrap_indices(half, months, paths=256, block=6, seed=25) + offset
               for offset in (0, split-first-half)]
    current_mean = regularized_mean(x[-60:])
    expected_returns = np.r_[current_mean, float(np.mean(rf[-60:]) * 12)]
    rows, cards = {}, []
    for name, w in current.items():
        if name not in history:
            unavailable[name] = failures.get(name, "No comparable dated historical path")
            continue
        path = history[name]
        returns = np.array(path["returns"])
        holdings = dict(zip(assets_with_cash, w.tolist()))
        stresses = {key: float(shock @ w) for key, shock in scenarios.items()}
        stress = max(0., -min(stresses.values()))
        estimate = float(expected_returns @ w)
        vol = float(np.sqrt(max(0., w @ covariance @ w)))
        projection = evaluate(mandate, returns[:split-first][indices], cash_paths, report=report)
        goal_summary = [{k: goal[k] for k in ("objective_id", "priority", "probability",
                                              "expected_deficit", "target", "funding")}
                        for goal in projection["goals"]]
        window_goals = [evaluate(mandate, returns[idx], rf[first:split][idx], report=report)["goals"]
                        for idx in windows]
        for j, (summary, goal) in enumerate(zip(goal_summary, projection["goals"])):
            probabilities = [g[j]["probability"] for g in window_goals]
            summary["window_probabilities"] = probabilities
            summary["objective_fit"] = objective_fit(goal, lam)
            summary["limitations"] = goal["limitations"]
        measured = [g for g in goal_summary if g["objective_fit"] is not None]
        fit = (sum(g["priority"]*g["objective_fit"] for g in measured) /
               sum(g["priority"] for g in measured)) if measured else None
        rows[name] = (holdings, stresses, returns)
        cards.append({"name": name, "version": version, "weights": holdings,
                      "period": f"{intervals[split][0]} – {intervals[-1][1]} · USD",
                      "costs": "10 bp on securities traded; quarterly signals, one-month execution lag",
                      "stress_loss": stress, "stress_usd": stress * mandate["capital"],
                      "metrics": metrics(returns[split-first:, None], [1]),
                      "worst_scenario": min(stresses, key=stresses.get),
                      "expected_return": estimate, "estimated_volatility": vol,
                      "development_turnover": float(12*np.mean(path["turnover"][:split-first])),
                      "development_return": float(12 * returns[:split-first].mean()),
                      "eligible_assets": eligible_count, "universe_size": len(assets),
                      "model_as_of": str(intervals[-1][1]), "goal_projection_paths": 256, "development_months": split-first,
                      "forecast_source": "Regularized trailing monthly returns at each decision",
                      "goal_projection": goal_summary,
                      "weighted_target_penalty": projection["weighted_target_penalty"],
                      "objective_fit": fit,
                      "risk_aversion_parameter": lam, "personalized": True,
                      "research_warning": "Quarterly refit with dated stock membership; retrospective ETF list and unverified release times."})
    # Goal return is a preference, not a guaranteed constraint.
    required = [g["required_return"]["annual_return"] for g in report["goals"]
                if g["required_return"].get("annual_return") is not None]
    target = max(required, default=None)
    for card in cards:
        growth = float(np.clip((card["expected_return"] + .05) / .20, 0, 1))
        if target is not None:
            growth = .5 * growth + .5 * float(np.clip(1 - max(target-card["expected_return"], 0.)/.20, 0, 1))
        if card["weighted_target_penalty"] is not None:
            goal_fit = float(np.clip(1-card["weighted_target_penalty"], 0., 1.))
            growth = .5 * growth + .5 * goal_fit
        if card["objective_fit"] is not None:
            growth = .5 * growth + .5 * card["objective_fit"]
        safety = float(np.clip(1 - card["stress_loss"] / max(report["effective_stress_limit"], 1e-10), 0, 1))
        soft_excess = []
        for field, observed in (("volatility", card["estimated_volatility"]),
                                ("max_asset_weight", max(card["weights"].values()))):
            constraint = mandate["constraints"][field]
            if constraint["mode"] == "soft" and constraint["value"] is not None:
                soft_excess.append(float(np.clip(max(0., observed-constraint["value"]) /
                                                  max(constraint["value"], .01), 0, 1)))
        penalty = .15 * max(soft_excess, default=0.)
        card["fit_score"] = float(risk_weight * safety + (1-risk_weight) * growth - penalty)
        weights = current[card["name"]]
        holdings = sum(weights > .0001)
        card["exposures"] = {kind: float(sum(weights[i] for i, asset in enumerate(assets)
                                                 if category(asset) == kind))
                             for kind in sorted({category(asset) for asset in assets})}
        card["exposures"]["cash"] = float(weights[-1])
        # Simple portfolios are proxied by the number of holdings. Activity uses
        # observed historical turnover; distribution income is unavailable.
        simplicity, activity, income = style
        style_terms = []
        if simplicity != "0":
            simple = 1 / np.sqrt(max(holdings, 1))
            style_terms.append(simple if simplicity == "2" else 1-simple)
        card["income_preference_unmeasured"] = income != "0"
        card["style_holdings"] = int(holdings)
        if activity != "0":
            turnover = card["development_turnover"]
            active = turnover / (1 + turnover)
            style_terms.append(active if activity == "2" else 1-active)
        if style_terms:
            card["fit_score"] += .08 * float(np.mean(style_terms))
        card["soft_constraint_penalty"] = penalty
        card["fit_risk_weight"] = risk_weight
        card["risk_growth_difference"] = safety - growth
    cards.sort(key=lambda c: (-c["fit_score"], c["name"]))
    for card in cards:
        card["pareto"] = not any(other["stress_loss"] <= card["stress_loss"] and
                                  other["expected_return"] >= card["expected_return"] and
                                  (other["stress_loss"] < card["stress_loss"] or
                                   other["expected_return"] > card["expected_return"]) for other in cards)
    # Preserve all computed strategy rules, but diversify the first twelve cards.
    diverse, remaining = [], []
    for card in cards:
        weights = current[card["name"]]
        if len(diverse) < 12 and all(.5*np.abs(weights-current[c["name"]]).sum() >= .05
                                    for c in diverse):
            diverse.append(card)
        else:
            remaining.append(card)
        card["methods_attempted"] = len(KEYS) + 2
        card["methods_unavailable"] = len(unavailable)
    distinct = []
    for card in diverse + remaining:
        alias = next((item for item in distinct if
                      .5*np.abs(current[item["name"]]-current[card["name"]]).sum() < .01), None)
        if alias is None:
            card["equivalent_methods"] = []
            distinct.append(card)
        else:
            alias["equivalent_methods"].append(card["name"])
    cards = distinct
    for shift in (-.10, 0., .10):
        effective_shift = np.clip(risk_weight+shift, 0., 1.) - risk_weight
        ranked = sorted(cards, key=lambda c: (-(c["fit_score"] + effective_shift *
                                                c["risk_growth_difference"]), c["name"]))
        for rank, card in enumerate(ranked, start=1):
            card.setdefault("sensitivity_ranks", []).append(rank)
    return {"version": version, "cards": cards, "rows": rows, "split": split-first,
            "reference": reference, "benchmark": benchmark, "cash": rf[first:], "dates": [str(b) for _, b in date_rows],
            "unavailable": unavailable, "data_version": data_version, "covariance": covariance,
            "labels": assets_with_cash, "eligible_assets": eligible_count}


def resolve(root, mandate, version):
    if not is_version(version):
        raise ValueError("Invalid personalized deck version")
    try:
        aversion = int(version.split(":")[1])
    except (ValueError, IndexError):
        raise ValueError("Invalid personalized deck version") from None
    result = run(root, mandate, aversion, version.split(":")[2])
    if result["version"] != version:
        raise ValueError("Stale personalized deck; rebuild after mandate or data changes")
    return result


def blend(root, mandate, version, names, budgets, optimized):
    from riskmatch.historical_matches import blend_rows
    context = resolve(root, mandate, version)
    if not context["cards"]:
        raise ValueError("No feasible personalized strategies")
    validated = validate_mandate(mandate)
    profile = ClientProfile(mandate["capital"], validated["horizon_years"], validated["effective_stress_limit"])
    if not isinstance(names, list) or any(not isinstance(k, str) or k not in {c["name"] for c in context["cards"]} for k in names):
        raise ValueError("Ineligible or stale selection")
    result = blend_rows(profile, names, budgets, optimized, context["rows"], context["split"],
                        context["reference"], version, context["cards"][0]["period"],
                        "10 bp modeled trades and additional sleeve transfers")
    weights = np.array([result["weights"][label] for label in context["labels"]])
    vol = float(np.sqrt(max(0., weights @ context["covariance"] @ weights)))
    if vol > hard_limit(mandate, "volatility", 1.) + 1e-7:
        raise ValueError("Combined portfolio exceeds modeled volatility limit")
    result["estimated_volatility"] = vol
    result["personalized"] = True
    result["benchmark"] = context["benchmark"]
    cards = {card["name"]: card for card in context["cards"]}
    result["expected_return"] = sum(budget * cards[name]["expected_return"]
                                    for name, budget in result["budgets"].items())
    result["model_as_of"] = context["cards"][0]["model_as_of"]
    result["eligible_assets"] = context["eligible_assets"]
    result["universe_size"] = context["cards"][0]["universe_size"]
    return result
