"""Quality checks for the local RiskMatch data vintage. Source files are read-only."""
import gzip
import hashlib
import json
from io import BytesIO
from pathlib import Path

import exchange_calendars as xc
import numpy as np
import pandas as pd


def verify_calendar(index, start=None, end=None):
    if index.empty or not index.is_unique or not index.is_monotonic_increasing:
        raise ValueError("Calendar is empty, duplicated or out of order")
    start, end = start or index[0], end or index[-1]
    calendar = xc.get_calendar("XNYS", start="2004-01-01", end="2028-01-01")
    expected_sessions = calendar.sessions_in_range(start, end)
    if not index.equals(expected_sessions):
        raise ValueError(f"XNYS calendar: missing {expected_sessions.difference(index).tolist()[:5]}, "
                         f"unexpected {index.difference(expected_sessions).tolist()[:5]}")


def audit_local(root=Path(".")):
    sources = json.loads((root / "data/pilot_checksums.json").read_text())
    for name, digest in sources.items():
        path = root / name
        if name.startswith("data/additional_data/") and not path.exists():
            continue
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != digest:
            raise ValueError(f"Input checksum mismatch: {name}")

    data = root / "data"
    prices = pd.read_csv(data / "raw/etf_prices_adjusted.csv", index_col=0, parse_dates=True)
    verify_calendar(prices.index, pd.Timestamp("2005-01-03"), pd.Timestamp("2026-11-18"))
    if (prices <= 0).any().any() or not np.isfinite(prices).all().all():
        raise ValueError("Missing or invalid price")
    returns = prices.pct_change(fill_method=None).iloc[1:]
    prepared = pd.read_parquet(data / "processed/returns.parquet")
    pd.testing.assert_frame_equal(prepared, returns, check_names=False, check_freq=False,
                                  atol=1e-12, rtol=1e-10)
    print(f"ETF: {len(prices)} XNYS sessions, {prices.shape[1]} series. "
          f"Maximum absolute raw-to-prepared return difference: {abs(prepared-returns).max().max():.3g}")

    public = data / "raw/public_phase2"
    for entry in json.loads((public / "manifest.json").read_text())["files"]:
        path = public / (entry["series"] + ".csv")
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"FRED checksum: {path}")
        s = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
        assert s.index.is_unique and s.index.is_monotonic_increasing
        assert np.isfinite(s.dropna()).all()
        print(entry["series"], "valid observations / source rows:", s.count(), len(s))

    folder = public / "alfred"
    vintages = pd.read_csv(folder / "manifest.csv")
    assert not vintages.duplicated(["series", "vintage"]).any()
    for row in vintages.itertuples():
        payload = gzip.decompress((folder / f"{row.series}_{row.vintage}.csv.gz").read_bytes())
        assert hashlib.sha256(payload).hexdigest() == row.sha256_csv
        vintage = pd.read_csv(BytesIO(payload), index_col=0, parse_dates=True)
        assert len(vintage) == row.rows and vintage.index.is_unique
        assert vintage.index.max() <= pd.Timestamp(row.vintage)
    print("ALFRED vintages checked:", len(vintages))

    messages = pd.read_csv(data / "Data for laboratories-20261119/sentratio_and_price_st.csv")
    assert not messages.duplicated(["ticker", "date"]).any()
    assert messages.N.ge(0).all() and messages.Polarity.between(-1, 1).all()
    print("StockTwits rows, zero-volume rows, missing returns:", len(messages),
          messages.N.eq(0).sum(), messages.daily_return.isna().sum())
    for source in ("market", "sentiment"):
        provenance = pd.read_parquet(data / f"processed/{source}_observation_provenance.parquet")
        times = provenance[["observation_date", "available_date"]]
        assert times.notna().all().all() and (times.available_date >= times.observation_date).all()
        if source == "sentiment":
            assert (times.available_date > times.observation_date).all()
        else:
            print("Market availability assigned by convention:", int(provenance.availability_is_assumed.sum()),
                  "/", len(provenance))
    panel_path = data / "additional_data/clean/monthly_panel.parquet"
    if panel_path.exists():
        panel = pd.read_parquet(panel_path, columns=[
            "date", "permno", "available_from", "datadate", "investable", "bm", "ret"])
        duplicates = panel.duplicated(["permno", "date"]).sum()
        future = panel.available_from.gt(panel.date).sum()
        print("WRDS rows, eligible rows, missing B/M, missing returns, duplicates, future dates:",
              len(panel), panel.investable.sum(), panel.bm.isna().sum(), panel.ret.isna().sum(),
              duplicates, future)
        print("Book-to-market and return missingness rates by eligibility:")
        print(panel[["bm","ret"]].isna().groupby(panel.investable).mean().round(5))
        assert duplicates == future == 0
    else:
        print("Private WRDS panel unavailable. H05 check skipped.")


def h05_panel_at_close(path):
    """Research view. The proxy for accounting data availability has no intraday timestamp."""
    fields = ["at", "be", "gp", "ag", "bm"]
    panel = pd.read_parquet(path, columns=[
        "date", "trade_date", "permno", "datadate", "available_from", "investable", *fields])
    after_close = panel.available_from.gt(panel.trade_date)
    same_day = panel.available_from.eq(panel.trade_date)
    print("WRDS available after the session / among investable rows / same day without a timestamp:",
          after_close.sum(), (after_close & panel.investable).sum(), same_day.sum())
    known_before = panel.available_from.lt(panel.trade_date)
    panel["accounts_available"] = known_before
    panel.loc[~known_before, fields] = np.nan
    assert panel.loc[~known_before, fields].isna().all().all()
    return panel
