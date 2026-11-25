"""Acquire the pinned bulk EDGAR mirror and verify its published LFS SHA before use."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.request import urlopen

import duckdb
from fetch_public_universe_data import ROOT, immutable_save

SOURCE = "https://huggingface.co/datasets/erlenbusch/sec-edgar/resolve/75008a0c4943e108944d0bc3982a12ab699ad70a/sec_edgar.duckdb"
SHA256 = "fdfd9c5807dac4725a1fb0b84b42a547be75f9a70d3568280a45930d1776a044"
FOLDER = ROOT / "data/raw/edgar_as_filed"
ARCHIVE = FOLDER / f"sec_edgar-{SHA256[:16]}.duckdb"


def verify(path):
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != SHA256:
            raise ValueError("SEC archive checksum mismatch")


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    if ARCHIVE.is_file():
        verify(ARCHIVE)
    else:
        with tempfile.TemporaryDirectory(dir=FOLDER) as temp:
            path = Path(temp) / "edgar.duckdb"
            with urlopen(SOURCE, timeout=120) as response, path.open("wb") as stream:
                shutil.copyfileobj(response, stream, 1024 * 1024)
            verify(path)
            path.replace(ARCHIVE)
    with duckdb.connect(str(ARCHIVE), read_only=True) as db:
        counts = {
            name: db.execute("select count(*) from " + name).fetchone()[0]
            for name in ("submissions", "numbers", "presentations", "tags")
        }
        dates = FOLDER / "filing_times_75008a0.parquet"
        if not dates.is_file():
            with tempfile.TemporaryDirectory(dir=FOLDER) as temp:
                path = Path(temp) / "dates.parquet"
                db.execute(
                    """copy (select adsh,cik,form,period,filed,accepted from submissions
                            where form in ('10-Q','10-K','10-Q/A','10-K/A') and accepted is not null)
                            to ? (format parquet)""",
                    [str(path)],
                )
                path.replace(dates)
    receipt = dict(
        source=SOURCE,
        sha256=SHA256,
        size=ARCHIVE.stat().st_size,
        tables=counts,
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    immutable_save(FOLDER, "receipt", json.dumps(receipt, indent=2).encode(), "json")
    print(counts)


if __name__ == "__main__":
    main()
