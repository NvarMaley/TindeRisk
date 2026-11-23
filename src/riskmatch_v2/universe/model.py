"""Broad factor risk, same-mandate alternatives and instrument-level coverage."""

from dataclasses import replace

import cvxpy as cp
import numpy as np
from scipy import sparse
from sklearn.covariance import LedoitWolf

from ..feasibility.study import market
from ..options.compare import LABELS


def moments(history, f, minimum=252):
    ok = np.isfinite(f).all(axis=1)
    x = f[ok]
    ys = history[ok]
    mask = np.isfinite(ys)
    n = mask.sum(axis=0)
    if (n < minimum).any():
        raise ValueError("Insufficient risk history")
    # Separate regressions with each title's actual dates. Center X and y per title.
    design = np.column_stack([np.ones(len(x)), x])
    y = np.nan_to_num(ys)
    lhs = np.einsum("ti,tj,tk->kij", design, design, mask.astype(float), optimize=True)
    rhs = (design.T @ y).T
    b = np.linalg.solve(lhs, rhs[:, :, None])[:, :, 0]
    residual = np.where(mask, y - design @ b.T, 0)
    sigma2 = np.sum(residual**2, axis=0) / (n - design.shape[1]) * 252
    fcov = LedoitWolf().fit(x).covariance_ * 252
    root = sparse.vstack(
        [
            sparse.csr_matrix(np.linalg.cholesky(fcov).T @ b[:, 1:].T),
            sparse.diags(np.sqrt(sigma2)),
        ],
        format="csc",
    )
    return y.sum(axis=0) / n * 252, root, b[:, 1:]


def fit(panel, day, config):
    inventory = panel.inventory(day)
    allcols = panel.names.get_indexer(inventory.index)
    # Slice before converting into double precision to bound memory for all historical PERMNOs.
    end = panel.dindex.get_loc(day) + 1
    H = panel.usd[end - 756 : end, allcols].astype(float)
    bond = (allcols >= len(panel.funds)) & (allcols < panel.stock0)
    H[:, bond] = panel.model_bond[end - 756 : end, allcols[bond] - len(panel.funds)]
    H[~np.isfinite(panel.close[end - 757 : end - 1, allcols])] = np.nan
    fxratio = panel.fx[end - 756 : end] / panel.fx[end - 757 : end - 1]
    H = (1 + H) * fxratio[:, None] - 1
    f = H[:, inventory.index.get_indexer(["SPY", "IEF", "GLD"])]
    counts = np.isfinite(H[-504:][np.isfinite(f[-504:]).all(axis=1)]).sum(axis=0)
    inventory["observations"] = counts
    inventory.loc[inventory.reason.eq("candidate") & (counts < 252), "reason"] = (
        "less than 252 common returns in 504 sessions"
    )
    take = inventory.reason.eq("candidate").to_numpy()
    H = H[:, take]
    names = inventory.index[take].tolist()
    m, root, beta = moments(H[-504:], f[-504:])
    m2, r2, _ = moments(H, f)

    # Historical cross-sectional extremes create unstable maxima when thousands of
    # names compete. Keep raw means for audit; constrain estimates at dated percentiles.
    def shrink(mu, strength):
        bounds = np.quantile(mu, [0.01, 0.99])
        return (1 - strength) * np.clip(mu, *bounds) + strength * np.median(mu)

    base = market(names, shrink(m, 0.5), root, config)
    models = [
        base,
        replace(base, mu=shrink(m2, 0.5), root=r2),
        replace(base, mu=shrink(m, 0.75)),
    ]
    shock = beta @ panel.shock[["SPY", "IEF", "GLD"]].to_numpy()
    for i, name in enumerate(names):
        if name in panel.observed_shocks:
            shock[i] = panel.observed_shocks[name]
    shock = np.maximum(shock, -1.0)
    inventory["included"] = take
    inventory.loc[take, "raw_annual_mean"] = m
    inventory.loc[take, "expected"] = base.mu
    inventory.loc[take, "volatility"] = np.sqrt(base.root.power(2).sum(axis=0)).A1
    inventory.loc[take, "stress"] = shock
    inventory.loc[take, "stress_source"] = np.where(
        np.isin(names, list(panel.observed_shocks)), "observed", "factor projection"
    )
    return models, shock, inventory


