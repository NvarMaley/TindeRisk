"""Close-to-close simulation in CHF, with actual fills and separate sale receivables."""

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class Tape:
    dates: list
    symbols: list
    usd: np.ndarray
    fx: np.ndarray
    mark: np.ndarray
    trade: np.ndarray
    dividends: np.ndarray
    splits: np.ndarray


def tape(prices, events, start, end):
    prices = prices.assign(symbol=prices.id.str.rsplit("-", n=1).str[-1])
    close = prices.pivot(index="day", columns="symbol", values="close").sort_index()
    fx = prices.groupby("day").fx.first().reindex(close.index)
    shape = close.shape
    split = pd.DataFrame(np.ones(shape), index=close.index, columns=close.columns)
    div = split.copy() * 0
    for row in events.itertuples():
        name = row.id.rsplit("-", 1)[-1]
        if row.day not in close.index:
            raise ValueError("Event out of the calendar")
        if row.kind == "splits":
            split.at[row.day, name] *= row.split
        elif row.kind == "dividends":
            div.at[row.day, name] += row.cash
    # Vendor close and dividend are split-adjusted. Restore units on each historical date.
    future = split.iloc[::-1].cumprod().iloc[::-1] / split
    usd = close.ffill() * future
    fxmark = fx.ffill()
    mark = usd.mul(fxmark, axis=0)
    trade = (close.notna() & close.gt(0)).mul(fx.notna() & fx.gt(0), axis=0)
    selection = close.index.to_series().between(start, end)
    ix = selection.to_numpy()
    if mark.loc[selection].isna().any().any():
        raise ValueError("Initial valuation price absent")
    return Tape(
        close.index[ix].tolist(),
        close.columns.tolist(),
        usd.to_numpy()[ix],
        fxmark.to_numpy()[ix],
        mark.to_numpy()[ix],
        trade.to_numpy()[ix],
        (div * future).mul(fxmark, axis=0).to_numpy()[ix],
        split.to_numpy()[ix],
    )


