"""Confirmed, scoped review decisions for the fictional household."""

from datetime import date, timedelta
import hashlib
import json
import numpy as np
from scipy.optimize import minimize
from .catalogue import approved
from .monitor import (
    COST,
    account_quote,
    FEED,
    UPDATES,
    db,
    get,
    history,
    identity,
    price,
    quote_status,
    snapshot,
    write,
)

# Authored fictional annual model, independent of the ETF archives.
MU = np.array([0.06, 0.025, 0.035])
COV = (
    np.diag([0.16, 0.065, 0.12])
    @ np.array([[1, 0.1, 0.15], [0.1, 1, 0.05], [0.15, 0.05, 1]])
    @ np.diag([0.16, 0.065, 0.12])
)

# Synthetic TLT and sector funds share factors with the original three assets.
_LOADINGS = np.zeros((13, 3))
_LOADINGS[:3] = np.eye(3)
_LOADINGS[3, 1] = 1.5
_LOADINGS[4:, 0] = [1.2, 1.05, 1.12, 0.7, 1.1, 0.6, 0.95, 0.9, 0.55]
COV = _LOADINGS @ COV @ _LOADINGS.T + np.diag([0.0] * 3 + [0.025**2] + [0.07**2] * 9)
MU = _LOADINGS @ MU


def revise(token, expected, bill, due, cap, path=None):
    with db(path) as conn:
        s = get(conn, token)
        if expected != s["version"]:
            raise ValueError("Mandate changed; reload")
        if (
            not np.isfinite(bill)
            or bill < 0
            or cap not in (0.04, 0.08)
            or due < UPDATES[s["cursor"]]["day"]
        ):
            raise ValueError("Invalid mandate revision")
        date.fromisoformat(due)
        if (s["bill"], s["due"], s["cap"]) == (bill, due, cap):
            return
        s.update(bill=bill, due=due, cap=cap, version=expected + 1, revision=True)
        write(
            conn,
            token,
            s,
            "mandate",
            dict(
                time=UPDATES[s["cursor"]]["asof"],
                bill=bill,
                due=due,
                cap=cap,
                version=s["version"],
            ),
        )


def assess(s, sale_allowed=True, delayed=True):
    size = len(s["units"])
    cov, mu = COV[:size, :size], MU[:size]
    q = account_quote(UPDATES[s["cursor"]], size)
    snap = snapshot(s)
    p = np.array(price(s["quote"]))
    values = np.array(s["units"]) * p
    prior = np.array(s["weights"])
    wealth = snap["sleeve"]
    w = values / wealth if wealth else np.zeros(size)
    out = dict(
        time=q["asof"],
        cursor=s["cursor"],
        version=s["version"],
        trade_version=s.get("trade_version", 0),
        before_units=s["units"],
        before_cash=s["cash"] + s["reserve"],
        price=p.tolist(),
        quote=q["id"],
        sale_allowed=sale_allowed,
        delayed=delayed,
        bill=s["bill"],
        cap=s["cap"],
        target_weights=s["weights"],
    )
    out["review_id"] = hashlib.sha256(
        json.dumps(out, sort_keys=True).encode()
    ).hexdigest()[:28]
    if quote_status(q) != "fresh" or not approved(
        s["model"],
        date.fromisoformat(q["day"]),
        "CHF",
        "illustrative CHF 50000",
        "synthetic local demonstration",
    ):
        return dict(**out, status="suspended")
    day = date.fromisoformat(q["day"])
    next_session = next((d for d in FEED["sessions"] if d > q["day"]), None)
    settlement = q["day"] if not delayed else next_session
    if (
        delayed
        and settlement
        and date.fromisoformat(settlement) > day + timedelta(days=5)
    ):
        settlement = None
    unsettled = sum(a["amount"] for a in s["settling"] if a["available"] > q["day"])
    available = max(0, s["cash"] - unsettled)
    locked_by_due = sum(a["amount"] for a in s["settling"] if a["available"] > s["due"])
    hold_resources = s["reserve"] + s["cash"] - locked_by_due
    need = max(0, s["bill"] - s["reserve"])
    risk = float(np.sqrt(w @ cov @ w))
    drift = float(np.max(abs(w - prior)))
    gap = max(0, s["bill"] - hold_resources)
    hard = (
        need > 1e-6 or risk > s["cap"] + 1e-6 or max(w) > 0.600001 or sum(w) > 0.900001
    )
    after = values.copy()
    reason = "hold within limits"
    if hard:
        reason = "funding or exposure constraint"
        max_sale = values.sum() if sale_allowed else 0.0
        sale_need = (
            min(gap / (1 - COST), max_sale)
            if settlement and settlement <= s["due"]
            else 0.0
        )
        # Reserve cash first. Solve for minimum absolute sales subject to risk, name and currency limits.
        earmark = min(need, s["cash"] - locked_by_due + sale_need * (1 - COST))

        def slacks(x):
            remaining = values - x
            base = wealth - earmark - COST * x.sum()
            return np.r_[
                x.sum() - sale_need,
                0.6 * base - remaining,
                0.9 * base - remaining.sum(),
                s["cap"] * base - np.sqrt(remaining @ cov @ remaining),
            ]

        if sale_allowed and wealth > 0 and min(slacks(np.zeros(size))) < -1e-6:
            # Use dimensionless decision variables for stable constraints.
            fit = minimize(
                lambda f: f.sum(),
                values / wealth,
                method="SLSQP",
                bounds=[(0, v / wealth) for v in values],
                constraints=[
                    {"type": "ineq", "fun": lambda f: slacks(f * wealth) / wealth}
                ],
                options={"ftol": 1e-11, "maxiter": 150},
            )
            if fit.success and min(slacks(fit.x * wealth)) >= -0.01:
                after = np.maximum(0, values - fit.x * wealth)
            else:
                reason = "no verified feasible correction"
    elif drift > 0.05 or s["revision"]:
        after = wealth * prior
        reason = "discretionary review"
    delta = after - values
    if not sale_allowed and (delta < -0.00001).any():
        after = values.copy()
        delta = after - values
        reason = "sales unavailable"
    fee = float(np.abs(delta).sum() * COST)
    newcash = s["cash"] - delta.sum() - fee
    net_sell = max(0, -delta.sum() - fee)
    lock = net_sell if delayed else 0.0
    transfer = min(need, max(0, newcash - unsettled - lock))
    sleeve = after.sum() + newcash - transfer
    risk_after = np.sqrt(after @ cov @ after) / sleeve if sleeve > 0 else 0.0
    benefit = float(delta @ mu - fee)
    margin = 0.005 * wealth + np.sqrt(delta @ cov @ delta) / np.sqrt(3)
    if not hard and (reason != "discretionary review" or benefit <= margin):
        after = values
        delta = np.zeros(size)
        fee = benefit = net_sell = lock = 0.0
        risk_after = risk
        newcash = s["cash"]
        transfer = 0.0
        reason = (
            "hold: benefit within uncertainty"
            if drift > 0.05 or s["revision"]
            else reason
        )
    if lock and not settlement:
        after = values
        delta = np.zeros(size)
        fee = benefit = net_sell = lock = 0.0
        newcash = s["cash"]
        transfer = min(need, available)
        reason = "settlement unverified"
        risk_after = np.sqrt(after @ cov @ after) / max(1e-12, wealth - transfer)
    trade_resources = (
        s["reserve"]
        + newcash
        - locked_by_due
        - (lock if settlement and settlement > s["due"] else 0.0)
    )
    actionable = (
        np.abs(delta).sum() > 0.01 or transfer > 0.01
    ) and newcash - transfer >= unsettled + lock - 0.01
    return dict(
        **out,
        status="proposal" if actionable else "hold",
        reason=reason,
        drift=drift,
        risk=risk,
        post_risk=risk_after,
        turnover=float(np.abs(delta).sum()),
        fee=fee,
        benefit=benefit,
        margin=margin,
        settlement=settlement,
        locked=lock,
        cash=float(newcash - transfer),
        reserve=s["reserve"] + transfer,
        units=(after / p).tolist(),
        reserve_transfer=transfer,
        hold_shortfall=gap,
        trade_shortfall=max(0, s["bill"] - trade_resources),
        hold_goal_wealth=wealth + float(values @ mu),
        trade_goal_wealth=sleeve + float(after @ mu),
    )


