"""Dated, funded transaction replay for the retrospective CHF cohorts."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from research.frontier.engine import ASSETS, Frontier, moments
from research.options.run import checked

ARMS = ["60/40", "classical", "robust"]
CASES = [
    "primary",
    "zero fee",
    "25bp",
    "second session",
    "miss opening",
    "half fill",
    "lag FX",
    "wide spread",
    "volume cap",
    "504 sessions",
    "half diagonal",
]


def intent(units, cash, price, weights):
    wealth = cash + units @ price
    return wealth * np.asarray(weights) / price - units


def fill(units, cash, order, quote, rate, fraction=1, capacity=None):
    size = order * fraction
    if capacity is not None:
        size = np.sign(size) * np.minimum(np.abs(size), capacity / quote)
    size = np.maximum(size, -units)
    sale = np.minimum(size, 0)
    buy = np.maximum(size, 0)
    funds = cash - sale @ quote * (1 - rate)
    need = buy @ quote * (1 + rate)
    if need > funds and need > 0:
        buy *= max(0, funds) / need
    size = buy + sale
    traded = np.abs(size) @ quote
    after = cash - size @ quote - rate * traded
    if after < -0.000001:
        raise ValueError("Unfunded transaction")
    return units + size, max(0, after), size, traded


def replay(dates, usd, fx, adv, w, cov, mu, train_end, arm, policy, case):
    q = usd * fx[:, None]
    ok = np.isfinite(q).all(axis=1) & (q > 0).all(axis=1)
    units = np.zeros(3)
    cash = 35000.0
    reserve = 15000.0
    prev = 50000.0
    index = peak = 1.0
    last = None
    events = []
    marks = []
    losses = []
    pending = None
    span = longest = 0
    total = fees = 0.0
    rate = {"zero fee": 0.0, "25bp": 0.0025, "wide spread": 0.0037}.get(case, 0.001)
    for i, day in enumerate(dates):
        flow = 0.0
        notional = fee = 0.0
        if pending is not None and i > pending["i"]:
            p = pending
            lag = i - p["i"]
            if (
                ok[i]
                and lag >= (2 if case == "second session" else 1)
                and not (case == "miss opening" and p["i"] == 0)
            ):
                before = units.copy()
                old_cash = cash
                capacity = adv[p["i"]] * 0.0000001 if case == "volume cap" else None
                units, cash, actual, notional = fill(
                    units,
                    cash,
                    p["order"],
                    q[i],
                    rate,
                    0.5 if case == "half fill" else 1.0,
                    capacity,
                )
                fee = rate * notional
                total += notional
                fees += fee
                for j, e in enumerate(p["rows"]):
                    if not e["intended_units"]:
                        continue
                    e.update(
                        status="filled"
                        if abs(actual[j] - e["intended_units"]) < 1e-7
                        else "partial",
                        fill_date=day,
                        lag=lag,
                        first_return_after=day,
                        filled_units=actual[j],
                        fill_usd=usd[i, j],
                        fill_fx=fx[i],
                        units_before=before[j],
                        units_after=units[j],
                        cash_before=old_cash,
                        cash_after=cash,
                        commission=abs(actual[j])
                        * q[i, j]
                        * (0 if rate == 0 else 0.0002),
                        fx_fee=abs(actual[j]) * q[i, j] * (0 if rate == 0 else 0.0005),
                        spread=abs(actual[j])
                        * q[i, j]
                        * (rate - 0.0007 if rate else 0),
                        timing_cost=actual[j] * (q[i, j] - e["decision_chf"]),
                    )
                pending = None
            elif lag >= 5:
                for e in p["rows"]:
                    if e["intended_units"]:
                        e["status"] = "expired"
                pending = None
        if i == len(dates) - 1:
            flow = -reserve
            reserve = 0.0
        if ok[i]:
            last = i
        if last is None:
            raise ValueError("No opening mark")
        position = units * q[last]
        sleeve = cash + position.sum()
        wealth = sleeve + reserve
        perf = (wealth - flow) / prev - 1
        index *= 1 + perf
        peak = max(peak, index)
        prev = wealth
        weights = position / sleeve
        vol = np.sqrt(weights @ cov @ weights)
        if ok[i] and i:
            losses.append(perf)
        span = span + 1 if ok[i] and vol > 0.080001 else 0
        longest = max(longest, span)
        marks.append(
            dict(
                date=day,
                available=ok[i],
                mark_date=dates[last],
                cash=cash,
                reserve=reserve,
                flow=flow,
                units_spy=units[0],
                units_ief=units[1],
                units_gld=units[2],
                wealth=wealth,
                unit_index=index,
                drawdown=index / peak - 1,
                turnover_chf=notional,
                fees_chf=fee,
                estimated_vol=vol,
                breach=span > 0,
            )
        )
        month_end = i + 1 < len(dates) and day.month != dates[i + 1].month
        if i == 0 or (month_end and policy == "monthly"):
            weights_order = intent(units, cash, q[last], w) if ok[i] else np.zeros(3)
            rows = []
            for j, a in enumerate(ASSETS):
                rows.append(
                    dict(
                        origin=day,
                        asset=a,
                        target=w[j],
                        forecast_cutoff=train_end,
                        annual_mean=mu[j],
                        signal=arm,
                        intended_units=weights_order[j],
                        decision_chf=q[last, j],
                        prior_adv_chf=adv[i, j],
                        filled_units=0.0,
                        status=(
                            "missing quote"
                            if not ok[i]
                            else (
                                "pending" if abs(weights_order[j]) > 0 else "no order"
                            )
                        ),
                    )
                )
            events.extend(rows)
            if ok[i]:
                pending = dict(i=i, order=weights_order, rows=rows)
    for e in events:
        e["unfilled_cost_to_terminal"] = (e["intended_units"] - e["filled_units"]) * (
            q[last, list(ASSETS).index(e["asset"])] - e["decision_chf"]
        )
    ret = np.array(losses)
    return (
        events,
        marks,
        dict(
            net_household_return=index - 1,
            annualized=index ** (365.25 / (dates[-1] - dates[0]).days) - 1,
            end_chf=wealth,
            withdrawal_paid=-flow,
            shortfall=15000 + flow,
            turnover_chf=total,
            fees_chf=fees,
            max_drawdown=min(r["drawdown"] for r in marks),
            daily_es05=ret[ret <= np.quantile(ret, 0.05)].mean(),
            breach_days=sum(r["breach"] for r in marks),
            longest_breach=longest,
            missing_marks=sum(not r["available"] for r in marks),
        ),
    )


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    f = ROOT / "research/frontier/results"
    grid = pd.read_csv(checked(f, "frontiers.csv"))
    training = json.loads(checked(f, "training.json").read_text())
    market = pd.read_parquet(checked(ROOT / "data/prepared_v1", "market.parquet"))

    def wide(key):
        return market.pivot(index="session", columns="asset", values=key)[list(ASSETS)]

    usd = wide("adjusted_usd")
    fx = wide("chf_per_usd").iloc[:, 0]
    returns = wide("chf_return")
    adv = {}
    for a in ASSETS:
        raw = json.loads(
            (ROOT / f"data/raw/price_events/{a}-20261118.json").read_text()
        )
        if hashlib.sha256(raw["payload"].encode()).hexdigest() != raw["sha256"]:
            raise ValueError("volume snapshot changed")
        data = json.loads(raw["payload"])["chart"]["result"][0]
        bar = data["indicators"]["quote"][0]
        dates = (
            pd.to_datetime(data["timestamp"], unit="s", utc=True)
            .tz_convert("America/New_York")
            .normalize()
            .tz_localize(None)
        )
        volume = pd.Series(
            np.array(bar["volume"], float) * np.array(bar["close"], float), index=dates
        )
        adv[a] = (
            (volume.reindex(usd.index) * fx).shift(1).rolling(20, min_periods=15).mean()
        )
    adv = pd.DataFrame(adv).fillna(0)
    orders = []
    daily = []
    summary = []
    for t, next_t in zip(training, training[1:]):
        origin = t["origin"]
        ix = usd.loc[origin : next_t["origin"]].index
        cap = 0.08
        g = grid[(grid.origin == origin) & (grid.cap == cap)].set_index("arm")
        for case in CASES:
            cov = np.array(t["covariance"])
            mu = np.array(t["annual_mean"])
            v = np.array(t["mean_uncertainty"])
            if case == "504 sessions":
                mu, cov, v = moments(
                    returns.loc[returns.index < origin].tail(504).to_numpy(),
                    np.random.default_rng(71),
                    199,
                )
            if case == "half diagonal":
                cov = (cov + np.diag(np.diag(cov))) / 2
            targets = g
            if case in ["504 sessions", "half diagonal"]:
                targets = pd.DataFrame(
                    Frontier(mu, cov, v, [True] * 3).rows(caps=[cap], arms=ARMS)
                ).set_index("arm")
            rate = fx.shift(1) if case == "lag FX" else fx
            x = rate.loc[ix].to_numpy().copy()
            # If the prior FX fix is absent on opening day, it prevents opening an order.
            if not np.isfinite(x[0]):
                x[0] = rate.loc[:origin].dropna().iloc[-1]
            for arm in ARMS:
                w = targets.loc[arm, ["w0", "w1", "w2"]].to_numpy(float)
                for policy in ["hold", "monthly"]:
                    keys = dict(cohort=origin, case=case, arm=arm, policy=policy)
                    e, m, s = replay(
                        ix,
                        usd.loc[ix].to_numpy(),
                        x,
                        adv.loc[ix].to_numpy(),
                        w,
                        cov,
                        mu,
                        t["last"],
                        arm,
                        policy,
                        case,
                    )
                    orders.extend(dict(**keys, **r) for r in e)
                    daily.extend(dict(**keys, **r) for r in m)
                    summary.append(dict(**keys, **s))
    pd.DataFrame(orders).to_parquet(out / "orders.parquet", index=False)
    pd.DataFrame(daily).to_parquet(out / "daily.parquet", index=False)
    pd.DataFrame(summary).to_csv(out / "cohorts.csv", index=False)
    (out / "manifest.json").write_text(
        json.dumps(
            {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.iterdir())
                if p.name != "manifest.json"
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    build(HERE / "results")