def options(models, shock, high=0.12, concession=0.025):
    p = models[0]
    w = cp.Variable(len(p.names))
    net = (p.mu - p.fees / p.years) @ w
    limits = [
        w >= 0,
        w <= p.hi,
        cp.sum(w) <= p.invested_max,
        (1 + p.fees) @ w <= 1,
        cp.norm(p.root @ w) <= high,
    ]

    def solve(goal, extra=()):
        problem = cp.Problem(goal, [*limits, *extra])
        problem.solve(solver="CLARABEL")
        if problem.status not in ("optimal", "optimal_inaccurate") or w.value is None:
            raise ValueError(f"Portfolio calculation not available: {problem.status}")
        weight = np.maximum(np.asarray(w.value).ravel(), 0)
        # Remove solver dust below a cent on the 35,000 CHF study pocket.
        weight[weight < 1e-7] = 0
        if not p.evaluate(weight, high=high)["valid"]:
            raise ValueError("Non-mandatory solution")
        return weight

    best = solve(cp.Maximize(net))
    floor = p.evaluate(best)["net"] - concession
    robust = cp.Variable()
    safe = []
    for model in models:
        safe.extend(
            [
                robust <= (model.mu - model.fees / model.years) @ w,
                cp.norm(model.root @ w) <= high,
            ]
        )
    robust_w = solve(cp.Maximize(robust), safe)
    if any(not m.evaluate(robust_w, high=high)["valid"] for m in models):
        raise ValueError("Robust risk outside the ceiling")
    diversify = solve(
        cp.Minimize(cp.sum_squares(w) + cp.square(1 - cp.sum(w))), [net >= floor]
    )
    hedge = solve(cp.Maximize(shock @ w), [net >= floor])
    for other in (diversify, hedge):
        if p.evaluate(other)["net"] + 1e-5 < floor:
            raise ValueError("Performance below floor")
    return dict(zip(LABELS[:4], [best, robust_w, diversify, hedge]))


def risk_metrics(models, shock, w):
    p = models[0]
    c = p.evaluate(w, high=0.12)
    risk = c["risk"]
    euler = (
        w * np.asarray(p.root.T @ (p.root @ w)).ravel() / risk if risk > 0 else w * 0
    )
    assert abs(euler.sum() - risk) < 1e-7
    estimates = [m.evaluate(w)["net"] for m in models]
    return dict(
        net=c["net"],
        vol=risk,
        variance=risk * risk,
        fee=c["fee"],
        cash=c["cash"],
        valid=c["valid"],
        interval=[min(estimates), max(estimates)],
        hhi=float(w @ w + (1 - w.sum()) ** 2),
        loss=float(-w @ shock),
        sharpe=c["net"] / risk if risk else None,
        n=int(np.count_nonzero(w)),
        weights={k: float(a) for k, a in zip(p.names, w) if a},
        euler={k: float(a) for k, a in zip(p.names, euler) if a},
    )


def affordable(p, w, prices, fx, bonds, budget, high=0.12, low=0):
    # USD stock prices are per share, dirty Treasury prices per USD 100 nominal.
    # Research convention: one share or USD 100 par. Verify all limits after rounding.
    step = prices * fx / budget
    units = np.floor(w / step)
    units[w == 0] = 0
    target = units * step
    for _ in range(1000):
        report = p.evaluate(target, low, high)
        if report["valid"]:
            return dict(
                status="checked batches",
                weights=target,
                units=units,
                cash_chf=report["cash"] * budget,
                vol=report["risk"],
                net=report["net"],
            )
        if report["risk"] < low:
            break
        contribution = target * np.asarray(p.root.T @ (p.root @ target)).ravel()
        eligible = (units > 0) & (contribution > 0)
        if not eligible.any():
            break
        j = np.argmax(np.where(eligible, contribution, -np.inf))
        units[j] -= 1
        target[j] = units[j] * step[j]
    return dict(status="no rounded checks")


