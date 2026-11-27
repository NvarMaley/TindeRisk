"""Dated mandate replay on archived stock returns and the supported ETF list."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import duckdb
import numpy as np

from riskmatch.backtesting.walk_forward import execute
from riskmatch.strategies.alternative_report import macro_signals
from riskmatch.strategies.long_only_report import load_signals, verified_pit

REFIT_MONTHS = 3
ESTIMATION_MONTHS = 60
EXECUTION_LAG_MONTHS = 1


def eligible_indices(assets, history, stamps, origin, members):
    """Require a complete trailing return window and dated stock membership."""
    if len(history) != ESTIMATION_MONTHS:
        raise ValueError("Incomplete matching estimation window")
    observed = np.isfinite(history) & (history >= -1)
    known = np.isnat(stamps) | (stamps <= np.datetime64(origin))
    listed = np.array([a["category"] != "stock" or a["instrument"] in members
                       for a in assets], dtype=bool)
    return np.flatnonzero((observed & known).all(axis=0) & listed)


@lru_cache(maxsize=1)
def archive(root, intervals, first, etf_keys, version, as_of):
    """Retain stocks independently of whether they survived until the archive cutoff."""
    pit = verified_pit(root, version)
    folder = Path(root) / "data/processed/returns" / version
    origins = [intervals[i-EXECUTION_LAG_MONTHS][0]
               for i in range(first, len(intervals), REFIT_MONTHS)]
    origins.append(intervals[-1][1])
    days = [a for a, _ in intervals[first-EXECUTION_LAG_MONTHS:]] + [intervals[-1][1]]
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
                "from read_parquet(?) where end_date between ? and ? "
                "and isfinite(total_return) and total_return >= -1",
                [str(folder / (source+".parquet")), intervals[0][1], intervals[-1][1]]).fetchall()
            for instrument,start,end,value,published in rows:
                j = dates.get((start,end))
                i = ids.get(instrument)
                if i is None or j is None:
                    continue
                if np.isfinite(panel[j, i]):
                    raise ValueError(f"Duplicate matching return for {source} {instrument} at {end}")
                panel[j, i] = value
                if published:
                    available[j, i] = published
        settlements = merger_settlements(db, pit, intervals, assets, panel)
        closing_rows = {end: t for t, (_, end) in enumerate(intervals)}
        for i, (paid, terminal) in settlements.items():
            # A retrospectively compounded terminal return is not a signal
            # before its payment date, even with no original release stamp.
            t = closing_rows[terminal]
            published = available[t, i]
            available[t, i] = (np.datetime64(paid) if np.isnat(published)
                               else max(published, np.datetime64(paid)))
    signals = load_signals(root, as_of, assets, origins, version)
    return assets, panel, available, signals, macro_signals(root,version,origins), caps, settlements


def merger_settlements(db, pit, intervals, assets, panel):
    """Link final merger payments to the last CIZ total-return month."""
    path = pit / "wrds_delistings.parquet"
    manifest = json.loads((pit.parent / "report.json").read_text())
    expected = next(row["file_hash"] for row in manifest["datasets"]
                    if row["dataset"] == "wrds_delistings")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError("Merger settlement input hash mismatch")
    rows = db.execute(
        """select instrument, last_day(observation_date), max(amount_date)
           from read_parquet(?)
           where observation_date between ? and ? and delactiontype='MER'
           group by 1,2
           having count(*)=1 and count(*) filter (
             where delstatustype='FPAY' and delpaymenttype in ('CASH','CST','STK')
               and delretmisstype='NA' and isfinite(delisting_return)
               and isfinite(distribution_amount) and distribution_amount>0
               and amount_date>=observation_date
               and (availability_time is null or cast(availability_time as date)<=amount_date)
           )=1""",
        [str(path), intervals[0][0], intervals[-1][1]]).fetchall()
    month_index = {(end.year, end.month): t for t, (_, end) in enumerate(intervals)}
    stock_index = {a["instrument"]: i for i, a in enumerate(assets) if a["category"] == "stock"}
    settlements = {}
    for instrument, month, payment in rows:
        i, t = stock_index.get(instrument), month_index.get((month.year, month.month))
        if i is not None and t is not None and np.isfinite(panel[t, i]):
            # A final value whose settlement is later than the next valuation
            # remains outside this monthly cash-at-terminal-value convention.
            next_valuation = intervals[min(t+1, len(intervals)-1)][1]
            if payment <= next_valuation:
                terminal_close = intervals[t][1]
                settlements[i] = max(terminal_close, payment), terminal_close
    return settlements


def replay(root, data, mandate, report, aversion, construct, as_of, etfs):
    _, intervals, _, rf, version, first, _, *_ = data
    assets, panel, available, signals, macro, caps, settlements = archive(
        root, tuple(intervals), first, etfs, version, as_of)
    states, failed = {}, {}
    for t in range(first,len(intervals)):
        day, next_close = intervals[t]
        if (t-first) % REFIT_MONTHS == 0:
            end = t-EXECUTION_LAG_MONTHS
            origin = intervals[end][0]
            window = slice(end-ESTIMATION_MONTHS,end)
            history = panel[window]
            idx = eligible_indices(assets, history, available[window], origin, caps.get(origin, {}))
            idx = idx[[i not in settlements or settlements[i][0] > origin for i in idx]]
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
        closed = np.array([i for i, (paid, terminal) in settlements.items()
                           if terminal <= day and paid <= next_close], dtype=int)
        exited[closed] = True
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
            holdings = state["holdings"]
            # Terminal total return is already in NAV. Converting its value to
            # cash at monthly resolution is a corporate action, not a trade.
            holdings[-1] += holdings[closed].sum()
            holdings[closed] = 0
            h, delta, _ = execute(holdings, target, .001)
            missing = np.flatnonzero((h[:-1] > 0) & ~np.isfinite(observed))
            if len(missing):
                ids = ", ".join(assets[i]["id"] for i in missing[:5])
                if len(missing) > 5:
                    ids += f" (+{len(missing)-5})"
                failed[key] = f"{day}: missing observed return for a held security through {next_close} ({ids})"
                del states[key]
                continue
            # Missing observations for zero positions contribute no P&L.
            h[:-1] *= 1+np.where(np.isfinite(observed),observed,0)
            h[-1] *= 1+rf[t]
            state["returns"].append(float(h.sum()/opening-1))
            state["turnover"].append(float(abs(delta).sum()/(2*opening)))
            state["holdings"] = h
    return states, failed
