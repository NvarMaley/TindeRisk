"""Build the section 6.1 dated frontiers and funded historical comparisons."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from research.frontier.engine import (
    ASSETS,
    TOL,
    Frontier,
    Limits,
    block_paths,
    moments,
)
from riskmatch.intake import Flow, amount, ladder

WEIGHTS = ["w0", "w1", "w2"]
OK = {"reference", "optimal", "optimal_inaccurate", "exact cash"}
SEED = 6101


def reserve(origin, due, capital=50000, payment=15000):
    return ladder(
        origin.date(),
        amount(str(capital)),
        amount("0"),
        [Flow(due.date(), "withdrawal", amount(str(payment)))],
        True,
    )


def screen(prices, origin, excluded=(), unresolved=(), allowed_currency=True):
    recent = prices.loc[:origin].tail(63)
    records = []
    for asset in prices.columns:
        x = recent[asset]
        reasons = []
        if asset in excluded:
            reasons.append("direct exclusion")
        if asset in unresolved:
            reasons.append("unverified look-through")
        if not allowed_currency:
            reasons.append("USD exposure prohibited")
        if len(x) < 63 or (x > 0).sum() < 60:
            reasons.append("insufficient quote coverage")
        if origin not in x.index or not (x.loc[origin] > 0):
            reasons.append("missing decision quote")
        records.append(
            {
                "asset": asset,
                "eligible": not reasons,
                "reason": "; ".join(reasons) or "eligible",
                "observed": int((x > 0).sum()),
            }
        )
    return pd.DataFrame(records)


def paired_fill(prices, origin, end):
    start = prices.loc[(prices.index > origin) & (prices.index <= end)].head(5).dropna()
    finish = (
        prices.loc[(prices.index > origin) & (prices.index <= end)].tail(5).dropna()
    )
    if start.empty or finish.empty or finish.index[-1] <= start.index[0]:
        return None
    return start.index[0], finish.index[-1], finish.iloc[-1] / start.iloc[0] - 1


def funding(row, budget, price_return):
    w = row[[f"w{i}" for i in range(len(price_return))]].to_numpy(dtype=float)
    sleeve = budget["investable"]
    initial = budget["protected"] + sleeve
    final = sleeve * (row.cash + w @ (1 + price_return))
    before = final + budget["protected"]
    paid = min(budget["protected"], budget["required"])
    return {
        "initial": initial,
        "investable": sleeve,
        "fee_chf": sleeve * row.fee,
        "protected": budget["protected"],
        "payment": paid,
        "shortfall": budget["required"] - paid,
        "end_after_payment": before - paid,
        "household_return": before / initial - 1,
    }


def dominance(frame):
    good = frame.status.isin(OK)
    flags = pd.Series(pd.NA, index=frame.index, dtype="boolean")
    for i, r in frame[good].iterrows():
        better = (frame.vol < r.vol - TOL) | (frame.net_mean > r.net_mean + TOL)
        flags[i] = bool(
            (
                good
                & (frame.vol <= r.vol + TOL)
                & (frame.net_mean >= r.net_mean - TOL)
                & better
            ).any()
        )
    return flags


def rank(g):
    g = g[g.status.isin(OK)].copy()
    if g.empty:
        return "unavailable"
    # Rank the three allocations under the same robust objective, treating numerical ties alike.
    score = g.net_mean - g.error
    return "|".join(sorted(g.arm[(score.max() - score) <= TOL]))


def sensitivity(out, data, estimates, elig, cutoff):
    weight_cols = [f"w{i}" for i in range(len(elig))]
    mu, cov, unc = estimates
    choices = ("60/40", "classical", "robust")
    rows = []
    for name, newmu, newcov, l in [
        ("base", mu, cov, Limits()),
        ("SPY mean -2pp", mu - 0.02 * (np.arange(len(mu)) == 0), cov, Limits()),
        ("half diagonal covariance", mu, (cov + np.diag(np.diag(cov))) / 2, Limits()),
        ("zero fee", mu, cov, Limits(fee=0)),
        ("25bp fee", mu, cov, Limits(fee=0.0025)),
        ("USD limit 70%", mu, cov, Limits(usd=0.7)),
        ("single limit 45%", mu, cov, Limits(single=0.45)),
    ]:
        for r in Frontier(newmu, newcov, unc, elig, l).rows(arms=choices):
            rows.append(dict(scenario=name, **r))
    deterministic = pd.DataFrame(rows)
    # Rank altered weights on the frozen base specification too, for a comparable choice across perturbations.
    base = Frontier(mu, cov, unc, elig)

    def evaluate_weights(g):
        feasible = {}
        for r in g[g.status.isin(OK)].itertuples():
            result = base.record(
                np.array([getattr(r, k) for k in weight_cols]), r.cap, 1, "reference"
            )
            if result["residual"] <= TOL:
                feasible[r.arm] = result["objective"]
        if not feasible:
            return "none feasible", 0
        top = max(feasible.values())
        return "|".join(sorted(k for k, v in feasible.items() if top - v <= TOL)), len(
            feasible
        )

    def winners(frame, key):
        result = []
        for (value, cap), g in frame.groupby([key, "cap"]):
            valid = g[g.status.isin(OK)]
            best_net = (
                "unavailable"
                if valid.empty
                else "|".join(
                    sorted(valid.arm[valid.net_mean.max() - valid.net_mean <= TOL])
                )
            )
            best_base, eligible_count = evaluate_weights(g)
            result.append(
                {
                    key: value,
                    "cap": cap,
                    "top_by_net_mean": best_net,
                    "top_by_penalized_mean": rank(g),
                    "top_rescored_under_base": best_base,
                    "eligible_when_rescored": eligible_count,
                }
            )
        return pd.DataFrame(result)

    base_ranks = winners(deterministic, "scenario")
    deterministic.merge(base_ranks, on=["scenario", "cap"]).to_csv(
        out / "scenario_sensitivity.csv", index=False
    )
    rng = np.random.default_rng(SEED + 1000)
    rows = []
    for draw, path in enumerate(block_paths(data, rng, 99)):
        mu2, cov2, unc2 = moments(path, rng, 99)
        for r in Frontier(mu2, cov2, unc2, elig).rows(arms=choices):
            rows.append(dict(draw=draw, **r))
    draws = pd.DataFrame(rows)
    reference = deterministic[deterministic.scenario == "base"][
        ["cap", "arm", *weight_cols]
    ]
    draws = draws.merge(reference, on=["cap", "arm"], suffixes=("", "_base"))
    draws["allocation_distance"] = np.abs(
        draws[weight_cols].to_numpy()
        - draws[[k + "_base" for k in weight_cols]].to_numpy()
    ).sum(axis=1)
    draws.to_parquet(out / "bootstrap.parquet", index=False)
    winners_draw = winners(draws, "draw").merge(
        base_ranks[base_ranks.scenario == "base"], on="cap", suffixes=("", "_base")
    )
    winners_draw.to_csv(out / "bootstrap_ranks.csv", index=False)
    summary = []
    for (cap, arm), g in draws.groupby(["cap", "arm"]):
        ok = g[g.status.isin(OK)]
        row = {
            "origin": cutoff,
            "cap": cap,
            "arm": arm,
            "attempted": len(g),
            "successful": len(ok),
            "failed": len(g) - len(ok),
            "violations": (g.residual > TOL).sum(),
        }
        for key in [
            *weight_cols,
            "vol",
            "net_mean",
            "objective",
            "turnover",
            "allocation_distance",
        ]:
            for q in [0.05, 0.5, 0.95]:
                row[f"{key}_p{int(q * 100):02}"] = ok[key].quantile(q)
        summary.append(row)
    pd.DataFrame(summary).to_csv(out / "dispersion.csv", index=False)


def benchmark_risk(frame, cov):
    weight_cols = [f"w{i}" for i in range(len(cov))]
    for cap, group in frame.groupby("cap"):
        b = group.loc[group.arm == "60/40", weight_cols].iloc[0].to_numpy(dtype=float)
        market_variance = b @ cov @ b
        for idx, r in group[group.status.isin(OK)].iterrows():
            w = r[weight_cols].to_numpy(dtype=float)
            frame.loc[idx, "beta_vs_fixed"] = (
                w @ cov @ b / market_variance if market_variance > 1e-15 else np.nan
            )
            frame.loc[idx, "tracking_error_vs_fixed"] = np.sqrt(
                max(0, (w - b) @ cov @ (w - b))
            )
            frame.loc[idx, "diversification_ratio"] = (
                w @ np.sqrt(np.diag(cov)) / r.vol if r.vol > 1e-7 else np.nan
            )


def prior_check(cov):
    # Conditional benchmark identity: excess-return prior and a noisy relative view.
    weight_cols = [f"w{i}" for i in range(len(cov))]
    b = np.zeros(len(cov))
    b[:2] = [0.6, 0.4]
    delta = 4.0
    tau = 0.05
    p = np.zeros(len(cov))
    p[:2] = [1, -1]
    prior = delta * cov @ b
    q = p @ prior + 0.01
    rows = []
    for error in [np.inf, 1e4, 1.0]:
        v = tau * cov @ p
        posterior = prior + v * (q - p @ prior) / (p @ v + error)
        recovered = np.linalg.solve(delta * cov, posterior)
        rows.append(
            dict(
                view_error_variance=error,
                max_deviation=np.max(np.abs(recovered - b)),
                **dict(zip(weight_cols, recovered)),
            )
        )
    return rows


def dual_checks():
    mu = np.array([0.09, 0.04])
    cov = np.diag([0.04, 0.01])
    v = cov / 30
    model = Frontier(mu, cov, v, [True, True], Limits(single=1, usd=1, fee=0))
    rows = []
    for cap in [0.06, 0.3]:
        r = model.solve(cap, 0)
        for h in [0.0001, 0.00005]:
            left = (r["objective"] - model.solve(cap - h, 0)["objective"]) / h
            right = (model.solve(cap + h, 0)["objective"] - r["objective"]) / h
            rows.append(
                {
                    "cap": cap,
                    "step": h,
                    "dual": r["risk_dual"],
                    "left": left,
                    "right": right,
                    "max_error": max(abs(r["risk_dual"] - v) for v in [left, right]),
                }
            )
    return pd.DataFrame(rows)


def chart(latest, out):
    fig, ax = plt.subplots(figsize=(7.5, 4.6), layout="constrained")
    for arm, marker in [("60/40", "s"), ("classical", "o"), ("robust", "D")]:
        g = latest[(latest.arm == arm) & latest.status.isin(OK)].sort_values("cap")
        ax.plot(
            100 * g.vol, 100 * g.net_mean, "-" + marker, label=arm, linewidth=1.6, ms=5
        )
    ax.set(
        xlabel="Estimated annual sleeve volatility (%)",
        ylabel="Estimated annual net mean (%)",
        title="CHF 35,000 investable sleeve · 30 October 2026",
    )
    ax.grid(alpha=0.2)
    ax.legend()
    fig.savefig(out / "frontier.png", dpi=160)
    plt.close(fig)


def build(out, assets=ASSETS):
    weight_cols = [f"w{i}" for i in range(len(assets))]
    prep = ROOT / "data/prepared_v1"
    path = prep / "market.parquet"
    expected = json.loads((prep / "manifest.json").read_text())[path.name]
    with path.open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != expected:
            raise ValueError("Market input changed")
    market = pd.read_parquet(path)
    market = market[market.asset.isin(assets)].copy()
    market["price"] = market.adjusted_usd * market.chf_per_usd

    def wide(col):
        return market.pivot(index="session", columns="asset", values=col)[
            list(assets)
        ].sort_index()

    prices = wide("price")
    ret = wide("chf_return")
    origins = [ret.loc[: f"{year}-10"].index[-1] for year in range(2019, 2027)]
    all_rows = []
    screens = []
    fits = []
    realized = []
    for i, origin in enumerate(origins):
        hist = ret.loc[ret.index < origin].tail(756)
        elig = screen(prices, origin)
        screens.append(elig.assign(origin=origin, scenario="base"))
        mask = elig.eligible.to_numpy()
        # Base sample gate was frozen for the complete universe.
        if len(hist) != 756 or len(hist.dropna()) < 719:
            raise ValueError(f"Insufficient training coverage at {origin}")
        estimates = moments(hist.to_numpy(), np.random.default_rng(SEED + i), 199)
        mu, cov, v = estimates
        fits.append(
            {
                "origin": str(origin.date()),
                "first": str(hist.index[0].date()),
                "last": str(hist.index[-1].date()),
                "scheduled": len(hist),
                "observed": len(hist.dropna()),
                "annual_mean": mu.tolist(),
                "covariance": cov.tolist(),
                "mean_uncertainty": v.tolist(),
                "min_cov_eigenvalue": np.linalg.eigvalsh(cov).min(),
                "min_uncertainty_eigenvalue": np.linalg.eigvalsh(v).min(),
            }
        )
        due = (
            origins[i + 1] if i + 1 < len(origins) else origin + pd.DateOffset(years=1)
        )
        budget = reserve(origin, due)
        frame = pd.DataFrame(Frontier(*estimates, mask).rows())
        benchmark_risk(frame, cov)
        frame["dominated_on_net_mean"] = dominance(frame)
        frame["origin"] = origin
        frame["investable_chf"] = budget["investable"]
        frame["reserve_chf"] = budget["protected"]
        for col, name in zip(weight_cols, assets):
            frame[name + "_chf"] = frame[col] * budget["investable"]
        frame["sleeve_cash_chf"] = frame.cash * budget["investable"]
        frame["fee_chf"] = frame.fee * budget["investable"]
        all_rows.append(frame)
        if i + 1 < len(origins):
            marks = paired_fill(prices, origin, due)
            for _, row in frame.iterrows():
                base = {"origin": origin, "due": due, "arm": row.arm, "cap": row.cap}
                if marks is None or row.status not in OK:
                    realized.append(dict(**base, status="unscored"))
                    continue
                fill, end, ret1 = marks
                realized.append(
                    dict(
                        **base,
                        fill=fill,
                        mark=end,
                        status="scored",
                        **funding(row, budget, ret1),
                    )
                )
    latest = all_rows[-1]
    pd.concat(all_rows).to_csv(out / "frontiers.csv", index=False)
    latest.to_csv(out / "latest.csv", index=False)
    (out / "training.json").write_text(json.dumps(fits, indent=2) + "\n")
    cases = []
    for name, keys, limits, cap, capital in [
        ("direct gold exclusion", {"excluded": ["GLD"]}, Limits(), 0.08, 50000),
        (
            "look-through unknown",
            {"unresolved": list(assets)},
            Limits(),
            0.08,
            50000,
        ),
        ("CHF-only", {"allowed_currency": False}, Limits(), 0.08, 50000),
        ("zero risk", {}, Limits(), 0, 50000),
        ("mandatory risk at zero cap", {}, Limits(minimum=0.2), 0, 50000),
        ("required exceeds USD limit", {}, Limits(minimum=0.95), 0.16, 50000),
        ("reserve consumes capital", {}, Limits(), 0.08, 15000),
        ("reserve shortfall", {}, Limits(), 0.08, 10000),
    ]:
        e = screen(prices, origin, **keys)
        screens.append(e.assign(origin=origin, scenario=name))
        b = reserve(origin, due, capital)
        if b["investable"] > 0:
            r = Frontier(*estimates, e.eligible.to_numpy(), limits).solve(cap, 0)
        else:
            r = {"status": "mandate infeasible" if b["shortfall"] else "reserve only"}
        cases.append(
            dict(
                scenario=name,
                cap=cap,
                protected=b["protected"],
                investable=b["investable"],
                shortfall=b["shortfall"],
                **r,
            )
        )
    pd.DataFrame(cases).to_csv(out / "mandate_cases.csv", index=False)
    pd.concat(screens).to_csv(out / "eligibility.csv", index=False)
    history = pd.DataFrame(realized)
    baseline = history[history.arm == "60/40"][
        ["origin", "cap", "household_return"]
    ].rename(columns={"household_return": "fixed_mix_return"})
    history = history.merge(baseline, on=["origin", "cap"])
    history["paired_gain"] = history.household_return - history.fixed_mix_return
    history.to_csv(out / "realized.csv", index=False)
    summary = (
        history.groupby(["arm", "cap"])
        .agg(
            scheduled=("origin", "size"),
            scored=("household_return", "count"),
            mean=("household_return", "mean"),
            variance=("household_return", "var"),
            mean_fee_chf=("fee_chf", "mean"),
            mean_paired_gain=("paired_gain", "mean"),
            worst_gap=("shortfall", "max"),
        )
        .reset_index()
    )
    summary["illustrative_score"] = summary["mean"] - 2 * summary.variance
    summary.to_csv(out / "historical_summary.csv", index=False)
    sensitivity(out, hist.to_numpy(), estimates, mask, str(origin.date()))
    pd.DataFrame(prior_check(cov)).to_csv(out / "conditional_prior.csv", index=False)
    dual_checks().to_csv(out / "duals.csv", index=False)
    chart(latest, out)
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
        build(stage)
        if dest.exists():
            if (dest / "manifest.json").read_bytes() != (
                stage / "manifest.json"
            ).read_bytes() or any(
                not (dest / p.name).is_file()
                or (dest / p.name).read_bytes() != p.read_bytes()
                for p in stage.iterdir()
            ):
                raise ValueError("Release differs; choose a new output directory")
        else:
            stage.rename(dest)
    print(f"Verified {dest}")
