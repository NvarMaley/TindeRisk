"""Collect a dated SEC index mirror and extract the fund trusts' earlier filing references."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.request import urlopen

import duckdb
from fetch_public_universe_data import ROOT, immutable_save, request

DEST = ROOT / "data/raw/sec_filing_index"
BASE = "https://api.github.com/repos/iangow/sec_submissions_data/releases"


def main():
    release = json.loads(request(BASE + "/latest"))
    (asset,) = (r for r in release["assets"] if r["name"] == "filings.parquet")
    digest = asset["digest"].removeprefix("sha256:")
    if len(digest) != 64:
        raise ValueError("Release has no SHA-256 fingerprint")
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST / ("filings-" + digest[:16] + ".parquet")
    if not path.exists():
        with tempfile.TemporaryDirectory(dir=DEST) as temp:
            partial = Path(temp) / "filings.parquet"
            with (
                urlopen(asset["browser_download_url"], timeout=100) as response,
                partial.open("wb") as stream,
            ):
                shutil.copyfileobj(response, stream, 1024 * 1024)
            with partial.open("rb") as stream:
                if (
                    partial.stat().st_size != asset["size"]
                    or hashlib.file_digest(stream, "sha256").hexdigest() != digest
                ):
                    raise ValueError("Incomplete reference index")
            partial.replace(path)
    with duckdb.connect() as db:
        total = db.execute("select count(*) from read_parquet(?)", [str(path)]).fetchone()[0]
        targets = json.loads((ROOT / "configs/sec_nport_targets.json").read_text())["targets"]
        trusts = sorted({int(t["cik"]) for t in targets})
        with tempfile.TemporaryDirectory(dir=DEST) as temp:
            refs = Path(temp) / "references.parquet"
            db.execute(
                """copy (select * from read_parquet(?) where try_cast(cik as bigint) in (select unnest(?))
                        and filingDate < date '2019-10-01' and form in ('N-Q','N-Q/A','N-CSR','N-CSRS'))
                        to ? (format parquet)""",
                [str(path), trusts, str(refs)],
            )
            count = db.execute("select count(*) from read_parquet(?)", [str(refs)]).fetchone()[0]
            entry = immutable_save(DEST, "legacy-fund-references", refs.read_bytes(), "parquet")
    record = dict(
        source=asset["browser_download_url"],
        revision=release["tag_name"],
        sha256=digest,
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
        rows=total,
        legacy_trust_filings=count,
        legacy_file=entry,
    )
    immutable_save(DEST, "receipt", json.dumps(record, indent=2).encode(), "json")
    print(total, count)


if __name__ == "__main__":
    main()
