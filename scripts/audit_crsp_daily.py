"""Extract only catalog ETF histories from a local CRSP CIZ daily export."""

from datetime import date
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
import pandas as pd
from riskmatch.market_data.local_sources import new_data_root, monthly_audit
from riskmatch.market_data.security_master import load_catalog


def audit(path, monthly, chunksize=500_000):
    before=path.stat(); items={i.ticker:i for i in load_catalog()[1]}
    ids={str(v["permno"]):t for t,v in monthly["etf"].items() if v.get("permno") and v["status"]=="observed_monthly_unvalidated"}
    stock_ids=set(monthly["selected_permnos"]); matched_stocks=set(); parts=[];row_count=0
    cols=["PERMNO","Ticker","DlyCalDt","DlyPrc","DlyRet","DlyBid","DlyAsk","ShrOut"]
    for c in pd.read_csv(path,usecols=cols,chunksize=chunksize,dtype={"PERMNO":str,"Ticker":str,"DlyCalDt":str},low_memory=False):
        row_count+=len(c)
        valid_return=pd.to_numeric(c.DlyRet,errors="coerce").notna()
        matched_stocks.update(c.loc[c.PERMNO.isin(stock_ids)&(c.DlyCalDt==monthly["snapshot_date"])&valid_return,"PERMNO"].dropna())
        selected=c[c.PERMNO.isin(ids)].copy()
        if not selected.empty:
            selected["catalog_ticker"]=selected.PERMNO.map(ids)
            parts.append(selected)
    if not parts:raise ValueError("No catalog ETF rows located")
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError("Source changed during scan")
    panel=pd.concat(parts,ignore_index=True)
    result={};clean=[]
    for t,item in items.items():
        g=panel[panel.catalog_ticker==t].copy()
        boundary=max(item.inception,item.listing_date or item.inception).isoformat()
        prelaunch=int((g.DlyCalDt<boundary).sum());g=g[g.DlyCalDt>=boundary]
        duplicate_count=int(g.duplicated(["PERMNO","DlyCalDt"],keep=False).sum())
        # Do not choose between duplicate rows; exclude them in this preliminary extract.
        g=g[~g.duplicated(["PERMNO","DlyCalDt"],keep=False)]
        returns=pd.to_numeric(g.DlyRet,errors="coerce");valid=g[returns.notna() & (returns>=-1)]
        dates=valid.DlyCalDt.dropna()
        result[t]={"status":"observed_daily_crsp_unvalidated" if len(dates) else "missing", "first":dates.min() if len(dates) else None,"last":dates.max() if len(dates) else None,"observed_days":int(dates.nunique()),"duplicate_rows_excluded":duplicate_count,"prelaunch_rows_excluded":prelaunch}
        clean.append(valid)
    return {"schema":"crsp-daily-audit-v1","audited_on":date.today().isoformat(),"source_size":before.st_size,"source_mtime_ns":before.st_mtime_ns,"source_rows":row_count,"etf":result,"observed_etfs":sum(v["status"]=="observed_daily_crsp_unvalidated" for v in result.values()),"stock_snapshot_count_with_return":len(matched_stocks),"snapshot_date":monthly["snapshot_date"],"status":"local_unvalidated","limitations":["no_volume_field","no_verified_historical_availability","no_calendar_reconciliation","no_cross_vendor_splicing","no_holdings_validation"]},pd.concat(clean,ignore_index=True)


def main():
    new=new_data_root();monthly=monthly_audit()
    if not new or not monthly:raise SystemExit("Run monthly audit first")
    result,panel=audit(new/"data_plus/raw/wrds/crsp_dsf.csv",monthly)
    dest=ROOT/"data/processed/universe";dest.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",dir=dest,delete=False,encoding="utf-8") as f:
        panel.to_csv(f,index=False);temp=Path(f.name)
    temp.replace(dest/"crsp_etf_daily_extract.csv")
    with tempfile.NamedTemporaryFile(mode="w",dir=dest,delete=False,encoding="utf-8") as f:
        json.dump(result,f,indent=2);temp=Path(f.name)
    temp.replace(dest/"crsp_daily_audit.json")
    print(f"Daily CRSP ETF coverage: {result['observed_etfs']}/{len(result['etf'])}; selected stock snapshot with daily return: {result['stock_snapshot_count_with_return']}. Local only.")


if __name__=="__main__":main()
