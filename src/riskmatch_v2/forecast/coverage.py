"""Transfer diagnostics per dated inventory name, including explicit missing outcomes."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..stress.inputs import inputs
from .evaluation import loss
from .sources import CONFIG, RAW, REPORT, frame


def incremental(x, y, base, dates, ends, cfg, variance):
    """One-dimensional Ridge on standardized x via expanding sufficient statistics."""
    rows, cols = y.shape
    n = np.zeros(cols)
    sx, sy, sxx, sxy = np.zeros((4, cols))
    lo = np.full(cols, np.inf)
    hi = -lo.copy()
    forecasts = np.full_like(y, np.nan)
    next_label = 0
    for i in range(rows):
        while next_label < i and ends[next_label] < dates[i]:
            j = next_label
            next_label += 1
            if dates[j] < cfg["final_start"] <= ends[j]:
                continue
            ok = np.isfinite(y[j]) & np.isfinite(base[j]) & np.isfinite(x[j])
            a = np.where(ok, x[j], 0.0)
            b = np.where(ok, y[j] - base[j], 0.0)
            n += ok
            sx += a
            sy += b
            sxx += a * a
            sxy += a * b
            lo = np.minimum(lo, np.where(ok, y[j], np.inf))
            hi = np.maximum(hi, np.where(ok, y[j], -np.inf))
        denom = np.maximum(n, 1.0)
        xx = np.maximum(sxx - sx * sx / denom, 0.0)
        xy = sxy - sx * sy / denom
        slope = (
            np.divide(xy, xx, out=np.zeros(cols), where=xx > 1e-14)
            * n
            / (n + cfg["ridge_alpha"])
        )
        pred = np.clip(base[i] + sy / denom + slope * (x[i] - sx / denom), lo, hi)
        ok = (n >= cfg["min_train"]) & np.isfinite(base[i]) & np.isfinite(x[i])
        forecasts[i, ok] = np.exp(pred[ok]) if variance else pred[ok]
    return forecasts


def main():
    cfg = json.loads(CONFIG.read_text())

    def read(path):
        return json.loads(Path(path).read_text())

    inv, _, _, daily, *_ = inputs(
        read("config/stress-8.json"), read("config/econometrie.json")
    )
    _, features, prices, _ = frame()
    # Prior known inputs on the SPY/FX calendar, forwarded only across short market-calendar differences.
    features = features.reindex(
        pd.to_datetime(daily.index), method="ffill", tolerance=pd.Timedelta(days=4)
    )
    dates = np.asarray(daily.index)
    a = daily.to_numpy()
    funds = prices.pivot(index="day", columns="symbol", values="close") * prices.pivot(
        index="day", columns="symbol", values="volume"
    )
    liquid = (
        np.log(funds.rolling(5).mean() / funds.rolling(63).mean())
        .shift(1)
        .reindex(daily.index)
    )
    ids = daily.columns
    local = []
    for h in cfg["horizons"]:
        starts = np.arange(126, len(daily) - h, h)
        days = dates[starts]
        ends = dates[starts + h]
        shape = (len(starts), len(ids))
        target_var, ret, hist, momentum, rv, liq = np.full((6, *shape), np.nan)
        fund_cols = ids.get_indexer(liquid.columns)
        assert (fund_cols >= 0).all()
        for j, i in enumerate(starts):
            past = a[i - 63 : i]
            future = a[i + 1 : i + h + 1]
            count = np.isfinite(past).sum(axis=0)
            value = np.nansum(past**2, axis=0) / np.maximum(count, 1)
            hist[j] = np.where(
                (count >= 50) & np.isfinite(past[-1]) & (value > 1e-12), value, np.nan
            )
            target_var[j] = np.mean(future**2, axis=0)
            ret[j] = np.prod(1 + future, axis=0) - 1
            momentum[j] = np.prod(1 + a[i - 126 : i - 21], axis=0) - 1
            rv[j] = np.log(np.maximum(np.mean(past[-21:] ** 2, axis=0), 1e-12))
            liq[j, fund_cols] = liquid.iloc[i].to_numpy()
        xs = {
            k: np.broadcast_to(features[k].iloc[starts].to_numpy()[:, None], shape)
            for k in ["vix", "curve", "unemployment", "gpr", "tone"]
        }
        xs.update(realized=rv, momentum=momentum, liquidity=liq)
        for target in ["variance", "return"] if h == 21 else ["variance"]:
            variance = target == "variance"
            y = target_var if variance else ret
            base = hist.copy() if variance else np.full(shape, np.nan)
            if not variance:
                for i, day in enumerate(days):
                    past = ret[
                        (ends < day)
                        & ~((days < cfg["final_start"]) & (ends >= cfg["final_start"]))
                    ]
                    count = np.isfinite(past).sum(axis=0)
                    base[i] = np.where(
                        count > 0,
                        0.5 * np.nansum(past, axis=0) / np.maximum(count, 1),
                        np.nan,
                    )
            for name, x in xs.items():
                pred = incremental(
                    x,
                    np.log(np.maximum(y, 1e-12)) if variance else y,
                    np.log(base) if variance else base,
                    days,
                    ends,
                    cfg,
                    variance,
                )
                final = days >= cfg["final_start"]
                # QLIKE's target-only term cancels in a paired difference.
                delta = (loss(target, y, base) - loss(target, y, pred))[final]
                counts = np.isfinite(delta).sum(axis=0)
                gain = np.nansum(delta, axis=0) / np.maximum(counts, 1)
                local.append(
                    pd.DataFrame(
                        {
                            "instrument": ids,
                            "class": inv.loc[ids, "class"].values,
                            "signal": name,
                            "target": target,
                            "horizon": h,
                            "n": counts,
                            "gain": np.where(counts > 0, gain, np.nan),
                            "comparable": counts >= 8,
                        }
                    )
                )
    ledger = pd.concat(local, ignore_index=True)
    assert (
        len(ledger) == len(ids) * 24
        and not ledger.duplicated(["instrument", "target", "horizon", "signal"]).any()
    )
    ledger.to_parquet(RAW.parent / "cross-asset.parquet", index=False)
    ledger["improved"] = ledger.comparable & ledger.gain.gt(0)
    ledger["measured_id"] = ledger.instrument.where(ledger.comparable)
    ledger["positive_id"] = ledger.instrument.where(ledger.improved)

    def table(keys):
        return (
            ledger.groupby(keys)
            .agg(
                inventory=("instrument", "nunique"),
                with_eight=("measured_id", "nunique"),
                any_positive=("positive_id", "nunique"),
            )
            .reset_index()
            .to_dict("records")
        )

    summary = {
        "inventory": len(ids),
        "rows": len(ledger),
        "by_signal": table(["class", "target", "horizon", "signal"]),
        "by_class": table(["class", "target", "horizon"]),
        "by_target": table(["target", "horizon"]),
    }
    (REPORT / "cross-asset.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n"
    )
    print(summary["by_target"])


if __name__ == "__main__":
    main()
