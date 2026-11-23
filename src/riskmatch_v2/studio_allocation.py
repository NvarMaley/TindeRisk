"""Personalised, whole-unit portfolios from the complete dated US research model."""

import hashlib
import json
from datetime import date
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import cvxpy as cp
import numpy as np

from .matching.engine import DAYS, FEE, _goal
from .options.scoring import scale

ROOT = Path(__file__).resolve().parents[2]
CASH = "CHF cash"
TITLES = {
    "return": (
        "Return seeker",
        "Seek higher model return within the estimated risk ceiling",
    ),
    "robust": (
        "All-weather",
        "Protect the weakest of three historical return estimates",
    ),
    "diversified": (
        "Spread the risk",
        "Balance concentration against estimated return",
    ),
    "defensive": (
        "Shock shelter",
        "Balance the tested 2008 and macro shocks against growth",
    ),
    "carbon": (
        "Carbon lens",
        "Prefer measured corporate holdings with lower reported intensity",
    ),
    "reference": (
        "The classic",
        "A 60/40 equity–Treasury ETF reference scaled within the sleeve",
    ),
    "cash": ("Cash reserve", "Retain the investable sleeve in CHF"),
    "blend": (
        "Your mix",
        "Combined holdings, rounded and checked as a single portfolio",
    ),
}


@lru_cache(maxsize=1)
def _data():
    pack = json.loads((ROOT / "reports/studio/model.json").read_text())
    pack["index"] = {s: i for i, s in enumerate(pack["symbols"])}
    for k in (
        "classes",
        "mu",
        "stress_2008",
        "factor_roots",
        "specific_risk",
        "carbon",
        "shocks",
    ):
        pack[k] = np.asarray(pack[k])
    if not np.isfinite(pack["shocks"]).all():
        raise ValueError("Incomplete scenario coefficients in the release.")
    seed = np.array(
        [int(hashlib.sha256(s.encode()).hexdigest()[:8], 16) for s in pack["symbols"]]
    )
    pack["usd"] = 20 + (seed % 18000) / 100.0
    bonds = pack["classes"] == "Direct Treasury"
    pack["usd"][bonds] = 85 + (seed[bonds] % 3000) / 100.0  # A unit is USD 100 face.
    pack["move"] = ((seed % 1001) - 500) / 100000.0
    return pack


def _tape(day):
    if day not in DAYS:
        raise ValueError("The simulated session is outside the dated tape.")
    k = DAYS.index(day)
    d = _data()
    usd = d["usd"] * (1 + (0, 0.018, -0.021, -0.038, 0.009)[k] + k * d["move"])
    fx = 0.90 * (1 + (0, -0.002, 0.003, -0.001, 0.002)[k])
    stamp = day + ("T20:00:00+00:00" if k == 0 else "T21:00:00+00:00")
    return usd, fx, stamp


def quotes(day, symbols):
    """Synthetic, dated lot prices and USD/CHF suitable for the simulation ledger."""
    usd, fx, stamp = _tape(day)
    idx = _data()["index"]
    return {
        s: {
            "price": float(usd[idx[s]]),
            "fx": fx,
            "price_at": stamp,
            "fx_at": stamp,
            "tradable": True,
        }
        for s in symbols
    }


def _number(value, name, low=0.0):
    x = float(value)
    if not np.isfinite(x) or x < low:
        raise ValueError(f"Invalid {name}.")
    return x


