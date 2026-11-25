"""Compare issuer-reported current holdings against Treasury identity metadata.

Never writes investability approvals or backfills historical holdings.
"""
from collections import Counter
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import tempfile

from fetch_issuer_holdings import bil_rows

ROOT=Path(__file__).resolve().parents[1]


def classify(name, asset_class, identifier, currency, as_of, treasury):
    if currency!="USD":return "other_currency"
    if name in {"USD CASH","US DOLLAR"} and asset_class=="Cash":return "ancillary_usd_cash"
    if asset_class=="Money Market":return "money_market_not_direct_treasury"
    if identifier.startswith("US") and len(identifier)==12:identifier=identifier[2:11]
    row=treasury.get(identifier)
    if not row:return "unresolved_identity"
    if row["first_observed_record_date"]<=as_of and row["first_observed_issue_date"]<=as_of<row["maturity"]:
        return "direct_treasury_identity_matched"
    return "unresolved_date"


def inspect_snapshot(ticker, content, as_of, treasury):
    if ticker=="BIL":
        rows=bil_rows(content);header=next(i for i,r in enumerate(rows) if {"Name","Identifier","Weight","Local Currency"}<=set(r))
        parsed=[]
        for r in rows[header+1:]:
            if len(r)<len(rows[header]) or not r[0]:continue
            d=dict(zip(rows[header],r))
            try:w=Decimal(d["Weight"])
            except (InvalidOperation,KeyError):continue
            if not w.is_finite():continue
            cls="Cash" if d["Name"]=="US DOLLAR" else "Money Market" if "MONEY MARKET" in d["Name"] else "Unclassified"
            parsed.append((d["Name"],cls,d["Identifier"],d["Local Currency"],w))
    else:
        rows=list(csv.reader(io.StringIO(content.decode("utf-8-sig"))));header=next(i for i,r in enumerate(rows) if {"Name","Asset Class","CUSIP","Weight (%)","Currency"}<=set(r))
        parsed=[]
        for r in rows[header+1:]:
            if len(r)!=len(rows[header]) or not r[0].strip():continue
            d=dict(zip(rows[header],r))
            try:w=Decimal(d["Weight (%)"].replace(",",""))
            except (InvalidOperation,KeyError):raise ValueError("Invalid weight in reported holding")
            if not w.is_finite():raise ValueError("Invalid weight")
            parsed.append((d["Name"],d["Asset Class"],d["CUSIP"],d["Currency"],w))
    counts=Counter();weights=Counter()
    for name,cls,identifier,currency,w in parsed:
        k=classify(name,cls,identifier,currency,as_of,treasury);counts[k]+=1;weights[k]+=w
    return {"ticker":ticker,"published_as_of":as_of,"rows":len(parsed),"classification_counts":dict(counts),
            "money_market_weight_pct":float(weights["money_market_not_direct_treasury"]),
            "strict_direct_treasury_snapshot_pass":bool(parsed and set(counts)<={"direct_treasury_identity_matched","ancillary_usd_cash"} and counts["direct_treasury_identity_matched"]),
            "status":"current_snapshot_only_not_allocation_approval"}


def main():
    base=ROOT/"data/raw/issuer_holdings";chosen={}
    for f in base.glob("*/receipt-*.json"):
        for r in json.loads(f.read_text())["receipts"]:
            if r["status"]!="snapshot_schema_checked_not_eligibility_verified":continue
            old=chosen.get(r["ticker"])
            if old is None or r["retrieved_at_utc"]>old[1]["retrieved_at_utc"]:chosen[r["ticker"]]=(f.parent,r)
    identity=json.loads((ROOT/"data/processed/universe/treasury_identity.json").read_text())
    treasury={r["cusip"]:r for r in identity["rows"]};results=[]
    for parent,r in chosen.values():
        path=parent/r["file"]["file"]
        if path.name!=r["file"]["file"]:raise ValueError("Invalid path")
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r["file"]["sha256"]:raise ValueError("Snapshot hash mismatch")
        result=inspect_snapshot(r["ticker"],raw,r["published_as_of"],treasury);results.append(result)
        print(result["ticker"],result["published_as_of"],result["classification_counts"],"money market",result["money_market_weight_pct"],"strict snapshot",result["strict_direct_treasury_snapshot_pass"])
    dest=ROOT/"data/processed/universe/issuer_holdings_audit.json"
    with tempfile.NamedTemporaryFile(mode="w",dir=dest.parent,delete=False,encoding="utf-8") as f:
        json.dump({"schema":"issuer-holdings-audit-v1","built_at_utc":datetime.now(timezone.utc).isoformat(),"snapshots":results},f,indent=2);temp=Path(f.name)
    temp.replace(dest)


if __name__=="__main__":main()
