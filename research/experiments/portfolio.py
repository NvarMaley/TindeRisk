"""Self-financing target, cost and withdrawal replays with drifted positions."""

import numpy as np
import pandas as pd
from models import ASSETS, BASE, CAND, EW


def trade(values, cash, target, rate):
    gross = values.sum() + cash
    after = gross
    for _ in range(30):
        desired = after * target
        traded = np.abs(desired - values).sum()
        nxt = gross - rate * traded
        if abs(nxt - after) < 1e-10:
            break
        after = nxt
    fee = traded * rate
    remainder = gross - fee - desired.sum()
    if remainder < -1e-6:
        raise ValueError("Unfunded trade")
    return desired, max(remainder, 0.0), traded, fee


def market_months(market, cash):
    def wide(col):
        return market.pivot(index="session", columns="asset", values=col)[ASSETS]

    close = wide("adjusted_usd")
    opens = wide("chart_open_proxy_usd") / wide("chart_close") * close
    fx = market[market.asset == "SPY"].set_index("session").chf_per_usd
    bill = cash.set_index("session").usd_cash_proxy
    months = {}
    for per, g in close.groupby(close.index.to_period("M")):
        days = g.index
        pos = close.index.get_loc(days[0])
        if not pos:
            continue
        prev = close.index[pos - 1]
        for currency in ["CHF", "USD"]:
            spot = fx.reindex(days) if currency == "CHF" else pd.Series(1.0, index=days)
            marks = g.mul(spot, axis=0)
            prices = opens.loc[days].mul(spot, axis=0)
            quotes = prices.dropna()
            fill = quotes.index[0] if len(quotes) else pd.NaT
            factors = (
                1 + bill.loc[days] if currency == "USD" else pd.Series(1.0, index=days)
            )
            if factors.isna().any():
                continue
            months[str(per), currency] = (
                close.loc[prev].to_numpy()
                * (fx.loc[prev] if currency == "CHF" else 1.0),
                marks.iloc[-1].to_numpy(),
                quotes.iloc[0].to_numpy() if len(quotes) else None,
                fill,
                factors.loc[:fill].prod() if len(quotes) else factors.prod(),
                factors.loc[factors.index > fill].prod() if len(quotes) else 1.0,
            )
    return months


def boundary_weights(drift, width):
    # Along the line to the target the largest deviation scales proportionally.
    distance = np.max(np.abs(drift - EW))
    return EW + (drift - EW) * min(1.0, width / distance) if distance else EW.copy()


def allocation_ledger(frozen, targets, months, *, policies_by_study=None):
    output = []
    if policies_by_study is None:
        policies_by_study = {
            s: [BASE[s], *CAND[s]] for s in ["H01", "H02", "H03", "H04", "H07"]
        }
        policies_by_study["H07"] += ["3pp band", "7pp band"]
    for study, policies in policies_by_study.items():
        base = frozen[(frozen.study == study) & (frozen.arm == BASE[study])]
        for phase, part in base[base.phase != "warm-up"].groupby("phase", sort=False):
            for arm in policies:
                for cost in [0, 10, 25, 50, 100] if study == "H07" else [0, 10, 25]:
                    units = np.zeros(3)
                    cash = 85000.0
                    reserve = 15000.0
                    invested = False
                    currency = "USD" if study in ["H03", "H04"] else "CHF"
                    if currency == "USD":
                        reserve = 0.0
                    for j, r in enumerate(part.itertuples()):
                        mo = r.holding_month
                        prev, end, opening, fill, before, after = months[mo, currency]
                        initial = (
                            units @ prev + cash
                            if np.isfinite(prev).all()
                            else (cash if not units.any() else np.nan)
                        )
                        drift = (
                            units * prev / initial
                            if np.isfinite(initial) and initial > 0
                            else np.full(3, np.nan)
                        )
                        if study == "H07":
                            target = EW
                            due = r.input_ready and (
                                not invested
                                or arm == "monthly"
                                or (
                                    arm == "quarterly" and int(mo[-2:]) in [1, 4, 7, 10]
                                )
                                or (
                                    "band" in arm
                                    and np.max(np.abs(drift - EW)) > float(arm[0]) / 100
                                )
                            )
                            if arm == "5pp boundary band" and invested and due:
                                target = boundary_weights(drift, 0.05)
                        else:
                            target = targets.get(
                                (study, arm, mo), targets.get((study, BASE[study], mo))
                            )
                            due = target is not None
                        cash *= before
                        traded = fee = 0.0
                        review = np.nan
                        action = "hold"
                        if opening is not None:
                            values = units * opening
                            if due:
                                values, cash, traded, fee = trade(
                                    values, cash, target, cost / 10000
                                )
                                units = values / opening
                                invested = True
                                action = "rebalance"
                            if study == "H07" and invested and r.input_ready:
                                review = np.abs(
                                    values / (values.sum() + cash) - EW
                                ).max()
                        cash *= after
                        endvalue = (
                            units @ end + cash
                            if np.isfinite(end).all()
                            else (cash if not units.any() else np.nan)
                        )
                        withdrawal = 15000.0 if currency == "CHF" and j == 11 else 0.0
                        if reserve < withdrawal:
                            raise ValueError("Unfunded protected payment")
                        reserve -= withdrawal
                        ret = endvalue / initial - 1 if initial > 0 else np.nan
                        endw = (
                            units * end / endvalue
                            if endvalue > 0
                            else np.full(3, np.nan)
                        )
                        output.append(
                            {
                                "study": study,
                                "phase": phase,
                                "arm": arm,
                                "holding_month": mo,
                                "currency": currency,
                                "cost_bp": cost,
                                "action": action,
                                "fill_proxy": fill if due else pd.NaT,
                                "traded": traded,
                                "fee": fee,
                                "net_return": ret,
                                "utility": ret - 2 * ret**2,
                                "wealth": endvalue,
                                "reserve": reserve,
                                "withdrawal": withdrawal,
                                "drift_review": review,
                                "w_spy": endw[0],
                                "w_ief": endw[1],
                                "w_gld": endw[2],
                                "target_spy": target[0]
                                if target is not None
                                else np.nan,
                                "target_ief": target[1]
                                if target is not None
                                else np.nan,
                                "target_gld": target[2]
                                if target is not None
                                else np.nan,
                            }
                        )
    return pd.DataFrame(output)


