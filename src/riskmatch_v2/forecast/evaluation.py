"""Matched scores, allocation replays, frozen combination rules and calibration."""

import numpy as np
from scipy.stats import binomtest


def block_ci(x, cfg):
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return [None, None]
    b = min(cfg["bootstrap"]["block"], len(x))
    rng = np.random.default_rng(cfg["bootstrap"]["seed"])
    start = rng.integers(
        0, len(x) - b + 1, (cfg["bootstrap"]["draws"], int(np.ceil(len(x) / b)))
    )
    sample = x[
        (start[:, :, None] + np.arange(b)).reshape(len(start), -1)[:, : len(x)]
    ].mean(axis=1)
    return np.quantile(sample, [0.025, 0.975]).tolist()


def split(t, cfg, final):
    if final:
        return t[t.index >= cfg["final_start"]]
    return t[(t.index >= cfg["validation_start"]) & (t.end < cfg["final_start"])]


def loss(target, y, estimate):
    if target == "return":
        return (y - estimate) ** 2
    return np.log(estimate) + y / estimate


def funded(t, column, target, r):
    cash, shares, fees = 35000.0, 0.0, 0.0
    exceeded = []
    prev = None
    for day, row in t.iterrows():
        if prev is not None and prev != day:
            cost = shares * 0.001
            cash += shares - cost
            fees += cost
            shares = 0
        wealth = cash + shares
        variance = row[column] if target == "variance" else row["hist"]
        w = min(0.6, 0.12 / np.sqrt(252 * variance))
        if target == "return" and row[column] <= 0:
            w = 0.0
        # Target is a fraction of pre-trade wealth. Maximum 60% leaves cash to pay fees.
        desired = w * wealth
        cost = abs(desired - shares) * 0.001
        cash = wealth - desired - cost
        shares = desired
        fees += cost
        daily = []
        for move in r.loc[(r.index > day) & (r.index <= row.end)].to_numpy():
            old = cash + shares
            shares *= 1 + move
            daily.append((cash + shares) / old - 1)
        exceeded.append(max(0.0, np.sqrt(252 * np.mean(np.square(daily))) - 0.12))
        prev = row.end
    cost = shares * 0.001
    return {
        "terminal_chf": cash + shares - cost,
        "fees_chf": fees + cost,
        "frequency": np.mean(np.array(exceeded) > 0),
        "mean_excess": np.mean(exceeded),
    }


def judge(t, name, target, r, cfg, reference="baseline"):
    z = t.dropna(subset=[name, reference, target])
    if len(z) < cfg["min_per_block"]:
        return {"n": len(z), "passed": False, "reason": "Insufficient paired outcomes"}
    diff = loss(target, z[target], z[reference]) - loss(target, z[target], z[name])
    ci = block_ci(diff, cfg)
    signs = sum(block.mean() > 0 for block in np.array_split(diff.to_numpy(), 3))
    base = funded(z, reference, target, r)
    candidate = funded(z, name, target, r)
    econ = (
        candidate["terminal_chf"] > base["terminal_chf"]
        if target == "return"
        else candidate["frequency"] < base["frequency"]
        and candidate["mean_excess"] < base["mean_excess"]
    )
    stat = ci[0] > 0 and signs >= 2 and len(z) >= 0.8 * len(t)
    return {
        "n": len(z),
        "coverage": len(z) / len(t),
        "gain": diff.mean(),
        "ci": ci,
        "positive_segments": int(signs),
        "mse": ((z[target] - z[name]) ** 2).mean(),
        "reference_mse": ((z[target] - z[reference]) ** 2).mean(),
        "score": loss(target, z[target], z[name]).mean(),
        "reference_score": loss(target, z[target], z[reference]).mean(),
        "statistical": bool(stat),
        "economic": bool(econ),
        "passed": bool(stat and econ),
        "reference_book": base,
        "candidate_book": candidate,
        "reason": "Passed research gates"
        if stat and econ
        else "Economic gate"
        if stat
        else "Statistical or coverage gate",
    }


