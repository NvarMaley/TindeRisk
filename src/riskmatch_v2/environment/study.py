"""Replay confirmed environmental preferences against the frozen CHF research model."""

import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd

from ..equity_extension.fetch import CAT
from ..library.controls import exclusion_status, exposure
from ..universe.desk import load_model
from .measurement import CUTOFF, LOCAL, REPORT, REVIEW, digest, sources

CHEVRON = "CUSIP6:166764"
HIGH = 0.12
CAPITAL = 35000
MEASURED_WEIGHT = 0.60


def decision(result, forbidden, strength, missing):
    """Interpret a confirmed issuer list and the P07/P08 missing-data instruction."""
    if strength not in {"mandatory", "soft"} or missing not in {
        "suspend",
        "ask for clarification",
        "flag and compare",
    }:
        raise ValueError("Unknown mandate instruction")
    state = exclusion_status(result, forbidden, strength == "mandatory")
    if state in {"suspendu", "partial coverage"}:
        return {
            "suspend": "suspended",
            "ask for clarification": "clarification required",
            "flag and compare": "unverified comparison only",
        }[missing]
    return state


def profile(result, measures, forbidden):
    identified = result["issuers"]
    if any(v < -1e-10 for v in identified.values()):
        raise ValueError(
            "Short identified positions require a separate carbon methodology"
        )
    covered = sum(v for k, v in identified.items() if k in measures)
    numerator = sum(v * measures[k] for k, v in identified.items() if k in measures)
    return {
        "forbidden": sum(identified.get(k, 0.0) for k in forbidden),
        "unknown_gross": result["unknown_gross"],
        "unknown_net": result["unknown_net"],
        "sovereign": identified.get("US-TREASURY", 0.0),
        "covered": covered,
        "numerator": numerator,
    }


def profiles(names, direct, holdings, measures, instant, forbidden):
    rows = []
    for name in names:
        if name in direct:
            r = {
                "issuers": {direct[name]: 1.0},
                "unknown_gross": 0.0,
                "unknown_net": 0.0,
            }
        elif name.startswith("PERMNO:"):
            r = {"issuers": {}, "unknown_gross": 1.0, "unknown_net": 1.0}
        else:
            r = exposure({name: 1.0}, holdings, {}, instant)
        rows.append(profile(r, measures, forbidden))
    return pd.DataFrame(rows, index=names)


def summarize(coeff, w):
    total = coeff.T @ w
    out = total.to_dict()
    out["intensity"] = (
        out["numerator"] / out["covered"] if out["covered"] > 1e-10 else None
    )
    # Residual cash and fees are outside the corporate criterion.
    out["unmeasured_invested_net"] = float(sum(w) - out["sovereign"] - out["covered"])
    return out


def solve(p, eligible, fixed=None, intensity=None, cap=None):
    """Optimize on eligible columns only, then independently verify the full allocation."""
    if p.current.any() or p.lo.any():
        raise ValueError("This study starts from cash with zero security minima")
    idx = np.flatnonzero(eligible)
    w = cp.Variable(len(idx), nonneg=True)
    constraints = [
        w <= p.hi[idx],
        cp.sum(w) <= p.invested_max,
        cp.sum(w) >= p.invested_min,
        (1 + p.fees[idx]) @ w <= 1,
        cp.norm(p.root[:, idx] @ w) <= HIGH,
    ]
    constraints.extend(a[idx] @ w <= limit for a, limit in p.groups.values())
    if fixed is not None:
        constraints.append(cp.sum(w) == fixed)
    if cap is not None:
        if fixed is None or not np.isfinite(intensity[idx]).all():
            raise ValueError(
                "The intensity comparison requires a fully measured fixed sleeve"
            )
        constraints.append((intensity[idx] - cap) @ w <= 0)
    problem = cp.Problem(
        cp.Maximize((p.mu[idx] - p.fees[idx] / p.years) @ w), constraints
    )
    problem.solve(solver="CLARABEL", tol_gap_abs=1e-10, tol_feas=1e-10)
    if problem.status != cp.OPTIMAL:
        raise ValueError(f"Environmental comparison unavailable: {problem.status}")
    full = np.zeros(len(p.names))
    full[idx] = np.where(w.value > 1e-9, w.value, 0)
    if (
        not p.evaluate(full, high=HIGH)["valid"]
        or fixed is not None
        and abs(full.sum() - fixed) > 1e-6
    ):
        raise ValueError("Allocation failed its mandate")
    if cap is not None and np.dot(intensity[idx], full[idx]) / full.sum() > cap + 1e-6:
        raise ValueError("Carbon ceiling exceeded")
    return full


def intensity_comparison(before, after, distance):
    if distance <= 1e-6:
        return "Same allocation"
    if before["intensity"] is None or after["intensity"] is None:
        return "No comparable measurement"
    if abs(before["covered"] - after["covered"]) > 1e-6 or any(
        row["unmeasured_invested_net"] > 1e-6 for row in (before, after)
    ):
        return "Partial or unequal coverage"
    if after["intensity"] < before["intensity"] - 1e-6:
        return "Lower measured intensity"
    return "No measured reduction"


def describe(p, coeff, w):
    metrics = p.evaluate(w, high=HIGH)
    return dict(
        **summarize(coeff, w),
        holdings=int((w > 0).sum()),
        invested=float(w.sum()),
        cash=metrics["cash"],
        net=metrics["net"],
        risk=metrics["risk"],
        fee_chf=metrics["fee"] * CAPITAL,
    )


