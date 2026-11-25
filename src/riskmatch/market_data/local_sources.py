"""Local source resolution; never hydrate large cloud placeholders implicitly."""

from pathlib import Path
import json
from datetime import date
from datetime import datetime
import stat
import csv
import hashlib
import io
from decimal import Decimal, InvalidOperation

ROOT = Path(__file__).resolve().parents[3]


def new_data_root(root=ROOT):
    root = Path(root) / "data"
    if not root.is_dir():
        return None
    matches = sorted(p for p in root.iterdir() if p.is_dir() and p.name.strip().casefold() == "new data")
    return matches[0] if len(matches) == 1 else None


def local_market_paths(root=ROOT):
    """Prefer the newly supplied, readable copy; legacy is a fallback, not merged."""
    root = Path(root)
    new = new_data_root(root)
    paths = []
    if new:
        paths.append(("new_data", new / "data1/raw"))
    paths.append(("legacy_data", root / "data/data/raw"))
    return paths


def monthly_audit(root=ROOT):
    """Read a local derived audit only; not raw CRSP records or historical investability."""
    path = Path(root) / "data/processed/universe/crsp_monthly_audit.json"
    try:
        obj = json.loads(path.read_text())
        if obj.get("schema") != "crsp-monthly-audit-v1":
            return None
        new = new_data_root(root)
        if new is None:
            return None
        st = (new / "data_plus/raw/wrds/crsp_msf.csv").stat()
        if obj.get("source_size") != st.st_size or obj.get("source_mtime_ns") != st.st_mtime_ns:
            return None
        return obj
    except (OSError, ValueError, TypeError):
        return None


def daily_audit(root=ROOT):
    path=Path(root)/"data/processed/universe/crsp_daily_audit.json"
    try:
        obj=json.loads(path.read_text());new=new_data_root(root)
        if obj.get("schema")!="crsp-daily-audit-v1" or not new:return None
        st=(new/"data_plus/raw/wrds/crsp_dsf.csv").stat()
        if obj.get("source_size")!=st.st_size or obj.get("source_mtime_ns")!=st.st_mtime_ns:return None
        return obj
    except (OSError,ValueError,TypeError):return None


def audit_available_for_as_of(audit, as_of):
    """Do not leak an audit made after the requested cutoff into a historical view."""
    if not audit:
        return None
    try:
        if date.fromisoformat(audit["audited_on"]) <= as_of:
            return audit
    except (ValueError, KeyError, TypeError):
        pass
    return None


def _derived_summary(path, schema, as_of):
    try:
        if getattr(path.stat(),"st_flags",0)&getattr(stat,"SF_DATALESS",0x40000000):return None
        obj=json.loads(path.read_text())
        if obj.get("schema")!=schema or datetime.fromisoformat(obj["built_at_utc"]).date()>as_of:return None
        return obj
    except (OSError,ValueError,TypeError,KeyError):return None


def membership_summary(as_of, root=ROOT):
    path = Path(root) / "data/processed/universe/universe_membership_review.json"
    try:
        report = audit_available_for_as_of(json.loads(path.read_text()), as_of)
        if report:
            return {"stock_months": report["stocks"]["months"],
                    "stock_exits": report["stocks"]["exits"],
                    "sovereign_count": report["treasuries"]["latest_confirmed"],
                    "statement_date": report["treasuries"]["last"],
                    "excluded_reports": report["funds"]["excluded_reports"]}
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return None


def treasury_identity_summary(as_of,root=ROOT):
    obj=_derived_summary(Path(root)/"data/processed/universe/treasury_identity.json","treasury-auction-identity-v1",as_of)
    if not obj:return None
    return {"cutoff":obj["cutoff"],"historical_by_type":obj["historical_by_type"],"not_matured_by_type":obj["not_matured_by_type"],"status":obj["source_status"]}


def issuer_holdings_summary(as_of,root=ROOT):
    obj=_derived_summary(Path(root)/"data/processed/universe/issuer_holdings_audit.json","issuer-holdings-audit-v1",as_of)
    return {r["ticker"]:r for r in obj["snapshots"] if date.fromisoformat(r["published_as_of"])<=as_of} if obj else {}


def fedinvest_summary(as_of,root=ROOT):
    """Verify local receipts and distinguish indicative marks from eligibility."""
    base=Path(root)/"data/raw/fedinvest"; snapshots=[]; eligible_types={"MARKET BASED BILL","MARKET BASED NOTE","MARKET BASED BOND","TIPS"}
    for path in sorted(base.glob("*/receipt-*.json")):
        try:
            r=json.loads(path.read_text()); day=date.fromisoformat(r["date"])
            if day>as_of or datetime.fromisoformat(r["retrieved_at_utc"]).date()>as_of:continue
            f=r["file"]; name=f["file"]
            if Path(name).name!=name:continue
            raw=(path.parent/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=f["sha256"]:continue
            rows=list(csv.DictReader(io.StringIO(raw.decode()))); positive=[]
            if len(rows)!=r["rows"] or any(x["date"]!=r["date"] for x in rows):continue
            for x in rows:
                if x["SECURITY TYPE"] not in eligible_types:continue
                try:
                    price=Decimal(x["END OF DAY"])
                    if price.is_finite() and price>0:positive.append(x["CUSIP"])
                except InvalidOperation:continue
            snapshots.append({"date":r["date"],"rows":len(rows),"scope_positive_eod":len(positive)})
        except (OSError,ValueError,KeyError,TypeError):continue
    if not snapshots:return None
    return {"days":len(snapshots),"rows":sum(x["rows"] for x in snapshots),"scope_positive_eod":sum(x["scope_positive_eod"] for x in snapshots),"first":snapshots[0]["date"],"last":snapshots[-1]["date"],"latest":snapshots[-1],"status":"government_valuation_marks_partial_not_approved"}
