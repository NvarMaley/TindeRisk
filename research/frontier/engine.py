"""One-year, CHF-sleeve optimization in units of pre-trade investable wealth."""

from dataclasses import dataclass

import cvxpy as cp
import numpy as np
from scipy.optimize import minimize

ASSETS = ("SPY", "IEF", "GLD")
CAPS = (0.0, 0.04, 0.08, 0.12, 0.16)
ARMS = (
    "cash",
    "equal weight",
    "60/40",
    "risky minimum variance",
    "concentration-aware GMV",
    "risk parity",
    "classical",
    "robust",
)
TOL = 2e-7


@dataclass(frozen=True)
class Limits:
    usd: float = 0.9
    single: float = 0.6
    fee: float = 0.001
    minimum: float = 0.0


def root(matrix):
    values, vectors = np.linalg.eigh(matrix)
    if values[0] < -1e-10:
        raise ValueError("Indefinite covariance")
    return np.sqrt(np.maximum(values, 0))[:, None] * vectors.T


def block_paths(data, rng, draws):
    n = len(data)
    starts = rng.integers(0, n - 20, (draws, (n + 20) // 21))
    indices = (starts[:, :, None] + np.arange(21)).reshape(draws, -1)[:, :n]
    return data[indices]


def moments(data, rng, draws):
    valid = np.isfinite(data).all(axis=1)
    obs = data[valid]
    if len(obs) < 2:
        raise ValueError("Insufficient joint sample")
    paths = block_paths(data, rng, draws)
    paths[~np.isfinite(paths).all(axis=2)] = np.nan
    means = np.nanmean(paths, axis=1) * 252
    return obs.mean(axis=0) * 252, np.cov(obs.T) * 252, np.cov(means.T)


def risky_mix(cov, eligible, parity, max_share=1.0):
    mask = np.asarray(eligible, bool)
    shape = np.zeros(len(mask))
    if not mask.any():
        return shape
    sub = cov[np.ix_(mask, mask)]
    n = len(sub)
    sub = sub / np.trace(sub)
    start = np.ones(n) / n
    if parity:
        # Equal risk budgets follow from x_i (Sigma x)_i = 1/n; normalize afterwards.
        x = start.copy()
        for _ in range(500):
            for i in range(n):
                other = sub[i] @ x - sub[i, i] * x[i]
                x[i] = 2 / n / (np.hypot(other, 2 * np.sqrt(sub[i, i] / n)) + other)
            if np.max(np.abs(x * (sub @ x) - 1 / n)) < 1e-11:
                shape[mask] = x / x.sum()
                return shape
        raise ValueError("Unconverged risk contributions")
    else:
        fit = minimize(
            lambda x: x @ sub @ x,
            start,
            jac=lambda x: 2 * sub @ x,
            bounds=[(0, max_share)] * n,
            constraints=[{"type": "eq", "fun": lambda x: x.sum() - 1}],
            method="SLSQP",
            options={"ftol": 1e-13},
        )
    if not fit.success:
        raise ValueError(fit.message)
    shape[mask] = fit.x / fit.x.sum()
    return shape


class Frontier:
    def __init__(self, mean, cov, uncertainty, eligible, limits=Limits(), initial=None):
        self.mean = np.asarray(mean)
        self.cov = np.asarray(cov)
        self.uncertainty = np.asarray(uncertainty)
        self.eligible = np.asarray(eligible, bool)
        self.initial = (
            np.zeros_like(self.mean) if initial is None else np.asarray(initial, float)
        )
        self.limits = limits
        if (
            (self.initial < 0).any()
            or self.initial.sum() > 1 + TOL
            or min(limits.usd, limits.single, limits.fee, limits.minimum) < 0
        ):
            raise ValueError("Invalid starting holdings or mandate")
        self.risk_root = root(cov)
        self.error_root = root(uncertainty)
        w = cp.Variable(len(mean))
        self.weight = w
        self.cap = cp.Parameter(nonneg=True)
        self.radius = cp.Parameter(nonneg=True)
        cost = limits.fee * cp.norm1(w - self.initial)
        self.risk_limit = cp.norm(self.risk_root @ w, 2) <= self.cap
        constraints = [
            w >= 0,
            w <= self.eligible * limits.single,
            cp.sum(w) <= limits.usd,
            cp.sum(w) >= limits.minimum,
            cp.sum(w) + cost <= 1,
            self.risk_limit,
        ]
        self.problem = cp.Problem(
            cp.Maximize(mean @ w - cost - self.radius * cp.norm(self.error_root @ w)),
            constraints,
        )
        self.mixes = {
            "cash": np.zeros_like(self.mean),
            "equal weight": self.eligible.astype(float),
            "risky minimum variance": risky_mix(self.cov, self.eligible, False),
            "risk parity": risky_mix(self.cov, self.eligible, True),
        }
        exposure = min(
            limits.usd, limits.single * self.eligible.sum(), 1 / (1 + limits.fee)
        )
        self.mixes["concentration-aware GMV"] = (
            risky_mix(
                self.cov, self.eligible, False, min(1.0, limits.single / exposure)
            )
            if exposure > 0
            else np.zeros_like(self.mean)
        )
        if len(mean) == 3:
            self.mixes["60/40"] = np.array([0.6, 0.4, 0]) * self.eligible

    def record(self, w, cap, radius, status, dual=np.nan):
        w = np.asarray(w, float)
        l = self.limits
        turn = np.abs(w - self.initial).sum()
        fee = l.fee * turn
        cash = 1 - w.sum() - fee
        vol = np.linalg.norm(self.risk_root @ w)
        error = np.linalg.norm(self.error_root @ w)
        net = self.mean @ w - fee
        slack = {
            "risk": cap - vol,
            "single": np.min(l.single - w),
            "USD": l.usd - w.sum(),
            "cash": cash,
            "minimum risky": w.sum() - l.minimum,
        }
        violation = max(
            0.0,
            max(-s for s in slack.values()),
            -w.min(),
            np.max(np.abs(w[~self.eligible]), initial=0.0),
        )
        active = [
            k
            for k, v in slack.items()
            if abs(v) <= TOL and (k != "minimum risky" or l.minimum > 0)
        ]
        result = {
            "status": status if violation <= TOL else "failed residual",
            "residual": violation,
            "binding": "|".join(active),
            "vol": vol,
            "net_mean": net,
            "error": error,
            "objective": net - radius * error,
            "turnover": turn,
            "fee": fee,
            "cash": cash,
            "risk_dual": dual,
        }
        result.update({f"w{i}": v for i, v in enumerate(w)})
        return result

    def solve(self, cap, radius):
        if cap < 0:
            return {"status": "infeasible risk limit"}
        if (
            cap == 0
            and np.linalg.eigvalsh(self.cov).min() > 0
            or not self.eligible.any()
        ):
            if self.limits.minimum > 0:
                return {"status": "infeasible required exposure"}
            return self.record(np.zeros_like(self.mean), cap, radius, "exact cash")
        self.cap.value = cap
        self.radius.value = radius
        try:
            self.problem.solve(
                solver="CLARABEL",
                tol_gap_abs=1e-10,
                tol_gap_rel=1e-10,
                tol_feas=1e-10,
                warm_start=False,
            )
        except cp.error.SolverError:
            return {"status": "solver failure"}
        if self.problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            return {"status": self.problem.status}
        raw = self.record(self.weight.value, cap, radius, self.problem.status)
        if raw["residual"] > TOL:
            return raw
        w = np.maximum(self.weight.value, 0)
        w[~self.eligible] = 0
        return self.record(
            w, cap, radius, self.problem.status, float(self.risk_limit.dual_value)
        )

    def reference(self, arm, cap):
        if cap < 0:
            return {"status": "infeasible risk limit"}
        mix = self.mixes[arm]
        if mix.sum() > 0:
            mix = mix / mix.sum()
            vol = np.linalg.norm(self.risk_root @ mix)
            upper = min(
                1.0,
                self.limits.usd,
                self.limits.single / mix.max(),
                cap / vol if vol else 1.0,
            )
            if upper + self.limits.fee * np.abs(upper * mix - self.initial).sum() > 1:
                from scipy.optimize import brentq

                upper = brentq(
                    lambda a: (
                        a + self.limits.fee * np.abs(a * mix - self.initial).sum() - 1
                    ),
                    0,
                    upper,
                )
            mix = upper * mix
        if mix.sum() < self.limits.minimum - TOL:
            return {"status": "infeasible required exposure"}
        return self.record(mix, cap, 0, "reference")

    def rows(self, caps=CAPS, arms=ARMS):
        for cap in caps:
            for arm in arms:
                row = (
                    self.solve(cap, float(arm == "robust"))
                    if arm in ("robust", "classical")
                    else self.reference(arm, cap)
                )
                yield dict(cap=cap, arm=arm, **row)
