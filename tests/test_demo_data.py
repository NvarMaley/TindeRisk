import json

import numpy as np
import pandas as pd

from src.audit_data import audit_asset_sentiment, audit_market_bundle
from src.demo_data import DEMO_PATH, MACRO, NOTICE, TICKERS, load_demo, make_demo


def test_committed_demo_is_reproducible_and_strict_json():
    payload = json.loads(DEMO_PATH.read_text(encoding="utf-8"),
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    assert payload == make_demo(42)
    assert payload["synthetic"] is True
    assert payload["notice"] == NOTICE
    assert DEMO_PATH.stat().st_size < 250_000


def test_demo_satisfies_market_and_sentiment_contracts_offline(monkeypatch):
    import socket

    def no_network(*args, **kwargs):
        raise AssertionError("demo must not use the network")

    monkeypatch.setattr(socket, "create_connection", no_network)
    _, frames, sentiment = load_demo()
    market = audit_market_bundle(frames, TICKERS, MACRO)
    report = audit_asset_sentiment(sentiment, TICKERS[:-1] + ["MARKET"])
    assert market["missing_sessions"] == 0
    assert report["coverage"]["XLK"]["undefined_polarity_rows"] >= 1
    assert np.isfinite(frames["returns"].to_numpy()).all()
    assert len(frames["prices"]) < 756


def test_loading_demo_does_not_write_production_data():
    from src.paths import PROCESSED_DATA

    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in PROCESSED_DATA.iterdir() if p.is_file()}
    _, first, _ = load_demo()
    _, second, _ = load_demo()
    pd.testing.assert_frame_equal(first["returns"], second["returns"])
    after = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in PROCESSED_DATA.iterdir() if p.is_file()}
    assert before == after
