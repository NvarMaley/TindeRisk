from datetime import date
import json

import duckdb
import pytest

from riskmatch.analytics import descriptive_report as research


def test_client_catalog_retains_assets_without_history(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/universe_catalog.json").write_text(json.dumps({"instruments": [
        {"security_id": "example", "ticker": "EX", "name": "Example Fund", "asset_class": "etf", "source": "https://example.com"}
    ]}))
    monkeypatch.setattr(research, "returns_report", lambda *args: {"datasets": []})
    catalog = research.client_catalog(tmp_path, date(2025, 1, 3))
    asset = catalog["items"][0]
    assert (asset["id"], asset["name"], asset["ticker"], asset["series"]) == ("example", "Example Fund", "EX", [])
    assert not catalog["approved"]


def test_cross_source_comparison_aligns_exact_intervals(tmp_path,monkeypatch):
    path=tmp_path/"fixture.parquet"
    with duckdb.connect() as db:
        db.execute("""copy (select * from (values
            ('A',date '2025-01-01',date '2025-01-02',.01),
            ('A',date '2025-01-02',date '2025-01-03',.02),
            ('B',date '2024-12-31',date '2025-01-02',.03),
            ('B',date '2025-01-02',date '2025-01-03',.04))
            as t(instrument,start_date,end_date,price_return)) to ? (format parquet)""",[str(path)])
    monkeypatch.setattr(research,"selected_source",lambda *args:(path,{"frequency":"daily"}))
    monkeypatch.setattr(research,"descriptive_report",lambda *args:{"datasets":[]})
    result=research.compare_series(tmp_path,[{"source":"one","instrument":"A"},{"source":"two","instrument":"B"}],
        date(2025,1,1),date(2025,1,3),"USD","price_return",date(2025,1,3))
    assert result["matrix"]["count"]==1
    assert result["matrix"]["covariance"] is None
    assert result["assets"][0]["history"][0][1]==pytest.approx(.01)
