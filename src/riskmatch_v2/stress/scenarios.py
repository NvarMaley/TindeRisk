"""Conditional local returns, direct Treasury repricing and exact currency translation."""

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from ..universe.treasury import terms
from .inputs import FACTORS


def price_case(day, maturity, coupon, dirty, y2, y10, d10, slope):
    """Per 100 face. Fit a constant spread on interpolated 2y/10y yield proxies."""
    day, maturity = pd.Timestamp(day), pd.Timestamp(maturity)
    flows = []
    for i in range(201):
        date = maturity - pd.DateOffset(months=i * 6)
        if maturity.is_month_end:
            date += pd.offsets.MonthEnd(0)
        if date <= day:
            break
        flows.append(((date - day).days / 365.25, coupon / 2 + (100 if i == 0 else 0)))
    if not flows:
        raise ValueError("No future cash flows")
    times, amounts = np.array(flows).T
    curve = np.interp(times, [2, 10], [y2, y10]) / 100
    move = np.interp(times, [2, 10], [d10 - slope, d10]) / 10000

    def pv(spread, shock):
        return (amounts / (1 + (curve + spread + shock) / 2) ** (2 * times)).sum()

    spread = brentq(lambda s: pv(s, 0) - dirty, -0.5, 1)
    base = pv(spread, 0)
    assert abs(base - dirty) < 1e-7
    duration = (pv(spread, -0.0001) - pv(spread, 0.0001)) / (2 * 0.0001 * base)
    linear = (
        -(
            amounts
            / (1 + (curve + spread) / 2) ** (2 * times)
            * times
            / (1 + (curve + spread) / 2)
            * move
        ).sum()
        / base
    )
    exact = pv(spread, move) / base - 1
    if np.all(move >= 0):
        assert exact <= 1e-12 and linear <= exact + 1e-12
    return {
        "cash_flows": len(times),
        "calibrated_spread_bp": spread * 10000,
        "modified_duration": duration,
        "rate_return": exact,
        "linear_rate_return": linear,
    }


def bond_table(day, y2, y10, cfg):
    terms_table = terms()
    marks = pd.read_parquet(
        "data/local/univers/bonds.parquet", filters=[("day", "=", day)]
    )
    rows = []
    for row in marks.itertuples():
        terms_row = terms_table.loc[row.name.removeprefix("UST:")]
        for scenario, shift in cfg["scenarios"].items():
            case = price_case(
                day,
                terms_row.maturity_date,
                float(terms_row.int_rate),
                row.close,
                y2,
                y10,
                shift.get("ten_year_bp", 0),
                shift.get("slope_bp", 0),
            )
            rows.append(dict(id=row.name, scenario=scenario, **case))
    return pd.DataFrame(rows)


def attribution(est, bonds, weights, cfg):
    beta = est.query("variant=='local_USD'").pivot(
        index="id", columns="factor", values="beta"
    )
    rows, summaries = [], []
    for name, g in weights.groupby("option"):
        w = g.set_index("id").weight
        for scenario, shift in cfg["scenarios"].items():
            coeff = beta.reindex(index=w.index, columns=FACTORS)
            components = coeff.mul(
                pd.Series(shift).reindex(FACTORS, fill_value=0), axis=1
            )
            # An unestimated coefficient is irrelevant for a factor with a zero shock.
            components.loc[:, ~components.columns.isin(shift)] = 0
            direct = bonds.query("scenario == @scenario").set_index("id").rate_return
            use = w.index.intersection(direct.index)
            components.loc[use, "ten_year_bp"] = direct.loc[use]
            components.loc[use, "slope_bp"] = 0
            local = components.sum(axis=1, skipna=False)
            fx = shift.get("fx", 0)
            total = (1 + local) * (1 + fx) - 1
            table = (
                components.add_prefix("local_")
                .assign(
                    weight=w,
                    local=local,
                    translation=fx,
                    interaction=local * fx,
                    total_chf=total,
                    weighted_chf=total * w,
                    used_cash_flows=w.index.isin(use),
                )
                .rename_axis("id")
                .reset_index()
            )
            table["option"], table["scenario"] = name, scenario
            rows.append(table)
            ok = local.notna()
            l = float(w[ok] @ local[ok])
            trans = w[ok].sum() * fx
            cross = l * fx
            point = float(w[ok] @ total[ok])
            assert abs(point - l - trans - cross) < 1e-12
            summaries.append(
                {
                    "option": name,
                    "scenario": scenario,
                    "positions": len(w),
                    "covered": int(ok.sum()),
                    "covered_weight": w[ok].sum(),
                    "missing_weight": w[~ok].sum(),
                    "chf_cash": 1 - w.sum(),
                    "local_pct": 100 * l,
                    "fx_pct": 100 * trans,
                    "interaction_pct": 100 * cross,
                    "covered_total_pct": 100 * point,
                    "known_fx_all_pct": 100 * w.sum() * fx,
                    "pnl_chf": point * cfg["scenario_budget_chf"],
                }
            )
    return pd.concat(rows, ignore_index=True), summaries
