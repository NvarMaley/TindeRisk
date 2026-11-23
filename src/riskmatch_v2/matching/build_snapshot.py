"""Build the public research parameter pack and the optional private first-close tape."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

from ..archive_labels import read_snapshot

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "reports/13-application"
PRIVATE = ROOT / "data/local/13"


def build():
    summary = json.loads((ROOT / "reports/univers-complet/resultats.json").read_text())
    bundle = ROOT / "data/local/univers" / summary["snapshot"]
    day = summary["date"]
    selected = {"filters": [("day", "=", day)]}
    weights = read_snapshot(bundle / "weights.parquet", **selected)
    inventory = read_snapshot(bundle / "membership.parquet", **selected).set_index("id")
    with np.load(bundle / "models.npz", allow_pickle=False) as f:
        names = pd.Index(f["names"])
        chosen = names[names.isin(weights.id)]
        ix = names.get_indexer(chosen)
        mu = f["mu"][:, ix].T
        stress = f["shock"][ix]
        prices = f["prices"][ix]
        fx = float(f["fx"])
    symbols = inventory.loc[chosen, "symbol"].tolist()
    if len(set(symbols)) != len(symbols):
        raise ValueError("Market pack requires unambiguous dated display identifiers")
    root = sparse.load_npz(bundle / "risk_0.npz")
    factors = root[:3, ix].toarray().T
    specific = root[3:, :].diagonal()[ix]
    stress_report = json.loads((ROOT / "reports/08-chocs/results.json").read_text())
    paths = ROOT / "data/local/8" / stress_report["archive"]
    attribution = pd.read_parquet(paths / "attribution.parquet")
    attribution["rates"] = attribution.local_ten_year_bp + attribution.local_slope_bp
    shocks = attribution.pivot_table(
        index="id", columns="scenario", values="total_chf", aggfunc="first"
    )
    shocks["Rate shock"] = (
        attribution.query("scenario=='Joint'")
        .drop_duplicates("id")
        .set_index("id")
        .rates
    )
    shock_names = ["Oil up", "Oil down", "CHF translation", "Rate shock", "Joint"]
    shock_table = shocks.reindex(index=chosen, columns=shock_names).to_numpy()
    if not np.isfinite(shock_table).all():
        raise ValueError("Missing scenario coverage in selected holdings")
    shares = (
        weights.pivot(index="id", columns="option", values="weight")
        .reindex(chosen)
        .fillna(0)
    )
    model = {
        "version": "13.1",
        "research_date": day,
        "model_id": summary["snapshot"],
        "universe": len(names),
        "shock_names": shock_names,
        "symbols": symbols,
        "asset_classes": inventory.loc[chosen, "class"].tolist(),
        "mu": mu.round(12).tolist(),
        "factor_loadings": factors.round(12).tolist(),
        "specific_risk": specific.round(12).tolist(),
        "stress_2008": stress.round(12).tolist(),
        "shocks": shock_table.round(12).tolist(),
        "options": {
            k: shares[k].to_numpy().round(12).tolist() for k in summary["cards"]
        },
        "aliases": summary["aliases"],
    }
    OUT.mkdir(exist_ok=True, parents=True)
    blob = (json.dumps(model, separators=(",", ":"), allow_nan=False) + "\n").encode()
    (OUT / "market.json").write_bytes(blob)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    if not np.isfinite(prices).all() or min(prices) <= 0:
        raise ValueError("Missing decision-date marks")
    (PRIVATE / "market-close.json").write_text(
        json.dumps(
            {
                "model_sha256": hashlib.sha256(blob).hexdigest(),
                "day": day,
                "fx": fx,
                "usd_prices": dict(zip(symbols, prices.tolist())),
            },
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    build()
