"""Link filing chronology locally by dated CIK and exact fiscal end; do not date restated values."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

import duckdb
from fetch_public_universe_data import ROOT, immutable_save

SOURCE = "https://huggingface.co/datasets/erlenbusch/sec-edgar/resolve/75008a0c4943e108944d0bc3982a12ab699ad70a/sec_edgar.duckdb"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference",
        action="store_true",
        help="Use the separate SEC index with supported timestamp provenance.",
    )
    args = parser.parse_args()
    dest = (
        ROOT
        / "data/processed/universe"
        / ("filing_reference" if args.reference else "filing_dates")
    )
    archive = ROOT / "data/raw/edgar_as_filed/filing_times_75008a0.parquet"
    delivery = json.loads((ROOT / "data/processed/universe/wrds_delivery.json").read_text())[
        "tables"
    ]
    (folder,) = (p for p in (ROOT / "data").iterdir() if p.name.strip() == "telecharger")
    db = duckdb.connect()
    source = SOURCE
    if args.reference:
        folder_index = ROOT / "data/raw/sec_filing_index"
        receipt = json.loads(
            max(folder_index.glob("receipt-*.json"), key=lambda p: p.stat().st_mtime_ns).read_text()
        )
        archive = folder_index / ("filings-" + receipt["sha256"][:16] + ".parquet")
        source = receipt["source"]
        db.execute("set timezone='America/New_York'")
        db.execute(
            """create temp table filings as select distinct accessionNumber as adsh,try_cast(cik as bigint) as cik,
                   form,reportDate period,filingDate filed,acceptanceDateTime accepted,timestamp_provenance
                   from read_parquet(?) where form in ('10-K','10-Q') and reportDate is not null and acceptanceDateTime is not null
                   and timestamp_provenance in ('sgml','live_pair','snapshot_pair','cross_cik_pair','trusted_snapshot_eastern')""",
            [str(archive)],
        )
    else:
        db.execute("create temp table filings as select * from read_parquet(?)", [str(archive)])
    db.execute(
        """create temp table links as select gvkey,try_cast(cik as bigint) cik,
         try_cast(linkdt as date) since,coalesce(try_cast(linkenddt as date),date '9999-12-31') until_date
         from read_csv(?,all_varchar=true) where linktype in ('LU','LC') and linkprim in ('P','C')""",
        [str(folder / delivery["links"]["file"])],
    )
    summary = {}
    for table, form in [("annual", "10-K"), ("quarterly", "10-Q")]:
        db.execute(
            """create or replace temp table periods as select distinct gvkey,try_cast(datadate as date) as period
                   from read_csv(?,all_varchar=true) where try_cast(datadate as date)<=current_date""",
            [str(folder / delivery[table]["file"])],
        )
        db.execute(
            """create or replace temp table matched as with identities as (
            select p.gvkey,p.period,min(l.cik) as cik from periods p join links l
            on p.gvkey=l.gvkey and p.period between l.since and l.until_date group by p.gvkey,p.period
            having count(distinct l.cik)=1)
            select i.*, f.adsh, f.form, f.accepted, f.filed from identities i join filings f using(cik,period)
            where f.form=? and cast(f.accepted as date)>=i.period and f.filed<=current_date
            qualify row_number() over(partition by i.gvkey,i.period order by f.accepted,f.adsh)=1""",
            [form],
        )
        n = db.execute("select count(*) from matched").fetchone()[0]
        total = db.execute("select count(*) from periods").fetchone()[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "matched.parquet"
            db.execute("copy matched to '" + str(path) + "' (format parquet)")
            entry = immutable_save(dest, table, path.read_bytes(), "parquet")
        summary[table] = dict(candidates=total, matched=n, file=entry)
    count, first, last = db.execute("select count(*),min(filed),max(filed) from filings").fetchone()
    with archive.open("rb") as s:
        sha = hashlib.file_digest(s, "sha256").hexdigest()
    record = dict(
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
        source=source,
        file_sha256=sha,
        rows=count,
        first=str(first),
        last=str(last),
        match=summary,
    )
    immutable_save(dest, "receipt", json.dumps(record, indent=2).encode(), "json")
    print(count, [(k, v["matched"], v["candidates"]) for k, v in summary.items()])


if __name__ == "__main__":
    main()
