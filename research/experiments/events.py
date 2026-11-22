"""Teaching event windows, pre-event model sensitivity and matched placebo dates."""

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from course_replay import DATA, FIXTURES


def classroom_events(out):
    path = DATA / "sentratio_and_price_for_pf2.pkl"
    if hashlib.sha256(path.read_bytes()).hexdigest() != FIXTURES[path.name]:
        raise ValueError("Unrecognized classroom file")
    df = pd.read_pickle(path).sort_values(["ticker", "date"])
    peaks = df.phi3.gt(2)
    stats = {
        "events": int(df.Event3.sum()),
        "peak_mismatches": int((peaks != df.Event3).sum()),
    }
    records = []
    for ticker, g in df.groupby("ticker"):
        g = g.reset_index(drop=True)
        # Match same-name, same-quarter controls using activity measured before each event.
        logvol = np.log1p(g[["VOL", "N"]]).rolling(20, min_periods=10).mean().shift()
        active = (
            g.Event3.astype(int)
            .rolling(41, center=True, min_periods=1)
            .max()
            .astype(bool)
        )
        quarter = g.date.dt.tz_localize(None).dt.to_period("Q")
        days = g.index[g.Event3].to_numpy()
        last = -100

        def measured(i, g=g):
            window = g.iloc[i - 20 : i + 6]
            if len(window) != 26:
                return {}
            train = g.iloc[max(0, i - 272) : i - 20][
                ["daily_return", "market_return"]
            ].dropna()
            clean = np.full(len(window), np.nan)
            if len(train) >= 126:
                a, b = np.linalg.lstsq(
                    np.c_[np.ones(len(train)), train.market_return],
                    train.daily_return,
                    rcond=None,
                )[0]
                clean = (window.daily_return - a - b * window.market_return).to_numpy()
            result = {}
            for stop in [-5, 0, 5]:
                count = 21 + stop
                for key, x in [
                    ("car", window.abnormal_return),
                    ("cap", window.abnormal_pol),
                    ("frozen_car", clean),
                ]:
                    result[f"{key}_{stop}"] = np.sum(np.asarray(x[:count]))
            return result

        for i in days:
            if i < 20 or i + 5 >= len(g):
                continue
            disjoint = i - last > 25
            if disjoint:
                last = i
            row = dict(
                ticker=ticker,
                date=g.date.iloc[i],
                label=g.Type.iloc[i],
                disjoint=disjoint,
                **measured(i),
            )
            candidates = (
                (quarter == quarter.iloc[i])
                & ~active
                & (g.index >= 20)
                & (g.index < len(g) - 5)
            )
            distance = (
                ((logvol[candidates] - logvol.iloc[i]) ** 2)
                .sum(axis=1, min_count=2)
                .dropna()
            )
            if len(distance):
                j = int(distance.idxmin())
                row["placebo_date"] = g.date.iloc[j]
                row.update({"placebo_" + k: v for k, v in measured(j).items()})
            records.append(row)
    events = pd.DataFrame(records)
    events.to_parquet(out / "event_windows.parquet", index=False)
    rows = []
    for sample, sub in [
        ("all", events),
        ("disjoint within ticker", events[events.disjoint]),
    ]:
        for metric in ["car", "cap", "frozen_car"]:
            for stop in [-5, 0, 5]:
                col = f"{metric}_{stop}"
                group = (
                    sub[sub.label.isin(["Good", "Neutral"])].dropna(subset=[col]).copy()
                )
                good = group.loc[group.label == "Good", col]
                neutral = group.loc[group.label == "Neutral", col]
                if not len(good) or not len(neutral):
                    continue
                naive = mannwhitneyu(good, neutral)
                # Resample calendar months jointly for firms, including overlapping event clusters.
                group["month"] = group.date.dt.strftime("%Y-%m")
                totals = (
                    group.groupby(["month", "label"])[col]
                    .agg(["sum", "count"])
                    .unstack(fill_value=0)
                )
                monthly = totals.reindex(
                    pd.period_range(
                        totals.index.min(), totals.index.max(), freq="M"
                    ).astype(str),
                    fill_value=0,
                )
                rng = np.random.default_rng(506)
                starts = rng.integers(
                    0, len(monthly) - 2, size=(999, (len(monthly) + 2) // 3)
                )
                idx = (starts[:, :, None] + np.arange(3)).reshape(999, -1)[
                    :, : len(monthly)
                ]
                diff = monthly["sum"]["Good"].to_numpy()[idx].sum(1) / monthly["count"][
                    "Good"
                ].to_numpy()[idx].sum(1) - monthly["sum"]["Neutral"].to_numpy()[
                    idx
                ].sum(1) / monthly["count"]["Neutral"].to_numpy()[idx].sum(1)
                lo, hi = np.quantile(diff, [0.025, 0.975])
                placebo = (group[col] - group["placebo_" + col]).mean()
                rows.append(
                    {
                        "sample": sample,
                        "metric": metric,
                        "stop": stop,
                        "good": len(good),
                        "neutral": len(neutral),
                        "u": naive.statistic,
                        "naive_p": naive.pvalue,
                        "mean_gap": good.mean() - neutral.mean(),
                        "block_low": lo,
                        "block_high": hi,
                        "placebo_pairs": group["placebo_" + col].notna().sum(),
                        "mean_event_minus_placebo": placebo,
                    }
                )
    pd.DataFrame(rows).to_csv(out / "event_comparisons.csv", index=False)
    return stats
