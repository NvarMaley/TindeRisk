"""Mandate-conditioned, funded portfolio construction on the local research universe.

All candidates are reconstructed from the mandate and frozen data. Historical
evaluation uses only information available at the start of each evaluation segment.
"""
from collections import Counter
from datetime import date
from functools import lru_cache, partial
import hashlib
import json
from pathlib import Path
from threading import Lock

import duckdb
import numpy as np
from scipy.optimize import linprog
from threadpoolctl import threadpool_limits

from riskmatch.analytics.descriptive_report import client_catalog
from riskmatch.backtesting.baseline_report import IDS, continuous_segments
from riskmatch.backtesting.mandate_replay import (
    ESTIMATION_MONTHS, EXECUTION_LAG_MONTHS, archive, eligible_indices, replay,
)
from riskmatch.backtesting.card_performance import card_performance
from riskmatch.backtesting.walk_models import REGISTRY, SIGNED, fit_models
from riskmatch.optimization.mean_variance_report import category, class_regularized_mean
from riskmatch.profiling.mandate import MATCHING_MAX_MONTHS, validate_mandate, add_month
from riskmatch.prototype import ClientProfile, metrics
from riskmatch.selection.sleeve_ledger import rebalance_paths
from riskmatch.simulation.stress_report import scenario_matrix
from riskmatch.market_data.returns import returns_report
from riskmatch.market_data.security_master import load_catalog
from riskmatch.market_data.portfolio_classification import dated_classification, exclusion_rule, optional_preferences
from riskmatch.simulation.stress_mc import covariance_model
from riskmatch.strategies.long_only_report import verified_pit

VERSION = "personalized-v3"
VARIANCE_PENALTY_SCALE = 13.3
AS_OF = date(2026, 11, 25)
DATA_END = date(2025, 12, 31)
DEVELOPMENT_START = date(2020, 12, 31)
HOLDOUT_START = date(2023, 11, 30)
MATCHING_PROTOCOL = "usd-dated-membership-60-v5"
MATCHING_INSTRUMENT_CATEGORIES = ("stock", "equity_etf", "treasury_etf")
RESEARCH_METHODS = ("passive_index", "maximum_sortino", "maximum_omega")
KEYS = tuple(k for k in REGISTRY if k not in SIGNED and k not in RESEARCH_METHODS
             and k != "smart_beta_equal")
OVERLAY_METHODS = ("defensive_reference", "constrained_utility")
FUNDED_METHODS = (*KEYS, *OVERLAY_METHODS)
FEATURED_LIMIT = 6
LOCK = Lock()


def is_version(value):
    return isinstance(value, str) and value.startswith(VERSION + ":")


def hard_limit(mandate, name, default):
    limit = mandate["constraints"][name]
    return limit["value"] if limit["mode"] == "hard" and limit["value"] is not None else default


@lru_cache(maxsize=1)
def listed_funds(root, version):
    _, instruments = load_catalog(root / "configs/universe_catalog.json")
    pit = verified_pit(root, version)
    with duckdb.connect() as db:
        identifiers = dict(db.execute(
            "select ticker,arg_max(instrument,observation_date) from read_parquet(?) "
            "where observation_date<=? group by ticker",
            [str(pit / "etf_daily_volume.parquet"), DATA_END]).fetchall())
    funds = tuple((fund.security_id, fund.asset_class, fund.ticker,
                   identifiers[fund.ticker], "etf_crsp_monthly")
                  for fund in instruments if fund.asset_class in ("equity_etf", "treasury_etf")
                  and fund.currency == "USD" and fund.ticker in identifiers
                  and (fund.listing_date or fund.inception) <= DATA_END)
    if len({fund[3] for fund in funds}) != len(funds):
        raise ValueError("Duplicate ETF identity in the matching registry")
    return funds


