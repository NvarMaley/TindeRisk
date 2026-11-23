"""Rebuild the dated 6.2 client option and goal report from frozen inputs."""

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
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from research.options.model import (
    ASSETS,
    CAPITAL,
    FEE,
    RESERVE,
    SLEEVE,
    comparison,
    eligible,
    flat_adjustments,
    gap_stats,
    monthly_levels,
    pairs,
    reverse,
    simulate,
    year_blocks,
)
from riskmatch.interview import report

ORIGIN = pd.Timestamp("2026-10-30")
CAPS = (0.04, 0.08)
PROFILE = report({"C01": "yes", "C03": "yes", "C04": "yes"})
SCENARIOS = [
    ("base", 8, 100, 0.02, 65000),
    ("zero inflation", 8, 100, 0, 65000),
    ("4% inflation", 8, 100, 0.04, 65000),
    ("save CHF 250", 8, 250, 0.02, 65000),
    ("10 years", 10, 100, 0.02, 65000),
    ("CHF 55,000 goal", 8, 100, 0.02, 55000),
    ("reversed years", 8, 100, 0.02, 65000),
]


def checked(folder, name):
    path = folder / name
    with path.open("rb") as f:
        if (
            hashlib.file_digest(f, "sha256").hexdigest()
            != json.loads((folder / "manifest.json").read_text())[name]
        ):
            raise ValueError(f"Input mismatch: {name}")
    return path


def first_month_range(gross, origin, w, fee, assets=ASSETS):
    month = origin.to_period("M")
    sample = gross.loc[month - 36 : month - 1].dropna()
    if len(sample) < 30:
        raise ValueError("Insufficient monthly coverage")
    chf = sample[list(assets)].mul(sample.FX, axis=0) - 1
    estimate = SLEEVE / CAPITAL * (chf.to_numpy() @ w - fee)
    return np.quantile(estimate, [0.1, 0.9]), len(sample)


def calibration(frontiers, history, daily, monthly, gross, assets=ASSETS):
    assets = list(assets)
    weights = [f"w{i}" for i in range(len(assets))]
    rows = []
    for (origin, cap), g in frontiers.groupby(["origin", "cap"]):
        origin = pd.Timestamp(origin)
        if cap not in CAPS or origin >= ORIGIN:
            continue
        for _, r in eligible(g, cap, weights).iterrows():
            h = history[
                (history.origin == str(origin.date()))
                & (history.cap == cap)
                & (history.arm == r.arm)
            ].iloc[0]
            month = origin.to_period("M") + 1
            bounds, n = first_month_range(
                gross, origin, r[weights].to_numpy(float), r.fee, assets
            )
            observed = np.nan
            if h.status == "scored" and pd.notna(monthly.loc[month, "mark"]):
                start = daily.loc[pd.Timestamp(h.fill)]
                end = monthly.loc[month]
                if end.mark >= pd.Timestamp(h.fill):
                    ret = (
                        end[assets].to_numpy(float) / start[assets].to_numpy(float)
                    ) * (end.FX / start.FX) - 1
                    observed = (
                        SLEEVE / CAPITAL * (ret @ r[weights].to_numpy(float) - r.fee)
                    )
            rows.append(
                {
                    "origin": origin,
                    "cap": cap,
                    "arm": r.arm,
                    "low": bounds[0],
                    "high": bounds[1],
                    "training": n,
                    "observed": observed,
                    "covered": float(bounds[0] - 1e-10 <= observed <= bounds[1] + 1e-10)
                    if np.isfinite(observed)
                    else np.nan,
                }
            )
    return pd.DataFrame(rows)


