"""Dated, lot-aware research matches on the section 6 portfolios and CHF cash."""

import hashlib
import itertools
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..funding import required_return, years
from ..options.compare import combine
from ..options.scoring import scale

ROOT = Path(__file__).resolve().parents[3]
DAYS = ("2026-10-30", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05")
FEE = 0.001
CASH = "CHF cash"
REVIEW_POLICY = {
    "version": "13.1",
    "weight_drift": 0.05,
    "drawdown": 0.10,
    "days_to_goal": 90,
}
SCORE_WEIGHTS = {"Goal": 35, "Stress": 15, "Diversification": 15, "Trading cost": 10}


@lru_cache(maxsize=256)
def _funding_rate(day, due, budget, reserve, flows, goal):
    report = required_return(day, due, budget + reserve, reserve, flows, goal)
    return report["rates"][0] if report["status"] == "unique" else None


def _goal(day, mandate, budget, nav, estimates):
    due = mandate.get("goal_date", day)
    horizon = max(0.0, years(day, due))
    goal = float(mandate.get("goal_chf") or 0.0)
    savings = float(mandate.get("savings_chf") or 0.0)
    reserve = float(mandate.get("reserve_chf") or 0.0)
    terminal_reserve = float(mandate.get("reserve_at_goal_chf") or 0.0)
    if (
        min(goal, reserve, terminal_reserve) < 0
        or not all(map(math.isfinite, (goal, savings, reserve, terminal_reserve)))
        or horizon > 100
    ):
        raise ValueError("Check the goal, cash flows and horizon.")
    schedule = []
    for flow in mandate.get("flows", []):
        when = flow.get("date")
        if not when or not day < when <= due or flow.get("currency") != "CHF":
            continue
        if flow["direction"] == "withdrawal":
            schedule.append((when, -float(flow["high"])))
        elif flow["certainty"] == "confirmed":
            schedule.append((when, float(flow["low"])))
    available = reserve
    investments = []
    for when, amount in sorted(schedule):
        protected = min(available, max(0.0, -amount))
        available -= protected
        investments.append((when, amount + protected))
    residual = savings - sum(a for _, a in investments)
    if residual:
        investments.append((due, residual))
    values = []
    for estimate in estimates:
        growth = max(0.0, 1 + estimate)
        value = nav * growth**horizon + terminal_reserve
        value += sum(a * growth ** years(when, due) for when, a in investments)
        values.append(value)
    # Already assigned reserve payments have been removed from risky cash flows.
    rate = (
        _funding_rate(day, due, budget, terminal_reserve, tuple(investments), goal)
        if horizon and goal
        else float(mandate.get("goal_rate", 0.06))
    )
    return goal, values, rate


class Market:
    """The same derived model serves both fill tapes; only the first close can be observed."""

    def __init__(self, *, public_only=False):
        raw = (ROOT / "reports/13-application/market.json").read_bytes()
        pack = json.loads(raw)
        self.day = pack["research_date"]
        self.days = list(DAYS)
        self.model_id = pack["model_id"]
        self.symbols = pack["symbols"]
        self.index = {name: i for i, name in enumerate(self.symbols)}
        self.classes = np.array(pack["asset_classes"])
        self.names = list(pack["options"])
        self.options = {k: np.array(v) for k, v in pack["options"].items()}
        self.options[CASH] = np.zeros(len(self.symbols))
        self.mu = np.array(pack["mu"])
        self.factors = np.array(pack["factor_loadings"])
        self.specific = np.array(pack["specific_risk"])
        self.stress = np.array(pack["stress_2008"])
        self.shocks = np.array(pack["shocks"])
        self.shock_names = pack["shock_names"]
        self.universe = pack["universe"]
        self.aliases = pack["aliases"]
        self.fx = 0.90
        # Deterministic fictitious lot prices are independent of licensed vendor marks.
        seed = np.array(
            [int(hashlib.sha256(s.encode()).hexdigest()[:8], 16) for s in self.symbols]
        )
        self.usd = 20.0 + (seed % 18000) / 100.0
        self.daily_move = ((seed % 1001) - 500) / 100000.0
        self.source = "Synthetic execution tape"
        path = ROOT / "data/local/13/market-close.json"
        if path.is_file() and not public_only:
            tape = json.loads(path.read_text())
            if (
                tape["day"] != self.day
                or tape["model_sha256"] != hashlib.sha256(raw).hexdigest()
            ):
                raise ValueError(
                    "Private execution tape and research model have different versions."
                )
            self.fx = tape["fx"]
            self.usd = np.array([tape["usd_prices"][s] for s in self.symbols])
            self.source = "Private archived first close"
        self.snapshot_id = f"{self.model_id} · {self.source}"

    def quotes(self, day):
        if day not in self.days:
            raise ValueError("No dated market snapshot for this session.")
        n = self.days.index(day)
        # First subsequent session applies a deterministic cross-sectional shock;
        # all later movements are illustrative, regardless of execution tape.
        cumulative = [0.0, 0.018, -0.021, -0.038, 0.009][n]
        usd = self.usd * (1 + cumulative + n * self.daily_move)
        fx = self.fx * (1 + [0.0, -0.002, 0.003, -0.001, 0.002][n])
        clock = "20:00:00+00:00" if n == 0 else "21:00:00+00:00"
        return {
            s: {
                "price": float(p),
                "fx": float(fx),
                "price_at": day + "T" + clock,
                "fx_at": day + "T" + clock,
            }
            for s, p in zip(self.symbols, usd)
        }

    def _marks(self, account):
        day = account.get("day", self.day)
        if day not in self.days:
            raise ValueError("No simulation marks for the requested session.")
        quotes = self.quotes(day)
        prices = np.array([q["price"] * q["fx"] for q in quotes.values()])
        for k, p in account.get("prices_chf", {}).items():
            if k in self.index:
                if not math.isfinite(p) or p <= 0:
                    raise ValueError("Invalid ledger mark.")
                prices[self.index[k]] = p
        held = np.zeros(len(prices))
        for k, q in account.get("holdings", {}).items():
            if k not in self.index or q < 0 or int(q) != q:
                raise ValueError("Unrecognized holding or invalid whole-lot quantity.")
            held[self.index[k]] = q
        cash = float(account["cash"])
        balance = float(account["value"])
        if (
            not math.isfinite(balance)
            or balance <= 0
            or not math.isfinite(cash)
            or cash < -0.011
        ):
            raise ValueError("A positive funded CHF sleeve is required.")
        if abs(held @ prices + cash - balance) > 0.02:
            raise ValueError("Ledger holdings and closing marks do not reconcile.")
        return day, prices, held, balance, account

    def _variance(self, w):
        return float(np.sum((w @ self.factors) ** 2) + np.sum((w * self.specific) ** 2))

    def _limits(self, mandate):
        low = float(mandate.get("low") or 0)
        high = float(mandate["high"]) if mandate.get("high") is not None else 1000.0
        if not all(math.isfinite(x) for x in [low, high]) or not 0 <= low <= high:
            raise ValueError("Invalid risk band.")
        return low, high

    def _target(self, parts, mandate, marks):
        _day, prices, _held, budget, _account = marks
        if not parts or not all(n in self.options for n in parts):
            raise ValueError("Select an available portfolio.")
        target = combine([self.options[k] for k in parts], list(parts.values()))
        if mandate.get("mode") == "minimum" and target.any():
            raise ValueError(
                "CHF cash is the minimum-risk option in this unlevered sleeve."
            )
        if mandate.get("blocked_reason"):
            raise ValueError(str(mandate["blocked_reason"]))
        low, high = self._limits(mandate)
        vol = math.sqrt(self._variance(target))
        total = target.sum()
        if total > 0:
            # Re-express portfolio weights after paying up to two one-way trading fees.
            # Solver limits and final gate are assessed on post-fee NAV.
            scale_limit = min(
                0.9 / total, 0.6 / target.max(), high / vol if vol else 1.0
            )
            multiplier = min(1.0, scale_limit * 0.998)
            if low > vol * multiplier and vol:
                multiplier = min(scale_limit * 0.998, low / vol * 1.015)
            target = target * multiplier
        units = np.floor(target * budget / prices).astype(int)
        return units

    def _value(self, units, parts, mandate, marks, detail=True):
        day, prices, held, budget, account = marks
        trades = (units - held) * prices
        fee = float(FEE * np.abs(trades).sum())
        nav = budget - fee
        dollars = units * prices
        cash = nav - dollars.sum()
        w = dollars / nav
        cw = cash / nav
        risk = math.sqrt(self._variance(w))
        returns = (w @ self.mu).tolist()
        net = float((nav / budget) * (1 + returns[0]) - 1)
        goal, projections, required = _goal(day, mandate, budget, nav, returns)
        risk_ceiling = mandate.get("high")
        low, high = self._limits(mandate)
        reasons = []
        if mandate.get("goal_date") and mandate["goal_date"] <= day:
            reasons.append("Confirm a new future goal date before trading.")
        if mandate.get("blocked_reason"):
            reasons.append(str(mandate["blocked_reason"]))
        if mandate.get("mode") == "minimum" and units.any():
            reasons.append("Positive risky holdings exceed the minimum-risk choice.")
        if not (
            low - 1e-9 <= risk
            and (risk < high if mandate.get("high_exclusive") else risk <= high + 1e-9)
        ):
            reasons.append(
                "The rounded portfolio falls outside the confirmed volatility band."
            )
        if cash < -0.01 or w.sum() > 0.900001 or w.max() > 0.600001:
            reasons.append("The funded position or investment limit would be exceeded.")
        if account.get("stale_symbols"):
            reasons.append("A held position lacks a fresh price or FX mark.")
        if mandate.get("constraints") and not mandate.get("blocked_reason"):
            reasons.append(
                "Mandatory client instructions require a verified exposure review."
            )
        changed = np.flatnonzero(units != held)
        if "quotes" in account:
            for j in changed:
                q = account["quotes"].get(self.symbols[j], {})
                if (
                    not q
                    or not q.get("tradable", True)
                    or any(str(q.get(k, ""))[:10] != day for k in ("price_at", "fx_at"))
                ):
                    reasons.append(
                        "A changed instrument is untradable or lacks same-session price and FX."
                    )
                    break
        available = float(account.get("settled_cash", account["cash"]))
        if account.get("settlement_day", day) <= day:
            available += float(-np.minimum(trades, 0).sum()) * (1 - FEE)
        if np.maximum(trades, 0).sum() * (1 + FEE) > available + 0.01:
            reasons.append(
                "Purchases exceed cash available on the settlement schedule."
            )
        excluded = set(mandate.get("excluded_ids", []))
        if excluded.difference(self.index):
            reasons.append("A requested exclusion cannot be verified on this snapshot.")
        if any(units[self.index[k]] > 0 for k in excluded.intersection(self.index)):
            reasons.append("A directly held instrument breaches a confirmed exclusion.")
        risk_cash = float(cw)
        hhi = float(w @ w + cw * cw)
        stress_loss = float(-(w @ self.stress))
        scenarios = dict(zip(self.shock_names, (dollars @ self.shocks).tolist()))
        # Compare the confirmed difficulty threshold to the most adverse *tested*
        # CHF loss including entry fees. A pass is conditional on these scenarios.
        stress_chf = fee + max(0.0, stress_loss * nav, -min(scenarios.values()))
        loss_capacity = mandate.get("loss_capacity_chf")
        if (
            loss_capacity is not None
            and stress_chf > float(loss_capacity["low"]) + 0.01
        ):
            reasons.append(
                "A tested CHF loss including fees exceeds the lower declared F04 loss threshold."
            )
        goal_score = (
            None
            if required is None
            else (
                scale(net, [0.0, max(0.0001, 2 * required)])
                if required > 0
                else (100.0 if net >= 0 else 0.0)
            )
        )
        subs = {
            "Goal": goal_score,
            "Stress": scale(stress_loss, [0.30, 0]),
            "Diversification": scale(hhi, [1.0, 0.1]),
            "Trading cost": scale(fee / budget, [0.0025, 0]),
        }
        score = (
            sum(SCORE_WEIGHTS[k] * v for k, v in subs.items())
            / sum(SCORE_WEIGHTS.values())
            if goal_score is not None
            else None
        )
        oil = max(abs(scenarios["Oil up"]), abs(scenarios["Oil down"]))
        result = {
            "valid": not reasons,
            "reason": " ".join(reasons),
            "date": day,
            "ledger_revision": account.get("revision"),
            "parts": dict(parts),
            "net": net,
            "vol": risk,
            "fee_chf": fee,
            "cash_chf": float(cash),
            "hhi": hhi,
            "scenarios": scenarios,
            "oil_abs_chf": oil,
            "score": score if not reasons else None,
            "score_coverage_pct": 75,
            "score_label": "Model-only comparison",
            "official_score": None,
            "subscores": subs,
            "goal_value_chf": projections[0],
            "goal_range_chf": [min(projections), max(projections)],
            "goal_gap_chf": max(0.0, goal - projections[0]),
            "goal_date": mandate.get("goal_date"),
            "goal_required": required,
            "capital_chf": budget,
            "net_asset_value_chf": nav,
            "turnover_chf": float(np.abs(trades).sum()),
            "risk_ceiling": risk_ceiling,
            "loss_2008": stress_loss,
            "tested_loss_chf": stress_chf,
            "source": self.source,
            "snapshot": self.snapshot_id,
            "estimated_return_range": [min(returns), max(returns)],
            "target_weights_basis": "Post-fee sleeve NAV",
        }
        if not detail:
            return result
        euler = (
            w * ((self.factors @ (w @ self.factors)) + self.specific**2 * w) / risk
            if risk > 0
            else np.zeros(len(w))
        )
        positive = np.flatnonzero(units > 0)
        lines = [
            {
                "id": self.symbols[j],
                "symbol": self.symbols[j],
                "asset_class": self.classes[j],
                "units": int(units[j]),
                "weight": float(w[j]),
                "chf": float(dollars[j]),
                "risk_contribution": float(euler[j]),
            }
            for j in sorted(positive, key=lambda j: -w[j])
        ]
        top = np.array(sorted(positive, key=lambda j: -w[j])[:8], dtype=int)
        corr = {}
        if len(top):
            cov = self.factors[top] @ self.factors[top].T + np.diag(
                self.specific[top] ** 2
            )
            scales = np.sqrt(np.diag(cov))
            rho = np.divide(
                cov,
                np.outer(scales, scales),
                out=np.zeros_like(cov),
                where=np.outer(scales, scales) > 0,
            )
            corr = {
                self.symbols[j]: {
                    self.symbols[k]: float(rho[a, b]) for b, k in enumerate(top)
                }
                for a, j in enumerate(top)
            }
        result.update(
            targets={self.symbols[j]: int(units[j]) for j in positive},
            weights={
                **{self.symbols[j]: float(w[j]) for j in positive},
                CASH: risk_cash,
            },
            classes={
                **{
                    k: float(w[self.classes == k].sum())
                    for k in sorted(set(self.classes[positive]))
                },
                CASH: risk_cash,
            },
            euler={
                **{
                    k: float(euler[self.classes == k].sum())
                    for k in sorted(set(self.classes[positive]))
                },
                CASH: 0.0,
            },
            concentration={
                **{
                    k: float((w[self.classes == k] ** 2).sum())
                    for k in sorted(set(self.classes[positive]))
                },
                CASH: cw * cw,
            },
            lines=lines,
            correlations=corr,
        )
        return result

    def plan(self, parts, mandate, account):
        marks = self._marks(account)
        # Always expose the actual rounded proposal and its reasons when limits fail.
        try:
            units = self._target(parts, mandate, marks)
        except ValueError as exc:
            fields = self._value(marks[2], {}, mandate, marks)
            return dict(
                fields, valid=False, reason=str(exc), score=None, parts=dict(parts)
            )
        result = self._value(units, parts, mandate, marks)
        return result

    def held(self, mandate, account):
        marks = self._marks(account)
        return self._value(marks[2], {}, mandate, marks)

    def suggest(self, names, criterion, mandate, account):
        if mandate.get("mode") == "minimum":
            return {CASH: 1.0}
        if criterion not in ("Sharpe", "Return", "Minimum risk"):
            raise ValueError("Choose a published blend criterion.")
        names = list(dict.fromkeys(names))
        if not 1 <= len(names) <= 5:
            raise ValueError("Select one to five portfolios.")
        # Exhaustively score a declared 10-point mix grid AFTER lot rounding and fees.
        # Each selected strategy must hold at least one grid unit.
        marks = self._marks(account)
        best = None
        best_parts = None
        for cuts in itertools.combinations(range(1, 10), len(names) - 1):
            shares = np.diff([0, *cuts, 10]) / 10
            parts = dict(zip(names, shares.tolist()))
            units = self._target(parts, mandate, marks)
            got = self._value(units, parts, mandate, marks, detail=False)
            if not got["valid"]:
                continue
            v = got["vol"]
            util = {
                "Sharpe": got["net"] / v if v else 0.0,
                "Return": got["net"],
                "Minimum risk": -v,
            }[criterion]
            key = (util, -got["fee_chf"])
            if best is None or key > best:
                best = key
                best_parts = parts
        if best_parts is None:
            raise ValueError(
                "No admissible rounded blend was found on the ten-point grid."
            )
        return best_parts

    def review(self, mandate, account):
        held = self.held(mandate, account)
        if not held["targets"]:
            return {
                "held": held,
                "alternative": None,
                "reason": "Choose and confirm a funded match first.",
            }
        options = [CASH] if mandate.get("mode") == "minimum" else self.names
        marks = self._marks(account)
        candidates = []
        for left, right in itertools.combinations_with_replacement(options, 2):
            for share in [1.0] if left == right else [0.25, 0.5, 0.75]:
                parts = (
                    {left: 1.0} if left == right else {left: share, right: 1 - share}
                )
                try:
                    units = self._target(parts, mandate, marks)
                except ValueError:
                    continue
                res = self._value(units, parts, mandate, marks, detail=False)
                if not res["valid"]:
                    continue
                before = held["oil_abs_chf"]
                if res["oil_abs_chf"] >= before - 0.01:
                    continue
                candidates.append((res, parts))
        if not candidates:
            return {
                "held": held,
                "alternative": None,
                "reason": "No admissible tested mix reduces the two-sided oil shock exposure.",
            }
        # Seek at least a 50% oil reduction, then prefer the cheapest transition.
        half = [
            p for p in candidates if p[0]["oil_abs_chf"] <= held["oil_abs_chf"] * 0.5
        ]
        if half:
            pick = min(half, key=lambda p: (p[0]["fee_chf"], p[0]["oil_abs_chf"]))
        else:
            pick = min(candidates, key=lambda p: (p[0]["oil_abs_chf"], p[0]["fee_chf"]))
        alternative = self.plan(pick[1], mandate, account)
        benefit = held["oil_abs_chf"] - alternative["oil_abs_chf"]
        return {
            "held": held,
            "alternative": alternative,
            "oil_improvement_chf": benefit,
            "after_fee_improvement_chf": benefit - alternative["fee_chf"],
            "reason": "Compare the smaller absolute oil shock against the one-way transition fee and the change in other exposures.",
        }

    def triggers(
        self,
        mandate,
        account,
        held,
        *,
        drift=0.0,
        drawdown=0.0,
        reported=False,
        mandate_changed=False,
    ):
        result = []
        if drift >= REVIEW_POLICY["weight_drift"]:
            result.append("Weight drift")
        if abs(drawdown) >= REVIEW_POLICY["drawdown"]:
            result.append("Drawdown threshold")
        if not held["valid"]:
            result.append("Mandate limits")
        if mandate.get("goal_date"):
            days = (
                date.fromisoformat(mandate["goal_date"])
                - date.fromisoformat(account.get("day", self.day))
            ).days
            if days <= REVIEW_POLICY["days_to_goal"]:
                result.append("Goal approaching" if days >= 0 else "Goal date passed")
        today = date.fromisoformat(account.get("day", self.day))
        if any(
            flow.get("direction") == "withdrawal"
            and flow.get("date")
            and 0
            <= (date.fromisoformat(flow["date"]) - today).days
            <= REVIEW_POLICY["days_to_goal"]
            for flow in mandate.get("flows", [])
        ):
            result.append("Scheduled withdrawal approaching")
        if reported:
            result.append("Client-reported risk")
        if mandate_changed:
            result.append("Mandate changed")
        return result


def engine_replay(public_only=False):
    """Recalculate both graphical and intervention controls without a browser or a ledger."""
    m = Market(public_only=public_only)
    day = m.days[0]
    a = {"day": day, "cash": 35000.0, "value": 35000.0, "holdings": {}}
    mandate = {
        "low": 0.0,
        "high": 0.12,
        "goal_chf": 50000.0,
        "goal_date": "2029-10-30",
        "savings_chf": 0.0,
        "reserve_chf": 15000.0,
    }
    parts = {"Return": 0.6, "Diversification": 0.4}
    match = m.plan(parts, mandate, a)

    def close_account(plan, next_day, flow=0.0):
        marks = m.quotes(next_day)
        value = sum(
            n * marks[k]["price"] * marks[k]["fx"] for k, n in plan["targets"].items()
        )
        cash = plan["cash_chf"] + flow
        return {
            "holdings": plan["targets"],
            "cash": cash,
            "value": cash + value,
            "day": next_day,
        }

    next_day = m.days[1]
    account = close_account(match, next_day, 1000.0)
    review = m.review(mandate, account)
    held, alternative = review["held"], review["alternative"]
    if not match["valid"] or not alternative or not alternative["valid"]:
        raise AssertionError("Expected a feasible matched blend and review.")
    compact_keys = [
        "valid",
        "net",
        "vol",
        "fee_chf",
        "cash_chf",
        "goal_value_chf",
        "goal_gap_chf",
        "goal_required",
        "scenarios",
        "oil_abs_chf",
        "score",
        "turnover_chf",
    ]

    def summary(plan):
        return {k: plan[k] for k in compact_keys} | {
            "positions": len(plan["targets"]),
            "source_shares": plan["parts"],
        }

    suggestions = {}
    for criterion in ("Sharpe", "Return", "Minimum risk"):
        fractions = m.suggest(list(parts), criterion, mandate, a)
        suggestions[criterion] = summary(m.plan(fractions, mandate, a))
    controls = {}
    for name, changes in [
        ("Earlier goal", {"goal_date": "2027-01-12"}),
        ("Higher goal", {"goal_chf": 75000}),
        ("Additional savings", {"savings_chf": 5000}),
        ("Lower risk cap", {"high": 0.06}),
    ]:
        controls[name] = summary(m.plan(parts, mandate | changes, account))
    outside = m.plan(parts, mandate | {"low": 0.35, "high": 0.45}, a)
    return {
        "source": m.source,
        "model_id": m.model_id,
        "modelled": m.universe,
        "union_of_source_positions": len(m.symbols),
        "match": summary(match),
        "classes": match["classes"],
        "euler": match["euler"],
        "weight_total": sum(match["weights"].values()),
        "euler_total": sum(match["euler"].values()),
        "hhi_total": sum(match["concentration"].values()),
        "hhi": match["hhi"],
        "confirmed_model_risk_ceiling": mandate["high"],
        "suggested": suggestions,
        "later_session": next_day,
        "contribution_chf": 1000.0,
        "held": summary(held),
        "revision": summary(alternative),
        "oil_shock_improvement_chf": review["oil_improvement_chf"],
        "after_fee_improvement_chf": review["after_fee_improvement_chf"],
        "changed_plans": controls,
        "outside_band": {"valid": outside["valid"], "reason": outside["reason"]},
        "notices": {
            "quiet": m.triggers(mandate, account, held, drift=0.049),
            "threshold": m.triggers(mandate, account, held, drift=0.05, drawdown=-0.1),
            "near_goal": m.triggers(
                mandate | {"goal_date": "2026-12-01"}, account, held
            ),
            "near_expense": m.triggers(
                mandate
                | {"flows": [{"direction": "withdrawal", "date": "2026-12-01"}]},
                account,
                held,
            ),
            "reported": m.triggers(
                mandate, account, held, reported=True, mandate_changed=True
            ),
        },
    }