def blend_search(models, components, *, criterion, low, high, minimum=0.0, rf=0.0):
    """Optimize in sleeve-weight space; verify each answer again on the underlying assets."""
    from scipy.optimize import minimize

    p = models[0]
    W = np.array(components)
    n = len(W)
    if not n or minimum < 0 or minimum * n > 1:
        raise ValueError("Minimum unachievable share")
    if criterion not in ("Return", "Minimum risk", "Sharpe"):
        raise ValueError("Unknown criterion")
    if any(m.current.any() for m in models):
        raise ValueError("The combination assumes an initial cash investment sleeve")
    if any(not p.evaluate(w, low, high)["valid"] for w in W):
        raise ValueError("Non-mandate component")
    projected = p.root @ W.T
    cov = projected.T @ projected
    net = W @ (p.mu - p.fees / p.years)

    def vol(z):
        return float(np.sqrt(max(0, float(z @ cov @ z))))

    def fun(z):
        if criterion == "Minimum risk":
            return vol(z)
        if criterion == "Return":
            return -net @ z
        return -(net @ z - rf) / max(vol(z), 1e-10)

    candidates = []
    starts = [np.full(n, 1 / n), *(np.eye(n) * (1 - minimum * n) + minimum)]
    for a in starts:
        res = minimize(
            fun,
            a,
            bounds=[(minimum, 1)] * n,
            method="SLSQP",
            constraints=[
                dict(type="eq", fun=lambda z: z.sum() - 1),
                dict(
                    type="ineq", fun=lambda z: np.array([vol(z) - low, high - vol(z)])
                ),
            ],
            options={"ftol": 1e-12, "maxiter": 150},
        )
        for z in (a, res.x):
            if (
                not np.isfinite(z).all()
                or abs(z.sum() - 1) > 1e-7
                or z.min() < minimum - 1e-7
            ):
                continue
            z = np.maximum(z, 0)
            z /= z.sum()
            w = z @ W
            if not p.evaluate(w, low, high)["valid"]:
                continue
            if criterion == "Sharpe" and (
                vol(z) <= 1e-6 or min(m.evaluate(w)["net"] for m in models) <= rf
            ):
                continue
            candidates.append((fun(z), z))
    if not candidates:
        return dict(status="no candidate verified")
    value, z = min(candidates, key=lambda x: x[0])
    return dict(
        parts=z.tolist(),
        status="candidate verified",
        value=float(value if criterion == "Minimum risk" else -value),
    )


def broad_frontier(p, low=0.0, high=0.12):
    """SOCP with an independently calculated support-function bound for a funded cash start."""
    from ..feasibility.engine import Frontier

    if low < 0 or high < low:
        raise ValueError("Invalid range")
    if (
        p.current.any()
        or p.lo.any()
        or p.invested_min
        or p.prefund
        or (1 + p.fees.max()) * p.invested_max > 1
        or any(
            not np.all(v == 1) or cap < p.invested_max for v, cap in p.groups.values()
        )
    ):
        return Frontier(p).solve(low=low, high=high)
    n = len(p.names)
    a = p.mu - p.fees / p.years

    def support(v):
        order = np.argsort(-v)
        bounds = np.where(v[order] > 0, p.hi[order], 0.0)
        before = np.cumsum(bounds) - bounds
        w = np.zeros(n)
        w[order] = np.minimum(bounds, np.maximum(0.0, p.invested_max - before))
        return w

    individual = np.sqrt(p.root.power(2).sum(axis=0)).A1
    extreme = support(individual)
    risk_bound = float(individual @ extreme) + 1e-9
    upper = float(a @ support(a)) + 1e-9
    best = None

    def result(state, proof):
        return dict(
            status=state,
            proof=proof,
            candidate=best,
            max_risk_bound=risk_bound,
            upper_net=upper,
            gap=max(0.0, upper - best["net"]) if best else None,
        )

    if low > risk_bound + 1e-6:
        return result("impossible", "triangular bound")
    x = cp.Variable(n)
    risk = cp.norm(p.root @ x) <= high
    prob = cp.Problem(
        cp.Maximize(a @ x), [x >= 0, x <= p.hi, cp.sum(x) <= p.invested_max, risk]
    )
    prob.solve(solver="CLARABEL")
    if x.value is None:
        return result("non_concluant", "absence of candidate")
    w = np.clip(x.value, 0, p.hi)

    def accept(v):
        nonlocal best
        c = p.evaluate(v, low, high)
        if c["valid"] and (best is None or c["net"] > best["net"]):
            best = c

    accept(w)
    y = p.root @ w
    if np.linalg.norm(y) > 1e-12:
        tangent = np.asarray(p.root.T @ y).ravel() / np.linalg.norm(y)
        lam = max(float(risk.dual_value), 0)
        v = a - lam * tangent
        upper = min(upper, float(lam * high + v @ support(v)) + 1e-8)
    if best is None:
        # The positive lower volatility bound is non-convex. Check attainable segments.
        j = int(np.argmax(individual * np.minimum(p.hi, p.invested_max)))
        one = np.zeros(n)
        one[j] = min(p.hi[j], p.invested_max)
        for endpoint in (one, extreme, support(a)):
            if np.linalg.norm(p.root @ endpoint) < low:
                continue
            l, r = 0.0, 1.0
            for _ in range(48):
                mid = (l + r) / 2.0
                if np.linalg.norm(p.root @ (w + mid * (endpoint - w))) < low:
                    l = mid
                else:
                    r = mid
            accept(w + r * (endpoint - w))
    if best is None:
        return result("non_concluant", "no witness verified in the slice")
    gap = upper - best["net"]
    if gap < -1e-6:
        raise ValueError("Upper bound incompatible with the tell-tale")
    return result(
        "optimal" if gap < 1e-4 else "candidate",
        "primal control and support hyperplan bound",
    )
