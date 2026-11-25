"""Look up an exact version in the local, metadata-only source inventory."""

from pathlib import Path

import duckdb


def inventory_snapshot(database: Path, request):
    result = {
        "provider": request.provider,
        "dataset_version": request.dataset_version,
        "as_of": request.as_of.isoformat(),
        "status": "version_unavailable",
    }
    if not database.is_file():
        return result | {"status": "inventory_unavailable"}
    with duckdb.connect(str(database), read_only=True) as db:
        rows = db.execute(
            """select local_relative_path,sha256,rights_status from source_receipt
            where provider=? and dataset_version=? and cast(retrieved_at_utc at time zone 'UTC' as date)<=?
            order by local_relative_path""",
            [request.provider, request.dataset_version, request.as_of],
        ).fetchall()
    if rows:
        return result | {
            "status": "indexed_metadata",
            "files": [{"path": p, "sha256": h, "rights": r} for p, h, r in rows],
        }
    return result


def inventory_counts(database: Path, as_of):
    if not database.is_file():
        return {"available": False, "files": 0, "providers": 0}
    with duckdb.connect(str(database), read_only=True) as db:
        files, providers = db.execute(
            """select count(*), count(distinct provider) from source_receipt
            where cast(retrieved_at_utc at time zone 'UTC' as date) <= ?""", [as_of]
        ).fetchone()
    return {"available": True, "files": files, "providers": providers}
