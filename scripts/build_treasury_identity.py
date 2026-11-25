"""Build a local Treasury issue-identity catalogue, not a secondary price panel."""
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import tempfile
import stat

ROOT=Path(__file__).resolve().parents[1]


def parse_date(value):
    try:return date.fromisoformat(value)
    except (TypeError,ValueError):return None


def identity(row):
    cusip=str(row.get("cusip", "")).strip();typ=row.get("security_type")
    floating=row.get("floating_rate");inflation=row.get("inflation_index_security",row.get("inflation_protected"))
    if typ not in {"Bill","Note","Bond"} or floating!="No" or inflation not in {"Yes","No"}:return None
    if len(cusip)!=9 or not cusip.isalnum() or inflation=="Yes" and typ=="Bill":return None
    issue,maturity,record=map(parse_date,(row.get("issue_date"),row.get("maturity_date"),row.get("record_date")))
    if not issue or not maturity or not record or issue>=maturity:return None
    family="tips" if inflation=="Yes" else {"Bill":"treasury_bill","Note":"treasury_note","Bond":"treasury_bond"}[typ]
    try:
        rate=Decimal(str(row.get("int_rate")))/Decimal(100) if typ!="Bill" else Decimal(0)
        coupon=str(rate.normalize()) if rate.is_finite() and rate>=0 else None
    except (InvalidOperation,TypeError,ValueError):coupon=None
    return cusip,family,issue,maturity,record,coupon


def build(rows,cutoff):
    grouped=defaultdict(list);rejected=0
    for row in rows:
        record=identity(row)
        if record is None or record[4]>cutoff or record[2]>cutoff:rejected+=1;continue
        grouped[record[0]].append(record)
    result=[];conflicts=0
    for cusip,records in grouped.items():
        families={r[1] for r in records};maturities={r[3] for r in records};coupons={r[5] for r in records if r[5] is not None}
        if len(families)!=1 or len(maturities)!=1 or len(coupons)>1:conflicts+=1;continue
        family=next(iter(families));maturity=next(iter(maturities))
        result.append({"cusip":cusip,"issuer":"US_TREASURY","instrument_type":family,"currency":"USD",
                       "first_observed_issue_date":min(r[2] for r in records).isoformat(),"maturity":maturity.isoformat(),
                       "coupon_rate_decimal":next(iter(coupons)) if coupons else None,"first_observed_record_date":min(r[4] for r in records).isoformat(),
                       "not_matured_at_cutoff":maturity>cutoff,"status":"auction_identity_only"})
    result.sort(key=lambda r:r["cusip"])
    return {"schema":"treasury-auction-identity-v1","cutoff":cutoff.isoformat(),"rows":result,"rejected_rows":rejected,"conflicting_cusips":conflicts,"source_status":"public_auction_receipts_not_secondary_market_prices",
            "historical_by_type":dict(Counter(x["instrument_type"] for x in result)),"not_matured_by_type":dict(Counter(x["instrument_type"] for x in result if x["not_matured_at_cutoff"]))}


def verified_rows(root,cutoff):
    chosen={}
    for receipt in root.glob("*/receipt-*.json"):
        if getattr(receipt.stat(),"st_flags",0)&getattr(stat,"SF_DATALESS",0x40000000):continue
        r=json.loads(receipt.read_text());stamp=datetime.fromisoformat(r["acquired_at_utc"])
        if stamp.date()>cutoff:continue
        for d in r["datasets"]:
            if d["dataset"] not in {"auctions_query","treasury_securities_auctions_v2"} or d["status"]!="downloaded_schema_checked_not_normalized":continue
            if d["dataset"] not in chosen or stamp>chosen[d["dataset"]][0]:chosen[d["dataset"]]=(stamp,receipt.parent,d)
    if set(chosen)!={"auctions_query","treasury_securities_auctions_v2"}:raise ValueError("Both historical and current receipts required")
    for _,parent,d in chosen.values():
        for f in d["files"]:
            if Path(f["file"]).name!=f["file"]:raise ValueError("Invalid receipt path")
            path=parent/f["file"]
            if getattr(path.stat(),"st_flags",0)&getattr(stat,"SF_DATALESS",0x40000000):raise ValueError("Materialize auction source in Finder first")
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=f["sha256"]:raise ValueError("Receipt hash mismatch")
            yield from json.loads(raw)["data"]


def main():
    cutoff=date.today();audit=build(verified_rows(ROOT/"data/raw/public_universe",cutoff),cutoff)
    audit["built_at_utc"]=datetime.now(timezone.utc).isoformat()
    dest=ROOT/"data/processed/universe/treasury_identity.json";dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",dir=dest.parent,delete=False,encoding="utf-8") as f:
        json.dump(audit,f,indent=2);temp=Path(f.name)
    temp.replace(dest)
    print("Historical CUSIPs",len(audit["rows"]),audit["historical_by_type"],"not matured",audit["not_matured_by_type"],"conflicts",audit["conflicting_cusips"])


if __name__=="__main__":main()
