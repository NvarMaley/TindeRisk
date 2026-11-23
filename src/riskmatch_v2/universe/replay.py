"""Self-financing, delayed cash settlement replay of dated targets in CHF."""

import numpy as np
import pandas as pd


def run(
    panel, plans, policy, *, fee=0.001, lag=1, miss=False, whole=False, capture=False
):
    ids = sorted({s for w in plans.values() for s, x in w.items() if x > 0})
    if not ids:
        ids = ["SPY"]
    cols = panel.names.get_indexer(ids)
    if (cols < 0).any():
        raise ValueError("Identity absent from the market")
    start = panel.dindex.get_loc(min(plans))
    stop = panel.dindex.get_loc(policy["market"]) + 1
    dates = panel.days[start:stop]
    price = panel.close[start:stop, cols].astype(float)
    usd = panel.usd[start:stop, cols].astype(float)
    fx = panel.fx[start:stop]
    mark_fx = pd.Series(panel.fx[:stop]).ffill().to_numpy()[start:]
    last = pd.DataFrame(panel.close[: start + 1, cols]).ffill().iloc[-1].to_numpy(float)
    bond = (cols >= len(panel.funds)) & (cols < panel.stock0)
    cash = float(policy["pocket"])
    pending = 0.0
    previous = cash
    pos = np.zeros(len(ids))
    unit = np.zeros(len(ids))
    stale = np.zeros(len(ids), int)
    first = True
    queue = None
    problems = set()
    navs = []
    audit = []
    fees = turn = paid = unpaid = 0.0
    index = {k: i for i, k in enumerate(ids)}
    redemptions = 0
    max_residual = 0.0
    gap_weight = 0.0
    ignored_orders = 0
    first_problem = None
    targets = {day: np.array([w.get(s, 0.0) for s in ids]) for day, w in plans.items()}
    for i, day in enumerate(dates):
        cash += pending
        pending = 0.0
        before = pos.copy()
        had = before > 1e-5
        valid_price = np.isfinite(price[i]) & (price[i] > 0)
        tradable = valid_price & np.isfinite(fx[i])
        returns = usd[i].copy()
        missing = ~np.isfinite(returns)
        # Missing quotations are carried solely for indicative valuation; an unknown total
        # return on a quoted equity is explicitly marked, even if the close is unchanged.
        proxy = missing & valid_price & (last > 0)
        returns[proxy] = price[i, proxy] / last[proxy] - 1
        returns[~np.isfinite(returns)] = 0.0
        vfx = mark_fx[i] / mark_fx[i - 1] if i else 1.0
        pos *= np.maximum(1 + returns, 0) * vfx
        coupon = (
            unit[bond]
            * panel.coupons[start + i, cols[bond] - len(panel.funds)]
            * mark_fx[i]
        )
        pos[bond] -= coupon
        cash += coupon.sum()
        pos = np.maximum(0.0, pos)
        stale = np.where(had & ~valid_price, stale + 1, 0)
        suspect = had & ((stale > 3) | (proxy & ~bond))
        if suspect.any():
            problems.update(np.array(ids)[suspect])
            first_problem = first_problem or str(day)
            gap_weight = max(gap_weight, float(before[suspect].sum() / previous))
        last = np.where(valid_price, price[i], last)
        # Total-return reinvestment can change equity units through distributions and splits.
        np.divide(pos, last * mark_fx[i], out=unit, where=(last > 0))
        for key, (kind, amount) in panel.exits.get(day, {}).items():
            j = index.get(key)
            if j is None or pos[j] <= 1e-8:
                continue
            pending += (
                pos[j] * amount if kind == "total" else unit[j] * amount * mark_fx[i]
            )
            redemptions += 1
            pos[j] = 0.0
            unit[j] = 0.0
        opening = float(cash + pending + pos.sum())
        flow = -min(1000.0, cash) if day == "2022-03-31" else 0.0
        if day == "2022-03-31":
            paid -= flow
            unpaid += 1000 + flow
        cash += flow
        cost = volume = 0.0
        if queue is not None and i >= queue["due"]:
            signal = queue["date"]
            if miss and first:
                queue = None
                first = False
                ignored_orders += 1
            else:
                first = False
                if queue["units"] is None:
                    denom = last * mark_fx[i]
                    amount = targets[signal] * (cash + pos.sum())
                    # A newly selected security must have a decision-day price.
                    if ((amount > 0) & ~(denom > 0)).any():
                        raise ValueError("Missing decision-making prices")
                    goal = np.divide(
                        amount, denom, out=np.zeros_like(pos), where=denom > 0
                    )
                    if whole:
                        goal = np.floor(goal)
                    queue["units"] = goal
                goal = queue["units"]
                delta = goal - unit
                if whole:
                    delta = np.where(
                        delta < 0, -np.minimum(unit, np.ceil(-delta)), np.floor(delta)
                    )
                quotes = np.where(tradable, price[i] * mark_fx[i], 0.0)
                sold = np.where(tradable, np.minimum(unit, np.maximum(-delta, 0)), 0.0)
                purchases = np.where(tradable, np.maximum(delta, 0), 0.0)
                required = purchases @ quotes * (1 + fee)
                if required > cash:
                    purchases *= max(0.0, cash) / required
                if whole:
                    purchases = np.floor(purchases + 1e-10)
                buys = purchases * quotes
                sales = sold * quotes
                cash -= buys.sum() * (1 + fee)
                pending += sales.sum() * (1 - fee)
                pos += buys - sales
                unit += purchases - sold
                cost = float((buys + sales).sum() * fee)
                volume = float((buys + sales).sum())
                if capture:
                    for j in np.flatnonzero(buys + sales > 1e-6):
                        audit.append(
                            (
                                signal,
                                day,
                                str(dates[i + 1]) if i + 1 < len(dates) else None,
                                ids[j],
                                float(purchases[j] - sold[j]),
                                float(quotes[j]),
                                float(fee * (buys[j] + sales[j])),
                            )
                        )
                # Allow pending sale proceeds to finance the outstanding basket on T+1.
                if pending < 1e-8 and not ((~tradable) & (abs(delta) > 1e-6)).any():
                    queue = None
                elif i - queue["due"] >= 5:
                    ignored_orders += 1
                    queue = None
        nav = float(cash + pending + pos.sum())
        residual = abs(nav - (opening + flow - cost))
        max_residual = max(max_residual, residual)
        if residual > 1e-5 or cash < -0.00001 or pos.min() < -0.00001:
            raise ValueError(f"Failed to reconcile {day}")
        r = (nav - flow) / previous - 1
        navs.append(
            (
                day,
                nav,
                r,
                cash,
                pending,
                float(pos.sum()),
                float(coupon.sum()),
                flow,
                cost,
                volume,
                residual,
            )
        )
        fees += cost
        turn += volume / previous
        previous = nav
        if day in targets:
            queue = dict(due=i + lag, date=day, units=None)
    frame = pd.DataFrame(
        navs,
        columns=[
            "day",
            "nav",
            "ret",
            "cash",
            "receivable",
            "invested",
            "coupon",
            "flow",
            "cost",
            "traded",
            "residual",
        ],
    ).set_index("day")
    gross = (1 + frame.ret).cumprod()
    duration = (
        pd.Timestamp(str(dates[-1])) - pd.Timestamp(str(dates[0]))
    ).days / 365.25
    dd = float((gross / gross.cummax() - 1).min())
    info = dict(
        final=previous,
        indicative_cagr=float(gross.iloc[-1] ** (1 / duration) - 1),
        indicative_drawdown=dd,
        realized_vol=float(frame.ret.std() * np.sqrt(252)),
        fees=fees,
        turnover=turn,
        paid=paid,
        unpaid=unpaid,
        unresolved=sorted(problems),
        first_problem=first_problem,
        max_gap_weight=gap_weight,
        cash_redemptions=redemptions,
        max_residual=max_residual,
        unfilled_baskets=ignored_orders,
    )
    if not problems:
        info.update(cagr=info["indicative_cagr"], drawdown=dd)
    else:
        info.update(cagr=None, drawdown=None)
    return (
        info,
        frame,
        pd.DataFrame(
            audit,
            columns=[
                "decision",
                "execution",
                "settlement",
                "id",
                "quantity",
                "price_chf",
                "fee_chf",
            ],
        ),
    )
