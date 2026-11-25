"""Explicit local-only streaming audit of the supplied CRSP CIZ monthly export."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
from riskmatch.market_data.local_sources import new_data_root
from riskmatch.market_data.security_master import load_catalog


def audit(path, snapshot_date, target=1000, chunksize=200_000):
    if not 300 <= target <= 3000:
        raise ValueError("Target must be 300–3000")
    before = path.stat()
    items = {i.ticker: i for i in load_catalog()[1]}
    stats = {t: {"ids": set(), "months": set(), "rows": 0, "prelaunch": 0} for t in items}
    stock = {}; conflicts = set(); row_count=0
    cols = ["PERMNO", "Ticker", "SecurityType", "SecuritySubType", "ShareType", "USIncFlg", "IssuerType", "MthCalDt", "MthCap", "MthRet"]
    for c in pd.read_csv(path, usecols=cols, chunksize=chunksize, dtype={"PERMNO": str, "Ticker": str, "MthCalDt": str}, low_memory=False):
        row_count += len(c)
        etf = c[c.Ticker.isin(items) & (c.SecuritySubType == "ETF") & pd.to_numeric(c.MthRet, errors="coerce").notna()]
        for t, g in etf.groupby("Ticker"):
            boundary = max(items[t].inception, items[t].listing_date or items[t].inception).isoformat()
            s = stats[t]
            s["prelaunch"] += int((g.MthCalDt < boundary).sum())
            g = g[g.MthCalDt >= boundary]
            s["ids"].update(g.PERMNO.dropna())
            s["months"].update(g.MthCalDt.dropna())
            s["rows"] += len(g)
        cap = pd.to_numeric(c.MthCap, errors="coerce")
        eligible = c[(c.MthCalDt == snapshot_date) & (c.SecurityType == "EQTY") & (c.SecuritySubType == "COM") &
                     (c.ShareType == "NS") & (c.USIncFlg == "Y") & c.IssuerType.isin(["CORP", "ACOR"]) & (cap > 0)]
        for _, row in eligible.iterrows():
            if pd.isna(row.PERMNO):
                continue
            value = float(row.MthCap)
            if row.PERMNO in stock and stock[row.PERMNO] != value:
                conflicts.add(row.PERMNO)
            stock[row.PERMNO] = value
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Source changed during audit")
    for p in conflicts:
        stock.pop(p, None)
    ranked = sorted(stock, key=lambda p: (-stock[p], p))[:target]
    etfs = {}
    for t, s in stats.items():
        months = sorted(s["months"])
        etfs[t] = {"status": "observed_monthly_unvalidated" if months and len(s["ids"]) == 1 else "missing_or_ambiguous",
                   "first": months[0] if months else None, "last": months[-1] if months else None,
                   "observed_months": len(months), "rows": s["rows"], "identity_count": len(s["ids"]),
                   "prelaunch_rows_rejected": s["prelaunch"], "permno": next(iter(s["ids"])) if len(s["ids"])==1 else None}
    return {"schema":"crsp-monthly-audit-v1", "audited_on":date.today().isoformat(), "source_size":before.st_size,
            "source_mtime_ns":before.st_mtime_ns,"source_rows":row_count,"snapshot_date":snapshot_date,
            "etf":etfs,"observed_etfs":sum(v["status"]=="observed_monthly_unvalidated" for v in etfs.values()),
            "stock_candidate_count":len(stock),"conflicting_stock_ids":len(conflicts),"selected_count":len(ranked),
            "selected_permnos":ranked,"target":target,"status":"local_research_not_pit_validated",
            "limitations":["rank_only_raw_market_cap_units", "no_publication_timestamp", "no_verified_listing_liquidity_or_delisting_gate", "no_daily_coverage_claim"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot",default="2025-12-31")
    parser.add_argument("--target",type=int,default=1000)
    args=parser.parse_args(); date.fromisoformat(args.snapshot)
    new = new_data_root()
    if new is None:
        raise SystemExit("New data directory missing or ambiguous")
    result = audit(new / "data_plus/raw/wrds/crsp_msf.csv",args.snapshot,args.target)
    dest = ROOT / "data/processed/universe/crsp_monthly_audit.json";dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",dir=dest.parent,delete=False,encoding="utf-8") as out:
        json.dump(result,out,indent=2); temp=Path(out.name)
    temp.replace(dest)
    print(f"Monthly ETF coverage: {result['observed_etfs']}/{len(result['etf'])}; preliminary stock count: {result['stock_candidate_count']}; selected {result['selected_count']}. Local audit only.")


if __name__ == "__main__":
    main()
