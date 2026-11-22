"""Run the seven dated comparisons from the frozen extracts and chapter 5 releases."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [
    str(ROOT),
    str(ROOT / "research"),
    str(ROOT / "research/experiments"),
    str(HERE),
]
from controls import blocks
from course_replay import DATA, FIXTURES
from estimators import gap_forecast, mean_forecast, rescaled_covariance
from filing import characteristics
from models import ASSETS, BASE, EW, minimum_variance
from portfolio import allocation_ledger, market_months

from research.sentiment_followup.run import allocation_path, checked, signals

LABELS = {
    "H01": "rescaled correlation",
    "H02": "gap-filtered variance",
    "H03": "forward curve",
    "H04": "restricted payout",
    "H05": "four published sorts",
    "H06": "cross-instrument sentiment",
    "H07": "5pp boundary band",
}
PHASES = ["validation", "historical replay"]


def artifact(folder, name, manifest="manifest.json"):
    checks = json.loads((folder / manifest).read_text())
    return pd.read_parquet(checked(folder / name, checks[name]))


def mean_inputs(origins, curve, market, study):
    if study == "H03":
        z = curve.set_index("Date").sort_index() / 100
        mat = np.arange(1, 6) * z.to_numpy()
        values = pd.DataFrame(
            np.diff(mat, prepend=np.zeros((len(mat), 1)), axis=1), index=z.index
        )
    else:
        spy = market[market.asset == "SPY"].set_index("session").sort_index()
        payout = spy.distribution_usd.rolling("365D").sum() / spy.chart_close
        values = payout.loc[
            payout.index >= payout.index.min() + pd.Timedelta(days=365)
        ].to_frame("payout")
    idx = values.index.searchsorted(origins, side="left") - 1
    result = values.iloc[np.maximum(0, idx)].copy()
    dates = pd.DatetimeIndex(result.index)
    valid = (idx >= 0) & ((origins - dates).days <= 7)
    result.index = origins
    result.loc[~valid, :] = np.nan
    return result.to_numpy(), dates.where(valid)


def published_curve_inputs(origins, curve):
    # Find the latest Tuesday strictly before each decision, then the preceding Friday.
    tuesdays = origins - pd.to_timedelta((origins.weekday - 1 - 1) % 7 + 1, unit="D")
    fridays = tuesdays - pd.Timedelta(days=4)
    return mean_inputs(fridays + pd.Timedelta(days=1), curve, None, "H03")


def financial(forecasts, market, curve):
    chf = market.pivot(index="session", columns="asset", values="chf_return")[ASSETS]
    rows = []
    weights = {}
    for study in list(LABELS)[:4]:
        t = forecasts[
            (forecasts.study == study) & (forecasts.arm == BASE[study])
        ].sort_values("origin")
        mse = (
            t.loc[t.phase == "development", "loss"].mean()
            if study in ["H03", "H04"]
            else 1.0
        )
        X, dates = (
            mean_inputs(pd.DatetimeIndex(t.origin), curve, market, study)
            if study in ["H03", "H04"]
            else (None, None)
        )
        if study == "H03":
            weekly_x, weekly_dates = published_curve_inputs(
                pd.DatetimeIndex(t.origin), curve
            )
        for i, r in enumerate(t.itertuples()):
            if r.phase not in PHASES:
                continue
            pred = np.nan
            target = None
            info = {}
            source_date = pd.NaT
            train_end = pd.NaT
            if X is not None:
                valid = (
                    (t.end < r.origin).to_numpy()
                    & np.isfinite(t.actual)
                    & np.isfinite(X).all(axis=1)
                )
                train_end = t.loc[valid, "end"].max()
                source_date = dates[i]
                pred = mean_forecast(X[valid], t.actual[valid].to_numpy(), X[i], study)
                if np.isfinite(pred):
                    target = np.zeros(3)
                    target[ASSETS.index("IEF" if study == "H03" else "SPY")] = float(
                        pred > 0
                    )
                info["observed"] = int(valid.sum())
                if study == "H03":
                    past = (t.end < r.origin).to_numpy()
                    weekly_pred = mean_forecast(
                        weekly_x[past], t.actual.to_numpy()[past], weekly_x[i], study
                    )
                    info.update(
                        weekly_source_bar=weekly_dates[i],
                        weekly_prediction=weekly_pred,
                        weekly_gain=(r.loss - (r.actual - weekly_pred) ** 2) / mse,
                    )
            else:
                long = chf.loc[: r.origin].tail(756)
                short = long.tail(63).dropna()
                if (
                    study == "H01"
                    and len(long) == 756
                    and len(long.dropna()) >= 719
                    and len(short) >= 60
                ):
                    cov = rescaled_covariance(long.dropna(), short)
                    target = minimum_variance(cov)
                    pred = r.horizon_sessions * (EW @ cov @ EW)
                    info = {
                        "observed": len(long.dropna()),
                        "condition": np.linalg.cond(cov),
                    }
                elif study == "H02":
                    pred, info = gap_forecast(long @ EW, r.horizon_sessions)
                    if np.isfinite(pred):
                        target = EW * min(
                            1, 0.10 / np.sqrt(252 * pred / r.horizon_sessions)
                        )
                train_end = long.index[-1]
            if target is not None:
                weights[study, LABELS[study], r.holding_month] = target
            loss = np.nan
            if np.isfinite(pred) and np.isfinite(r.actual):
                if X is not None:
                    loss = (r.actual - pred) ** 2
                elif r.actual > 0:
                    ratio = r.actual / pred
                    loss = ratio - np.log(ratio) - 1
            gain = (r.loss - loss) / mse
            rows.append(
                dict(
                    study=study,
                    phase=r.phase,
                    month=r.holding_month,
                    origin=r.origin,
                    train_end=train_end,
                    source_date=source_date,
                    prediction=pred,
                    actual=r.actual,
                    reference_point=r.point,
                    loss=loss,
                    reference_loss=r.loss,
                    gain=gain,
                    deployed_gain=gain
                    if np.isfinite(pred)
                    else (0.0 if np.isfinite(r.loss) else np.nan),
                    own_signal=np.isfinite(pred),
                    **info,
                )
            )
    return pd.DataFrame(rows), weights


def transfer(frozen, calendar, out):
    path = DATA / "sentratio_and_price_for_pf2.pkl"
    lab = pd.read_pickle(checked(path, FIXTURES[path.name]))[
        ["date", "ticker", "daily_return", "Nbullish", "Nbearish", "N"]
    ].copy()
    lab["session"] = (
        pd.to_datetime(lab.date, utc=True).dt.tz_localize(None).dt.normalize()
    )
    returns = lab.pivot(
        index="session", columns="ticker", values="daily_return"
    ).reindex(calendar)
    months = frozen[
        (frozen.study == "H06")
        & (frozen.arm == BASE["H06"])
        & frozen.phase.isin(PHASES)
    ].copy()
    ledgers = []
    for symbol in sorted(set(returns.columns) - {"AAPL", "SPY"}):
        data = returns[[symbol, "SPY"]]
        messages = lab[lab.ticker.isin(data.columns)]
        score = signals(data, messages, instrument=symbol).polarity
        months["input_ready"] = [
            len(data.loc[:d].tail(252).dropna()) >= 126 for d in months.origin
        ]
        candidate = allocation_path(data, months, score).rename(
            columns={"weight_aapl": "weight_instrument"}
        )
        anchor = allocation_path(data, months, pd.Series(np.nan, index=score.index))
        keys = ["phase", "holding_month", "cost_bp"]
        cand = candidate.merge(
            anchor[keys + ["utility", "net_return"]].rename(
                columns={"utility": "anchor_utility", "net_return": "anchor_return"}
            ),
            on=keys,
            validate="one_to_one",
        )
        cand["instrument"] = symbol
        cand["gain"] = cand.utility - cand.anchor_utility
        ledgers.append(cand)
    detail = pd.concat(ledgers, ignore_index=True)
    detail.to_parquet(out / "sentiment_transfer.parquet", index=False)
    g = detail[detail.cost_bp == 10].copy()
    influence = []
    for (phase, omitted), _ in g.groupby(["phase", "instrument"]):
        peers = g[(g.phase == phase) & (g.instrument != omitted)]
        mc = peers.groupby("holding_month").gain.mean()
        influence.append(
            {
                "phase": phase,
                "omitted": omitted,
                "scored_months": mc.count(),
                "mean_gain": mc.mean(),
            }
        )
    pd.DataFrame(influence).to_csv(out / "sentiment_influence.csv", index=False)
    g["own_gain"] = g.gain.where(g.own_signal)
    # Aggregate all eligible pairs equally within month, including reference fallbacks.
    result = (
        g.groupby(["phase", "holding_month"])
        .agg(
            gain=("own_gain", "mean"),
            deployed_gain=("gain", "mean"),
            eligible_pairs=("gain", "count"),
            signal_pairs=("own_gain", "count"),
            scheduled_pairs=("instrument", "size"),
        )
        .reset_index()
    )
    result["own_signal"] = result.signal_pairs.gt(0)
    return result.rename(columns={"holding_month": "month"}).assign(study="H06")


def evaluate(out):
    frozen = ROOT / "data/prepared_v1"
    v1 = ROOT / "research/experiments/results"
    market, cash, sample, lab = [
        artifact(frozen, n + ".parquet")
        for n in ["market", "usd_cash", "samples", "sentiment_returns"]
    ]
    forecasts = artifact(v1, "forecasts.parquet")
    prior = artifact(v1, "allocations.parquet")
    inputs = HERE / "inputs"
    meta = json.loads((inputs / "provenance.json").read_text())
    for name, h in meta["extracts"].items():
        checked(inputs / name, h)
    curve = pd.read_csv(inputs / "zero_yields.csv", parse_dates=["Date"])
    filing = json.loads((inputs / "aapl_2023_filing.json").read_text())
    panel_path = frozen / "security_universe.parquet"
    checked(
        panel_path, json.loads((frozen / "manifest.json").read_text())[panel_path.name]
    )
    issuer = pd.read_parquet(
        panel_path, filters=[("permno", "==", filing["security"]["permno"])]
    )
    example = characteristics(filing, issuer, market.session.unique(), filing["origin"])
    (out / "filing_example.json").write_text(json.dumps(example, indent=2) + "\n")
    points, weights = financial(forecasts, market, curve)
    # Recover the registered reference targets, including missing origins, from its original funded ledger.
    for r in prior[
        prior.phase.isin(PHASES)
        & prior.cost_bp.eq(10)
        & prior.arm.eq(prior.study.map(BASE))
    ].itertuples():
        w = np.array([r.target_spy, r.target_ief, r.target_gld])
        if np.isfinite(w).all():
            weights[r.study, r.arm, r.holding_month] = w
    arms = {s: [LABELS[s]] for s in ["H01", "H02", "H03", "H04", "H07"]}
    portfolios = allocation_ledger(
        sample[sample.phase.isin(PHASES)],
        weights,
        market_months(market, cash),
        policies_by_study=arms,
    )
    keys = ["study", "phase", "holding_month", "cost_bp"]
    refs = prior[prior.arm.eq(prior.study.map(BASE))][
        keys + ["wealth", "utility", "net_return", "traded", "withdrawal"]
    ].rename(columns=lambda c: c if c in keys else "reference_" + c)
    portfolios = portfolios.merge(refs, on=keys, validate="one_to_one")
    np.testing.assert_allclose(portfolios.withdrawal, portfolios.reference_withdrawal)
    portfolios.to_parquet(out / "funded.parquet", index=False)
    h7 = portfolios[(portfolios.study == "H07") & (portfolios.cost_bp == 10)].copy()
    h7["gain"] = h7.net_return - h7.reference_net_return
    h7 = h7.rename(columns={"holding_month": "month"}).assign(
        deployed_gain=h7.gain, own_signal=True
    )
    external = pd.read_csv(inputs / "french_portfolios.csv")
    external["gain"] = external.favorable - external.middle
    external["phase"] = np.where(
        external.month < "2019", "validation", "historical replay"
    )
    external.groupby(["phase", "signal", "size"]).gain.agg(
        ["mean", "std", "count"]
    ).reset_index().to_csv(out / "factor_components.csv", index=False)
    h5 = (
        external.groupby(["phase", "month"])
        .gain.mean()
        .reset_index()
        .assign(study="H05", own_signal=True)
    )
    h5["deployed_gain"] = h5.gain
    h6 = transfer(sample, pd.DatetimeIndex(lab.session), out)
    monthly = pd.concat(
        [
            points,
            h5,
            h6,
            h7[["study", "phase", "month", "gain", "deployed_gain", "own_signal"]],
        ],
        ignore_index=True,
    )
    monthly.to_parquet(out / "monthly.parquet", index=False)
    other = []
    for study, arm in [("H01", "Ledoit-Wolf"), ("H02", "EWMA")]:
        b = forecasts[(forecasts.study == study) & (forecasts.arm == arm)][
            ["holding_month", "loss"]
        ]
        same = points[points.study == study].merge(
            b,
            left_on="month",
            right_on="holding_month",
            validate="one_to_one",
            suffixes=("", "_other"),
        )
        for phase, group in same.groupby("phase"):
            gain = group.loss_other - group.loss
            other.append(
                {
                    "study": study,
                    "phase": phase,
                    "alternative": arm,
                    "n": gain.count(),
                    "gain": gain.mean(),
                    "unit": "QLIKE gain",
                }
            )
    for arm in ["quarterly", "5pp band"]:
        alternative = prior[
            (prior.study == "H07") & (prior.arm == arm) & (prior.cost_bp == 10)
        ][["holding_month", "net_return"]]
        same = h7.merge(
            alternative,
            left_on="month",
            right_on="holding_month",
            validate="one_to_one",
            suffixes=("", "_other"),
        )
        for phase, group in same.groupby("phase"):
            gain = group.net_return - group.net_return_other
            other.append(
                {
                    "study": "H07",
                    "phase": phase,
                    "alternative": arm,
                    "n": gain.count(),
                    "gain": gain.mean(),
                    "unit": "net return gain",
                }
            )
    pd.DataFrame(other).to_csv(out / "alternative_references.csv", index=False)
    register = pd.read_csv(ROOT / "research/studies.csv").set_index("id")
    scores = []
    for (study, phase), g in monthly.groupby(["study", "phase"]):
        for size in [1, 3, 6]:
            for rule, col in [("paired", "gain"), ("with fallback", "deployed_gain")]:
                a = g.sort_values("month")[col]
                lo, hi, bound = blocks(a, size)
                scores.append(
                    {
                        "study": study,
                        "candidate": LABELS[study],
                        "phase": phase,
                        "sample": rule,
                        "block": size,
                        "months": len(a),
                        "scored": a.count(),
                        "gain": a.mean(),
                        "low": lo,
                        "high": hi,
                        "seven_way_lower": bound,
                        "minimum": register.at[study, "minimum_gain"]
                        if study != "H05"
                        else np.nan,
                    }
                )
    summary = pd.DataFrame(scores)
    summary.to_csv(out / "scorecard.csv", index=False)
    registry = []
    fallback = {
        **BASE,
        "H05": "withhold four-characteristic sleeve",
        "H06": "no-view anchor",
        "H07": "monthly rebalance",
    }
    controls = {
        "H01": (
            "parallel risk forecast",
            "fresh QLIKE gain and funded turnover benefit",
        ),
        "H02": ("volatility diagnostic", "beat rolling and EWMA on fresh paired dates"),
        "H03": ("curve scenario", "archive actual publication vintages and retest"),
        "H04": (
            "valuation diagnostic",
            "stable improvement over expanding mean on fresh dates",
        ),
        "H05": (
            "size and characteristic diagnostics",
            "dated filing panel, rank IC and net sleeve",
        ),
        "H06": (
            "sentiment diagnostic",
            "timestamped message feed and fresh net utility gain",
        ),
        "H07": (
            "parallel rebalancing ledger",
            "fresh costed gain, drift and protected payment checks",
        ),
    }
    for study, ss in summary[
        (summary.block == 3) & (summary["sample"] == "with fallback")
    ].groupby("study"):
        v = ss.set_index("phase")
        hist = v.loc["historical replay"]
        net = portfolios[
            (portfolios.study == study)
            & (portfolios.phase == "historical replay")
            & (portfolios.cost_bp == 10)
        ]
        registry.append(
            {
                "study": study,
                "research_candidate": LABELS[study],
                "validation_gain": v.at["validation", "gain"],
                "replay_gain": hist.gain,
                "replay_seven_way_lower": hist.seven_way_lower,
                "minimum": hist.minimum,
                "positive_both": bool((v.gain > 0).all()),
                "meets_replay_minimum": bool(hist.gain >= hist.minimum)
                if study != "H05"
                else None,
                "costed_monthly_utility_gain": (
                    net.utility - net.reference_utility
                ).mean()
                if len(net)
                else (hist.gain if study == "H06" else np.nan),
                "independent_months": 0,
                "admitted": False,
                "active_reference": fallback[study],
                "research_use": controls[study][0],
                "next_gate": controls[study][1],
            }
        )
    pd.DataFrame(registry).to_csv(out / "signal_register.csv", index=False)
    (out / "manifest.json").write_text(
        json.dumps(
            {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.iterdir())
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results")
    dest = parser.parse_args().output.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=dest.parent) as tmp:
        stage = Path(tmp) / "release"
        stage.mkdir()
        evaluate(stage)
        if dest.exists():
            if {p.name: p.read_bytes() for p in dest.iterdir()} != {
                p.name: p.read_bytes() for p in stage.iterdir()
            }:
                raise ValueError("Output differs. Choose a separate directory.")
        else:
            stage.rename(dest)
    print(f"Verified {dest}")