def matching_calendar(root, version):
    """Align the SPY valuation calendar and the monthly USD cash proxy."""
    pit = verified_pit(root, version)
    rf_path = pit / "fama_french.parquet"
    report = json.loads((pit.parent / "report.json").read_text())
    expected = next(row["file_hash"] for row in report["datasets"] if row["dataset"] == "fama_french")
    with rf_path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError("Cash proxy input hash mismatch")
    with duckdb.connect() as db:
        rows = db.execute(
            "select start_date,end_date from read_parquet(?) where instrument=? "
            "and start_date>=? and end_date<=? and isfinite(total_return) and total_return>=-1 "
            "order by end_date",
            [str(root / "data/processed/returns" / version / "etf_crsp_monthly.parquet"),
             IDS[0], date(2015, 10, 30), DATA_END]).fetchall()
        rates = db.execute(
            "select observation_date,value from read_parquet(?) where instrument='RF' "
            "and frequency='monthly' and observation_date<=? and isfinite(value) and value>=-1",
            [str(rf_path), DATA_END]).fetchall()
    monthly = {(day.year, day.month): rate for day, rate in rates}
    if len(monthly) != len(rates) or len({b for _, b in rows}) != len(rows):
        raise ValueError("Duplicate matching calendar or cash observation")
    open_months = [(a, b) for a, b in rows if (b.year, b.month) in monthly
                   and (b.year-a.year)*12+b.month-a.month == 1]
    segments = continuous_segments(open_months)
    if not segments or segments[-1][-1][1] != DATA_END:
        raise ValueError("The matching calendar does not reach the frozen cutoff")
    intervals = tuple(segments[-1])
    cash = np.array([monthly[b.year, b.month] for _, b in intervals])
    return intervals, cash


@lru_cache(maxsize=1)
def market_data(root):
    root = Path(root).resolve()
    version = returns_report(root, AS_OF).get("return_id")
    if not version:
        raise ValueError("Matching return archive unavailable")
    intervals, cash = matching_calendar(root, version)
    starts = [a for a, _ in intervals]
    first, split = starts.index(DEVELOPMENT_START), starts.index(HOLDOUT_START)
    if first < ESTIMATION_MONTHS + EXECUTION_LAG_MONTHS:
        raise ValueError("Insufficient history to start the comparable replay")
    origins = [starts[first], starts[split], DATA_END]
    assets, panel, available, signals, macro, caps, settlements = archive(
        root, intervals, first, listed_funds(root, version), version, AS_OF)
    indices = eligible_indices(assets, panel[-ESTIMATION_MONTHS:],
                               available[-ESTIMATION_MONTHS:], DATA_END, caps.get(DATA_END, {}))
    indices = [i for i in indices if i not in settlements or settlements[i][0] > DATA_END]
    with duckdb.connect() as db:
        tickers = dict(db.execute(
            "select instrument,snapshot_ticker from read_parquet(?)",
            [str(verified_pit(root, version) / "stock_refresh_identity.parquet")]).fetchall())
    selected = [assets[i].copy() for i in indices]
    for asset in selected:
        if asset["category"] == "stock":
            asset["ticker"] = tickers.get(asset["instrument"]) or asset["ticker"]
    if not any(asset["ticker"] == "SPY" for asset in selected):
        raise ValueError("SPY reference unavailable on the matching window")
    labels = [asset["ticker"] for asset in selected]
    counts = Counter(labels)
    labels = [label if counts[label] == 1 else f"{label} ({asset['id']})"
              for label, asset in zip(labels, selected)]
    return selected, intervals, panel[:, indices], cash, version, first, split, origins, signals, macro, caps, labels


def matching_catalog(root, as_of):
    root = Path(root).resolve()
    assets, intervals, *_ = market_data(root)
    catalog = client_catalog(root, as_of)
    catalogue = {item["id"]: item for item in catalog["items"]}
    first, last = intervals[-ESTIMATION_MONTHS][0].isoformat(), intervals[-1][1].isoformat()
    items = []
    for asset in assets:
        item = catalogue.get(asset["id"])
        if item is None:
            # An archived constituent may be absent from the newer descriptive stock list.
            item = {**asset, "name": asset["ticker"], "provider": "CRSP / DoltHub",
                    "url": "https://www.crsp.org/", "series": [{
                        "source": asset["source"], "instrument": asset["instrument"],
                        "frequency": "monthly", "first": first, "last": last,
                        "kinds": ["total_return"], "kind_dates": {
                            "total_return": {"first": first, "last": last}},
                    }]}
        items.append({**item, "matching_source": asset["source"]})
    items.append({**catalogue["cash"], "matching_source": "fama_french_rf"})
    return {**catalog, "items": items, "matching_data_start": first,
            "matching_data_end": last, "matching_months": ESTIMATION_MONTHS}