def build(out, assets=ASSETS, frontier_dir=None):
    assets = list(assets)
    weights = [f"w{i}" for i in range(len(assets))]
    f = frontier_dir or ROOT / "research/frontier/results"
    latest, history, frontiers, variants = [
        pd.read_csv(checked(f, x + ".csv"))
        for x in ("latest", "realized", "frontiers", "scenario_sensitivity")
    ]
    market = pd.read_parquet(checked(ROOT / "data/prepared_v1", "market.parquet"))
    daily, monthly, long_gross = monthly_levels(market, assets)
    gross = long_gross.loc[ORIGIN.to_period("M") - 240 : ORIGIN.to_period("M") - 1]
    years, picks, starts = year_blocks(gross)
    # Calibration uses the full historical monthly panel, always sliced strictly before its origin.
    calib = calibration(frontiers, history, daily, monthly, long_gross, assets)
    calib.to_csv(out / "range_calibration.csv", index=False)
    if assets == ASSETS:
        frozen = pd.read_csv(
            checked(ROOT / "research/shocks/results", "scenario_holdings.csv")
        )
        shock = (
            frozen[
                (frozen.cutoff == str(ORIGIN.date()))
                & (frozen.scenario == "Joint shock")
                & (frozen.mix == "Equal weight")
            ]
            .set_index("asset")
            .loc[assets]
        )
        shock_return = (shock.contribution / shock.weight).to_numpy()
    else:
        from research.shocks.analysis import SHOCKS, fit, training_window
        from research.shocks.build import load_panel

        beta, _, _ = fit(training_window(load_panel(assets), ORIGIN), 200, assets)
        shock = SHOCKS["Joint shock"]
        shock_return = (1 + np.array(shock[:3]) @ beta[1:]) * (1 + shock[3]) - 1
    chf = gross[assets].mul(gross.FX, axis=0) - 1
    cards = []
    pair_rows = []
    goals = []
    trajectory = []
    stress = []
    adjust = []
    for cap in CAPS:
        group = eligible(latest, cap, weights)
        if group.empty:
            raise ValueError("No feasible options")
        for basis, a in [("household", SLEEVE / CAPITAL), ("sleeve", 1.0)]:
            pair_rows.extend(
                dict(cap=cap, basis=basis, **r) for r in pairs(group, PROFILE, a)
            )
        for _, r in group.iterrows():
            key = {"cap": cap, "arm": r.arm}
            w = r[weights].to_numpy(float)
            history_arm = history[
                (history.cap == cap)
                & (history.arm == r.arm)
                & (history.status == "scored")
            ]
            bounds, n = first_month_range(gross, ORIGIN, w, r.fee, assets)
            empir = (chf @ w).dropna()
            a = SLEEVE / CAPITAL
            hmu, hvol = a * r.net_mean, a * r.vol
            coverage = calib[(calib.cap == cap) & (calib.arm == r.arm)].covered
            card = dict(
                **key,
                origin=str(ORIGIN.date()),
                annual_household_mean=hmu,
                annual_household_vol=hvol,
                annual_sleeve_mean=r.net_mean,
                annual_sleeve_vol=r.vol,
                sharpe=hmu / hvol if hvol > 1e-10 else None,
                household_low_phi_score=hmu - PROFILE["low"] * hvol**2 / 2,
                household_high_phi_score=hmu - PROFILE["high"] * hvol**2 / 2,
                monthly_p10=bounds[0],
                monthly_p90=bounds[1],
                range_months=n,
                coverage_hits=int(coverage.sum()),
                coverage_count=coverage.count(),
                historical_count=len(history_arm),
                historical_household_mean=history_arm.household_return.mean(),
                historical_household_min=history_arm.household_return.min(),
                historical_household_max=history_arm.household_return.max(),
                joint_shock_pnl_chf=SLEEVE * (w @ shock_return),
                worst_month_pnl_chf=SLEEVE * empir.min(),
                worst_month=str(empir.idxmin()) if w.sum() > 1e-10 else None,
                available_sleeve_cash=r.sleeve_cash_chf,
                protected_chf=RESERVE,
                entry_fee_chf=r.fee_chf,
                **{name: r[name] for name in [a + "_chf" for a in assets]},
            )
            cards.append(card)
            scenario_paths = {
                100: simulate(years, w, 100),
                250: simulate(years, w, 250),
            }
            rev = simulate(years[:, :8][:, ::-1], w, 100)
            for label, horizon, saving, inflation, target in SCENARIOS:
                path = rev if label == "reversed years" else scenario_paths[saving]
                outcome = path[horizon - 1]["terminal"]
                due = target * (1 + inflation) ** horizon
                goals.append(
                    dict(
                        **key,
                        scenario=label,
                        years=horizon,
                        saving=saving,
                        inflation=inflation,
                        real_target=target,
                        nominal_target=due,
                        **gap_stats(outcome, due),
                    )
                )
            for year, p in enumerate(scenario_paths[100][:8], 1):
                trajectory.append(
                    dict(
                        **key,
                        year=year,
                        date=(ORIGIN + pd.DateOffset(years=year)).date(),
                        paid_from_reserve=RESERVE if year == 1 else 0,
                        remaining_reserve=0,
                        p10=np.quantile(p["terminal"], 0.1),
                        median=np.median(p["terminal"]),
                        p90=np.quantile(p["terminal"], 0.9),
                        median_review_fee=np.median(p["fee"]),
                    )
                )
            flat = simulate(np.ones((1, 1, len(assets))), w, 100)[0]
            for name, bill, cash, securities, saleable in [
                (
                    "reserved",
                    15000,
                    RESERVE + flat["cash"][0],
                    flat["securities"][0],
                    True,
                ),
                (
                    "larger at one year",
                    22000,
                    RESERVE + flat["cash"][0],
                    flat["securities"][0],
                    True,
                ),
                (
                    "earlier, unsettled",
                    22000,
                    RESERVE + r.sleeve_cash_chf,
                    SLEEVE * w.sum(),
                    False,
                ),
            ]:
                resources = (
                    RESERVE + r.sleeve_cash_chf
                    if not saleable
                    else scenario_paths[100][0]["withdrawal_resources"]
                )
                short = np.maximum(bill - resources, 0)
                stress.append(
                    dict(
                        **key,
                        case=name,
                        bill=bill,
                        **reverse(cash, securities, bill, saleable),
                        sampled_gap_frequency=np.mean(short > 1e-6),
                        sampled_mean_gap_chf=np.mean(short),
                        resources_p10=np.quantile(resources, 0.1),
                        resources_p90=np.quantile(resources, 0.9),
                    )
                )
            adjust.append(dict(**key, **flat_adjustments(w)))
    for name, table in [
        ("options", cards),
        ("pairwise", pair_rows),
        ("goal_scenarios", goals),
        ("funding_path", trajectory),
        ("reverse_stress", stress),
        ("goal_adjustments", adjust),
    ]:
        pd.DataFrame(table).to_csv(out / (name + ".csv"), index=False)
    annual_pairs = []
    for row in pair_rows:
        if row["basis"] != "household":
            continue
        sample = history[
            (history.cap == row["cap"]) & (history.status == "scored")
        ].pivot(index="origin", columns="arm", values="household_return")
        sample = sample[[row["first"], row["second"]]].dropna()
        first, second = sample.iloc[:, 0], sample.iloc[:, 1]
        actual = comparison(
            first.mean() - second.mean(), first.var() - second.var(), PROFILE
        )
        annual_pairs.append(
            {
                "cap": row["cap"],
                "first": row["first"],
                "second": row["second"],
                "years": len(sample),
                "estimated": row["result"],
                "historical": actual["result"],
                "historical_left": actual["left"],
                "historical_right": actual["right"],
                "historical_crossover": actual["crossover"],
            }
        )
    pd.DataFrame(annual_pairs).to_csv(out / "ranking_history.csv", index=False)
    var_rows = []
    for (name, cap), g in variants[variants.cap.isin(CAPS)].groupby(
        ["scenario", "cap"]
    ):
        var_rows.extend(
            dict(scenario=name, cap=cap, **r)
            for r in pairs(
                g[
                    g.status.isin(
                        ["reference", "exact cash", "optimal", "optimal_inaccurate"]
                    )
                ],
                PROFILE,
                SLEEVE / CAPITAL,
            )
        )
    pd.DataFrame(var_rows).to_csv(out / "model_sensitivity.csv", index=False)
    examples = []
    for name, answers in [
        ("bounded", {"C01": "yes", "C03": "yes", "C04": "yes"}),
        ("one-sided", {"C01": "yes", "C03": "yes"}),
        ("conflicting", {"C01": "yes", "C04": "no", "C03": "no"}),
        ("unresolved", {}),
    ]:
        p = report(answers)
        examples.append(
            {
                "case": name,
                "answers": answers,
                "status": p["status"],
                "low": p["low"],
                "high": p["high"],
                "example_pair": comparison(0.02, 0.012, p)["result"],
            }
        )
    meta = {
        "origin": str(ORIGIN.date()),
        "profiles": examples,
        "transfer": "unverified",
        "independent_months": 0,
        "fee": FEE,
        "blocks": len(starts),
        "months": len(gross.dropna()),
        "first_month": str(gross.index[0]),
        "last_month": str(gross.index[-1]),
        "seed": 6202,
        "paths": len(picks),
    }
    (out / "design.json").write_text(json.dumps(meta, indent=2) + "\n")
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
    dest.parent.mkdir(exist_ok=True, parents=True)
    with TemporaryDirectory(dir=dest.parent) as tmp:
        stage = Path(tmp) / "release"
        stage.mkdir()
        build(stage)
        if dest.exists():
            if {p.name: p.read_bytes() for p in dest.iterdir()} != {
                p.name: p.read_bytes() for p in stage.iterdir()
            }:
                raise ValueError("Release differs; choose new --output")
        else:
            stage.rename(dest)
    print(f"Verified {dest}")