class _Session:
    def __init__(self, m):
        self.m = m
        self.d = _data()
        a = m.get("account") or {}
        self.day = a.get("day") or m.get("day") or DAYS[0]
        self.budget = _number(a.get("value", m["capital_chf"]), "investable balance")
        self.reserve = _number(m.get("reserve_chf", 0), "protected reserve")
        self.low = _number(m.get("low", 0), "risk floor")
        self.high = (
            _number(m["high"], "risk ceiling") if m.get("high") is not None else None
        )
        if self.high is not None and self.low > self.high:
            raise ValueError("The risk band is reversed.")
        self.years = max(
            (date.fromisoformat(m["goal_date"]) - date.fromisoformat(self.day)).days
            / 365.25,
            1 / 365.25,
        )
        self.target = _number(m.get("target_return") or 0, "target return", -1.0)
        self.capacity = m.get("loss_capacity_chf")
        if isinstance(self.capacity, dict):
            self.capacity = self.capacity.get("low")
        if self.capacity is not None:
            self.capacity = _number(self.capacity, "loss budget")
        goal_policy = {"reserve_at_goal_chf": self.reserve, **m}
        self.required = (
            _goal(self.day, goal_policy, self.budget, self.budget, [0.0])[2]
            if self.budget > 0 and m["goal_date"] > self.day
            else None
        )
        self.aspiration = max(self.target, self.required or 0.0)
        self.reason = m.get("blocked_reason") or ""
        self.account = a
        self.idx = self.d["index"]
        self.n = len(self.idx)
        self.held = np.zeros(self.n, dtype=np.int64)
        usd, fx, _ = _tape(self.day)
        self.prices = usd * fx
        for s, units in a.get("holdings", {}).items():
            if s not in self.idx or int(units) != units or units < 0:
                raise ValueError("Unknown holding or invalid simulated unit count.")
            self.held[self.idx[s]] = int(units)
        for s, value in a.get("prices_chf", {}).items():
            if s in self.idx and self.held[self.idx[s]]:
                self.prices[self.idx[s]] = _number(value, "recorded price", 0.000001)
        self.cash = _number(a.get("cash", self.budget), "cash")
        self.settled = _number(a.get("settled_cash", self.cash), "settled cash")
        if abs(self.cash + self.held @ self.prices - self.budget) > 0.02:
            raise ValueError("The holdings and cash do not reconcile to the account.")
        self.allowed = np.ones(self.n, dtype=bool)
        if m.get("allowed_classes") is not None:
            self.allowed &= np.isin(self.d["classes"], m["allowed_classes"])
        for ticker in m.get("exclusions", []):
            ticker = str(ticker).strip().upper()
            if ticker not in self.idx:
                self.reason = (
                    "An excluded ticker cannot be identified in this snapshot."
                )
            else:
                self.allowed[self.idx[ticker]] = False
        if m.get("exclude_chevron"):
            carbon = self.d["carbon"]
            self.allowed &= (carbon[:, 0] <= 1e-9) & (carbon[:, 1] <= 1e-9)
        self.allowed &= self.prices <= self.budget * 0.60
        if self.budget <= 0.005:
            self.reason = "There is no investable cash after the protected reserve."
        if m["goal_date"] <= self.day:
            self.reason = "The goal date has passed. Update the household facts."
        if a.get("stale_symbols"):
            self.reason = "A held security has a stale price or FX mark."

    def sigma(self, weights, variant=0):
        f = self.d["factor_roots"][variant]
        s = self.d["specific_risk"][variant]
        return float(np.sqrt(np.sum((weights @ f) ** 2) + np.sum((weights * s) ** 2)))

    def solve(self, key):
        allow = self.allowed.copy()
        if key == "carbon":
            allow &= self.d["carbon"][:, 2] >= 0.99999
        ix = np.flatnonzero(allow)
        full = np.zeros(self.n)
        if not len(ix) or self.reason or self.high == 0:
            return full
        high = self.high
        if key == "reference":
            if not all(allow[self.idx[k]] for k in ("SPY", "IEF")):
                return None
            full[[self.idx["SPY"], self.idx["IEF"]]] = [0.60, 0.40]
            shrink = (
                min(0.899, 0.992 * high / self.sigma(full))
                if high is not None
                else 0.899
            )
            return full * shrink
        w = cp.Variable(len(ix), nonneg=True)
        mu = self.d["mu"][ix]
        previous = self.held * self.prices / self.budget
        outside = float(previous[~allow].sum())
        fee = FEE * (cp.norm1(w - previous[ix]) + outside)
        # Bounds are evaluated again on post-fee NAV after conversion to whole units.
        limits = [
            w <= 0.599,
            cp.sum(w) <= 0.898,
            cp.sum(w) + fee <= 1 - (self.cash - self.settled) / self.budget,
        ]
        if high is not None:
            for variant in (0, 1) if key == "robust" else (0,):
                root = self.d["factor_roots"][variant, ix]
                specific = self.d["specific_risk"][variant, ix]
                limits.append(
                    cp.norm(cp.hstack([root.T @ w, cp.multiply(specific, w)]))
                    <= high * 0.992
                )
        stress = self.d["stress_2008"][ix]
        shocks = self.d["shocks"][ix]
        if self.capacity is not None:
            cap = self.capacity / self.budget
            limits.extend([-stress @ w + fee <= cap, -shocks.T @ w + fee <= cap])
        net = mu[:, 0] @ w - fee / self.years
        objective = net
        if key == "robust":
            worst = cp.Variable()
            limits.append(worst <= mu.T @ w - fee / self.years)
            objective = worst
        elif key == "diversified":
            objective = (
                0.10 * net
                - 0.9 * cp.sum_squares(w)
                + 0.10 * cp.sum(w)
                - 2.0 * cp.pos(self.aspiration - net)
            )
        elif key == "defensive":
            worst = cp.Variable(nonneg=True)
            limits.extend([worst >= -stress @ w, worst >= -shocks.T @ w])
            objective = (
                0.12 * net
                - worst
                - 0.15 * cp.sum_squares(w)
                - 2.0 * cp.pos(self.aspiration - net)
            )
        elif key == "carbon":
            intensity = self.d["carbon"][ix, 3] / self.d["carbon"][ix, 2]
            objective = (
                net - 0.12 * np.log1p(intensity) @ w - cp.pos(self.aspiration - net)
            )
            # Capital invested in this option has measured corporate coverage.
            objective += 0.50 * cp.sum(w)

        def run():
            problem = cp.Problem(cp.Maximize(objective), limits)
            try:
                problem.solve(solver="CLARABEL")
            except cp.error.SolverError:
                return None
            if w.value is None or problem.status not in (
                "optimal",
                "optimal_inaccurate",
            ):
                return None
            candidate = np.zeros(self.n)
            candidate[ix] = np.where(w.value > 1e-7, w.value, 0)
            return candidate

        result = run()
        if result is None:
            return None
        if self.low and self.sigma(result) < self.low * 1.012:
            # A supporting plane gives a sufficient lower-risk condition on one
            # convex branch. Failure here cannot certify global infeasibility.
            ix0 = ix[
                np.argmax(
                    mu[:, 0]
                    + np.sqrt(
                        np.sum(self.d["factor_roots"][0, ix] ** 2, axis=1)
                        + self.d["specific_risk"][0, ix] ** 2
                    )
                )
            ]
            root = self.d["factor_roots"][0]
            specific = self.d["specific_risk"][0]
            g = root @ root[ix0]
            g[ix0] += specific[ix0] ** 2
            g /= np.sqrt(g[ix0])
            limits.append(g[ix] @ w >= self.low * 1.015)
            branch = run()
            if branch is not None:
                result = branch
        return result

    def allocations(self):
        if self.m.get("mode") == "minimum" or self.high == 0 or not self.allowed.any():
            return {"cash": np.zeros(self.n)}
        keys = ["return", "robust", "diversified", "defensive", "reference"]
        if self.m.get("prefer_lower_emissions"):
            keys.insert(3, "carbon")
        return {key: self.solve(key) for key in keys}

    def rounded(self, weights):
        ideal = weights * self.budget / self.prices
        units = np.floor(ideal).astype(np.int64)
        spare = (weights * self.budget - units * self.prices).sum()
        rem = ideal - units
        for i in np.argsort(-rem):
            if rem[i] <= 0 or spare <= 0.005:
                break
            if (
                self.prices[i] <= spare
                and (units[i] + 1) * self.prices[i] <= self.budget * 0.5999
            ):
                units[i] += 1
                spare -= self.prices[i]
        # Round-off can raise risk relative to the continuous solution,
        # especially for small accounts. Remove the largest Euler exposure.
        for _ in range(15):
            nav, _, _, _, w = self.amounts(units)
            risk = self.sigma(w)
            if not self.high or risk <= self.high:
                break
            fw = w @ self.d["factor_roots"][0]
            marginal = (
                self.d["factor_roots"][0] @ fw + self.d["specific_risk"][0] ** 2 * w
            )
            i = int(np.argmax(np.where(units > 0, marginal * self.prices, -np.inf)))
            if marginal[i] <= 0:
                break
            take = int(
                np.ceil(
                    (risk - self.high * 0.998)
                    * nav
                    * risk
                    / (marginal[i] * self.prices[i])
                )
            )
            units[i] -= min(units[i], max(1, take))
        return units

    def amounts(self, units):
        dol = units * self.prices
        fee = float(np.abs((units - self.held) * self.prices).sum() * FEE)
        nav = self.budget - fee
        cash = float(nav - dol.sum())
        w = dol / nav if nav > 0 else np.zeros(self.n)
        return nav, cash, fee, dol, w

    def evaluate(self, units, key, parts, detail=True):
        nav, cash, fee, dol, w = self.amounts(units)
        risk = self.sigma(w)
        projections = (w @ self.d["mu"]).tolist()
        # Comparable annual estimate includes a one-time transition cost amortised over the horizon.
        rate = float(projections[0] - fee / max(0.01, self.budget) / self.years)
        moves = dol @ self.d["shocks"]
        stress = float(dol @ self.d["stress_2008"])
        loss = fee + max(0.0, -min(moves), -stress)
        reason = self.reason
        if not reason and (
            (w.max() if len(w) else 0) > 0.600001
            or w.sum() > 0.900001
            or cash < -0.005
            or nav <= 0
            or cash + 0.005 < self.cash - self.settled
        ):
            reason = "The rounded allocation exceeds a funding, settlement or concentration limit."
        if not reason and (
            np.any(units[~self.allowed])
            or (
                key == "carbon"
                and np.any((units > 0) & (self.d["carbon"][:, 2] < 0.99999))
            )
        ):
            reason = "The resulting holdings do not satisfy the selected restrictions."
        if not reason and (
            risk + 1e-8 < self.low
            or (
                self.high is not None
                and (
                    risk > self.high + 1e-8
                    or (self.m.get("high_exclusive") and risk >= self.high)
                )
            )
        ):
            reason = "Whole units cannot place this candidate within the estimated risk band."
        if (
            key == "robust"
            and not reason
            and self.high is not None
            and self.sigma(w, 1) > self.high + 1e-8
        ):
            reason = "Whole units exceed the ceiling under the alternate covariance estimate."
        if not reason and self.capacity is not None and loss > self.capacity + 0.01:
            reason = "The tested loss exceeds the financial loss budget."
        if not detail:
            return not reason, rate / risk if risk > 1e-8 else (
                0.0 if rate == 0 else -np.inf
            )
        title, subtitle = TITLES[key]
        inputs = dict(self.m)
        inputs.setdefault("reserve_at_goal_chf", self.reserve)
        if nav > 0 and self.m["goal_date"] > self.day:
            goal, values, required = _goal(
                self.day, inputs, self.budget, nav, projections
            )
        else:
            goal, values, required = float(self.m["goal_chf"]), [self.reserve], None
        gap = max(0.0, goal - values[0])
        covered = float(w @ self.d["carbon"][:, 2])
        intensity = (
            float(w @ self.d["carbon"][:, 3] / covered) if covered > 1e-8 else None
        )
        hhi = float(w @ w + (cash / max(0.01, nav)) ** 2)
        target = max(self.target, required if required is not None else 0.0)
        components = {
            "Goal": scale(rate, [0.0, max(0.01, 2 * target)]),
            "Stress": scale(loss / max(0.01, self.budget), [0.30, 0.0]),
            "Diversification": scale(hhi, [1.0, 0.10]),
            "Trading cost": scale(fee / max(0.01, self.budget), [0.0025, 0.0]),
        }
        score = (
            35 * components["Goal"]
            + 15 * components["Stress"]
            + 15 * components["Diversification"]
            + 10 * components["Trading cost"]
        ) / 75
        selected = np.flatnonzero(units)
        ordered = sorted(selected, key=lambda i: -w[i])
        top = [
            {
                "symbol": self.d["symbols"][i],
                "name": self.d["issuers"][i],
                "weight": float(w[i]),
            }
            for i in ordered[:8]
        ]
        classes = {
            str(c): float(w[self.d["classes"] == c].sum())
            for c in np.unique(self.d["classes"][selected])
        }
        classes[CASH] = cash / max(0.01, nav)
        corr = {}
        if risk > 1e-8:
            root = self.d["factor_roots"][0]
            spec = self.d["specific_risk"][0]
            for proxy in ("SPY", "IEF", "GLD"):
                i = self.idx[proxy]
                cov = (w @ root) @ root[i] + w[i] * spec[i] ** 2
                corr[proxy] = float(
                    np.clip(
                        cov / (risk * np.sqrt(root[i] @ root[i] + spec[i] ** 2)), -1, 1
                    )
                )
        scenarios = {
            k: float(v) for k, v in zip(self.d["scenarios"], moves, strict=True)
        }
        strengths = [
            f"{len(selected)} invested holdings. CHF {cash:,.0f} remains in the sleeve."
        ]
        if corr:
            k = min(corr, key=lambda name: abs(corr[name]))
            strengths.append(
                f"The weakest model correlation is with {k} ({corr[k]:+.2f})."
            )
        risks = [
            f"The 2008 scenario changes this allocation by CHF {stress:+,.0f}.",
            "The return estimate uses historical averages. Selecting from thousands of assets can inflate it.",
        ]
        if rate < self.target:
            risks.append("The estimated return falls below your desired annual return.")
        if gap:
            risks.append(
                f"Central scenario falls CHF {gap:,.0f} short of the dated goal."
            )
        env_label = (
            "Partial point-source coverage"
            if covered > 1e-8
            else "No measured emissions coverage"
        )
        if key == "carbon" and covered > 1e-8:
            env_label = "Lower-intensity objective on measured issuers"
        return {
            "id": key,
            "name": title,
            "subtitle": subtitle,
            "valid": not reason,
            "reason": reason,
            "parts": parts,
            "date": self.day,
            "model_date": self.d["date"],
            "net": rate,
            "vol": risk,
            "estimated_return_range": [
                min(projections) - fee / max(0.01, self.budget) / self.years,
                max(projections) - fee / max(0.01, self.budget) / self.years,
            ],
            "goal_required": required,
            "goal_gap_chf": float(gap),
            "goal_value_chf": float(values[0]),
            "goal_chf": goal,
            "target_return": self.m.get("target_return"),
            "capital_chf": self.budget,
            "reserve_chf": self.reserve,
            "reserve_rate": self.m.get("reserve_rate", 0.0),
            "reserve_at_goal_chf": self.m.get("reserve_at_goal_chf", self.reserve),
            "loss_2008_chf": stress,
            "tested_loss_chf": float(loss),
            "fee_chf": fee,
            "cash_chf": cash,
            "positions": len(selected),
            "score": None if reason else round(score, 1),
            "subscores": components,
            "score_label": "Model comparison · 75 observed points rescaled to 100",
            "weights": classes,
            "top": top,
            "targets": {self.d["symbols"][i]: int(units[i]) for i in selected},
            "strengths": strengths,
            "risks": risks,
            "correlations": corr,
            "scenarios": scenarios,
            "signals": _notice(corr, scenarios),
            "esg": {
                "coverage": covered,
                "intensity": intensity,
                "unit": "US point-source tCO₂e per USD million of 2023 revenue",
                "label": env_label,
                "as_of": self.d["environment_date"],
            },
            "universe": self.n,
            "eligible": int(self.allowed.sum()),
            "source": "Synthetic execution tape",
        }


