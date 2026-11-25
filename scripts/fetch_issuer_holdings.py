"""Fetch the five Treasury ETF current holdings from public issuer download links.

Raw snapshots are local-only, not historical holdings certification.
"""
import csv
from datetime import datetime, timezone, date
import io
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

from fetch_public_universe_data import request, immutable_save

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
    "SHY":"https://www.ishares.com/us/products/239452/ishares-1-3-year-treasury-bond-etf/latest-holdings.csv",
    "IEF":"https://www.ishares.com/us/products/239456/ishares-7-10-year-treasury-bond-etf/latest-holdings.csv",
    "TLT":"https://www.blackrock.com/us/individual/products/239454/ishares-20%2B-year-treasury-bond-etf/latest-holdings.csv",
    "TIP":"https://www.ishares.com/us/products/239467/ishares-tips-bond-etf/latest-holdings.csv",
    "BIL":"https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-bil.xlsx",
}


def csv_snapshot(content):
    rows=list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
    dates=[r[1] for r in rows if len(r)>1 and r[0].strip()=="Fund Holdings as of"]
    if len(dates)!=1:raise ValueError("Missing published holdings date")
    try:
        as_of=date.fromisoformat(dates[0])
    except ValueError:
        as_of=datetime.strptime(dates[0],"%b %d, %Y").date()
    if as_of>date.today():raise ValueError("Future holdings data")
    header=next((i for i,r in enumerate(rows) if {"Name","Asset Class","CUSIP","Weight (%)"}<=set(r)),None)
    if header is None:raise ValueError("Holdings schema changed")
    records=[dict(zip(rows[header],r)) for r in rows[header+1:] if len(r)==len(rows[header]) and r[0].strip()]
    if not records:raise ValueError("No holdings rows")
    return as_of.isoformat(),len(records),sorted(set(r["Asset Class"] for r in records))


def bil_rows(content):
    ns={"x":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        for name in ("xl/sharedStrings.xml","xl/worksheets/sheet1.xml"):
            if z.getinfo(name).file_size>10_000_000:raise ValueError("XLSX part exceeds bound")
        strings=["".join(i.itertext()) for i in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("x:si",ns)]
        rows=[]
        for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//x:row",ns):
            vals=[]
            for c in row.findall("x:c",ns):
                v=c.find("x:v",ns);s=v.text if v is not None else ""
                vals.append(strings[int(s)] if c.get("t")=="s" and s else s)
            rows.append(vals)
    return rows


def bil_snapshot(content):
    rows=bil_rows(content)
    if not any(r[:2]==["Ticker Symbol:","BIL"] for r in rows):raise ValueError("Unexpected fund")
    dates=[r[1].removeprefix("As of ") for r in rows if len(r)>1 and r[0]=="Holdings:"]
    if len(dates)!=1:raise ValueError("Missing BIL date")
    as_of=datetime.strptime(dates[0],"%d-%b-%Y").date()
    if as_of>date.today():raise ValueError("Future holdings data")
    header=next((i for i,r in enumerate(rows) if {"Name","Identifier","Weight","Local Currency"}<=set(r)),None)
    if header is None:raise ValueError("BIL schema changed")
    records=[r for r in rows[header+1:] if len(r)>=len(rows[header]) and r[0] and r[1]]
    if not records:raise ValueError("No BIL holdings rows")
    return as_of.isoformat(),len(records)


def main():
    root=ROOT/"data/raw/issuer_holdings"/date.today().isoformat();receipts=[]
    for ticker,url in SOURCES.items():
        try:
            data=request(url)
            if ticker=="BIL":
                as_of,n=bil_snapshot(data)
                info={"published_as_of":as_of,"rows":n,"status":"snapshot_schema_checked_not_eligibility_verified"};ext="xlsx"
            else:
                as_of,n,classes=csv_snapshot(data)
                info={"published_as_of":as_of,"rows":n,"asset_classes_reported":classes,"status":"snapshot_schema_checked_not_eligibility_verified"};ext="csv"
            receipt={"ticker":ticker,"source":url,"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),**info,"file":immutable_save(root,ticker,data,ext)}
            receipts.append(receipt);print(ticker,info["status"],info["published_as_of"],info["rows"],flush=True)
        except (OSError,ValueError,TypeError,zipfile.BadZipFile) as exc:
            receipts.append({"ticker":ticker,"source":url,"status":"unavailable","error_type":type(exc).__name__});print(ticker,"unavailable",type(exc).__name__,flush=True)
    immutable_save(root,"receipt",json.dumps({"schema":"issuer-holdings-receipt-v1","receipts":receipts,"rights":"local research only; historical verification and redistribution rights pending"},indent=2).encode(),"json")


if __name__=="__main__":main()