def previous(conn, token, kind, rid):
    rows = conn.execute(
        "SELECT data FROM events WHERE account=? AND kind=? ORDER BY seq DESC",
        (identity(token), kind),
    )
    return next(
        (r for (v,) in rows if (r := json.loads(v)).get("review_id") == rid), None
    )


def prepare(token, sale_allowed=True, delayed=True, path=None):
    with db(path) as conn:
        s = get(conn, token)
        r = assess(s, sale_allowed, delayed)
        if not previous(conn, token, "review", r["review_id"]):
            write(conn, token, s, "review", r)
        return r


def respond(token, rid, action, path=None):
    if action not in ("accept", "decline", "hold"):
        raise ValueError("Unknown response")
    with db(path) as conn:
        s = get(conn, token)
        if previous(conn, token, "decision", rid):
            return "already recorded"
        r = previous(conn, token, "review", rid)
        if not r:
            raise ValueError("Unknown review")
        current = assess(s, r["sale_allowed"], r["delayed"])
        if current["review_id"] != rid or current["status"] == "suspended":
            action = "expired"
        elif action == "accept" and r["status"] != "proposal":
            raise ValueError("No eligible trade")
        event = dict(time=UPDATES[s["cursor"]]["asof"], review_id=rid, action=action)
        if action == "accept":
            before = snapshot(s)["wealth"]
            s.update(
                units=r["units"],
                cash=r["cash"],
                reserve=r["reserve"],
                trade_version=s.get("trade_version", 0) + 1,
                revision=None,
            )
            if r["locked"]:
                s["settling"].append(
                    dict(amount=r["locked"], available=r["settlement"])
                )
            now = snapshot(s)
            if abs(now["wealth"] - before + r["fee"]) > 0.01:
                raise ValueError("Execution failed to reconcile")
            s["index"] *= now["wealth"] / before
            event.update(
                **now,
                units=s["units"],
                fee=r["fee"],
                flow=0.0,
                market_pnl=0.0,
                fx_pnl=0.0,
                status="confirmed simulation",
                index=s["index"],
                drawdown=s["index"] / s["peak"] - 1,
            )
        write(conn, token, s, "decision", event)
        return action


def shadows(events):
    rows = []
    for i, r in enumerate(events):
        if r["kind"] != "review" or r["status"] == "suspended":
            continue
        flow = 0.0
        for e in events[i + 1 :]:
            if e["kind"] != "mark":
                continue
            flow += e.get("flow", 0.0)
            if e["status"] != "fresh":
                continue
            q = next(x for x in UPDATES if x["id"] == e["feed_id"])
            p = price(account_quote(q, len(r["units"])))
            hold = r["before_cash"] + np.dot(r["before_units"], p) + flow
            trade = r["cash"] + r["reserve"] + np.dot(r["units"], p) + flow
            rows.append(
                dict(
                    review_id=r["review_id"],
                    date=e["time"],
                    shadow_hold=hold,
                    shadow_proposal=trade,
                    difference=trade - hold,
                )
            )
    return rows
