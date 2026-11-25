from datetime import date
from pathlib import Path

import duckdb

from riskmatch.market_data.source_catalog import ProviderRequest, request_snapshot
from riskmatch.market_data.source_inventory import inventory_counts


def test_local_inventory_respects_version_and_first_verified_utc_day(tmp_path):
    path = tmp_path / "data/processed/universe/source_inventory.duckdb"
    path.parent.mkdir(parents=True)
    schema = Path(__file__).resolve().parents[2] / "configs/data_catalog_schema.sql"
    with duckdb.connect(str(path)) as db:
        db.execute(schema.read_text())
        db.execute("""insert into source_receipt values
            ('fixture','synthetic','v1','2026-02-01 00:01:00+00','2026-02-01',
             'synthetic.csv','fixture_hash','fixture','content_verified')""")
    first = date(2026, 2, 1)
    earlier = date(2026, 1, 31)
    assert inventory_counts(path, earlier)["files"] == 0
    assert inventory_counts(path, first) == {"available": True, "files": 1, "providers": 1}
    for version, cutoff, expected in (
        ("v1", first, "indexed_metadata"),
        ("v1", earlier, "version_unavailable"),
        ("unknown", first, "version_unavailable"),
    ):
        result = request_snapshot(ProviderRequest("synthetic", version, cutoff), root=tmp_path)
        assert result["status"] == expected
