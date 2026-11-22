"""Build the 3.2 historical data release from the frozen 3.1 sources."""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import pandas as pd
from cleaning.companies import company_panels
from cleaning.markets import SLEEVE, market_panel, schedule
from cleaning.samples import sample_manifest
from cleaning.timing import macro_panels

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data/prepared_v1"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def factors(data, out):
    folder = data / "additional_data/raw/factors"
    tables = []
    for filename, columns in [
        (
            "F-F_Research_Data_5_Factors_2x3_CSV.zip",
            ["MKT_RF", "SMB", "HML", "RMW", "CMA", "RF"],
        ),
        ("F-F_Momentum_Factor_CSV.zip", ["UMD"]),
    ]:
        with ZipFile(folder / filename) as archive:
            rows = csv.reader(
                archive.read(archive.namelist()[0]).decode("latin1").splitlines()
            )
            values = [
                (r[0].strip(), *map(float, r[1:]))
                for r in rows
                if r and re.fullmatch(r"\d{6}", r[0].strip())
            ]
        frame = pd.DataFrame(values, columns=["period", *columns]).set_index("period")
        if not frame.index.is_unique:
            raise ValueError("Duplicate monthly factor key")
        tables.append(frame.mask(frame.isin([-99.99, -999])) / 100)
    table = pd.concat(tables, axis=1).loc["199801":"202512"].reset_index()
    table["vintage"] = "2026-10-14 download; retrospective factors"
    table.to_parquet(out / "monthly_factors.parquet", index=False)


def build(out):
    data = ROOT / "data"
    frozen = ROOT / "research/source_catalogue/raw_manifest_v1.csv"
    receipt = pd.read_csv(frozen).set_index("path")
    inputs = [
        data / "raw/etf_prices_adjusted.csv",
        *sorted((data / "raw/price_events").glob("*.json")),
        data / "raw/public_phase2/DEXSZUS.csv",
        *sorted((data / "raw/public_phase2/alfred").glob("*.gz")),
        *(
            data / f"raw/{name}.csv"
            for name in ("DTB3", "T10Y2Y", "BAA10Y", "ln7_public_aapl_spy_prices")
        ),
        *(
            data / f"additional_data/raw/wrds/{name}.csv"
            for name in ("crsp_msf", "crsp_dsf", "ccm_lnkhist", "comp_funda")
        ),
        data / "raw/GICS.zip",
        *sorted(data.glob("Data for laboratories*/*.csv")),
        data / "additional_data/raw/factors/F-F_Research_Data_5_Factors_2x3_CSV.zip",
        data / "additional_data/raw/factors/F-F_Momentum_Factor_CSV.zip",
    ]
    for path in inputs:
        if digest(path) != receipt.at[path.relative_to(ROOT).as_posix(), "sha256"]:
            raise ValueError(f"Changed v1 input: {path}")
    auxiliary = {
        str(p.relative_to(ROOT)): digest(p)
        for p in (
            data / "processed/metadata.json",
            data / "processed/ln7_company_sector_days.parquet",
            data / "additional_data/clean/monthly_panel.parquet",
        )
    }
    market = market_panel(data, out)
    calendar = schedule("XNYS")
    features, cash = macro_panels(
        data, out, calendar, pd.DatetimeIndex(sorted(market.session.unique()))
    )
    firms, company_stats = company_panels(data, out)
    factors(data, out)
    sentiment = sample_manifest(data, out, calendar, market, features, cash, firms)
    summary = {
        "raw_manifest_sha256": digest(frozen),
        "raw_files_verified": len(inputs),
        "auxiliary_sha256": auxiliary,
        "first_session": str(market.session.min().date()),
        "last_session": str(market.session.max().date()),
        "market_rows": len(market),
        "provisional": int(market.provisional_close.sum()),
        "usd_returns": int(market.usd_return.count()),
        "chf_returns": int(market.chf_return.count()),
        "stale": int(market.usd_return.eq(0).sum()),
        "mad_flags": int(market.mad_flag.sum()),
        "source_differences": int(market.source_gap_flag.sum()),
        "splits": int(market.split_ratio.ne(1).sum()),
        "distributions": int(market.distribution_usd.ne(0).sum()),
        "sleeve_complete_chf": int(
            market.pivot(index="session", columns="asset", values="chf_return")[SLEEVE]
            .dropna()
            .shape[0]
        ),
        "max_cash_approximation_gap_bp": float(
            (cash.usd_cash_proxy - cash.simple_proxy).abs().max() * 10000
        ),
        "company": company_stats,
        "sentiment": sentiment,
    }
    (out / "audit.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return {p.name: digest(p) for p in sorted(out.iterdir())}


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--output", type=Path, default=TARGET)
    output = args.parse_args().output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".prepare-") as temp:
        staged = Path(temp) / "v1"
        staged.mkdir()
        hashes = build(staged)
        (staged / "manifest.json").write_text(
            json.dumps(hashes, indent=2, sort_keys=True) + "\n"
        )
        if output.exists():
            existing = {
                p.name: digest(p)
                for p in output.iterdir()
                if p.is_file() and p.name != "manifest.json"
            }
            if (
                existing != hashes
                or (output / "manifest.json").read_bytes()
                != (staged / "manifest.json").read_bytes()
            ):
                raise ValueError(
                    "Rebuild differs from existing release; inspect differences in a separate --output directory"
                )
        else:
            staged.rename(output)
    print(f"Verified {len(hashes)} versioned outputs in {output}")


if __name__ == "__main__":
    main()
