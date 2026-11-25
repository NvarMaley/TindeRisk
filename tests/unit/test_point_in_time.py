from datetime import date
from pathlib import Path

import duckdb
import pytest

from riskmatch.market_data.point_in_time import (
    DatedIdentity, Observation, as_of_rows, equity_close, identity_at,
    lagged_feature, require_snapshot, session_close, session_status,
    snapshot_report, store_feature,
)


def test_revision_delay_and_feature_invariance(tmp_path):
    d1, d2 = date(2025, 1, 2), date(2025, 1, 3)
    close = equity_close(d2, 16)
    original = Observation("fixture", "price", d1, equity_close(d1, 16), "v1", 100, "USD")
    revised = Observation("fixture", "price", d1, equity_close(date(2025, 1, 6), 16), "v2", 105, "USD")
    unknown = Observation("fixture", "price", d2, None, "v1", 120, "USD")
    assert as_of_rows([revised, original, unknown], close) == (original,)
    assert as_of_rows([original, revised], revised.available) == (revised,)
    args = dict(instrument="fixture", field="price", session_days=[d1,d2], lag=1, lookback=1, unit="USD")
    feature = lagged_feature([original], close, **args)
    assert feature == lagged_feature([revised, original, unknown], close, **args)
    with pytest.raises(ValueError, match="Missing observation"):
        lagged_feature([revised, unknown], close, **args)
    path = tmp_path / "features.duckdb"
    store_feature(path, feature)
    store_feature(path, feature)
    with duckdb.connect(str(path)) as db:
        assert db.execute("select count(*) from features").fetchone() == (1,)


def test_calendar_cross_market_and_dated_ticker():
    winter, summer = date(2025, 1, 2), date(2025, 7, 3)
    assert equity_close(winter, 16).hour == 21
    assert equity_close(summer, 13).hour == 17
    sessions = {summer: equity_close(summer, 13)}
    assert session_close(summer, sessions).hour == 17
    assert session_status(date(2025, 7, 4), sessions, []) == "closed"
    assert session_status(summer, sessions, []) == "missing"
    first = DatedIdentity("old", "X", winter, summer, equity_close(winter, 16))
    future = DatedIdentity("new", "X", summer, None, equity_close(summer, 16))
    assert identity_at([first, future], "X", equity_close(winter, 16)) == "old"
    with pytest.raises(ValueError, match="Unknown"):
        identity_at([first, future], "X", session_close(summer, sessions))
    assert identity_at([first, future], "X", future.available) == "new"


def test_conflicts_and_snapshot_gate(tmp_path):
    day = date(2025, 1, 2)
    cutoff = equity_close(day, 16)
    rows = [Observation("x", "close", day, cutoff, str(n), n, "USD") for n in (1,2)]
    with pytest.raises(ValueError, match="Conflicting"):
        as_of_rows(rows, cutoff)
    report = snapshot_report(tmp_path, day)
    assert report["reason"] == "snapshot_unavailable"
    with pytest.raises(ValueError, match="market_snapshot_unavailable"):
        require_snapshot(report, ["listed_daily"])
    with pytest.raises(ValueError, match="market_snapshot_unavailable"):
        require_snapshot({"approved": True, "datasets": []}, ["listed_daily"])


def test_normalization_excludes_conflicts_and_preserves_source(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    from build_pit_snapshot import normalize
    source = tmp_path / "fixture.csv"
    content = "instrument,observation_date,close\nX,2025-01-02,1\nX,2025-01-02,1\nY,2025-01-02,2\nY,2025-01-02,3\nZ,2025-01-02,-1\n"
    source.write_text(content)
    with duckdb.connect() as db:
        result = normalize(db, ("fixture", source, "*", "instrument,observation_date", "close>0", "USD"), tmp_path)
        assert (result["rows"], result["duplicates"], result["conflicts"], result["invalid"]) == (1,1,2,1)
        assert db.execute("select availability_time from read_parquet(?)", [str(tmp_path/"fixture.parquet")]).fetchone() == (None,)
    assert source.read_text() == content


def test_snapshot_integrity_and_cutoff(tmp_path):
    import json
    import hashlib
    base = tmp_path / "data/processed/pit"
    base.mkdir(parents=True)
    content = b"synthetic partition"
    datasets = [{"dataset":"fixture","file_hash":hashlib.sha256(content).hexdigest()}]
    key = hashlib.sha256(json.dumps(datasets, sort_keys=True).encode()).hexdigest()
    folder = base / key
    folder.mkdir()
    partition = folder / "fixture.parquet"
    partition.write_bytes(content)
    (base / "report.json").write_text(json.dumps({
        "snapshot_id":key,"built_at":"2025-01-02T00:00:00+00:00","datasets":datasets,"approved":False
    }))
    assert snapshot_report(tmp_path, date(2025,1,1))["reason"] == "snapshot_unavailable"
    assert snapshot_report(tmp_path, date(2025,1,2))["snapshot_id"] == key
    partition.write_bytes(b"changed")
    assert snapshot_report(tmp_path, date(2025,1,2))["reason"] == "snapshot_integrity_failure"
