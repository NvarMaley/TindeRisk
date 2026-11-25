"""Download a fixed public index archive before matching ticker strings entirely offline."""

import csv
from datetime import datetime, timezone
import json
import tempfile
from pathlib import Path
from urllib.request import urlopen

import duckdb
from fetch_public_universe_data import ROOT, immutable_save

URL = "https://dataset.aethereal.top/files/sp500-stock-prices.parquet"


def audit(path):
    dest = ROOT / "data/raw/public_equity_refresh"
    db = duckdb.connect()
    samples = db.execute(
        """select ticker,count(*),min(date),max(date),count(distinct date)
              from read_parquet(?) where date >= '2026-01-01' and cast(date as date) <= current_date
              and close>0 and isfinite(close) and volume >=0 group by ticker""",
        [str(path)],
    ).fetchall()
    covered = {t for t, n, a, b, u in samples if n == u}
    if not covered:
        raise ValueError("No valid public ticker series")
    report = json.loads((ROOT / "data/processed/universe/crsp_monthly_audit.json").read_text())
    cohort = set(report["selected_permnos"])
    names = {}
    (folder,) = (p for p in (ROOT / "data").iterdir() if p.name.strip() == "new data")
    with (folder / "data_plus/raw/wrds/crsp_msf.csv").open() as stream:
        for row in csv.DictReader(stream):
            if row["PERMNO"] in cohort and row["MthCalDt"] == report["snapshot_date"]:
                names.setdefault(row["PERMNO"], set()).add(row["Ticker"])
    matches = sum(len(v) == 1 and next(iter(v)) in covered for v in names.values())
    record = dict(
        source=URL,
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
        tickers=len(covered),
        last=str(max(r[3] for r in samples)),
        cohort=len(cohort),
        ticker_matches=matches,
        kind="Current-index sample; ticker matches only, no historical index or issuer continuity inference.",
        file=immutable_save(dest, "sp500", path.read_bytes(), "parquet"),
    )
    immutable_save(dest, "receipt", json.dumps(record, indent=2).encode(), "json")
    print(record["tickers"], matches, record["last"])


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "prices.parquet"
        with urlopen(URL, timeout=90) as r:
            data = r.read(100_000_001)
        if len(data) > 100_000_000:
            raise ValueError("Oversized archive")
        path.write_bytes(data)
        audit(path)
