from datetime import date, datetime, timezone
from pathlib import Path
import hashlib
import json

from riskmatch.market_data.local_sources import new_data_root, local_market_paths, audit_available_for_as_of, fedinvest_summary
from riskmatch.market_data.source_catalog import catalog, ProviderRequest, request_snapshot, public_receipts, source_report

D=date(2026,11,24)


def test_source_registry_and_unavailable_provider():
    entries=catalog()["entries"]
    assert len(entries)==16 and all(r["required_fields"] and r["rights"] for r in entries)
    r=request_snapshot(ProviderRequest("not_subscribed","v1",D),{})
    assert r["status"]=="provider_unavailable" and r["as_of"]==D.isoformat()


def test_local_resolution_and_no_audit_lookahead(tmp_path):
    path=tmp_path/"data"/"new data ";path.mkdir(parents=True)
    assert new_data_root(tmp_path)==path
    assert local_market_paths(tmp_path)[0][1]==path/"data1/raw"
    assert audit_available_for_as_of({"audited_on":"2026-11-24"},date(2026,11,23)) is None
    report=source_report(D,tmp_path)
    assert report["approved_for_allocation"]==0
    assert next(r for r in report["rows"] if r["id"]=="ETF_DAILY")["status"]=="missing"


def test_public_receipt_verifies_hash_and_cutoff(tmp_path):
    base=tmp_path/"data/raw/public_universe/2026-11-24";base.mkdir(parents=True)
    raw=b"synthetic\n";p=base/"one.csv";p.write_bytes(raw)
    body={"schema":"public-source-receipt-v1","acquired_at_utc":datetime(2026,11,24,tzinfo=timezone.utc).isoformat(),"datasets":[{"dataset":"fixture","status":"downloaded_schema_checked_not_normalized","rows":1,"first_record":"2020-01-01","last_record":"2020-01-01","kind":"synthetic","files":[{"file":p.name,"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}]}]}
    (base/"receipt-fixture.json").write_text(json.dumps(body))
    assert public_receipts(tmp_path,D)["fixture"]["verification"]=="hash_checked"
    assert not public_receipts(tmp_path,date(2026,11,23))
    p.write_bytes(b"tampered\n")
    assert not public_receipts(tmp_path,D)


def test_fedinvest_receipts_and_scope(tmp_path):
    base=tmp_path/"data/raw/fedinvest/2026-11-23";base.mkdir(parents=True)
    raw=b"date,CUSIP,SECURITY TYPE,END OF DAY\n2026-11-23,912345678,TIPS,100\n2026-11-23,912345679,MARKET BASED FRN,100\n2026-11-23,912345680,MARKET BASED BILL,0\n"
    (base/"prices-fixture.csv").write_bytes(raw)
    receipt={"date":"2026-11-23","retrieved_at_utc":"2026-11-24T12:00:00+00:00","rows":3,"file":{"file":"prices-fixture.csv","sha256":hashlib.sha256(raw).hexdigest()}}
    (base/"receipt-fixture.json").write_text(json.dumps(receipt))
    assert fedinvest_summary(D,tmp_path)["scope_positive_eod"]==1
    assert fedinvest_summary(date(2026,11,23),tmp_path) is None
    assert next(r for r in source_report(D,tmp_path)["rows"] if r["id"]=="TREASURY_DAILY")["status"]=="local_partial"
    (base/"prices-fixture.csv").write_bytes(b"tampered")
    assert fedinvest_summary(D,tmp_path) is None


def test_futures_research_audit_respects_cutoff_and_language(tmp_path):
    folder = tmp_path / "data/processed/universe"
    folder.mkdir(parents=True)
    (folder / "research_extensions.json").write_text(json.dumps({
        "audited_on": D.isoformat(),
        "futures": {"roots": 2, "months": 4, "last": "2024-03-28"},
    }))
    def futures(day):
        return next(row for row in source_report(day, tmp_path)["rows"] if row["id"] == "FUTURES")
    assert futures(date(2026, 11, 23))["status"] == "missing"
    assert "2 familles" in futures(D)["evidence_fr"]
    assert futures(D)["allocation_approved"] is False