@lru_cache(maxsize=1)
def _signals():
    registry = json.loads((ROOT / "reports/12-forecasts/registry.json").read_text())
    labels = {
        "increment_momentum": "Quantitative",
        "increment_tone": "Sentiment",
        "increment_curve": "Macro",
        "increment_vix": "Market",
        "increment_gpr": "Geopolitical",
    }
    rows = []
    for r in registry:
        if r["name"] not in labels or r["target"] != "variance" or r["horizon"] != 21:
            continue
        indicator = r["name"].split("_", 1)[1].upper()
        reading = (
            f"The SPY 21-session variance estimate was {r['direction']} its reference"
            if r["estimate"] is not None
            else "The SPY 21-session variance estimate was unavailable"
        )
        rows.append(
            {
                "family": labels[r["name"]],
                "reading": f"{indicator} · {reading} on {r['measured_at']}. The {r['issued']} review recorded {r['status']}.",
                "measured_at": r["measured_at"],
                "issued": r["issued"],
                "weight": float(r["weight"]),
                "scope": r["scope"],
            }
        )
    return rows


def _notice(correlations, scenarios):
    out = []
    for signal in _signals():
        context = ""
        if signal["family"] == "Macro":
            context = (
                f" This portfolio's rate shock is CHF {scenarios['Rates up']:+,.0f}."
            )
        elif signal["family"] == "Market" and "SPY" in correlations:
            context = f" Portfolio–SPY model correlation {correlations['SPY']:+.2f}."
        else:
            context = " Direct transfer to this allocation is unvalidated."
        out.append({**signal, "reading": signal["reading"] + context})
    return out


