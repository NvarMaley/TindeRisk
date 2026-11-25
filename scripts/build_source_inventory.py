"""Atomically inventory local acquisitions without reading observation values into the catalog."""

import fcntl
import hashlib
import shutil
import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DERIVED = DATA / "processed/universe"
DIGEST = re.compile(r"-([a-f0-9]{16})(?:\.|$)")


def inspect(path, provider, observed, rights):
    before = path.stat()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"Input changed: {path.name}")
    fingerprint = DIGEST.search(path.name)
    if fingerprint and not digest.startswith(fingerprint[1]):
        raise ValueError(f"Filename fingerprint mismatch: {path.name}")
    rel = str(path.relative_to(DATA))
    key = hashlib.sha256((rel + "|" + digest).encode()).hexdigest()
    return (
        key,
        provider,
        digest,
        observed,
        observed.date(),
        rel,
        digest,
        rights,
        "content_verified",
    )


def build():
    DERIVED.mkdir(parents=True, exist_ok=True)
    with (DERIVED / "source_inventory.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _build_locked()


def _build_locked():
    dest = DERIVED / "source_inventory.duckdb"
    now = datetime.now(UTC)
    rows = []
    for group in sorted((DATA / "raw").iterdir()):
        if group.is_dir():
            for file in sorted(group.rglob("*")):
                if file.is_file() and not file.name.startswith("."):
                    rows.append(inspect(file, group.name, now, "source_specific_review"))
    delivery = json.loads((DERIVED / "wrds_delivery.json").read_text())
    (folder,) = (p for p in DATA.iterdir() if p.name.strip() == "telecharger")
    for name, table in sorted(delivery["tables"].items()):
        file = folder / table["file"]
        if file.stat().st_size != table["size"] or file.stat().st_mtime_ns != table["mtime_ns"]:
            raise ValueError(f"WRDS delivery changed: {name}")
        rows.append(inspect(file, "wrds_" + name, now, "institutional_agreement_pending"))
    (folder,) = (p for p in DATA.iterdir() if p.name.strip() == "new data")
    for file in sorted((folder / "data_plus/raw/wrds").glob("*.csv")):
        rows.append(inspect(file, "wrds_" + file.stem, now, "institutional_agreement_pending"))
    if not rows:
        raise ValueError("No acquisitions")
    DERIVED.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DERIVED) as tmp:
        new = Path(tmp) / dest.name
        if dest.exists():
            shutil.copyfile(dest, new)
        with duckdb.connect(str(new)) as db:
            db.execute((ROOT / "configs/data_catalog_schema.sql").read_text())
            db.executemany(
                "insert into source_receipt values (?,?,?,?,?,?,?,?,?) on conflict do nothing", rows
            )
            db.execute("""create or replace view source_versions as select provider,dataset_version,
                min(retrieved_at_utc) as first_verified_at_utc,count(*) as file_count
                from source_receipt group by provider,dataset_version""")
            count = db.execute("select count(*) from source_receipt").fetchone()[0]
        new.replace(dest)
    print(
        f"{len(rows)} acquisitions inspected, {len({r[1] for r in rows})} source groups, {count} versioned file records"
    )


if __name__ == "__main__":
    build()
