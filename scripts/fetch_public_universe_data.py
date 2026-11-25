"""Download public research inputs explicitly; immutable local files, no credentials or Git data."""

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import os
import tempfile
import time
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TREASURY_BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_GROUPS = {
    "rates_fx": ("DTB3", "DGS1MO", "DGS3MO", "DGS2", "DGS5", "DGS10", "DGS30", "DFII5", "DFII10", "DFII30", "DEXSZUS"),
    "macro": ("CPIAUCSL", "INDPRO", "UNRATE", "GDPC1"),
}


def request(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent":"RiskMatch academic local research/1.0"}), timeout=30) as response:
                data=response.read(20_000_001)
                if len(data)>20_000_000:
                    raise ValueError("Response exceeds bounded download size")
                return data
        except HTTPError as exc:
            if exc.code not in {429,500,502,503,504} or attempt==2:
                raise
            delay=exc.headers.get("Retry-After", "")
            wait = 2**attempt
            if delay.isdigit():
                wait = int(delay)
            elif delay:
                try:
                    wait = max(0, parsedate_to_datetime(delay).timestamp() - time.time())
                except (TypeError, ValueError, OverflowError):
                    pass
            if wait > 30:
                raise
            time.sleep(wait)
        except (URLError, TimeoutError):
            if attempt==2: raise
            time.sleep(2**attempt)


def immutable_save(root, name, content, extension):
    digest=hashlib.sha256(content).hexdigest()
    root.mkdir(parents=True,exist_ok=True)
    path=root/f"{name}-{digest[:16]}.{extension}"
    with tempfile.NamedTemporaryFile(dir=root, prefix=".incoming-") as staged:
        staged.write(content)
        staged.flush()
        os.fsync(staged.fileno())
        try:
            os.link(staged.name, path)
        except FileExistsError:
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Existing immutable file fingerprint mismatch") from None
    return {"file":path.name,"sha256":digest,"size":len(content)}


def treasury(root,start,end,endpoint):
    old=endpoint=="auctions_query"
    fields=["record_date","cusip","security_type","security_term" if old else "security_desc","issue_date","maturity_date","int_rate","high_yield","floating_rate","announcemt_date", "price_per100" if old else "price_per_amt", "inflation_index_security" if old else "inflation_protected"]
    pages=[];dates=[];count=0;expected=None;page=1
    while True:
        args={"filter":f"record_date:gte:{start},record_date:lte:{end}","sort":"record_date,cusip","page[size]":1000,"page[number]":page}
        # The legacy endpoint rejects field projection; preserve its complete raw schema.
        if not old:args["fields"]=",".join(fields)
        url=TREASURY_BASE+endpoint+"?"+urlencode(args)
        content=request(url); payload=json.loads(content); rows=payload.get("data")
        if not isinstance(rows,list):raise ValueError("Invalid Treasury API response")
        meta=payload["meta"]
        if expected is None:expected=int(meta["total-count"])
        if expected!=int(meta["total-count"]):raise ValueError("Treasury pagination count changed")
        for r in rows:
            if not set(fields)<=set(r) or not start<=r["record_date"]<=end:raise ValueError("Treasury schema or date outside requested interval")
            dates.append(r["record_date"])
        count+=len(rows)
        pages.append(immutable_save(root,f"{endpoint}-page-{page:03}",content,"json"))
        if page>=int(meta["total-pages"]):break
        if page>=100 or not rows:raise ValueError("Incomplete Treasury pagination")
        page+=1;time.sleep(.25)
    if count!=expected:raise ValueError("Treasury pagination incomplete")
    return {"dataset":endpoint,"source":TREASURY_BASE+endpoint,"rows":count,"first_record":min(dates) if dates else None,"last_record":max(dates) if dates else None,"files":pages,"kind":"auction_records_not_secondary_market_prices","status":"downloaded_schema_checked_not_normalized"}


def fred_series(root,start,end,group,series):
    url=FRED_CSV+"?"+urlencode({"id":series,"cosd":start,"coed":end})
    content=request(url);reader=csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    if not reader.fieldnames or series not in reader.fieldnames:raise ValueError("FRED response schema mismatch")
    date_field=reader.fieldnames[0];rows=list(reader)
    dates=[date.fromisoformat(r[date_field]) for r in rows]
    if not rows or max(dates)>date.fromisoformat(end) or len(dates)!=len(set(dates)):raise ValueError("FRED response dates outside requested cutoff or duplicates")
    return {"dataset":f"fred_{group}_{series}","source":FRED_CSV,"series":series,"rows":len(rows),"first_record":min(dates).isoformat(),"last_record":max(dates).isoformat(),"files":[immutable_save(root,f"fred-{series}",content,"csv")],"kind":"latest_vintage_not_point_in_time","status":"downloaded_schema_checked_not_normalized"}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--start",default="1998-01-01");parser.add_argument("--as-of",default=date.today().isoformat());parser.add_argument("--treasury-only",action="store_true");args=parser.parse_args()
    if not date.fromisoformat(args.start)<=date.fromisoformat(args.as_of)<=date.today():raise SystemExit("Invalid acquisition interval")
    root=ROOT/"data/raw/public_universe"/args.as_of;results=[]
    tasks=[("treasury_legacy",lambda:treasury(root,args.start,args.as_of,"auctions_query")),("treasury_v2",lambda:treasury(root,args.start,args.as_of,"treasury_securities_auctions_v2"))]
    if not args.treasury_only:tasks += [(f"fred_{group}_{series}",lambda group=group,series=series:fred_series(root,args.start,args.as_of,group,series)) for group,series_list in FRED_GROUPS.items() for series in series_list]
    for name,fn in tasks:
        try:
            result=fn();results.append(result);print(name,result["status"],result["rows"],flush=True)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            results.append({"dataset":name,"status":"unavailable","error_type":type(exc).__name__});print(name,"unavailable",type(exc).__name__,flush=True)
    manifest={"schema":"public-source-receipt-v1","acquired_at_utc":datetime.now(timezone.utc).isoformat(),"requested_start":args.start,"requested_end":args.as_of,"datasets":results,"rights":"local research only; source-specific redistribution rights require review"}
    immutable_save(root,"receipt",json.dumps(manifest,indent=2).encode(),"json")


if __name__=="__main__":main()