@lru_cache(maxsize=16)
def _prepared(serialized):
    session = _Session(json.loads(serialized))
    return session, session.allocations()


def _prepare(mandate):
    # The cache holds only inputs that affect allocations. The profile narrative,
    # submitted answers and dossier identifiers have no role in sizing a trade.
    fields = (
        "capital_chf",
        "reserve_chf",
        "reserve_at_goal_chf",
        "reserve_rate",
        "goal_chf",
        "goal_date",
        "savings_chf",
        "flows",
        "goal_rate",
        "low",
        "high",
        "high_exclusive",
        "mode",
        "target_return",
        "exclusions",
        "exclude_chevron",
        "prefer_lower_emissions",
        "allowed_classes",
        "blocked_reason",
        "loss_capacity_chf",
        "day",
    )
    inputs = {k: mandate[k] for k in fields if k in mandate}
    if account := mandate.get("account"):
        fields = (
            "day",
            "value",
            "cash",
            "settled_cash",
            "holdings",
            "prices_chf",
            "stale_symbols",
        )
        inputs["account"] = {k: account[k] for k in fields if k in account}
    return _prepared(
        json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
    )


def candidates(mandate):
    """Produce checked alternatives, keeping infeasible candidates explicitly marked."""
    s, allocations = _prepare(mandate)
    cards = []
    for key, w in allocations.items():
        card = s.evaluate(
            s.rounded(w) if w is not None else np.zeros(s.n, dtype=int), key, {key: 1.0}
        )
        if w is None:
            card.update(
                valid=False,
                score=None,
                reason="No continuous solution under this strategy and mandate.",
            )
        cards.append(card)
    return cards


