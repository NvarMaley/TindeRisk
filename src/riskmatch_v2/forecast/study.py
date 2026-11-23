"""Run the section 12 protocol from the frozen section 4/6/7/8 archives."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .evaluation import calibrate, combination, judge, split
from .models import black_litterman, forecast, matured, ridge
from .overheating import overheating
from .portfolios import notices
from .registry import controls
from .sources import CONFIG, RAW, REPORT, asof, collect, frame

FAMILY = {
    "realized": "Quantitative",
    "momentum": "Quantitative",
    "liquidity": "Quantitative",
    "curve": "Macro",
    "unemployment": "Macro",
    "tone": "Sentiment",
    "gpr": "Geopolitical",
    "vix": "Market",
}


def write(name, value):
    def scalar(v):
        if isinstance(v, np.generic):
            return v.item()
        raise TypeError(type(v))

    (REPORT / name).write_text(
        json.dumps(value, indent=2, allow_nan=False, default=scalar) + "\n"
    )


def checks():
    # One observation revised and one duplicated text near the DST boundary.
    times = ["2020-10-30T21:30Z", "2020-11-02T21:30Z"]
    vals = pd.Series([1.0, 9.0], index=times)
    before, after = asof(vals, ["2020-11-02T21:00Z", "2020-11-03T21:00Z"], 7)
    documents = pd.DataFrame(
        {"digest": ["same", "same", "new"], "day": [1, 2, 3]}
    ).drop_duplicates("digest")
    assert before == 1 and after == 9 and len(documents) == 2
    return {
        "prior_release": before,
        "first_after_revision": after,
        "unique_from_three": len(documents),
        "local_closes_utc": [
            str(pd.Timestamp(d + " 16:00", tz="America/New_York").tz_convert("UTC"))
            for d in ["2020-10-30", "2020-11-02"]
        ],
    }


def input_lock(cfg):
    def sha(p):
        with p.open("rb") as fp:
            return hashlib.file_digest(fp, "sha256").hexdigest()

    # Fingerprint canonically date-bounded inputs where the provider appends new rows.
    vix = (
        pd.read_csv(RAW / "vix.csv", parse_dates=["DATE"])
        .set_index("DATE")
        .sort_index()
        .loc[: cfg["decision"], "CLOSE"]
    )
    norm = lambda frame: hashlib.sha256(
        frame.to_csv(index=True, float_format="%.12g").encode()
    ).hexdigest()
    hashes = {
        "vix_through_cut": norm(vix),
        "statements": norm(pd.read_parquet(RAW / "statements.parquet")),
        "gpr_editions": norm(pd.read_parquet(RAW / "gpr.parquet")),
    }
    for p in [
        CONFIG,
        Path("data/local/4/raw/macro_releases.parquet"),
        Path("data/local/4/4.0-2026-11-23/prices.parquet"),
        Path("data/local/8/DGS2.csv"),
        Path("data/local/4/raw/DGS10.csv"),
    ]:
        hashes[p.name] = sha(p)
    lock = REPORT / "sources.json"
    if lock.exists() and json.loads(lock.read_text()) != hashes:
        raise ValueError("Published input lock differs; create a new study version")
    write("sources.json", hashes)
    return hashes


def main():
    cfg = json.loads(CONFIG.read_text())
    REPORT.mkdir(exist_ok=True, parents=True)
    collect()
    hashes = input_lock(cfg)
    r, f, prices, inventory = frame()
    scores = []
    registry = []
    mixes = {}
    calibration = {}
    view = {}
    local = RAW.parent
    import arch

    for h in cfg["horizons"]:
        for target, t in forecast(r, f, h, cfg).items():
            key = f"{target}-{h}"
            t.to_parquet(local / (key + ".parquet"))
            names = [c for c in t if c.startswith(("alone_", "increment_"))]
            if target == "variance":
                names = ["ewma", "garch", *names]
            validation = split(t, cfg, False)
            final = split(t, cfg, True)
            published = pd.concat(
                [validation.assign(block="validation"), final.assign(block="final")]
            )
            columns = ["end", "cut", "block", target, "baseline", *names]
            if target == "return":
                columns += ["frequency", "probability", "lower", "upper"]
            published.index.name = "decision"
            published[columns].to_csv(
                REPORT / (key + "-predictions.csv"), float_format="%.10g"
            )
            val = {n: judge(validation, n, target, r, cfg) for n in names}
            mix = combination(t, names, val, cfg, r, target)
            mixes[key] = mix
            last = f.iloc[-1].copy()
            past = matured(t, r.index[-1], cfg["final_start"])
            last["baseline"] = float(
                r.iloc[-64:-1].pow(2).mean()
                if target == "variance"
                else 0.5 * past["return"].mean()
            )
            for n in names:
                test = judge(final, n, target, r, cfg)
                passed = val[n]["passed"] and test["passed"]
                reason = (
                    "Historical gates passed; original market-data vintages unverified"
                    if passed
                    else "Validation: " + val[n]["reason"]
                    if not val[n]["passed"]
                    else "Final: " + test["reason"]
                )
                scores.append(
                    {
                        "target": target,
                        "horizon": h,
                        "model": n,
                        "validation": val[n],
                        "final": test,
                        "research_pass": passed,
                    }
                )
                feature = n.partition("_")[2]
                if n == "ewma":
                    pred = np.average(
                        r.iloc[-64:-1].pow(2), weights=0.94 ** np.arange(62, -1, -1)
                    )
                elif n == "garch":
                    hist = r.iloc[-757:-1].dropna() * 100
                    fit = arch.arch_model(
                        hist, mean="Zero", p=1, q=1, rescale=False
                    ).fit(disp="off", show_warning=False)
                    pred = (
                        fit.forecast(horizon=h + 1).variance.iloc[-1, 1:].mean() / 10000
                        if fit.convergence_flag == 0
                        else np.nan
                    )
                else:
                    pred = ridge(
                        past,
                        last,
                        [feature],
                        target,
                        n.startswith("increment_"),
                        cfg["ridge_alpha"],
                    )
                measure = last.get(feature, np.nan)
                registry.append(
                    {
                        "name": n,
                        "scope": "SPY in CHF",
                        "target": target,
                        "horizon": h,
                        "version": 1,
                        "issued": "2026-11-23",
                        "measured_at": cfg["decision"],
                        "expires": "2026-12-04",
                        "family": FAMILY.get(feature, "Variance model"),
                        "input": float(measure) if pd.notna(measure) else None,
                        "reference": last.baseline,
                        "estimate": float(pred) if np.isfinite(pred) else None,
                        "direction": (
                            "above"
                            if pred > last.baseline
                            else "below"
                            if pred < last.baseline
                            else "equal"
                        )
                        if np.isfinite(pred)
                        else "unavailable",
                        "status": "research only" if passed else "rejected",
                        "weight": 0.0,
                        "reason": reason,
                    }
                )
            if target == "return":
                for label, part in [("validation", validation), ("final", final)]:
                    calibration[label] = calibrate(part, cfg)
                calibration["probability_eligible"] = all(
                    z["probability_pass"]
                    for z in [calibration["validation"], calibration["final"]]
                )
                calibration["interval_eligible"] = all(
                    z["interval_pass"]
                    for z in [calibration["validation"], calibration["final"]]
                )
                sparse = final.copy()
                sparse["return"] = 0.01
                sparse.iloc[0, sparse.columns.get_loc("return")] = -0.06
                shifted = final.copy()
                shifted["return"] = shifted.upper + 0.01
                calibration["controls"] = {
                    "sparse_probability": calibrate(sparse, cfg)["probability_pass"],
                    "shifted_interval": calibrate(shifted, cfg)["interval_pass"],
                }
                # Research diagnostic: pick the strongest validation MSE increment, freeze uncertainty there.
                candidates = [
                    n
                    for n in names
                    if n.startswith("increment_") and val[n].get("coverage", 0) >= 0.8
                ]
                best = max(candidates, key=lambda n: val[n]["gain"])
                omega = float((validation[best] - validation["return"]).pow(2).mean())
                # tau*Sigma is the variance of the mean of matured return blocks at the decision.
                uncertainty = np.array(
                    [
                        matured(t, d, cfg["final_start"])["return"].var()
                        / len(matured(t, d, cfg["final_start"]))
                        for d in final.index
                    ]
                )
                trial = final.copy()
                trial["posterior"] = [
                    black_litterman(p, q, v, omega)
                    for p, q, v in zip(final.baseline, final[best], uncertainty)
                ]
                zero = black_litterman(0.01, 0.09, 0.001, np.inf)
                assert zero == 0.01
                view = {
                    "candidate": best,
                    "P": [[1]],
                    "omega": omega,
                    "prior_uncertainty_last": uncertainty[-1],
                    "zero_confidence": zero,
                    "final": judge(trial, "posterior", target, r, cfg),
                    "deployed": False,
                }
    write("registry.json", registry)
    write("experiments.json", scores)
    heat = overheating(prices, cfg)
    write("overheating-months.json", heat.pop("records"))
    ports, funding = notices(registry)

    write(
        "results.json",
        {
            "decision": cfg["decision"],
            "protocol_sha": hashes[CONFIG.name],
            "sessions": len(r),
            "start": str(r.index[0].date()),
            "features": inventory,
            "release_controls": checks(),
            "combinations": mixes,
            "calibration": calibration,
            "black_litterman": view,
            "overheating": heat,
            "portfolios": ports,
            "funding": funding,
            "registry_controls": controls(),
            "previous_universe": json.loads(
                Path("reports/econometrie/results.json").read_text()
            )["forecasts"],
        },
    )
    print(
        "Forecast candidates",
        len(scores),
        "research gates passed",
        sum(z["research_pass"] for z in scores),
    )


if __name__ == "__main__":
    main()
