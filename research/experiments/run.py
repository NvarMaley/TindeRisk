"""Reproduce the frozen chapter 5 replay and its machine-readable evidence."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from controls import (
    calibration,
    economic_effects,
    equity_null,
    forecast_comparison,
    paired,
    residual_plot,
    selection_sensitivity,
    series_tests,
)
from events import classroom_events
from models import add_controls, forecast, macro_refit_check
from portfolio import allocation_ledger, market_months, sentiment
from stock import momentum_component

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / "data/prepared_v1"


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def build(out):
    hashes = json.loads((PREP / "manifest.json").read_text())

    def read(name):
        path = PREP / (name + ".parquet")
        if sha(path) != hashes[path.name]:
            raise ValueError(f"Input changed: {name}")
        return pd.read_parquet(path)

    frozen, market, features, cash, lab = [
        read(k)
        for k in ["samples", "market", "features", "usd_cash", "sentiment_returns"]
    ]
    r, targets, tables = forecast(frozen, market, features, cash)
    macro_refit_check(tables["H03"], out)
    forecasts = add_controls(r)
    forecasts["version"] = "chapter5-v1"
    forecasts["asset"] = forecasts.study.map(
        {
            "H01": "SPY/IEF/GLD equal weight",
            "H02": "SPY/IEF/GLD equal weight",
            "H03": "IEF",
            "H04": "SPY",
        }
    )
    forecasts.to_parquet(out / "forecasts.parquet", index=False)
    ledger = allocation_ledger(frozen, targets, market_months(market, cash))
    ledger.to_parquet(out / "allocations.parquet", index=False)
    sent = sentiment(frozen, lab, read("sentiment_events"))
    sent.to_parquet(out / "black_litterman.parquet", index=False)
    register = pd.read_csv(ROOT / "research/studies.csv").set_index("id")
    paired(forecasts, ledger, sent, register, frozen, out)
    selection_sensitivity(out)
    economic_effects(ledger, sent, out)
    residual_plot(forecasts, out)
    pnl = []
    for (study, phase, arm, bp), g in ledger.groupby(
        ["study", "phase", "arm", "cost_bp"]
    ):
        pnl.append(
            {
                "study": study,
                "phase": phase,
                "arm": arm,
                "cost_bp": bp,
                "months": len(g),
                "observed": g.net_return.count(),
                "final_sleeve": g.wealth.iloc[-1],
                "traded": g.traded.sum(),
                "fees": g.fee.sum(),
                "withdrawn": g.withdrawal.sum(),
                "mean_utility": g.utility.mean(),
                "rebalances": g.action.eq("rebalance").sum(),
                "review_drift_max": g.drift_review.max(),
                "drift_breaches": (g.drift_review > 0.10).sum(),
                "unobserved_reviews": g.drift_review.isna().sum(),
                "avg_weight_change": g[["target_spy", "target_ief", "target_gld"]]
                .diff()
                .abs()
                .sum(axis=1, min_count=3)
                .mean(),
            }
        )
    pd.DataFrame(pnl).to_csv(out / "policy_summary.csv", index=False)
    gate = frozen[frozen.study.eq("H05")].copy()
    if gate.input_ready.any():
        raise ValueError("Changed filing gate requires a new release")
    gate["status"] = "withheld: no verified filing publication"
    gate.to_parquet(out / "stock_eligibility.parquet", index=False)
    vix_path = ROOT / "data/raw/VIXCLS.csv"
    known = pd.read_csv(
        ROOT / "research/source_catalogue/raw_manifest_v1.csv"
    ).set_index("path")
    if sha(vix_path) != known.at["data/raw/VIXCLS.csv", "sha256"]:
        raise ValueError("VIX input changed")
    vix = (
        pd.read_csv(vix_path, index_col=0, parse_dates=True, na_values=["."])
        .iloc[:, 0]
        .reindex(market.session.drop_duplicates().sort_values())
        .shift(1)
    )
    calibration(forecasts, vix.to_frame("prior_vix"), out)
    forecast_comparison(forecasts, out)
    series_tests(tables, out)
    equity_null(tables["H04"], out)
    momentum_component(read("security_universe"), out)
    stats = classroom_events(out)
    (out / "event_audit.json").write_text(json.dumps(stats, indent=2) + "\n")
    (out / "manifest.json").write_text(
        json.dumps({p.name: sha(p) for p in sorted(out.iterdir())}, indent=2) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("results")
    )
    dest = parser.parse_args().output.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=dest.parent) as tmp:
        output = Path(tmp) / "release"
        output.mkdir()
        build(output)
        if dest.exists():
            if {p.name: sha(p) for p in dest.iterdir()} != {
                p.name: sha(p) for p in output.iterdir()
            }:
                raise ValueError("Release differs; choose a separate --output")
        else:
            output.rename(dest)
    print(f"Verified {dest}")
