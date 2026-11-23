"""Replay the first decision with a verified OTC continuation and audit archived fills."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import duckdb
import numpy as np
import pandas as pd
import requests

from ..archive_labels import LEGACY_LABELS, read_snapshot
from .data import cash_exits
from .replay import run

REPORT = Path("reports/univers-complet")
CAT = Path("data/local/4/4.0-2026-11-23")
START, ANCHOR, STOP = "2017-10-31", "2017-12-18", "2018-01-31"
KEY = "PERMNO:88257"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/PFBX"
PARAMS = {
    "period1": 1506816000,
    "period2": 1543622400,
    "interval": "1d",
    "events": "div,splits",
}


def prefix_panel(plans):
    ids = sorted({k for plan in plans.values() for k in plan[START]})
    funds = [k for k in ids if not k.startswith("PERMNO:")]
    assert set(funds) == {"SPY", "IEF"}
    data = pd.read_parquet(
        CAT / "prices.parquet", filters=[("day", ">=", START), ("day", "<=", STOP)]
    )
    data["id"] = data.id.str.rsplit("-", n=1).str[-1]
    data = data[data.id.isin(funds)].rename(columns={"return_usd": "usd"})
    days = pd.Index(sorted(data.day.unique()))
    stocks = pd.read_parquet(
        "data/local/univers/crsp_daily_2014_2025.parquet",
        filters=[
            ("permno", "in", [int(k[7:]) for k in ids if k.startswith("PERMNO:")]),
            ("day", ">=", pd.Timestamp(START).date()),
            ("day", "<=", pd.Timestamp(STOP).date()),
        ],
    )
    stocks["id"] = "PERMNO:" + stocks.permno.astype(str)
    stocks["day"] = pd.to_datetime(stocks.day).dt.strftime("%Y-%m-%d")
    data = pd.concat([data, stocks], ignore_index=True)
    names = pd.Index(funds + [k for k in ids if k not in funds])

    def matrix(field):
        return (
            data.pivot(index="day", columns="id", values=field)
            .reindex(index=days, columns=names)
            .to_numpy(dtype=np.float32)
            .copy()
        )

    fx = pd.read_parquet(CAT / "fx.parquet").set_index("day").value.reindex(days)
    return SimpleNamespace(
        names=names,
        dindex=days,
        days=days.to_numpy(),
        close=matrix("close"),
        usd=matrix("usd"),
        fx=fx.to_numpy(),
        stock0=len(funds),
        funds=funds,
        coupons=np.empty((len(days), 0)),
        exits={},
    )


def observed_quotes(raw):
    chart = json.loads(raw)["chart"]["result"][0]
    meta = chart["meta"]
    if (
        meta["symbol"],
        meta["currency"],
        meta["exchangeName"],
        meta["instrumentType"],
    ) != ("PFBX", "USD", "OQX", "EQUITY"):
        raise ValueError("Unexpected security or venue")

    def day(timestamp):
        return (
            pd.to_datetime(timestamp, unit="s", utc=True)
            .tz_convert("America/New_York")
            .strftime("%Y-%m-%d")
        )

    dates = pd.Index([day(t) for t in chart["timestamp"]])
    quotes = pd.DataFrame(chart["indicators"]["quote"][0], index=dates)
    for events in chart.get("events", {}).values():
        if any(ANCHOR < day(e["date"]) <= STOP for e in events.values()):
            raise ValueError(
                "Corporate action in bridge window requires an explicit cash or share adjustment"
            )
    if not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError("Invalid quote calendar")
    return quotes.loc[
        (quotes.volume > 0) & (quotes.close > 0), ["close", "volume"]
    ].loc[:STOP]


def apply_bridge(panel, quotes):
    col = panel.names.get_loc(KEY)
    local = pd.Series(panel.close[:, col], index=panel.dindex)
    overlap = (
        pd.concat([local.rename("local"), quotes.close], axis=1, join="inner")
        .dropna()
        .loc[:"2017-12-15"]
        .tail(5)
    )
    if (
        len(overlap) != 5
        or (overlap.local - overlap.close).abs().max() > 0.011
        or not np.isclose(local[ANCHOR], 13.0)
    ):
        raise ValueError("Cross-source overlap or archived anchor failed")
    previous = local[ANCHOR]
    added = 0
    for date, row in quotes.loc[quotes.index > ANCHOR].iterrows():
        i = panel.dindex.get_loc(date)
        if np.isfinite(panel.close[i, col]) or np.isfinite(panel.usd[i, col]):
            raise ValueError("Bridge cannot overwrite an existing observation")
        panel.usd[i, col] = row.close / previous - 1
        panel.close[i, col] = previous = row.close
        added += 1
    return added


def ledger(bundle):
    nav = (
        read_snapshot(bundle / "nav.parquet").set_index(["option", "day"]).sort_index()
    )
    orders = read_snapshot(bundle / "orders.parquet")
    gross = orders.quantity * orders.price_chf
    orders = orders.assign(
        buy=gross.clip(lower=0),
        sell=(-gross).clip(lower=0),
        buy_fee=orders.fee_chf.where(gross > 0, 0.0),
        sell_fee=orders.fee_chf.where(gross < 0, 0.0),
    )
    trades = orders.groupby(["option", "execution"])[
        ["buy", "sell", "fee_chf", "buy_fee", "sell_fee"]
    ].sum()
    trades.index.names = nav.index.names
    if not nav.index.is_unique or not trades.index.isin(nav.index).all():
        raise ValueError("Duplicate valuation or an order without a daily ledger")
    calendar = pd.Series(sorted(nav.index.get_level_values("day").unique()))
    next_session = pd.Series(calendar.shift(-1).to_numpy(), index=calendar)
    if (
        not orders.settlement.fillna("")
        .eq(orders.execution.map(next_session).fillna(""))
        .all()
    ):
        raise ValueError("Settlement date differs from the next replay session")
    f = nav.join(trades).fillna({k: 0 for k in trades})
    expected_cash = (
        f.cash.groupby(level=0).shift().fillna(35000.0)
        + f.receivable.groupby(level=0).shift().fillna(0.0)
        + f.coupon
        + f.flow
        - f.buy
        - f.buy_fee
    )
    errors = {
        "cash_chf": (expected_cash - f.cash).abs().max(),
        "fees_chf": (f.cost - f.fee_chf).abs().max(),
        "turnover_chf": (f.traded - f.buy - f.sell).abs().max(),
        "nav_chf": (f.nav - f.invested - f.cash - f.receivable).abs().max(),
    }
    if max(errors.values()) > 0.0001:
        raise ValueError(f"Ledger did not reconcile: {errors}")
    return {
        "order_rows": len(orders),
        "portfolio_days": len(nav),
        "max_absolute_residual": errors,
    }


def request_list(archive, bundle, local_folder):
    """Keep the instrument-level, frozen-run follow-up queue beside the private inputs."""
    nav_orders = read_snapshot(bundle / "orders.parquet")
    by_id = nav_orders.groupby("id").execution.agg(["min", "max"])
    queue = {}
    for name, variants in archive["runs"].items():
        for scenario, info in variants.items():
            for key in info["unresolved"]:
                queue.setdefault(key, {"central": [], "other_scenarios": set()})
                if scenario == "central":
                    queue[key]["central"].append(name)
                else:
                    queue[key]["other_scenarios"].add(scenario)
    for key, record in queue.items():
        record["other_scenarios"] = sorted(record["other_scenarios"])
        if key in by_id.index:
            record["first_archived_fill"] = str(by_id.loc[key, "min"])
            record["last_archived_fill"] = str(by_id.loc[key, "max"])
    (local_folder / "requested-identifiers.json").write_text(
        json.dumps(queue, indent=2) + "\n"
    )
    return {
        "original_central_ids": sum(bool(v["central"]) for v in queue.values()),
        "original_ids_all_scenarios": len(queue),
    }


def first_missing_quotes():
    """Check the raw CRSP tape, including quote fields dropped by the research panel."""
    tape = "data/local/5/raw/crsp_dsf.csv"
    with duckdb.connect() as db:
        missing = db.execute(
            """
            SELECT DlyCalDt, TRY_CAST(DlyPrc AS DOUBLE), TRY_CAST(DlyRet AS DOUBLE),
                   TRY_CAST(DlyBid AS DOUBLE), TRY_CAST(DlyAsk AS DOUBLE)
              FROM read_csv(?,all_varchar=true) WHERE PERMNO='15266'
               AND DlyCalDt BETWEEN '2018-01-10' AND '2018-01-22' ORDER BY DlyCalDt
        """,
            [tape],
        ).fetchall()
    if len(missing) != 8 or not all(
        p is None and r is None and bid == 0.01 and ask is None
        for _, p, r, bid, ask in missing
    ):
        raise ValueError(
            "The BHAC raw tape changed; review the next unresolved interval"
        )
    return {
        "id": "PERMNO:15266",
        "symbol": "BHAC",
        "missing_sessions": len(missing),
        "from": missing[0][0],
        "through": missing[-1][0],
        "next_observed_close": "2018-01-23",
        "evidence": "No close, return or offer; one-sided USD 0.01 bid.",
    }


def main():
    archive = json.loads((REPORT / "resultats.json").read_text())
    bundle = Path("data/local/univers") / archive["snapshot"]
    plans = {
        LEGACY_LABELS.get(k, k): {START: v[START]}
        for k, v in json.loads((bundle / "historical_plans.json").read_text()).items()
    }
    policy = json.loads(Path("config/options-6.json").read_text()) | {"market": STOP}
    panel = prefix_panel(plans)
    panel.register = pd.DataFrame(
        columns=["exit_cash_usd"]
    )  # The 2026 extension lies outside this replay.
    panel.exits = cash_exits(panel)
    nav = read_snapshot(bundle / "nav.parquet")
    baseline = {}
    for name, plan in plans.items():
        result, frame, fills = run(panel, plan, policy, capture=True)
        expected = nav[nav.option.eq(name)].set_index("day").loc[START:STOP]
        np.testing.assert_allclose(
            frame[expected.select_dtypes("number").columns],
            expected.select_dtypes("number"),
            rtol=1e-10,
            atol=1e-7,
        )
        baseline[name] = (result, fills)
    raw_path = Path("data/local/6/repair/PFBX.json")
    if not raw_path.exists():
        response = requests.get(
            URL, params=PARAMS, headers={"User-Agent": "Mozilla/5.0"}, timeout=30
        )
        response.raise_for_status()
        observed_quotes(response.content)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(response.content)
    quotes = observed_quotes(raw_path.read_bytes())
    used = quotes.loc[START:STOP].to_csv(float_format="%.6f")
    quote_hash = hashlib.sha256(used.encode()).hexdigest()
    prior_path = REPORT / "replay-evidence.json"
    if (
        prior_path.exists()
        and json.loads(prior_path.read_text())["quotes_sha256"] != quote_hash
    ):
        raise ValueError(
            "Historical quote series changed; review the overlap before publishing"
        )
    identity = pd.read_parquet(
        CAT / "identifiers.parquet", filters=[("permno", "=", 88257)]
    )
    identity = identity[
        (identity.id_from.astype(str) <= "2017-12-15")
        & (identity.id_to.astype(str) >= "2017-12-15")
    ]
    assert set(zip(identity.ticker, identity.cusip)) == {("PFBX", "71103B102")}
    added = apply_bridge(panel, quotes)
    records = {}
    for name, plan in plans.items():
        for scenario, spec in policy["scenarios"].items():
            result, frame, fills = run(panel, plan, policy, capture=True, **spec)
            if not fills[fills.id.eq(KEY) & fills.execution.gt(ANCHOR)].empty:
                raise ValueError("OTC valuation evidence cannot authorize a trade")
            if scenario == "central":
                pd.testing.assert_frame_equal(baseline[name][1], fills)
            records[name, scenario] = (result, frame)
    first = min(r["first_problem"] for r, _ in records.values() if r["first_problem"])
    for (name, scenario), (info, _) in records.items():
        if info["first_problem"] == first:
            # Through the first disputed day, isolate which held security triggered the rule.
            r, _, _ = run(
                panel,
                plans[name],
                policy | {"market": str(first)},
                **policy["scenarios"][scenario],
            )
            assert r["unresolved"] == ["PERMNO:15266"], r["unresolved"]
    end = panel.dindex[panel.dindex.get_loc(first) - 1]
    summaries = {}
    for (name, scenario), (r, frame) in records.items():
        prefix = frame.loc[:end]
        summaries.setdefault(name, {})[scenario] = {
            "sessions": len(prefix),
            "end": str(end),
            "cumulative": float((1 + prefix.ret).prod() - 1),
            "fees_chf": float(prefix.cost.sum()),
            "traded_chf": float(prefix.traded.sum()),
            "first_problem_through_january": r["first_problem"],
        }
    result = {
        "snapshot": archive["snapshot"],
        "source_url": requests.Request("GET", URL, params=PARAMS).prepare().url,
        "quotes_sha256": quote_hash,
        "added_positive_volume_marks": added,
        "scope_end": STOP,
        "first_remaining_problem": str(first),
        "scenarios": summaries,
        "archive_ledger": ledger(bundle),
        "next_gap": first_missing_quotes(),
        "original_queue": request_list(archive, bundle, raw_path.parent),
    }
    prior_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    main()