def replay(
    t,
    decisions,
    initial,
    reserve,
    *,
    fee=0.001,
    lag=1,
    settle=1,
    whole=False,
    miss=False,
    flows=None,
    capture=False,
    risk_cap=0.12,
):
    """Decisions are close-time targets or callbacks receiving weights after that session.
    Orders are denominated in units once sized. Remaining buys await settled cash.
    """
    if initial <= 0 or reserve < 0 or not 0 <= fee < 1 or lag < 1 or settle < 1:
        raise ValueError("Invalid replay settings")
    n = len(t.symbols)
    units = np.zeros(n)
    cash = float(initial)
    receivables = {}
    prepaid = {}  # Cash blocked for purchases, offset by an equal payable until settlement.
    orders = []
    daily = []
    holdings = []
    queue = None
    first = True
    paid = unpaid = fees = notional = 0.0
    previous = initial
    prev_mark = None
    plan = {}

    def event(day, kind, **kwargs):
        orders.append(dict(day=day, kind=kind, **kwargs))

    for i, day in enumerate(t.dates):
        mark = t.mark[i]
        cash += receivables.pop(i, 0.0)
        prepaid.pop(i, 0.0)
        before = units.copy()
        units *= t.splits[i]
        if queue and queue.get("delta") is not None:
            queue["delta"] *= t.splits[i]
        income = float(units @ t.dividends[i])
        cash += income
        flow = float((flows or {}).get(day, 0))
        booked = max(flow, -max(cash, 0.0))
        cash += booked
        paid += max(-booked, 0)
        unpaid += max(booked - flow, 0)
        if flow:
            event(day, "flux", requested=flow, booked=booked)
        cost = traded = 0.0
        nav = cash + sum(receivables.values()) + units @ mark
        if queue and i >= queue["due"]:
            signal = queue["signal"]
            if miss and first:
                event(day, "Missed basket", signal=signal)
                queue = None
            elif not t.trade[i].all():
                event(day, "currency or exchange absent", signal=signal)
            else:
                if queue["delta"] is None:
                    target = queue["target"] * nav / mark
                    if whole:
                        target = np.floor(target + 1e-10)
                    queue["delta"] = target - units
                delta = queue["delta"]
                sales = np.minimum(np.maximum(-delta, 0), units)
                purchases = np.maximum(delta, 0)
                needed = (purchases @ mark) * (1 + fee)
                if needed > cash and needed > 0:
                    purchases = purchases * (cash / needed)
                    if whole:
                        purchases = np.floor(purchases + 1e-10)
                executed = purchases - sales
                buy = float(purchases @ mark)
                sell = float(sales @ mark)
                traded = buy + sell
                cost = traded * fee
                cash -= buy * (1 + fee)
                if buy:
                    prepaid[i + settle] = prepaid.get(i + settle, 0) + buy * (1 + fee)
                if sell:
                    receivables[i + settle] = receivables.get(i + settle, 0) + sell * (
                        1 - fee
                    )
                units += executed
                delta -= executed
                for j in np.flatnonzero(abs(executed) > 1e-10):
                    proceeds_day = i + settle
                    event(
                        day,
                        "vente" if executed[j] < 0 else "achat",
                        signal=signal,
                        symbol=t.symbols[j],
                        quantity=executed[j],
                        usd=t.usd[i, j],
                        fx=t.fx[i],
                        gross=abs(executed[j]) * mark[j],
                        fee=abs(executed[j]) * mark[j] * fee,
                        settlement=t.dates[proceeds_day]
                        if proceeds_day < len(t.dates)
                        else None,
                    )
                if abs(delta) @ mark < 1e-6:
                    queue = None
                elif not receivables:
                    event(
                        day,
                        "Unfunded balance",
                        signal=signal,
                        unfilled_chf=float(abs(delta) @ mark),
                    )
                    queue = None
                else:
                    event(
                        day,
                        "outstanding balance",
                        signal=signal,
                        unfilled_chf=float(abs(delta) @ mark),
                    )
            first = False
        nav = float(cash + sum(receivables.values()) + units @ mark)
        # Independent self-financing identity, using overnight holdings before any execution.
        pnl = (
            0.0
            if prev_mark is None
            else float(before @ (t.splits[i] * mark - prev_mark))
        )
        residual = nav - (previous + pnl + income + booked - cost)
        if abs(residual) > 1e-6 or cash < -1e-6 or (units < -1e-8).any():
            raise ValueError(f"Register not reconciled on {day}")
        daily.append(
            dict(
                day=day,
                nav=nav,
                cash=cash,
                pending=sum(receivables.values()),
                positions=units @ mark,
                bank_cash=cash + sum(prepaid.values()),
                blocked_cash=sum(prepaid.values()),
                purchase_payable=sum(prepaid.values()),
                reserve=reserve,
                fee=cost,
                turnover=traded / previous,
                dividend=income,
                flow=booked,
                change_pnl=pnl,
                residual=residual,
                ret=(nav - booked) / previous - 1,
            )
        )
        if capture:
            holdings.append(units.copy())
        if day in decisions:
            if queue:
                event(day, "remaining balance replaced", signal=queue["signal"])
            spec = decisions[day]
            target = np.asarray(
                spec(units * mark / nav) if callable(spec) else spec, float
            )
            if (
                target.shape != (n,)
                or not np.isfinite(target).all()
                or min(target) < -1e-6
                or target.sum() > 1.000001
            ):
                raise ValueError("Invalid basket target")
            target = target.clip(0)
            plan[day] = target.tolist()
            queue = dict(target=target, due=i + lag, signal=day, delta=None)
        previous, prev_mark = nav, mark
        fees += cost
        notional += traded
    if queue:
        event(t.dates[-1], "order pending at the end", signal=queue["signal"])
    d = pd.DataFrame(daily).set_index("day")
    growth = (1 + d.ret).cumprod()
    years = (pd.Timestamp(t.dates[-1]) - pd.Timestamp(t.dates[0])).days / 365.25
    result = dict(
        final=nav,
        fees=fees,
        paid=paid,
        unpaid=unpaid,
        turnover=float(d.turnover.sum()),
        cagr=float(growth.iloc[-1] ** (1 / years) - 1)
        if years and growth.iloc[-1] > 0
        else None,
        drawdown=float((growth / growth.cummax() - 1).min()),
        max_residual=float(d.residual.abs().max()),
        realized_vol=float(d.ret.std() * np.sqrt(252)) if len(d) > 1 else None,
        realized_sharpe=float(d.ret.mean() / d.ret.std() * np.sqrt(252))
        if d.ret.std() > 1e-10
        else None,
        vol_breaches=int((d.ret.rolling(63).std() * np.sqrt(252) > risk_cap).sum()),
        missing=sum(x["kind"] == "Missed basket" for x in orders),
        delayed=sum(x["kind"] == "outstanding balance" for x in orders),
    )
    for tag, start, end in [
        ("crisis_2020", "2020-02-20", "2020-03-23"),
        ("annee_2022", "2022-01-01", "2022-12-31"),
    ]:
        period = d.loc[start:end, "ret"]
        result[tag] = float((1 + period).prod() - 1) if len(period) else None
    return (
        result,
        d,
        pd.DataFrame(orders),
        pd.DataFrame(
            holdings,
            index=d.index if capture else None,
            columns=t.symbols if capture else None,
        ),
        plan,
    )
