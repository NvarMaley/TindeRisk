"""Construct and measure distinct portfolios on one dated CHF mandate."""

from dataclasses import replace
import cvxpy as cp
import numpy as np
from scipy.optimize import minimize
from ..feasibility.engine import Frontier
from ..feasibility.inputs import estimate
from ..feasibility.study import market

LABELS = ("Return", "Robust", "Diversification", "Hedge", "60/40 benchmark")


def models(history, config, current=None):
    out = []
    for days, method, shrink in [
        (504, "LedoitWolf", 0.5),
        (756, "LedoitWolf", 0.5),
        (504, "empirical", 0.75),
    ]:
        if len(history) < days:
            raise ValueError("History of insufficient calibration")
        mu, root = estimate(history.tail(days), method, shrink)
        p = market(history.columns, mu, root, config)
        out.append(replace(p, current=current) if current is not None else p)
    return out


def weights(models, shock, high, concession, low=0.0):
    p = models[0]
    frontier = Frontier(p)
    primary = frontier.solve(low=low, high=high)
    if not primary["candidate"]:
        raise ValueError("No ceiling portfolio verified")
    best = primary["candidate"]
    result = {LABELS[0]: np.array(best["weights"])}
    n = len(p.names)
    x = cp.Variable(2 * n)
    w = x[:n]
    constraints = [
        frontier.A @ x <= frontier.b,
        w >= p.lo,
        w <= p.hi,
        x[n:] >= 0,
        x[n:] <= 1,
        cp.norm(p.root @ w) <= high,
    ]
    floor = frontier.g @ x >= best["net"] - concession
    worst = cp.Variable()
    robust = [cp.norm(m.root @ w) <= high for m in models]
    robust.extend(worst <= m.mu @ w - m.fees @ x[n:] / m.years for m in models)
    for name, objective, extra in [
        (LABELS[1], cp.Maximize(worst), robust),
        (LABELS[2], cp.Minimize(cp.sum_squares(w) + cp.square(1 - cp.sum(w))), [floor]),
        (LABELS[3], cp.Maximize(shock @ w), [floor]),
    ]:
        fit = cp.Problem(objective, [*constraints, *extra])
        fit.solve(solver="CLARABEL")
        if fit.status == cp.OPTIMAL and w.value is not None:
            candidate = np.maximum(w.value.copy(), 0)
            # A lower volatility edge is non-convex. Approach it from the verified
            # primary witness; validate the actual result and all variant constraints.
            witness = result[LABELS[0]]
            if (
                np.linalg.norm(p.root @ candidate) < low
                and np.linalg.norm(p.root @ witness) >= low
            ):
                left, right = 0.0, 1.0
                for _ in range(45):
                    mid = (left + right) / 2
                    if (
                        np.linalg.norm(
                            p.root @ (candidate + mid * (witness - candidate))
                        )
                        < low
                    ):
                        left = mid
                    else:
                        right = mid
                candidate = candidate + right * (witness - candidate)
            valid = p.evaluate(candidate, low=low, high=high)["valid"]
            if name == LABELS[1]:
                valid = valid and all(
                    m.evaluate(candidate, high=high)["valid"] for m in models
                )
            else:
                valid = (
                    valid
                    and p.evaluate(candidate)["net"] >= best["net"] - concession - 1e-6
                )
            if valid:
                result[name] = candidate
    ref = np.zeros(n)
    ref[p.names.index("SPY")] = 0.60
    ref[p.names.index("IEF")] = 0.40
    result[LABELS[4]] = ref
    return result


def distinct(options, threshold):
    kept, aliases = {}, {}
    for name, w in options.items():
        match = next(
            (
                key
                for key, v in kept.items()
                if (abs(w - v).sum() + abs(w.sum() - v.sum())) / 2 <= threshold
            ),
            None,
        )
        if match is None:
            kept[name] = w
        else:
            aliases[name] = match
    return kept, aliases


