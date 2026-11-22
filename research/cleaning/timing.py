"""Availability rules shared by historical panels and mutation tests."""

import numpy as np
import pandas as pd

from .markets import cash_accrual, dated_csv


def next_session_open(days, calendar):
    idx = calendar.index.searchsorted(pd.DatetimeIndex(days), side="right")
    if (idx >= len(calendar)).any():
        raise ValueError("Availability outside frozen calendar")
    return calendar.open.iloc[idx].array


def asof(decisions, history):
    # Observations must be knowable strictly before decision, even if timestamps coincide.
    return pd.merge_asof(
        decisions.sort_values("decision_at"),
        history.sort_values("available_at"),
        left_on="decision_at",
        right_on="available_at",
        direction="backward",
        allow_exact_matches=False,
    )


def macro_panels(data, output, calendar, sessions):
    raw = data / "raw"
    raw_vintages, features = [], []
    for path in sorted((raw / "public_phase2/alfred").glob("*.csv.gz")):
        symbol, day = path.name.split(".")[0].split("_")
        values = dated_csv(path).iloc[:, 0]
        vintage = pd.Timestamp(day)
        available = next_session_open([vintage], calendar)[0]
        raw_vintages.append(
            pd.DataFrame(
                {
                    "series": symbol,
                    "observation_date": values.index,
                    "value": values.values,
                    "vintage": vintage,
                    "available_at": available,
                }
            )
        )
        valid = values.dropna()
        last = valid.index[-1]
        if last > vintage:
            raise ValueError("Future observation in vintage")
        value = (
            valid[last]
            if symbol == "UNRATE"
            else valid[last] / valid.get(last - pd.DateOffset(years=1), np.nan) - 1
        )
        features.append(
            {
                "series": symbol,
                "observation_date": last,
                "vintage": vintage,
                "available_at": available,
                "value": value,
                "basis": "archived vintage",
                "published_at": pd.NaT,
            }
        )
    if len(features) != 786:
        raise ValueError("Incomplete v1 ALFRED inventory")
    releases = pd.concat(raw_vintages, ignore_index=True)
    releases["published_at"] = pd.Series(
        pd.NaT, dtype="datetime64[ns, UTC]", index=releases.index
    )
    if releases.duplicated(["series", "vintage", "observation_date"]).any():
        raise ValueError("Nonunique ALFRED key")
    releases.to_parquet(output / "macro_releases.parquet", index=False)
    ledger = [pd.DataFrame(features)]
    for name in ("DTB3", "T10Y2Y", "BAA10Y"):
        value = dated_csv(raw / (name + ".csv")).iloc[:, 0].loc["1997":].dropna()
        ledger.append(
            pd.DataFrame(
                {
                    "series": name,
                    "observation_date": value.index,
                    "vintage": pd.NaT,
                    "published_at": pd.NaT,
                    "available_at": next_session_open(value.index, calendar),
                    "value": value.values,
                    "basis": "retrospective latest export; next-session timing proxy",
                }
            )
        )
    decisions = (
        calendar.loc[sessions, ["close"]]
        .rename(columns={"close": "decision_at"})
        .rename_axis("session")
        .reset_index()
    )
    histories = pd.concat(ledger, ignore_index=True)
    histories["published_at"] = pd.to_datetime(histories.published_at, utc=True)
    panels = []
    for name, history in histories.groupby("series"):
        # Several source days can first be available together following a holiday.
        history = history.sort_values(
            ["available_at", "observation_date"]
        ).drop_duplicates("available_at", keep="last")
        joined = asof(decisions, history)
        joined["series"] = name
        panels.append(joined)
    panel = pd.concat(panels, ignore_index=True)
    panel.to_parquet(output / "features.parquet", index=False)
    cash = panel.loc[
        panel.series.eq("DTB3"),
        ["session", "decision_at", "value", "observation_date", "available_at"],
    ].copy()
    gap = cash.session.diff().dt.days
    cash["usd_cash_proxy"] = cash_accrual(cash.value.shift(), gap)
    cash["simple_proxy"] = cash.value.shift() / 100 * gap / 360
    cash.to_parquet(output / "usd_cash.parquet", index=False)
    return panel, cash
