"""Portfolio-specific notices based on actual dated section 6 holdings and section 8 stresses."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..stress.exposures import portfolio_paths
from ..stress.inputs import inputs
from .registry import controlled_estimate


def notices(registry):
    def read(path):
        return json.loads(Path(path).read_text())

    stress = read("reports/08-chocs/results.json")
    _, weights, _, daily, *_ = inputs(
        read("config/stress-8.json"), read("config/econometrie.json")
    )
    paths = portfolio_paths(daily.iloc[-150:], weights)
    cases = pd.DataFrame(stress["cases"])
    attrib = pd.read_parquet(
        Path("data/local/8") / stress["archive"] / "attribution.parquet"
    )
    result = []
    for name, g in weights.groupby("option"):
        x = paths[name].iloc[-63:]
        moves = cases[cases.option.eq(name)].set_index("scenario")
        rates = attrib[attrib.option.eq(name) & attrib.scenario.eq("Joint")]
        rate = rates.local_ten_year_bp + rates.local_slope_bp
        previous = paths[name].iloc[-126:-63]
        previous_risk = (
            float(np.sqrt(252 * previous.pow(2).mean()))
            if previous.count() >= 50
            else None
        )
        trailing = np.sqrt(252 * paths[name].pow(2).rolling(21).mean())
        change = (trailing - trailing.shift(21)).dropna()
        rising = change[change > 0.01]
        example = None
        if not rising.empty:
            end = rising.index[-1]
            example = {
                "asof": str(end),
                "earlier_annual_vol": trailing.shift(21)[end],
                "later_annual_vol": trailing[end],
                "weights": "October fixed-weight backcast",
            }
        notices = []
        for h in [21, 63]:
            # Equal-weight rolling reference as in the directional forecast study.
            rv = x.pow(2).mean() if x.count() >= 50 and pd.notna(x.iloc[-1]) else np.nan
            estimate, parts = controlled_estimate(
                registry, stress["end"], name, "variance", h, {}, rv
            )
            notices.append(
                {
                    "horizon": h,
                    "n": int(x.count()),
                    "annual_vol": np.sqrt(252 * estimate)
                    if np.isfinite(estimate)
                    else None,
                    "horizon_rms": np.sqrt(h * estimate)
                    if np.isfinite(estimate)
                    else None,
                    "signal_weights": parts,
                }
            )
        result.append(
            {
                "name": name,
                "positions": len(g),
                "invested": g.weight.sum(),
                "date": stress["end"],
                "notices": notices,
                "previous_annual_reference": previous_risk,
                "rising_risk_control": example,
                "oil_up_chf": moves.at["Oil up", "pnl_chf"],
                "fx_up_chf": moves.at["CHF translation", "pnl_chf"],
                "rates_chf": 35000 * (rates.weight * rate).sum(),
                "rates_covered": rates.loc[rate.notna(), "weight"].sum(),
                "joint_chf": moves.at["Joint", "pnl_chf"],
                "joint_covered": moves.at["Joint", "covered_weight"],
            }
        )
    funding = {}
    for c in ["A", "B"]:
        s = read(f"reports/07-funding/client-{c}.json")
        funding[c] = {
            k: v["mean_terminal_gap_chf"]
            for k, v in s["deterministic_stress"]["Custom"].items()
        }
        funding[c]["missed_scheduled_payments_flat"] = s["deterministic_stress"][
            "Custom"
        ]["flat_market"]["missed"]
        funding[c]["missed_scheduled_payments_after_shock"] = s["deterministic_stress"][
            "Custom"
        ]["immediate_30pct_loss"]["missed"]
    return result, funding