def metrics(models, w, shock, low, high, rf=0.0):
    p = models[0]
    c = p.evaluate(w, low, high)
    cov = (p.root.T @ p.root).toarray()
    variance = float(w @ cov @ w)
    vol = np.sqrt(max(variance, 0))
    contributions = w * (cov @ w) / vol if vol > 1e-9 else np.zeros(len(w))
    if abs(contributions.sum() - c["risk"]) > 1e-7:
        raise ValueError("Failure to reconcile contributions to Euler")
    values = [m.evaluate(w)["net"] for m in models]
    return dict(
        net=c["net"],
        interval=[min(values), max(values)],
        vol=float(vol),
        variance=variance,
        fee=c["fee"],
        cash=c["cash"],
        turnover=c["turnover"],
        valid=c["valid"],
        violations=c["residual"],
        euler=dict(zip(p.names, contributions.tolist())),
        sharpe=(c["net"] - rf) / vol if vol > 1e-8 else None,
        loss=float(-shock @ w),
        hhi=float(w @ w + (1 - w.sum()) ** 2),
        weights=dict(zip(p.names, w.tolist())),
    )


def combine(components, parts):
    W = np.asarray(components, float)
    a = np.asarray(parts, float)
    if (
        W.ndim != 2
        or len(W) == 0
        or a.shape != (len(W),)
        or not np.isfinite(a).all()
        or not np.isfinite(W).all()
        or (a < 0).any()
        or abs(a.sum() - 1) > 1e-8
    ):
        raise ValueError(
            "The shares must be positive or zero and total 100%."
        )
    return a @ W


def mix_search(models, components, *, criterion, low, high, minimum=0.0, rf=0.0):
    p = models[0]
    W = np.asarray(components, float)
    n = len(W)
    if not n or not np.isfinite(minimum) or not 0 <= minimum <= 1 / n:
        raise ValueError("Minimum incompatible shares")
    if criterion not in ("Return", "Minimum risk", "Sharpe"):
        raise ValueError("Unknown criterion")
    if any(not p.evaluate(w, low, high)["valid"] for w in W):
        raise ValueError("One component is non-mandatory")

    def objective(a):
        w = a @ W
        fee = p.fees @ abs(w - p.current)
        net = p.mu @ w - fee / p.years
        risk = np.linalg.norm(p.root @ w)
        if criterion == "Minimum risk":
            return risk
        if criterion == "Return":
            return -net
        return -(net - rf) / max(risk, 1e-9)

    def slack(a):
        w = a @ W
        c = p.evaluate(w)
        fixed = [
            c["risk"] - low,
            high - c["risk"],
            c["cash"],
            c["funding"],
            w.sum() - p.invested_min,
            p.invested_max - w.sum(),
        ]
        return np.r_[
            fixed, w - p.lo, p.hi - w, [cap - v @ w for v, cap in p.groups.values()]
        ]

    starts = [np.full(n, 1 / n), *(np.eye(n) * (1 - n * minimum) + minimum)]
    choices = []
    for a in starts:
        solved = minimize(
            objective,
            a,
            method="SLSQP",
            bounds=[(minimum, 1)] * n,
            constraints=[
                dict(type="eq", fun=lambda z: z.sum() - 1),
                dict(type="ineq", fun=slack),
            ],
            options={"ftol": 1e-11, "maxiter": 150},
        )
        for candidate in [a, solved.x]:
            if not np.isfinite(candidate).all() or candidate.min() < minimum - 1e-8:
                continue
            z = np.clip(candidate, 0, 1)
            if abs(z.sum() - 1) > 1e-8:
                continue
            z /= z.sum()
            c = p.evaluate(z @ W, low, high)
            if c["valid"] and (
                criterion != "Sharpe"
                or (
                    c["risk"] > 1e-6
                    and min(m.evaluate(z @ W)["net"] for m in models) > rf
                )
            ):
                choices.append((objective(z), z))
    if not choices:
        return dict(
            status="Inoperative Sharp"
            if criterion == "Sharpe"
            else "inconclusive research"
        )
    value, a = min(choices, key=lambda pair: pair[0])
    return dict(
        status="candidate verified",
        parts=a.tolist(),
        value=float(value if criterion == "Minimum risk" else -value),
    )