def matching_classification(root, data):
    _, intervals, _, _, _, first, _, _, _, _, caps, _ = data
    dates = tuple(a for a, _ in intervals[first-EXECUTION_LAG_MONTHS:]) + (DATA_END,)
    instruments = tuple(sorted({instrument for members in caps.values() for instrument in members}))
    return dated_classification(Path(root).resolve(), dates, instruments)


def matching_exclusions(root, mandate, data=None):
    companies, sectors, _ = optional_preferences(mandate["constraints"])
    if not companies and not sectors:
        return None
    data = data if data is not None else market_data(Path(root).resolve())
    return exclusion_rule(mandate, matching_classification(root, data), DATA_END,
                          {a["instrument"]: a["ticker"] for a in data[0] if a["category"] == "stock"})


def portfolio_composition(root, data, weights, covariance):
    assets, *_, labels = data
    classification = matching_classification(root, data).get(DATA_END, {})
    kinds = ["stock", "equity_etf", "treasury_etf", "cash"]
    categories = [asset["category"] for asset in assets] + ["cash"]
    allocation = {kind: float(sum(w for w, item in zip(weights, categories) if item == kind)) for kind in kinds}
    sectors = Counter()
    positions = []
    for weight, label, asset in zip(weights[:-1], labels, assets):
        if weight <= 1e-8:
            continue
        sector = classification.get(asset["instrument"], (None, None, None))[2] if asset["category"] == "stock" else None
        if asset["category"] == "stock":
            sectors[sector or "unknown"] += float(weight)
        positions.append({"name": label, "weight": float(weight), "type": asset["category"], "sector": sector})
    if weights[-1] > 1e-8:
        positions.append({"name": "USD cash", "weight": float(weights[-1]), "type": "cash", "sector": None})
    positions.sort(key=lambda row: (-row["weight"], row["name"]))
    marginal = covariance @ weights
    risk = float(weights @ marginal)
    standalone = float(weights @ np.sqrt(np.maximum(covariance.diagonal(), 0.)))
    shares = {kind: float(sum(w * m for w, m, item in zip(weights, marginal, categories) if item == kind) / risk)
              for kind in kinds} if risk > 1e-12 else None
    return {"allocation": allocation, "positions": positions, "stock_sectors": dict(sectors),
            "effective_positions": float(1 / (weights @ weights)), "volatility": float(np.sqrt(max(risk, 0.))),
            "weighted_standalone_volatility": standalone, "variance_shares": shares,
            "cross_covariance": max(risk, 0.) - float((weights ** 2) @ covariance.diagonal())}


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
    return float(1 + VARIANCE_PENALTY_SCALE * risk_weight**2), risk_weight


