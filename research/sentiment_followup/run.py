"""Frozen H06 follow-up: recent polarity for allocation and activity for risk."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research/experiments"))
sys.path.insert(0, str(ROOT / "research"))
from controls import blocks
from course_replay import FIXTURES
from portfolio import posterior_weight, trade

TICKERS = ["AAPL", "SPY"]
ANCHOR = np.array([0.5, 0.5])


def checked(path, checksum):
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != checksum:
            raise ValueError(f"Input differs from the frozen snapshot: {path}")
    return path


def load():
    prep = ROOT / "data/prepared_v1"
    sums = json.loads((prep / "manifest.json").read_text())

    def read(name):
        return pd.read_parquet(checked(prep / name, sums[name]))

    data = read("sentiment_returns.parquet").set_index("session")[TICKERS]
    months = (
        read("samples.parquet")
        .query("study=='H06' and arm=='no-view anchor' and phase!='warm-up'")
        .sort_values("origin")
    )
    archive = ROOT / "research/experiments/results"
    old = pd.read_parquet(
        checked(
            archive / "black_litterman.parquet",
            json.loads((archive / "manifest.json").read_text())[
                "black_litterman.parquet"
            ],
        )
    )
    path = ROOT / "data/Data for laboratories-20261119/sentratio_and_price_for_pf2.pkl"
    cols = ["date", "ticker", "Nbullish", "Nbearish", "N"]
    msg = pd.read_pickle(checked(path, FIXTURES[path.name]))[cols]
    msg = msg[msg.ticker.isin(TICKERS)].copy()
    msg["session"] = (
        pd.to_datetime(msg.date, utc=True).dt.tz_localize(None).dt.normalize()
    )
    return data, months, old, msg


def signals(data, msg):
    def wide(col):
        return msg.pivot(index="session", columns="ticker", values=col).reindex(
            data.index
        )[TICKERS]

    bull, bear, activity = [wide(col) for col in ("Nbullish", "Nbearish", "N")]
    valid = bull.ge(0) & bear.ge(0) & activity.ge(bull + bear)
    up = bull.where(valid).rolling(5).sum()
    down = bear.where(valid).rolling(5).sum()
    polarity = (up - down) / (up + down).where(up + down > 0)
    relative = polarity.AAPL - polarity.SPY

    def standardize(value, lag, clip):
        previous = value.shift(lag).rolling(63, min_periods=50)
        sd = previous.std()
        return ((value - previous.mean()) / sd.where(sd > 1e-12)).clip(-clip, clip)

    volume = np.log1p(activity.where(activity >= 0))
    raw = volume.AAPL - volume.SPY
    return pd.DataFrame(
        {
            "polarity": standardize(relative, 5, 2).shift(1) / 2,
            "activity": standardize(raw, 1, 3).shift(2),
        },
        index=data.index,
    )


def allocation(data, months, signal, old):
    rows = []
    for phase, sample in months.groupby("phase", sort=False):
        for cost in [0, 10, 25]:
            w = ANCHOR.copy()
            for r in sample.itertuples():
                score = signal.get(r.origin)
                active = r.input_ready and pd.notna(score)
                hist = data.loc[: r.origin].tail(252).dropna()
                cov = hist.cov().to_numpy() * 21
                target, te = (
                    posterior_weight(cov, score, relative_to_prior=True)
                    if active
                    else (ANCHOR, 0.0)
                )
                obs = data.loc[r.holding_month]
                net = fee = turn = np.nan
                if r.input_ready and obs.notna().all().all():
                    v = w * (1 + obs.iloc[0].to_numpy())
                    v, _, turn, fee = trade(v, 0.0, target, cost / 10000)
                    v *= (1 + obs.iloc[1:]).prod().to_numpy()
                    net = v.sum() - 1
                    w = v / v.sum()
                else:
                    w = ANCHOR.copy()
                rows.append(
                    {
                        "phase": phase,
                        "holding_month": r.holding_month,
                        "origin": r.origin,
                        "signal_cutoff": data.index[data.index.get_loc(r.origin) - 1],
                        "first_close": obs.index[0],
                        "cost_bp": cost,
                        "score": score,
                        "own_signal": active,
                        "weight_aapl": target[0],
                        "te": te,
                        "traded": turn,
                        "fee": fee,
                        "net_return": net,
                        "utility": net - 2 * net**2,
                    }
                )
    table = pd.DataFrame(rows)
    for arm, name in [
        ("no-view anchor", "anchor"),
        ("signed view or anchor", "original"),
    ]:
        ref = old[old.arm == arm][
            ["holding_month", "cost_bp", "utility", "net_return"]
        ].rename(columns={"utility": name + "_utility", "net_return": name + "_return"})
        table = table.merge(ref, on=["holding_month", "cost_bp"], validate="one_to_one")
    table["gain"] = table.utility - table.anchor_utility
    return table


def fit_activity(train):
    """Profile the positive intercept out of the QLIKE objective at each slope."""
    clean = train[["base", "actual", "activity"]].dropna()
    if len(clean) < 252:
        return None
    x = clean.activity.to_numpy()
    ratio = (clean.actual / clean.base).to_numpy()

    def objective(b):
        return np.log(np.mean(ratio * np.exp(-b * x))) + b * x.mean()

    if ratio.mean() <= 0:
        return None
    res = minimize_scalar(
        objective, method="bounded", bounds=(-1, 1), options={"xatol": 1e-10}
    )
    if not res.success:
        raise ValueError("Activity calibration failed")
    b = res.x
    return ratio.mean(), np.mean(ratio * np.exp(-b * x)), b, len(clean)


def risk(data, months, activity):
    spread = data.AAPL - data.SPY
    frame = pd.DataFrame(
        {
            "actual": spread**2,
            "activity": activity,
            "base": (spread**2).shift(1).rolling(21, min_periods=18).mean(),
        }
    )
    frame["base"] = frame.base.where(frame.base > 0)
    rows = []
    for r in months.itertuples():
        out = frame.loc[r.holding_month].copy()
        past = frame.loc[frame.index < r.origin]
        params = fit_activity(past)
        out["origin"] = r.origin
        out["holding_month"] = r.holding_month
        out["phase"] = r.phase
        out["training_last"] = past.dropna().index.max()
        out["reference"] = out["candidate"] = out["slope"] = np.nan
        out["n_train"] = 0
        if params:
            ref, intercept, slope, n = params
            out["reference"] = out.base * ref
            out["candidate"] = out.base * intercept * np.exp(slope * out.activity)
            out["slope"] = slope
            out["n_train"] = n
        out["deployed"] = out.candidate.fillna(out.reference)
        for col in ["candidate", "deployed"]:
            # The constant depending only on the realization cancels, including at zero.
            out[col + "_gain"] = np.log(out.reference / out[col]) + out.actual * (
                1 / out.reference - 1 / out[col]
            )
        rows.append(out)
    return pd.concat(rows).rename_axis("session").reset_index()


def summaries(pnl, daily):
    result = []

    def add(endpoint, phase, cost, gains, n, eligible, threshold):
        for length in [1, 3, 6]:
            lo, hi, _ = blocks(gains, length)
            result.append(
                {
                    "endpoint": endpoint,
                    "phase": phase,
                    "cost_bp": cost,
                    "block_months": length,
                    "scheduled_months": len(gains),
                    "scored_months": gains.count(),
                    "scored_observations": n,
                    "own_signal_scored": eligible,
                    "mean_gain": gains.mean(),
                    "low": lo,
                    "high": hi,
                    "minimum": threshold,
                }
            )

    for (phase, cost), g in pnl.groupby(["phase", "cost_bp"]):
        add(
            "allocation",
            phase,
            cost,
            g.gain,
            g.gain.count(),
            (g.own_signal & g.gain.notna()).sum(),
            0.0005,
        )
    for phase, g in daily.groupby("phase"):
        add(
            "risk",
            phase,
            np.nan,
            g.groupby("holding_month", sort=True).deployed_gain.mean(),
            g.deployed_gain.count(),
            g.candidate_gain.count(),
            0.02,
        )
    return pd.DataFrame(result)


def build(folder):
    data, months, old, msg = load()
    signal = signals(data, msg)
    pnl = allocation(data, months, signal.polarity, old)
    daily = risk(data, months, signal.activity)
    pnl.to_parquet(folder / "allocation.parquet", index=False)
    daily.to_parquet(folder / "daily_risk.parquet", index=False)
    summaries(pnl, daily).to_csv(folder / "comparison.csv", index=False)
    (folder / "manifest.json").write_text(
        json.dumps(
            {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(folder.iterdir())
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("results")
    )
    dest = parser.parse_args().output.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=dest.parent) as tmp:
        stage = Path(tmp) / "release"
        stage.mkdir()
        build(stage)
        if dest.exists():
            if {p.name: p.read_bytes() for p in dest.iterdir()} != {
                p.name: p.read_bytes() for p in stage.iterdir()
            }:
                raise ValueError(
                    "Existing release differs, specify a fresh output path"
                )
        else:
            stage.rename(dest)
    print(f"Verified {dest}")