def blend(mandate, selected_ids, weights=None):
    """Combine strategies before integer rounding; a suggested blend maximises net/vol on a 10% grid."""
    s, allocations = _prepare(mandate)
    keys = list(selected_ids)
    if not keys or len(set(keys)) != len(keys):
        raise ValueError("Select at least one distinct portfolio.")
    for key in keys:
        if key not in allocations or allocations[key] is None:
            raise ValueError("A selected portfolio is unavailable.")
        ok, _ = s.evaluate(s.rounded(allocations[key]), key, {key: 1.0}, detail=False)
        if not ok:
            raise ValueError("A selected portfolio falls outside the mandate.")
    if weights is not None:
        if isinstance(weights, dict) and set(weights) != set(keys):
            raise ValueError("Weights must match the selected portfolios.")
        selected = np.asarray(
            [weights[k] for k in keys] if isinstance(weights, dict) else weights,
            dtype=float,
        )
        if (
            selected.shape != (len(keys),)
            or not np.isfinite(selected).all()
            or min(selected) < 0
            or abs(selected.sum() - 1) > 1e-8
        ):
            raise ValueError("Portfolio shares must be nonnegative and sum to 100%.")
    if len(keys) == 1:
        return s.evaluate(s.rounded(allocations[keys[0]]), keys[0], {keys[0]: 1.0})
    pool = np.array([allocations[k] for k in keys])
    if weights is None:
        best = -np.inf
        selected = None
        for dividers in combinations(range(1, 10), len(keys) - 1):
            parts = np.diff([0, *dividers, 10]) / 10
            units = s.rounded(parts @ pool)
            ok, ratio = s.evaluate(units, "blend", {}, detail=False)
            if ok and ratio > best:
                selected, best = parts, ratio
        if selected is None:
            raise ValueError("No valid mix on the ten-percentage-point grid.")
    return s.evaluate(
        s.rounded(selected @ pool),
        "blend",
        dict(zip(keys, selected.tolist(), strict=True)),
    )