def main():
    inventory, measured, audit = sources()
    bundle_id = json.loads(Path("reports/univers-complet/resultats.json").read_text())[
        "snapshot"
    ]
    bundle = Path("data/local/univers") / bundle_id
    models, _, _, _ = load_model(bundle)
    p = models[0]
    holdings_path = CAT / "holdings.parquet"
    holdings = pd.read_parquet(holdings_path)
    direct = {
        f"PERMNO:{r.permno}": r.code
        for r in inventory.dropna(subset=["code"]).itertuples()
    }
    direct.update(
        dict.fromkeys((n for n in p.names if n.startswith("UST:")), "US-TREASURY")
    )
    direct["CHF cash"] = "CHF cash"
    measures = measured.set_index("code").intensity.to_dict()
    if measured.groupby("code").intensity.nunique().max() != 1:
        raise ValueError("Ambiguous issuer measurement")
    banned = {CHEVRON}
    security = "PERMNO:14541"
    assert direct[security] == CHEVRON
    c = profiles(p.names, direct, holdings, measures, REVIEW, banned)
    # September/October positions may not be reconstructed from a November edition.
    cases = []
    for title, weights, instant in [
        ("Chevron directly", {security: 1.0}, REVIEW),
        ("XLE before publication", {"XLE": 1.0}, CUTOFF),
        ("XLE after publication", {"XLE": 1.0}, REVIEW),
        ("SPY after publication", {"SPY": 1.0}, REVIEW),
        ("Half Chevron, half XLE", {security: 0.5, "XLE": 0.5}, REVIEW),
        ("GLD without issuer file", {"GLD": 1.0}, REVIEW),
        (
            "Direct US Treasury",
            {next(n for n in p.names if n.startswith("UST:")): 1.0},
            REVIEW,
        ),
    ]:
        r = exposure(weights, holdings, direct, instant)
        z = profile(r, measures, banned)
        cases.append(
            dict(
                case=title,
                instant=instant,
                **z,
                intensity=z["numerator"] / z["covered"] if z["covered"] else None,
                mandatory=decision(r, banned, "mandatory", "suspend"),
                soft=decision(r, banned, "soft", "flag and compare"),
                ask=decision(r, banned, "mandatory", "ask for clarification"),
            )
        )
    neutral = solve(p, np.ones(len(c), dtype=bool))
    eligible = c.forbidden.le(1e-12) & c.unknown_gross.le(1e-10)
    hard = solve(p, eligible)
    if (
        summarize(c, hard)["forbidden"] > 1e-12
        or summarize(c, hard)["unknown_gross"] > 1e-10
    ):
        raise ValueError("Unverified hard exclusion")
    peers = c.covered.eq(1.0) & pd.Index(p.names).str.startswith("PERMNO:")
    intensities = c.numerator.where(peers).to_numpy()
    base = solve(p, peers, fixed=MEASURED_WEIGHT)
    cap = 0.8 * summarize(c, base)["intensity"]
    soft = solve(p, peers, fixed=MEASURED_WEIGHT, intensity=intensities, cap=cap)
    pairs = []
    archive = {}
    for label, ref, variant, n in [
        ("Chevron exclusion", neutral, hard, int(eligible.sum())),
        ("Point-source intensity", base, soft, int(peers.sum())),
    ]:
        before, after = describe(p, c, ref), describe(p, c, variant)
        delta = {
            k: after[k] - before[k]
            for k in ["net", "risk", "fee_chf", "covered", "forbidden", "unknown_gross"]
        }
        distance = float(abs(ref - variant).sum() / 2)
        pairs.append(
            {
                "criterion": label,
                "eligible": n,
                "reference": before,
                "variant": after,
                "change": delta,
                "intensity_comparison": intensity_comparison(before, after, distance),
                "allocation_distance": distance,
            }
        )
        archive[label + " reference"] = ref
        archive[label + " variant"] = variant
    c.assign(**archive).rename_axis("instrument").to_parquet(
        LOCAL / "allocations.parquet"
    )
    data = {
        "market_date": CUTOFF,
        "review": REVIEW,
        "bundle": bundle_id,
        "assets": len(c),
        "capital_chf": CAPITAL,
        "risk_ceiling": HIGH,
        "measured_sleeve": MEASURED_WEIGHT,
        "intensity_cap": cap,
        "controls": cases,
        "pairs": pairs,
        "holdings_date": str(holdings.day.max()),
        "audit": audit,
    }
    paths = [
        holdings_path,
        bundle / "models.npz",
        bundle / "risk_0.npz",
        Path("config/faisabilite-5.json"),
    ]
    audit["model_inputs"] = {path.name: digest(path) for path in paths}
    REPORT.mkdir(parents=True, exist_ok=True)
    published = (
        measured.drop_duplicates("cik")
        .sort_values("parent")[
            [
                "parent",
                "cik",
                "adsh",
                "accepted_utc",
                "tag",
                "facilities",
                "tonnes",
                "revenue",
                "intensity",
            ]
        ]
        .copy()
    )
    published["accepted_utc"] = pd.to_datetime(
        published.accepted_utc, utc=True
    ).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    (REPORT / "issuers.json").write_text(
        json.dumps(published.to_dict("records"), indent=2, allow_nan=False) + "\n"
    )
    (REPORT / "results.json").write_text(
        json.dumps(data, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    main()
