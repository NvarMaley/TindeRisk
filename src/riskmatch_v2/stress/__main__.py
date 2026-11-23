"""Run from the V2 repository: python -m riskmatch_v2.stress."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from .events import study
from .exposures import aggregation, bootstrap, estimate, portfolio_paths
from .inputs import LOCAL, REPORT, inputs, shock_counts
from .scenarios import attribution, bond_table


def records(df):
    return json.loads(df.to_json(orient="records", double_precision=12))


def run():
    LOCAL.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(exist_ok=True)
    config = Path("config/stress-8.json")
    cfg = json.loads(config.read_bytes())
    parent = json.loads(Path(cfg["parent"]).read_bytes())
    inv, weights, usd, chf, f, regime, bonds, rates, y2, y10 = inputs(cfg, parent)
    counts = shock_counts(f, regime, cfg)
    print("Dated factors prepared", flush=True)
    portfolios = portfolio_paths(chf, weights)
    usd_ports = portfolio_paths(usd, weights)
    cc = chf.join(portfolios)
    est = estimate(f, usd.join(usd_ports), cc, cfg, parent)
    oil = est.query("factor=='oil'").pivot(index="id", columns="variant", values="beta")
    contemporaneous = ["rolling_" + str(o) for o in cfg["rolling_offsets"]] + [
        "double_window",
        "reduced",
        "trim_oil_tails",
        "local_USD",
    ]
    joint = oil.reindex(index=inv.index, columns=contemporaneous).dropna()
    sign = joint.gt(0).nunique(axis=1)
    print("Estimated", len(est), "coefficient records", flush=True)
    base = est.query("variant=='rolling_0'")
    index_sheet = inv[["symbol", "class", "reason", "included"]].copy()
    index_sheet["measured"] = index_sheet.index.isin(base.id)
    index_sheet["oil_sign_across_variants"] = sign.map(
        {1: "Consistent", 2: "Conflicting"}
    )
    index_sheet["oil_sign_across_variants"] = (
        index_sheet.oil_sign_across_variants.fillna("Incomplete comparison")
    )
    idx = base.query("factor=='oil'").set_index("id")
    index_sheet["oil_interval_excludes_zero"] = (
        ((idx.low > 0) | (idx.high < 0)).reindex(index_sheet.index).astype("boolean")
    )
    index_sheet["oil_interpretation"] = "Unestimated"
    index_sheet.loc[index_sheet.measured, "oil_interpretation"] = "Uncertain"
    index_sheet.loc[
        (index_sheet.oil_sign_across_variants == "Consistent")
        & index_sheet.oil_interval_excludes_zero.fillna(False),
        "oil_interpretation",
    ] = "Consistent sign and interval excludes zero"
    control = aggregation(f, chf, weights, cfg)
    episode, replay = study(
        usd, rates, bonds, portfolios, f, y10, cfg, parent, weights, chf
    )
    bond_cases = bond_table(parent["end"], y2.iloc[-1], y10.iloc[-1], cfg)
    ledger, cases = attribution(est, bond_cases, weights, cfg)
    # Conditional empirical mean returns by sign and prior volatility regime.
    groups = []
    for row in counts:
        ok = (f.index > cfg["calibration_end"]) & regime.eq(row["regime"])
        for side, mask in [
            ("Down", f.oil <= row["lower"]),
            ("Up", f.oil >= row["upper"]),
        ]:
            sample = cc.loc[ok & mask]
            table = pd.DataFrame(
                {
                    "n": sample.count(),
                    "mean_chf": sample.mean().where(sample.count() >= 5),
                }
            )
            groups.append(
                table.rename_axis("id")
                .reset_index()
                .assign(rule=row["rule"], regime=row["regime"], side=side)
            )
    tails = pd.concat(groups, ignore_index=True)
    ids = ["XLE", "GLD", "IEF", "PERMNO:11850", "PERMNO:14593", *portfolios.columns]
    examples = (
        idx.reindex(ids)
        .dropna(subset=["beta"])[["n", "beta", "low", "high", "pearson", "spearman"]]
        .copy()
    )
    examples[["beta", "low", "high"]] *= 1000
    examples.index = [
        inv.at[k, "symbol"] if k in inv.index else k for k in examples.index
    ]
    example_conflict = index_sheet.loc[
        index_sheet.oil_sign_across_variants.eq("Conflicting")
    ].head(5)
    bond_joint = bond_cases.query("scenario=='Joint'").sort_values("modified_duration")
    out = {
        "end": parent["end"],
        "universe": len(inv),
        "factor_counts": f.count().to_dict(),
        "common_factors": int(f.notna().all(axis=1).sum()),
        "session_count": len(f),
        "regime_counts": regime.value_counts().to_dict(),
        "shocks": counts,
        "coverage": records(
            index_sheet.groupby("class").measured.agg(["size", "sum"]).reset_index()
        ),
        "sign_counts": sign.value_counts()
        .rename(index={1: "Consistent", 2: "Conflicting"})
        .to_dict(),
        "lag_sign_comparison": records(
            oil.reindex(inv.index)[["rolling_0", "lag_one"]]
            .dropna()
            .assign(same=lambda t: (t.rolling_0 > 0) == (t.lag_one > 0))
            .groupby("same")
            .size()
            .rename("instruments")
            .reset_index()
        ),
        "excluded_crises_comparison": records(
            oil.reindex(inv.index)[["history", "history_excluding_crises"]]
            .dropna()
            .assign(same=lambda t: (t.history > 0) == (t.history_excluding_crises > 0))
            .groupby("same")
            .size()
            .rename("instruments")
            .reset_index()
        ),
        "measured_eligible": int((index_sheet.included & index_sheet.measured).sum()),
        "incomplete_sign": len(inv) - len(sign),
        "interpretation": index_sheet.oil_interpretation.value_counts().to_dict(),
        "conflicting_examples": records(
            oil.loc[
                example_conflict.index,
                ["rolling_0", "rolling_252", "lag_one", "local_USD"],
            ].join(example_conflict.symbol)
        ),
        "example_oil_plus10_pct": records(examples.rename_axis("name").reset_index()),
        "controls": control,
        "tail_example": records(tails[tails.id.eq("60/40 benchmark")]),
        "episode_counts": records(
            episode.groupby(["episode", "status"])
            .size()
            .rename("instruments")
            .reset_index()
        ),
        "episode_examples": records(episode[episode.id.isin(["SPY", "IEF", "GLD"])]),
        "replays": replay,
        "bond_events": records(
            episode[episode.id.str.startswith("UST:")]
            .groupby(["episode", "status"])
            .size()
            .rename("instruments")
            .reset_index()
        ),
        "bootstrap": {
            k: bootstrap(
                f.iloc[-cfg["window"] :],
                portfolios[k].iloc[-cfg["window"] :],
                cfg["bootstrap"],
            )
            for k in portfolios
        },
        "cases": cases,
        "bonds_repriced": len(bond_joint),
        "bond_examples": records(bond_joint.iloc[[0, len(bond_joint) // 2, -1]]),
    }
    tracked = [
        config,
        Path(cfg["parent"]),
        *sorted(Path(__file__).parent.glob("*.py")),
        Path("src/riskmatch_v2/econometrics.py"),
        Path("src/riskmatch_v2/universe/data.py"),
        Path("src/riskmatch_v2/universe/treasury.py"),
        Path("data/local/univers") / parent["source_snapshot"] / "manifest.json",
        LOCAL / "DGS2.csv",
        Path("config/sources-4.json"),
    ]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
    stamp = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16]
    out["archive"] = stamp
    dest = LOCAL / stamp
    if not dest.exists():
        with TemporaryDirectory(dir=LOCAL) as tmp:
            stage = Path(tmp) / "archive"
            stage.mkdir()
            for name, frame in {
                "factors": f.assign(regime=regime),
                "security_index": index_sheet,
                "exposures": est,
                "historical_crises": episode,
                "oil_tails": tails,
                "attribution": ledger,
                "bonds": bond_cases,
            }.items():
                frame.to_parquet(stage / (name + ".parquet"))
            (stage / "inputs.json").write_text(json.dumps(hashes, indent=2))
            stage.rename(dest)
    (REPORT / "results.json").write_text(
        json.dumps(out, indent=2, allow_nan=False) + "\n"
    )
    print("Private archive", dest, flush=True)


if __name__ == "__main__":
    run()
