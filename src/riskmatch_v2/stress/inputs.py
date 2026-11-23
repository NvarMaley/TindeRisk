"""Dated inputs for the section 8 factor and event studies."""

import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd

from ..archive_labels import read_snapshot
from ..econometrics import ecb_series
from ..library.sources import checked
from ..universe.data import Panel

LOCAL = Path("data/local/8")
REPORT = Path("reports/08-chocs")
FACTORS = ["market", "fx", "oil", "ten_year_bp", "slope_bp"]


def inputs(cfg, parent):
    base = Path("data/local/univers") / parent["source_snapshot"]
    dated = {"filters": [("day", "=", parent["end"])]}
    inv = read_snapshot(base / "membership.parquet", **dated).set_index("id")
    weights = read_snapshot(base / "weights.parquet", **dated)
    p = Panel()
    ids = p.names.get_indexer(inv.index)
    assert min(ids) >= 0 and p.days[-1] == parent["end"]
    rates = pd.Series(p.fx, index=p.days).combine_first(
        ecb_series(parent).reindex(p.days)
    )
    close = p.close[:, ids]
    usd = p.usd[:, ids].astype(float)
    bonds = (ids >= len(p.funds)) & (ids < p.stock0)
    usd[:, bonds] = p.model_bond[:, ids[bonds] - len(p.funds)]
    usd[1:] = np.where(
        np.isfinite(close[1:]) & np.isfinite(close[:-1]), usd[1:], np.nan
    )
    usd[0] = np.nan
    usd = pd.DataFrame(usd, index=p.days, columns=inv.index)
    fx = rates.pct_change(fill_method=None)
    chf = (1 + usd).mul(1 + fx, axis=0) - 1
    two = LOCAL / "DGS2.csv"
    if not two.exists():
        with urlopen(cfg["two_year_url"], timeout=60) as response:
            blob = response.read()
        import hashlib

        if hashlib.sha256(blob).hexdigest() != cfg["two_year_sha256"]:
            raise ValueError("DGS2 download differs from the frozen vintage")
        two.write_bytes(blob)
    checked(two, cfg["two_year_sha256"])
    raw = Path("data/local/4/raw")
    sources = json.loads(Path("config/sources-4.json").read_text())

    def level(key):
        path = two if key == "DGS2" else raw / (key + ".csv")
        if path != two:
            checked(path, sources[path.name]["sha256"])
        return pd.read_csv(path, index_col="observation_date")[key].reindex(usd.index)

    y2, y10, wti = level("DGS2"), level("DGS10"), level("DCOILWTICO")
    f = pd.DataFrame(
        {
            "market": usd.SPY,
            "fx": fx,
            "oil": wti.diff(),
            "ten_year_bp": 100 * y10.diff(),
            "slope_bp": 100 * (y10 - y2).diff(),
        }
    )
    vol = f.market.rolling(cfg["vol_window"]).std().shift(1) * np.sqrt(252)
    regime = pd.Series(pd.NA, index=f.index, dtype="string")
    regime[vol.notna()] = np.where(
        vol.dropna() >= cfg["high_vol_annual"], "High", "Normal"
    )
    # Keep raw per-mark bond returns for the Treasury calendar used by historical paths.
    observed_bonds = pd.DataFrame(
        p.usd[:, ids[bonds]], index=p.days, columns=inv.index[bonds]
    )
    return inv, weights, usd, chf, f, regime, observed_bonds, rates, y2, y10


def shock_counts(f, regime, cfg):
    cut = cfg["calibration_end"]
    oil = f.oil
    low, high = oil.loc[:cut].quantile(cfg["quantiles"])
    assert (
        low < 0 < high
        and (oil >= cfg["oil_cut_usd"]).any()
        and (oil <= -cfg["oil_cut_usd"]).any()
    )
    assert "2022-07-04" not in f.index and pd.isna(f.at["2022-10-10", "ten_year_bp"])
    rows = []
    for method, a, b in [
        ("Fixed USD", -cfg["oil_cut_usd"], cfg["oil_cut_usd"]),
        ("Calibration quantiles", low, high),
    ]:
        for label in ["Normal", "High"]:
            sample = oil[(oil.index > cut) & regime.eq(label)].dropna()
            rows.append(
                {
                    "rule": method,
                    "regime": label,
                    "lower": a,
                    "upper": b,
                    "measured": len(sample),
                    "negative": int((sample <= a).sum()),
                    "positive": int((sample >= b).sum()),
                }
            )
    return rows