def posterior_weight(cov, direction, uncertainty=1, *, relative_to_prior=False):
    anchor = np.array([0.5, 0.5])
    p = np.array([1.0, -1.0])
    if not direction:
        return anchor, 0.0
    spread = p @ cov @ p
    prior = 4 * cov @ anchor
    innovation = 0.01 * direction if relative_to_prior else 0.01 * direction - p @ prior
    adjustment = innovation / (4 * (1 + uncertainty) * spread)
    active = np.clip(
        adjustment,
        -min(0.5, 0.02 / np.sqrt(12 * spread)),
        min(0.5, 0.02 / np.sqrt(12 * spread)),
    )
    return anchor + active * p, abs(active) * np.sqrt(12 * spread)


def sentiment(frozen, returns, events):
    data = returns.set_index("session")[["AAPL", "SPY"]]
    rows = []
    for (phase, arm), sample in frozen[
        (frozen.study == "H06") & (frozen.phase != "warm-up")
    ].groupby(["phase", "arm"], sort=False):
        for bp in [0, 10, 25]:
            w = np.array([0.5, 0.5])
            new_segment = True
            for r in sample.itertuples():
                hist = data.loc[: r.origin].tail(252).dropna()
                active = events[
                    (events.available_at < r.decision_at)
                    & (
                        events.available_at.dt.strftime("%Y-%m")
                        == r.origin.strftime("%Y-%m")
                    )
                ]
                seen = active.dropna(subset=["direction"])
                source = seen.iloc[-1] if len(seen) else None
                if int(r.view_direction) != (
                    int(source.direction) if source is not None else 0
                ):
                    raise ValueError("Sentiment input differs from frozen manifest")
                signal = (
                    source.Type
                    if source is not None
                    else "no classified event"
                    if active.N.sum() > 0
                    else "no observed messages"
                )
                direction = int(r.view_direction) if arm != BASE["H06"] else 0
                desired, te = (
                    posterior_weight(hist.cov().to_numpy() * 21, direction)
                    if r.input_ready
                    else (np.array([0.5, 0.5]), 0.0)
                )
                obs = data.loc[r.holding_month].to_numpy()
                net = turn = fee = np.nan
                reset = new_segment
                if np.isfinite(obs).all() and r.input_ready:
                    v = w * (1 + obs[0])
                    v, _, turn, fee = trade(v, 0.0, desired, bp / 10000)
                    v *= np.prod(1 + obs[1:], axis=0)
                    net = v.sum() - 1
                    w = v / v.sum()
                    new_segment = False
                else:
                    w = np.array([0.5, 0.5])
                    new_segment = True
                rows.append(
                    {
                        "study": "H06",
                        "arm": arm,
                        "phase": phase,
                        "holding_month": r.holding_month,
                        "cost_bp": bp,
                        "signal_status": signal,
                        "signal_session": source.session
                        if source is not None
                        else pd.NaT,
                        "signal_available": source.available_at
                        if source is not None
                        else pd.NaT,
                        "view_direction": direction,
                        "target_aapl": desired[0],
                        "achieved_te": te,
                        "view_q": 0.01 * direction if direction else np.nan,
                        "omega": 0.05 * 21 * hist.diff(axis=1).iloc[:, 1].var()
                        if len(hist) > 1
                        else np.nan,
                        "portfolio_reset": reset,
                        "traded": turn,
                        "fee": fee,
                        "net_return": net,
                        "utility": net - 2 * net**2,
                    }
                )
    return pd.DataFrame(rows)
