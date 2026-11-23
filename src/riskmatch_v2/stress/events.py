"""Observed drawdowns, censored recoveries and conditional pre-event replays."""

import numpy as np
import pandas as pd

from ..econometrics import hac


def path_metrics(returns, event_n):
    """Require an uninterrupted path to the trough, then censor at the first missing mark."""
    part = np.asarray(returns, dtype=float)
    complete = np.isfinite(part) & (part >= -1)
    if not complete[:event_n].all():
        return np.nan, np.nan, None, "Missing event path"
    first_gap = np.flatnonzero(~complete)
    stop = int(first_gap[0]) if len(first_gap) else len(part)
    nav = np.r_[1.0, np.cumprod(1 + part[:stop])]
    event = nav[: event_n + 1]
    peak = np.maximum.accumulate(event)
    dd = event / peak - 1
    trough = int(np.argmin(dd))
    if dd[trough] >= -1e-12:
        return event[-1] - 1, dd[trough], 0, "No drawdown"
    hits = np.flatnonzero(nav[trough + 1 :] >= peak[trough])
    if len(hits):
        return event[-1] - 1, dd[trough], int(hits[0] + 1), "Recovered"
    return (
        event[-1] - 1,
        dd[trough],
        None,
        "Censored at data gap" if len(first_gap) else "Censored at horizon",
    )


def study(local, fx, bonds, benchmark_paths, f, y10, cfg, parent, weights, chf):
    rows, comparisons = [], []
    index = local.index
    for name, (start, end) in parent["events"].items():
        start_i, end_i = index.get_loc(start), index.get_loc(end)
        # All required factors must be observed every event day for a conditional comparison.
        event = f.iloc[start_i + 1 : end_i + 1]
        before = f.iloc[start_i + 1 - cfg["window"] : start_i + 1]
        valid_dates = before.dropna().index
        for option, holdings in weights.groupby("option"):
            w = holdings.set_index("id").weight
            usable = (
                chf.loc[valid_dates, w.index].notna().all()
                & chf.loc[event.index, w.index].notna().all()
            )
            paths = [("All positions", benchmark_paths[option], w.sum())]
            if usable.any() and not usable.all():
                # Retain original weights and park unmatched positions in CHF cash.
                # Ex-post observation coverage makes this a counterfactual subportfolio.
                sub = (
                    chf.loc[before.index.union(event.index), w.index[usable]]
                    @ w[usable]
                )
                paths.append(("Observable subset", sub, w[usable].sum()))
            for scope, y, weight in paths:
                fit = hac(
                    np.column_stack((np.ones(len(before)), before)),
                    y.loc[before.index].values,
                    cfg["minimum"],
                    parent["hac_lags"],
                )
                actual = y.loc[event.index]
                observed = (
                    float((1 + actual).prod() - 1) if actual.notna().all() else None
                )
                expected = None
                if fit is not None and event.notna().all().all():
                    predicted = np.column_stack((np.ones(len(event)), event)) @ fit[0]
                    expected = float(np.prod(1 + predicted) - 1)
                comparisons.append(
                    {
                        "episode": name,
                        "option": option,
                        "scope": scope,
                        "invested_weight": weight,
                        "event_sessions": len(event),
                        "observed_sessions": int(actual.count()),
                        "fit_n": fit[2] if fit else None,
                        "observed": observed,
                        "conditional": expected,
                        "abnormal": observed - expected
                        if observed is not None and expected is not None
                        else None,
                    }
                )
        for is_bond in (False, True):
            # Treasury observations use dated FedInvest marks on US Treasury business days.
            # Missing issue-specific returns on those days break the path.
            cal = index[y10.notna()] if is_bond else index
            if start not in cal or end not in cal:
                raise ValueError("Event endpoints missing from the class calendar")
            i, j = cal.get_loc(start), cal.get_loc(end)
            dates = cal[i : j + cfg["recovery_followup"] + 1]
            if len(dates) != j - i + 1 + cfg["recovery_followup"]:
                raise ValueError("Recovery follow-up truncated")
            raw = (
                bonds.reindex(dates)
                if is_bond
                else local.drop(columns=bonds.columns).loc[dates]
            )
            if is_bond:
                # Observed returns span the preceding mark. Reject an interval when
                # that mark is missing on the immediately preceding Treasury session.
                marks = pd.read_parquet(
                    "data/local/univers/bonds.parquet",
                    columns=["day", "name", "previous"],
                )
                prev = marks[marks.day.isin(dates)].pivot(
                    index="day", columns="name", values="previous"
                )
                required = pd.Series(dates[:-1], index=dates[1:])
                raw = raw.iloc[1:].where(
                    prev.reindex(index=dates[1:], columns=raw.columns).eq(
                        required, axis=0
                    )
                )
            else:
                raw = raw.iloc[1:]
            # Construct growth in USD first. Only compare CHF levels on observed FX
            # marks. An interior FX gap censors the drawdown/recovery path.
            valued = (1 + raw).mul(
                fx.loc[dates].pct_change(fill_method=None).iloc[1:] + 1, axis=0
            ) - 1
            for key, series in valued.items():
                ret, draw, time, status = path_metrics(series.values, j - i)
                rows.append((key, name, j - i, ret, draw, time, status))
    return pd.DataFrame(
        rows,
        columns=[
            "id",
            "episode",
            "sessions",
            "return_chf",
            "drawdown",
            "recovery_sessions",
            "status",
        ],
    ), comparisons