def bounds_for(assets, mandate, day, membership):
    allowed = set(mandate["constraints"]["allowed_assets"])
    cap = hard_limit(mandate, "max_asset_weight", 1.)
    upper = np.array([min(cap, .05 if a["category"] == "stock" else .65)
                      if a["category"] in MATCHING_INSTRUMENT_CATEGORIES and category(a) in allowed and
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


def construct(data, mandate, report, aversion, end, origin, *, allowed=None):
    assets, _, returns, cash, _, _, _, _, signals, macro, caps, _ = data
    window = slice(end-ESTIMATION_MONTHS, end)
    x, rf = returns[window], cash[window]
    upper, cash_cap = bounds_for(assets, mandate, origin, signals[0])
    if allowed is not None:
        upper *= [allowed(asset, origin) for asset in assets]
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
        covariance[np.ix_(active, active)] = covariance_model(
            np.column_stack([x, rf])[:, active])[3] * 12
    reference = defensive_reference(bounds, shock_matrix, covariance, loss, vol_limit)
    expected = class_regularized_mean(x, assets)
    fitted = fit_models(KEYS, x, rf, assets, upper, origin, signals,
                        optimizer_limit=64, market_caps=caps.get(origin), lam=lam, seed=24,
                        macro=macro.get(origin), mean_estimates=expected)
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
            mean = np.r_[expected, float(np.mean(rf)*12)]
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
    for key in OVERLAY_METHODS:
        if key not in candidates:
            diagnostics.setdefault(key, "No feasible defensive reference or funded optimization subset")
    return candidates, diagnostics, scenarios, covariance, int(np.count_nonzero(upper)), lam, risk_weight


def fingerprint(mandate, aversion, data_version, style="000"):
    payload = json.dumps([VERSION, data_version, mandate, aversion, VARIANCE_PENALTY_SCALE,
                          MATCHING_PROTOCOL, DATA_END.isoformat()], sort_keys=True,
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
    funds = listed_funds(root, data_version)
    _, _, prefer_diversification = optional_preferences(mandate["constraints"])
    allowed = matching_exclusions(root, mandate, data)
    fit = partial(construct, allowed=allowed)
    history, failures = replay(root, data, mandate, report, aversion, fit, AS_OF,
                               funds, allowed=allowed)
    current, unavailable, scenarios, covariance, eligible_count, lam, risk_weight = fit(
        data, mandate, report, aversion, len(x), origins[2])
    assets_with_cash = labels + ["USD cash"]
    date_rows = intervals[first:]
    shared = history.keys() & current.keys()
    benchmark = "defensive_reference" if "defensive_reference" in shared else next(iter(sorted(shared)), None)
    reference = np.array(history[benchmark]["returns"]) if benchmark else np.array([])
    comparison = next((name for name in ("equal_weight", "defensive_reference") if name in shared), None)
    comparison_returns = np.asarray(history[comparison]["returns"]) if comparison else None
    from riskmatch.analytics.factor_report import factor_report
    input_version = hashlib.sha256(json.dumps([
        data_version, factor_report(root, AS_OF).get("run_id"), funds
    ], sort_keys=True).encode()).hexdigest()
    version = fingerprint(mandate, aversion, input_version, style)
    from riskmatch.analytics.objectives import evaluate, bootstrap_indices
    start = date.fromisoformat(report["as_of"])
    end = date.fromisoformat(report["horizon_date"])
    months = 1
    while add_month(start, months) < end:
        months += 1
    if months > MATCHING_MAX_MONTHS:
        raise ValueError("Research scenario horizon exceeds 50 years")
    indices = bootstrap_indices(split-first, months, paths=256, block=6, seed=25)
    cash_paths = rf[first:split][indices]
    half = (split-first)//2
    windows = [bootstrap_indices(half, months, paths=256, block=6, seed=25) + offset
               for offset in (0, split-first-half)]
    current_mean = class_regularized_mean(x[-ESTIMATION_MONTHS:], assets)
    expected_returns = np.r_[current_mean, float(np.mean(rf[-ESTIMATION_MONTHS:]) * 12)]
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
                      "costs": "10 bp on securities traded; quarterly target updates, monthly rebalancing, one-month execution lag",
                      "stress_loss": stress, "stress_usd": stress * mandate["capital"],
                      "metrics": metrics(returns[split-first:, None], [1], cash_returns=rf[split:]),
                      "backtest": card_performance(returns, rf[first:], date_rows, split-first,
                                                   benchmark_name=comparison, benchmark_returns=comparison_returns),
                      "worst_scenario": min(stresses, key=stresses.get),
                      "expected_return": estimate, "estimated_volatility": vol,
                      "development_turnover": float(12*np.mean(path["turnover"][:split-first])),
                      "development_return": float(12 * returns[:split-first].mean()),
                      "eligible_assets": eligible_count, "universe_size": len(assets),
                      "model_as_of": str(intervals[-1][1]), "estimation_months": ESTIMATION_MONTHS, "goal_projection_paths": 256, "development_months": split-first,
                      "forecast_source": "Trailing 60 monthly returns shrunk toward their asset-class median",
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
        if prefer_diversification:
            card["fit_score"] += .08 * (1 - float(weights @ weights))
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
    # Keep the best fitting allocations with at least 5% of capital reallocated
    # between any two featured portfolios.
    diverse, remaining = [], []
    for card in cards:
        weights = current[card["name"]]
        card["featured"] = len(diverse) < FEATURED_LIMIT and all(
            .5*np.abs(weights-current[c["name"]]).sum() >= .05 for c in diverse)
        if card["featured"]:
            diverse.append(card)
        else:
            remaining.append(card)
        card["methods_attempted"] = len(FUNDED_METHODS)
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
    spy = next(i for i, asset in enumerate(assets) if asset["ticker"] == "SPY")
    spy_returns = x[split:, spy].copy()
    spy_returns[0] = (1 + spy_returns[0]) / 1.001 - 1
    market_metrics = metrics(spy_returns[:, None], [1], cash_returns=rf[split:])
    return {"version": version, "cards": cards, "rows": rows, "split": split-first,
            "reference": reference, "benchmark": benchmark, "cash": rf[first:], "dates": [str(b) for _, b in date_rows],
            "unavailable": unavailable, "data_version": data_version, "covariance": covariance,
            "labels": assets_with_cash, "eligible_assets": eligible_count,
            "market_reference": {k: market_metrics[k] for k in ("cagr", "vol", "sharpe")}}


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


def comparison_report(deck):
    """Expose mandate-specific availability while keeping legacy card responses."""
    representatives = {card["name"]: card["name"] for card in deck["cards"]}
    representatives.update({name: card["name"] for card in deck["cards"]
                            for name in card["equivalent_methods"]})
    methods = []
    for name in FUNDED_METHODS:
        if name in representatives:
            methods.append({"name": name, "status": "available",
                            "card": representatives[name]})
        else:
            reason = deck["unavailable"][name]
            status = "backtest_incomplete" if reason[4:5] == "-" and reason[10:11] == ":" else "unavailable"
            methods.append({"name": name, "status": status, "reason": reason})
    methods.extend({"name": name, "status": "research"} for name in RESEARCH_METHODS)
    return {"cards": deck["cards"], "methods": methods, "market_reference": deck["market_reference"]}


def blend(root, mandate, version, names, budgets, optimized):
    from riskmatch.historical_matches import blend_rows
    context = resolve(root, mandate, version)
    if not context["cards"]:
        raise ValueError("No feasible personalized strategies")
    validated = validate_mandate(mandate)
    profile = ClientProfile(mandate["capital"], validated["horizon_years"], validated["effective_stress_limit"])
    cards = {card["name"]: card for card in context["cards"]}
    if (not isinstance(names, list) or not names or
            any(not isinstance(k, str) or k not in cards for k in names) or len(set(names)) != len(names)):
        raise ValueError("Ineligible or stale selection")
    if optimized == "return":
        # Return is linear in the sleeve budgets. Each individual sleeve is
        # already feasible, so the best feasible single sleeve attains the maximum.
        best = max(names, key=lambda name: cards[name]["expected_return"])
        budgets = [float(name == best) for name in names]
        optimized = False
    result = blend_rows(profile, names, budgets, optimized, context["rows"], context["split"],
                        context["reference"], version, context["cards"][0]["period"],
                        "10 bp modeled trades and additional sleeve transfers", cash=context["cash"])
    weights = np.array([result["weights"][label] for label in context["labels"]])
    vol = float(np.sqrt(max(0., weights @ context["covariance"] @ weights)))
    if vol > hard_limit(mandate, "volatility", 1.) + 1e-7:
        raise ValueError("Combined portfolio exceeds modeled volatility limit")
    result["estimated_volatility"] = vol
    result["personalized"] = True
    result["benchmark"] = context["benchmark"]
    result["expected_return"] = sum(budget * cards[name]["expected_return"]
                                    for name, budget in result["budgets"].items())
    result["model_as_of"] = context["cards"][0]["model_as_of"]
    result["eligible_assets"] = context["eligible_assets"]
    result["universe_size"] = context["cards"][0]["universe_size"]
    data = market_data(Path(root).resolve())
    result["composition"] = portfolio_composition(root, data, weights, context["covariance"])
    return result
