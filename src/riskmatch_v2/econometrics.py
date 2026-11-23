"""Instrument-level CHF exposures, observed episodes and chronological variance comparisons."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
from riskmatch_v2.archive_labels import read_snapshot
from scipy.stats import t

from .library.sources import checked
from .universe.data import Panel
from .universe.sheets import sheets

REPORT = Path("reports/econometrie")
LOCAL = Path("data/local/econometrics")
CONFIG = Path("config/econometrie.json")
FACTORS = ["market_usd", "usd_chf", "wti_usd", "yield_10y_pp"]


def hac(x, y, minimum, lag):
    valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
    n = int(valid.sum())
    if n < minimum:
        return None
    z = x[valid]
    if np.linalg.matrix_rank(z) < z.shape[1]:
        return None
    coef = np.linalg.lstsq(z, y[valid], rcond=None)[0]
    residual = y[valid] - z @ coef
    score = np.zeros_like(x)
    score[valid] = z * residual[:, None]
    meat = score.T @ score
    for k in range(1, lag + 1):
        cov = score[k:].T @ score[:-k]
        meat += (1 - k / (lag + 1)) * (cov + cov.T)
    bread = np.linalg.inv(z.T @ z)
    stderr = np.sqrt(
        np.maximum(0, np.diag(bread @ meat @ bread) * n / (n - z.shape[1]))
    )
    return coef, t.ppf(0.975, n - z.shape[1]) * stderr, n


def exposures(factors, daily, inventory, lag):
    rows = []
    qualified = inventory.index[
        inventory.included | inventory.reason.str.startswith("less than 252")
    ]
    for window, offset, shift in [(252, 0, 0), (252, 252, 0), (504, 0, 0), (252, 0, 1)]:
        end = len(daily) - offset
        x = factors.shift(shift).iloc[end - window : end].to_numpy()
        x = np.column_stack((np.ones(window), x))
        for key in qualified:
            est = hac(
                x,
                daily[key].iloc[end - window : end].to_numpy(),
                200 if window == 252 else 400,
                lag,
            )
            if est is None:
                continue
            b, half, n = est
            for k, name in enumerate(FACTORS, 1):
                rows.append(
                    (
                        key,
                        name,
                        window,
                        offset,
                        shift,
                        n,
                        b[k],
                        b[k] - half[k],
                        b[k] + half[k],
                    )
                )
    return pd.DataFrame(
        rows,
        columns=[
            "id",
            "factor",
            "window",
            "offset",
            "lag",
            "n",
            "beta",
            "low95",
            "high95",
        ],
    )


def episodes(panel, usd, events):
    # Endpoint FX suffices for cumulative CHF growth; require every local daily return.
    rows = []
    fx = pd.Series(panel.fx, index=panel.days)
    for name, (start, end) in events.items():
        part = usd.loc[start:end].iloc[1:]
        ok = part.notna().all() & (part >= -1).all()
        levels = (1 + part.loc[:, ok]).cumprod()
        levels.loc[start] = 1.0
        levels = levels.sort_index().mul(fx.reindex(levels.index) / fx[start], axis=0)
        if not np.isfinite(fx[[start, end]]).all():
            continue
        draw = (levels / levels.cummax() - 1).min()
        for key in levels:
            rows.append(
                (
                    key,
                    name,
                    len(part),
                    levels.at[end, key] - 1,
                    draw[key],
                    int(levels[key].count()),
                )
            )
    return pd.DataFrame(
        rows,
        columns=[
            "id",
            "episode",
            "sessions",
            "return_chf",
            "observed_drawdown",
            "marks",
        ],
    )


def forecasts(daily, end_eligible, first, decay):
    out = []
    raw = daily.to_numpy()

    def estimate(block):
        finite = np.isfinite(block)
        safe = np.where(finite, block, 0.0)
        weights = decay ** np.arange(len(block) - 1, -1, -1)
        ok = (finite.sum(axis=0) >= 50) & finite[-1]
        hist = (safe**2).sum(axis=0) / np.maximum(1, finite.sum(axis=0))
        ew = weights @ (safe**2) / np.maximum(1e-12, weights @ finite)
        return np.where(ok, hist, np.nan), np.where(ok, ew, np.nan)

    last_hist, last_ew = estimate(raw[-63:])
    for horizon in (21, 63):
        count = np.zeros(raw.shape[1], int)
        gains = np.zeros(raw.shape[1])
        for i in range(
            max(63, daily.index.searchsorted(first)), len(raw) - horizon + 1, horizon
        ):
            hist, ew = estimate(raw[i - 63 : i])
            future = raw[i : i + horizon]
            target = np.mean(future**2, axis=0)
            ok = np.isfinite(target) & (hist > 1e-12) & (ew > 1e-12)
            # Positive paired QLIKE difference favours EWMA. Common target term cancels.
            gains[ok] += np.log(hist[ok] / ew[ok]) + target[ok] * (
                1 / hist[ok] - 1 / ew[ok]
            )
            count += ok
        for j, key in enumerate(daily.columns):
            if end_eligible[j] or count[j]:
                out.append(
                    (
                        key,
                        horizon,
                        count[j],
                        gains[j] / count[j] if count[j] else None,
                        np.sqrt(252 * last_hist[j]) if end_eligible[j] else None,
                        np.sqrt(252 * last_ew[j]) if end_eligible[j] else None,
                    )
                )
    return pd.DataFrame(
        out, columns=["id", "horizon", "windows", "qlike_gain", "hist_vol", "ewma_vol"]
    )


def ecb_series(config):
    import requests

    rates = {}
    for currency, digest in config["ecb_files"].items():
        path = LOCAL / "source" / f"ECB-{currency}.csv"
        if not path.exists():
            url = f"https://data-api.ecb.europa.eu/service/data/EXR/D.{currency}.EUR.SP00.A"
            response = requests.get(
                url,
                params={
                    "startPeriod": "2014-10-01",
                    "endPeriod": config["end"],
                    "format": "csvdata",
                },
                timeout=60,
            )
            response.raise_for_status()
            if hashlib.sha256(response.content).hexdigest() != digest:
                raise ValueError("ECB vintage differs from the registered file")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
        checked(path, digest)
        records = pd.read_csv(path, index_col="TIME_PERIOD")
        if not records.index.is_unique or not records.CURRENCY.eq(currency).all():
            raise ValueError("Unexpected ECB series")
        rates[currency] = records.loc[records.OBS_STATUS.eq("A"), "OBS_VALUE"]
    return rates["CHF"] / rates["USD"]


def run():
    cfg = json.loads(CONFIG.read_bytes())
    base = Path("data/local/univers") / cfg["source_snapshot"]
    inv = read_snapshot(
        base / "membership.parquet", filters=[("day", "=", cfg["end"])]
    ).set_index("id")
    market = Path("data/local/4/raw")
    files = [
        CONFIG,
        Path(__file__),
        base / "manifest.json",
        market / "DGS10.csv",
        market / "DCOILWTICO.csv",
    ]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    stamp = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16]
    panel = Panel()
    fx_date = panel.dindex.get_loc(cfg["fx_date"])
    cross = cfg["eur_chf"] / cfg["eur_usd"]
    reserve_fx = ecb_series(cfg).reindex(panel.days).to_numpy()
    if not np.isclose(reserve_fx[fx_date], cross):
        raise ValueError("ECB archive and reference publication disagree")
    fill = ~np.isfinite(panel.fx) & np.isfinite(reserve_fx)
    panel.fx[fill] = reserve_fx[fill]
    sheet, monthly = sheets(panel, inv)
    cols = panel.names.get_indexer(inv.index)
    usd = panel.usd[:, cols].copy()
    bond = (cols >= len(panel.funds)) & (cols < panel.stock0)
    usd[:, bond] = panel.model_bond[:, cols[bond] - len(panel.funds)]
    usd[1:] = np.where(
        np.isfinite(panel.close[:-1, cols]) & np.isfinite(panel.close[1:, cols]),
        usd[1:],
        np.nan,
    )
    usd[0] = np.nan
    usd = pd.DataFrame(usd, index=panel.days, columns=inv.index)
    fx = pd.Series(panel.fx, index=usd.index).pct_change(fill_method=None)
    daily = (1 + usd).mul(1 + fx, axis=0) - 1
    factors = pd.DataFrame({"market_usd": usd.SPY, "usd_chf": fx})
    for name, series in [("wti_usd", "DCOILWTICO"), ("yield_10y_pp", "DGS10")]:
        level = pd.read_csv(market / (series + ".csv"), index_col="observation_date")[
            series
        ]
        factors[name] = level.reindex(daily.index).diff()
    beta = exposures(factors, daily, inv, cfg["hac_lags"])
    stress = episodes(panel, usd, cfg["events"])
    weights = read_snapshot(
        base / "weights.parquet", filters=[("day", "=", cfg["end"])]
    )
    sensitivity = beta.query(
        "window==252 and offset==0 and lag==0 and factor=='wti_usd'"
    ).set_index("id")
    portfolio = []
    for name, g in weights.groupby("option"):
        held = g.set_index("id").weight
        coeff = sensitivity.beta.reindex(held.index)
        obs = coeff.notna()
        portfolio.append(
            {
                "option": name,
                "positions": len(held),
                "covered": int(obs.sum()),
                "invested": float(held.sum()),
                "covered_weight": float(held[obs].sum()),
                "covered_wti_plus10_pct": float(1000 * (held[obs] @ coeff[obs])),
            }
        )

    eligible = (inv.included | inv.reason.str.startswith("less than 252")).to_numpy()
    vol = forecasts(daily, eligible, cfg["forecast_test_start"], cfg["forecast_decay"])
    # Elevated 63-session USD momentum against the preceding 252 valid-session window.
    # A descriptive flag, with no calibrated probability of a bubble.
    recent = usd.iloc[-63:]
    prior = usd.iloc[-315:-63]
    logprior = np.log1p(prior.where(prior > -1))
    logrecent = np.log1p(recent.where(recent > -1))
    z = (logrecent.sum(min_count=63) - 63 * logprior.mean()) / (
        np.sqrt(63) * logprior.std().replace(0, np.nan)
    )
    z = z.where(eligible & (logprior.count() >= 200)).dropna()
    scores = z.rename("momentum_z").to_frame().assign(alert=z >= 2)
    counts = sheet.groupby("years").full_sample.sum()
    old = pd.read_parquet(base / "sheets.parquet").groupby("years").full_sample.sum()
    central = beta.query("window==252 and offset==0 and lag==0")
    oil = central.query("factor=='wti_usd'").set_index("id")
    oil_prior = beta.query(
        "factor=='wti_usd' and window==252 and offset==252 and lag==0"
    ).set_index("id")
    paired = oil.join(oil_prior[["beta"]], rsuffix="_prior", how="inner")
    examples = {}
    for symbol, key in [
        ("XLE", "XLE"),
        ("XOM", "PERMNO:11850"),
        ("AAPL", "PERMNO:14593"),
        ("IEF", "IEF"),
        ("GLD", "GLD"),
    ]:
        if key in oil.index and inv.at[key, "symbol"] == symbol:
            examples[symbol] = {
                c: float(oil.at[key, c] * 1000) for c in ["beta", "low95", "high95"]
            }
    result = {
        "snapshot": stamp,
        "source_snapshot": cfg["source_snapshot"],
        "end": cfg["end"],
        "universe": len(inv),
        "cross": cross,
        "fx_fills": int(fill.sum()),
        "portfolios": portfolio,
        "class_coverage": {
            k: {"examined": len(g), "estimated": int(g.index.isin(central.id).sum())}
            for k, g in inv.groupby("class")
        },
        "windows": {int(k): [int(old[k]), int(v)] for k, v in counts.items()},
        "exposures": central.id.nunique(),
        "stable_oil_sign": int(
            (np.sign(paired.beta) == np.sign(paired.beta_prior)).sum()
        ),
        "paired_oil": len(paired),
        "examples_wti_plus10_pct": examples,
        "events": stress.groupby("episode").size().to_dict(),
        "forecasts": {
            int(h): {
                "at_least_8": int((g.windows >= 8).sum()),
                "ewma_better": int(((g.windows >= 8) & (g.qlike_gain > 0)).sum()),
            }
            for h, g in vol.groupby("horizon")
        },
        "momentum_measured": len(scores),
        "momentum_flags": int(scores.alert.sum()),
    }
    LOCAL.mkdir(parents=True, exist_ok=True)
    dest = LOCAL / stamp
    if not dest.exists():
        with TemporaryDirectory(dir=LOCAL) as tmp:
            stage = Path(tmp) / "output"
            stage.mkdir()
            for key, frame in [
                ("sheets", sheet),
                ("monthly_all_chf", monthly),
                ("sensitivities", beta),
                ("crises", stress),
                ("forecasts", vol),
                ("momentum", scores),
            ]:
                frame.to_parquet(stage / (key + ".parquet"))
            (stage / "sources.json").write_text(json.dumps(hashes, indent=2))
            stage.rename(dest)
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
