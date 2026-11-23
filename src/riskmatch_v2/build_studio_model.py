"""Package derived, dated multi-asset estimates; original prices and histories stay local."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

from .archive_labels import read_snapshot
from .stress.scenarios import attribution

ROOT = Path(__file__).resolve().parents[2]


def build():
    def read(path):
        return json.loads((ROOT / path).read_text())

    historical = read("reports/univers-complet/resultats.json")
    model_id = historical["snapshot"]
    day = historical["date"]
    root = ROOT / "data/local/univers" / model_id
    membership = read_snapshot(
        root / "membership.parquet", filters=[("day", "=", day)]
    ).set_index("id")
    with np.load(root / "models.npz", allow_pickle=False) as f:
        ids = pd.Index(f["names"].tolist(), name="id")
        assert set(ids) == set(membership.index[membership.included])
        estimates = f["mu"].T
        stress = f["shock"]
    inv = membership.loc[ids]
    if not inv.symbol.is_unique:
        raise ValueError("Dated tickers need disambiguation before publishing")
    cfg = read("config/stress-8.json")
    cfg["scenarios"]["Rates up"] = {"ten_year_bp": 50, "slope_bp": 25}
    stress_root = (
        ROOT / "data/local/8" / read("reports/08-chocs/results.json")["archive"]
    )
    betas = pd.read_parquet(stress_root / "exposures.parquet")
    bonds = pd.read_parquet(stress_root / "bonds.parquet")
    # Reuse the calibrated direct Treasury repricing for the same rate move.
    rates = bonds.loc[bonds.scenario == "Joint"].assign(scenario="Rates up")
    rows = pd.DataFrame(
        {
            "id": ids,
            "option": "Full universe",
            "weight": np.full(len(ids), 1 / len(ids)),
        }
    )
    table, _ = attribution(betas, pd.concat([bonds, rates]), rows, cfg)
    shocks = table.pivot(index="id", columns="scenario", values="total_chf").reindex(
        ids
    )
    carbon = pd.read_parquet(ROOT / "data/local/11/allocations.parquet").loc[ids]
    data = {
        "model_id": model_id,
        "date": day,
        "environment_date": read("reports/11-environment/results.json")["review"][:10],
        "symbols": inv.symbol.tolist(),
        "issuers": inv.issuer.fillna(inv.symbol).tolist(),
        "classes": inv["class"].tolist(),
        "mu": estimates.round(9).tolist(),
        "stress_2008": stress.round(9).tolist(),
        "factor_roots": [],
        "specific_risk": [],
        "scenarios": list(shocks),
        "shocks": json.loads(shocks.to_json(orient="values", double_precision=9)),
        "carbon": carbon[["forbidden", "unknown_gross", "covered", "numerator"]]
        .round(9)
        .values.tolist(),
    }
    # Baseline 504-day and alternate 756-day covariance specifications.
    for k in (0, 1):
        r = sparse.load_npz(root / f"risk_{k}.npz")
        assert r.shape == (len(ids) + 3, len(ids))
        data["factor_roots"].append(r[:3].toarray().T.round(9).tolist())
        data["specific_risk"].append(r[3:].diagonal().round(9).tolist())
    destination = ROOT / "reports/studio/model.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    build()
