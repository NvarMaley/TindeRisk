"""Retain reported US-GAAP facts for exact original filings while preserving period duration."""

import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile

import duckdb
from fetch_edgar_archive import ARCHIVE
from fetch_public_universe_data import ROOT, immutable_save

TAGS = (
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "NetIncomeLoss",
    "NetCashProvidedByUsedInOperatingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
)


def main():
    dest = ROOT / "data/processed/universe/filing_dates"
    receipt = json.loads(
        max(dest.glob("receipt-*.json"), key=lambda p: p.stat().st_mtime_ns).read_text()
    )
    with (
        duckdb.connect(str(ARCHIVE), read_only=True) as db,
        tempfile.TemporaryDirectory(dir=dest) as temp,
    ):
        result = {}
        for name, entry in receipt["match"].items():
            source = dest / entry["file"]["file"]
            path = Path(temp) / (name + ".parquet")
            db.execute(
                """copy (select f.gvkey,f.adsh,f.accepted,f.period,n.tag,n.version,n.qtrs,n.uom,n.value
                        from read_parquet(?) f join numbers n using (adsh)
                        where n.ddate=f.period and n.tag in (select unnest(?)) and n.version like 'us-gaap/%'
                        and n.segments is null and n.coreg is null and n.uom='USD' and isfinite(n.value))
                        to ? (format parquet)""",
                [str(source), list(TAGS), str(path)],
            )
            rows, filings = db.execute(
                "select count(*),count(distinct adsh) from read_parquet(?)", [str(path)]
            ).fetchone()
            result[name] = dict(
                rows=rows,
                filings=filings,
                file=immutable_save(dest, name + "-original", path.read_bytes(), "parquet"),
            )
    immutable_save(
        dest,
        "facts",
        json.dumps(
            dict(acquired_at_utc=datetime.now(timezone.utc).isoformat(), tags=TAGS, tables=result),
            indent=2,
        ).encode(),
        "json",
    )
    print({k: (v["rows"], v["filings"]) for k, v in result.items()})


if __name__ == "__main__":
    main()
