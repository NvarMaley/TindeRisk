"""Optional official EODHD price update adapter; requires the user's authorized API token.

No account creation, paid plan, data splicing or credential logging.
"""
import argparse
from datetime import date, datetime, timezone
import json
from math import isfinite
import os
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fetch_public_universe_data import immutable_save

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from riskmatch.market_data.security_master import load_catalog


def validate_response(raw,start,end):
    rows=json.loads(raw)
    if not isinstance(rows,list) or not rows:raise ValueError("Empty or non-data response")
    dates=set()
    for row in rows:
        if not {"date","open","high","low","close","adjusted_close","volume"}<=set(row):raise ValueError("Missing EOD fields")
        d=date.fromisoformat(row["date"])
        if d in dates or not start<=d<=end:raise ValueError("Duplicate or outside requested dates")
        dates.add(d)
        for key in ("open","high","low","close","adjusted_close"):
            x=row[key]
            if not isinstance(x,(int,float)) or not isfinite(x) or x<=0:raise ValueError("Invalid price")
        if not isinstance(row["volume"],(int,float)) or not isfinite(row["volume"]) or row["volume"]<0:raise ValueError("Invalid volume")
    return {"rows":len(rows),"first":min(dates).isoformat(),"last":max(dates).isoformat()}


def main():
    p=argparse.ArgumentParser();p.add_argument("--ticker",action="append");p.add_argument("--from",dest="start",default="2026-01-01");p.add_argument("--to",dest="end",default=date.today().isoformat());p.add_argument("--max-requests",type=int,default=18);args=p.parse_args()
    token=os.getenv("EODHD_API_TOKEN")
    if not token:raise SystemExit("EODHD_API_TOKEN is not configured. Obtain your own authorized API access; no requests made.")
    start,end=map(date.fromisoformat,(args.start,args.end))
    if not start<=end<=date.today() or not 1<=args.max_requests<=20:raise SystemExit("Invalid dates or conservative request cap")
    catalog=[x.ticker for x in load_catalog()[1]];tickers=args.ticker or catalog
    if len(tickers)!=len(set(tickers)) or not set(tickers)<=set(catalog):raise SystemExit("Use unique catalog ETF tickers")
    root=ROOT/"data/raw/eodhd"/date.today().isoformat();results=[]
    attempted=0
    for ticker in tickers[:args.max_requests]:
        attempted+=1
        try:
            endpoint=f"https://eodhd.com/api/eod/{ticker}.US";url=endpoint+"?"+urlencode({"api_token":token,"fmt":"json","from":args.start,"to":args.end,"period":"d"})
            # One HTTP request per selected ticker: no retries that could consume a free quota.
            with urlopen(Request(url,headers={"User-Agent":"RiskMatch local research"}),timeout=30) as response:raw=response.read(5_000_001)
            if len(raw)>5_000_000:raise ValueError("Response exceeds bound")
            meta=validate_response(raw,start,end);results.append({"ticker":ticker,"source":endpoint,"status":"schema_checked_not_reconciled",**meta,"file":immutable_save(root,ticker,raw,"json")});print(ticker,"received",meta["rows"],flush=True)
        except HTTPError as exc:
            results.append({"ticker":ticker,"status":"unavailable","error_type":"HTTPError"});print(ticker,"unavailable HTTP",exc.code,flush=True)
            if exc.code in {401,403,429}:break
        except (OSError,ValueError,TypeError,KeyError) as exc:
            results.append({"ticker":ticker,"status":"unavailable","error_type":type(exc).__name__});print(ticker,"unavailable",type(exc).__name__,flush=True)
    receipt={"schema":"eodhd-update-receipt-v1","acquired_at_utc":datetime.now(timezone.utc).isoformat(),"requested_from":args.start,"requested_to":args.end,"datasets":results,"pending_tickers":tickers[attempted:],"rights":"configured subscription terms; local research only; no automatic CRSP splice"}
    immutable_save(root,"receipt",json.dumps(receipt,indent=2).encode(),"json")
    print("Pending tickers:",", ".join(receipt["pending_tickers"]) or "none")


if __name__=="__main__":main()
