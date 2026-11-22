"""Verify the imported local research pack without modifying the original files."""
import csv
import gzip
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def check_pilot_inputs(root, manifest):
    historical_cards = {"questions/bank.json", "questions/transfer_validation.json"}
    absent, issues, archived = [], [], []
    for name, expected in manifest.items():
        path = root / name
        if not path.is_file():
            absent.append(name)
        if name in historical_cards:
            archived.append(name)
        elif not path.is_file() or digest(path) != expected:
            issues.append(name)
    return absent, issues, archived


def verify(root):
    data = root / "data"
    public = data / "raw/public_phase2"
    manifest = read_json(data / "pilot_checksums.json")
    absent, issues, archived = check_pilot_inputs(root, manifest)
    fred = read_json(public / "manifest.json")["files"]
    for row in fred:
        if digest(public / (row["series"] + ".csv")) != row["sha256"]:
            issues.append(row["series"])

    vintages = public / "alfred"
    with (vintages / "manifest.csv").open(newline="") as stream:
        vintage_rows = list(csv.DictReader(stream))

    def check_vintage(row):
        name = f"{row['series']}_{row['vintage']}.csv.gz"
        with gzip.open(vintages / name, "rb") as stream:
            return name if hashlib.file_digest(stream, "sha256").hexdigest() != row["sha256_csv"] else None

    with ThreadPoolExecutor(max_workers=12) as pool:
        issues.extend(item for item in pool.map(check_vintage, vintage_rows) if item)
    if len({(r["series"], r["vintage"]) for r in vintage_rows}) != len(vintage_rows):
        issues.append("duplicate series/vintage")

    with (data / "additional_data/manifest.csv").open(newline="") as stream:
        wrds = [r for r in csv.DictReader(stream) if r["provider"].startswith("WRDS")]
    for row in wrds:
        if digest(data / "additional_data/raw/wrds" / (row["dataset"] + ".csv")) != row["sha256"]:
            issues.append(row["dataset"])

    prices = pd.read_csv(data / "raw/etf_prices_adjusted.csv", index_col="date", parse_dates=True)
    if not (prices.index.is_unique and prices.index.is_monotonic_increasing
            and np.isfinite(prices).all().all() and prices.gt(0).all().all()):
        raise ValueError("Price keys or levels failed validation.")
    returns = prices.pct_change(fill_method=None).iloc[1:]
    saved = pd.read_parquet(data / "processed/returns.parquet")
    returns.columns.name = saved.columns.name  # CSV does not encode the column-axis name.

    pd.testing.assert_frame_equal(returns, saved, check_freq=False, rtol=1e-11, atol=1e-12)
    sector = pd.read_parquet(data / "processed/ln7_company_sector_days.parquet")
    panel = pq.ParquetFile(data / "additional_data/clean/monthly_panel.parquet")
    return dict(pilot_entries=len(manifest), missing=absent, archived_questionnaire_entries=archived, integrity_issues=issues,
                fred_files=len(fred), alfred_files=len(vintage_rows), wrds_extracts=len(wrds),
                prices=[len(prices), len(prices.columns)], price_dates=[str(i.date()) for i in (prices.index.min(), prices.index.max())],
                returns_reconciled=len(saved), firm_month_panel_rows=panel.metadata.num_rows,
                company_days=len(sector), effective_sector_matches=int(sector.effective_status.eq("effective_match").sum()),
                known_sector_rows=int(sector.gics_sector.notna().sum()))


if __name__ == "__main__":
    result = verify(Path(__file__).resolve().parents[1])
    print(json.dumps(result, indent=2))
    if result["integrity_issues"]:
        raise SystemExit(1)
