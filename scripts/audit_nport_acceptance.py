"""Match fund filings to acceptance instants in the local SEC index by CIK and accession."""

import csv
from datetime import datetime, timezone
import gzip
import io
import json

import duckdb
from fetch_public_universe_data import ROOT, immutable_save

RAW = ROOT / "data/raw"


def main():
    folder = RAW / "nport_research_mirror"
    index = RAW / "sec_filing_index"
    receipt = json.loads(
        max(index.glob("receipt-*.json"), key=lambda p: p.stat().st_mtime_ns).read_text()
    )
    market_index = index / ("filings-" + receipt["sha256"][:16] + ".parquet")
    funds = json.loads(
        max(folder.glob("receipt-*.json"), key=lambda p: p.stat().st_mtime_ns).read_text()
    )["funds"]
    db = duckdb.connect()
    db.execute("set timezone='UTC'")
    db.execute("create table targets(ticker varchar,cik bigint,accession varchar,reported date)")
    for fund in funds:
        with gzip.open(folder / fund["filings"]["file"]["file"]) as stream:
            rows = json.load(stream)
        db.executemany(
            "insert into targets values (?,?,?,?)",
            [
                (fund["ticker"], int(r["registrant_cik"]), r["accession_number"], r["report_date"])
                for r in rows
            ],
        )
    results = db.execute(
        """select distinct t.*,i.filingDate,i.acceptanceDateTime,i.timestamp_provenance from targets t
                          left join read_parquet(?) i on t.cik=try_cast(i.cik as bigint) and t.accession=i.accessionNumber
                          order by ticker,reported""",
        [str(market_index)],
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([v[0] for v in results.description])
    values = results.fetchall()
    writer.writerows(values)
    trusted = {"sgml", "live_pair", "snapshot_pair", "cross_cik_pair", "trusted_snapshot_eastern"}
    supported = {r[2] for r in values if r[-1] in trusted and r[-2] and r[-3] >= r[3]}
    dest = ROOT / "data/processed/universe/nport_acceptance"
    file = immutable_save(
        dest, "accepted", gzip.compress(buffer.getvalue().encode(), mtime=0), "csv.gz"
    )
    report = dict(
        file=file,
        filings=len({r[2] for r in values}),
        supported=len(supported),
        source=receipt["source"],
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    immutable_save(dest, "receipt", json.dumps(report, indent=2).encode(), "json")
    print(report["supported"], report["filings"])


if __name__ == "__main__":
    main()
