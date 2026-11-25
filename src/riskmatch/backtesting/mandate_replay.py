"""Dated mandate replay on archived stock returns and the supported ETF list."""
from functools import lru_cache
from pathlib import Path

import duckdb
import numpy as np

from riskmatch.backtesting.walk_forward import execute
from riskmatch.optimization.mean_variance_report import category
from riskmatch.strategies.alternative_report import macro_signals
from riskmatch.strategies.long_only_report import load_signals, verified_pit

REFIT_MONTHS = 3


@lru_cache(maxsize=1)
def archive(root, intervals, first, etf_keys, version, as_of):
    """Retain stocks independently of whether they survived until the archive cutoff."""
    pit = verified_pit(root, version)
    folder = Path(root) / "data/processed/returns" / version
    origins = [intervals[i-1][0] for i in range(first, len(intervals), REFIT_MONTHS)]
    days = [a for a, _ in intervals[first-1:]]
    with duckdb.connect() as db:
        membership = db.execute(
            "select instrument, observation_date, market_cap_source_units from read_parquet(?) "
            "where observation_date in (select unnest(?))",
            [str(pit / "stock_membership.parquet"), days]).fetchall()
        caps = {}
        for instrument, day, cap in membership:
            caps.setdefault(day, {})[instrument] = float(cap or 0)
        stocks = sorted({i for i, _, _ in membership})
        assets = [dict(id="stock:"+i, category="stock", ticker="stock:"+i,
                       instrument=i, source="stock_monthly") for i in stocks]
        assets += [dict(zip(("id", "category", "ticker", "instrument", "source"), row))
                   for row in etf_keys]
        dates = {pair:j for j,pair in enumerate(intervals)}
        panel = np.full((len(intervals), len(assets)), np.nan)
        available = np.full(panel.shape, np.datetime64("NaT"), dtype="datetime64[D]")
        for source in ("stock_monthly", "etf_crsp_monthly"):
            ids = {str(a["instrument"]):i for i,a in enumerate(assets) if a["source"] == source}
            rows = db.execute(
                "select instrument,start_date,end_date,total_return,cast(availability_time as date) "
                "from read_parquet(?) where end_date between ? and ? and total_return >= -1",
                [str(folder / (source+".parquet")), intervals[0][1], intervals[-1][1]]).fetchall()
            for instrument,start,end,value,published in rows:
                j = dates.get((start,end))
                i = ids.get(instrument)
                if i is not None and j is not None and np.isfinite(value):
                    panel[j,i] = value
                    if published:
                        available[j,i] = published
    signals = load_signals(root, as_of, assets, origins, version)
    return assets, panel, available, signals, macro_signals(root,version,origins), caps


def replay(root, data, mandate, report, aversion, construct, as_of):
    current, intervals, _, rf, version, first, split, *_ = data
    etfs = tuple(tuple(a[k] for k in ("id","category","ticker","instrument","source"))
                 for a in current if a["category"] != "stock")
    assets, panel, available, signals, macro, caps = archive(
        root, tuple(intervals), first, etfs, version, as_of)
    supported = mandate["constraints"]["allowed_assets"]
    permitted = np.array([category(a) in supported or a["ticker"]=="SPY" for a in assets])
    states, failed = {}, {}
    for t in range(first,len(intervals)):
        day = intervals[t][0]
        if (t-first) % REFIT_MONTHS == 0:
            end = t-1  # one full month between decision close and execution
            origin = intervals[end][0]
            window = slice(max(0,end-60),end)
            history = panel[window]
            stamp = available[window]
            usable = (np.isfinite(history) & (np.isnat(stamp) | (stamp<=np.datetime64(origin)))).all(axis=0)
            idx = np.flatnonzero(usable & permitted & np.array([
                a["category"]!="stock" or a["instrument"] in caps.get(origin,{}) for a in assets]))
            subset = [assets[i] for i in idx]
            sample = (subset, None, history[:,idx], rf[window], version, None, None, None,
                      signals, macro, caps, None)
            fitted, diagnostics, *_ = construct(sample,mandate,report,aversion,len(history),origin)
            if t == first:
                for key in fitted:
                    h = np.zeros(len(assets)+1)
                    h[-1] = 1.
                    states[key] = dict(holdings=h, returns=[], turnover=[])
            failed.update({k:f"{origin}: {v}" for k,v in diagnostics.items() if k not in failed})
            for key in list(states):
                if key not in fitted:
                    del states[key]
                    continue
                target = np.zeros(len(assets)+1)
                target[idx] = fitted[key][:-1]
                target[-1] = fitted[key][-1]
                states[key]["target"] = target
        exited = np.array([a["category"]=="stock" and a["instrument"] not in caps.get(day,{})
                           for a in assets])
        observed = panel[t]
        for key, state in list(states.items()):
            target = state["target"].copy()
            # Do not replace forbidden stocks with cash if that would break a mandate.
            if np.any(target[:-1][exited] > 1e-10):
                target[-1] += target[:-1][exited].sum()
                target[:-1][exited] = 0
                c = mandate["constraints"]
                cap = c["max_asset_weight"]
                if "cash" not in c["allowed_assets"] or (cap["mode"]=="hard" and cap["value"] is not None and target[-1]>cap["value"]+1e-8):
                    failed[key] = f"{day}: mandatory exit conflicts with cash constraint"
                    del states[key]
                    continue
                state["target"] = target
            opening = state["holdings"].sum()
            h, delta, _ = execute(state["holdings"], target, .001)
            if np.any((h[:-1] > 0) & ~np.isfinite(observed)):
                failed[key] = f"{day}: missing observed return for a held security"
                del states[key]
                continue
            # Missing observations for zero positions contribute no P&L.
            h[:-1] *= 1+np.where(np.isfinite(observed),observed,0)
            h[-1] *= 1+rf[t]
            state["returns"].append(float(h.sum()/opening-1))
            state["turnover"].append(float(abs(delta).sum()/(2*opening)))
            state["holdings"] = h
    return states, failed