def calibrate(t, cfg):
    z = t.dropna(subset=["probability", "lower", "upper", "frequency"])
    y = z["return"].le(-0.05).astype(int)
    p = z.probability
    gain = (y - z.frequency) ** 2 - (y - p) ** 2
    bins = []
    for low, high in zip([0, 0.1, 0.2, 0.4], [0.1, 0.2, 0.4, 1.000001]):
        hit = (p >= low) & (p < high)
        if hit.any():
            bins.append(
                {
                    "low": low,
                    "n": int(hit.sum()),
                    "predicted": p[hit].mean(),
                    "actual": y[hit].mean(),
                    "frequency_ci": list(
                        binomtest(int(y[hit].sum()), int(hit.sum())).proportion_ci(
                            method="wilson"
                        )
                    ),
                }
            )
    ci = block_ci(gain, cfg)
    counts = len(z) >= 30 and min(y.sum(), len(y) - y.sum()) >= 10
    reliable = bool(
        counts
        and ci[0] > 0
        and all(abs(b["predicted"] - b["actual"]) <= 0.1 for b in bins if b["n"] >= 5)
    )
    covered = (z["return"] >= z.lower) & (z["return"] <= z.upper)
    ic = block_ci(covered, cfg)
    return {
        "n": len(z),
        "events": int(y.sum()),
        "brier": float(((p - y) ** 2).mean()),
        "reference_brier": float(((z.frequency - y) ** 2).mean()),
        "gain_ci": ci,
        "bins": bins,
        "probability_pass": reliable,
        "interval_coverage": covered.mean(),
        "width": (z.upper - z.lower).mean(),
        "coverage_ci": ic,
        "interval_pass": bool(
            len(z) >= 30 and abs(covered.mean() - 0.8) <= 0.05 and ic[0] <= 0.8 <= ic[1]
        ),
    }


def combination(t, names, validation, cfg, r, target):
    ranked = sorted(
        [n for n in names if validation[n]["passed"] and n.startswith("increment_")],
        key=lambda n: -validation[n]["gain"],
    )
    v = split(t, cfg, False)
    kept = []
    for n in ranked:
        if all(abs(v[n].corr(v[k])) <= 0.85 for k in kept):
            kept.append(n)
    if len(kept) < 2:
        result = {
            "eligible": ranked,
            "retained": kept,
            "weights": {},
            "status": "Reference only; fewer than two independent validated signals.",
        }
        if ranked:
            final = split(t, cfg, True).dropna(subset=ranked).copy()
            result["correlations"] = v[ranked].corr().to_dict()
            result["best_against_reference"] = judge(final, ranked[0], target, r, cfg)
            # With one retained signal, both combinations reproduce the best signal exactly.
            final["retained_combination"] = final[kept[0]]
            result["combination_against_best"] = judge(
                final, "retained_combination", target, r, cfg, ranked[0]
            )
            final["unfiltered_equal"] = final[ranked].mean(axis=1)
            result["redundancy_control"] = judge(
                final, "unfiltered_equal", target, r, cfg, ranked[0]
            )
        return result
    raw = np.array([validation[n]["gain"] for n in kept])
    weights = raw / raw.sum()
    final = split(t, cfg, True).dropna(subset=kept).copy()
    if len(final) < 0.8 * len(split(t, cfg, True)):
        return {
            "eligible": ranked,
            "retained": kept,
            "weights": {},
            "status": "Reference only; insufficient joint coverage.",
        }
    final["weighted"] = final[kept] @ weights
    final["equal"] = final[kept].mean(axis=1)
    checks = {
        m: {b: judge(final, m, target, r, cfg, b) for b in ["baseline", kept[0]]}
        for m in ["equal", "weighted"]
    }
    return {
        "eligible": ranked,
        "retained": kept,
        "weights": dict(zip(kept, weights)),
        "final": checks,
        "status": "Research combination passed"
        if all(z["passed"] for z in checks["weighted"].values())
        else "Reference only; no confirmed incremental gain.",
    }
