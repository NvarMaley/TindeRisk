"""Expanding-window predictions. Every label in a fit matures before its decision."""

import numpy as np
import pandas as pd
from arch import arch_model
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def black_litterman(prior, view, prior_var, omega):
    """Single absolute excess-return view, P=[1], all quantities in block units."""
    if prior_var < 0 or omega <= 0:
        raise ValueError("Invalid view uncertainty")
    return prior + prior_var / (omega + prior_var) * (view - prior)


def matured(table, start, boundary=None):
    eligible = table.end < start
    if boundary is not None:
        eligible &= ~((table.index < boundary) & (table.end >= boundary))
    return table[eligible]


def ridge(train, row, columns, target, incremental, alpha):
    past = train.dropna(subset=[*columns, target, "baseline"])
    if len(past) < 24 or row[columns].isna().any():
        return np.nan
    y = past[target].to_numpy()
    if target == "variance":
        y = np.log(np.maximum(y, 1e-12))
    baseline = np.log(past.baseline) if target == "variance" else past.baseline
    estimator = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    estimator.fit(past[columns], y - baseline if incremental else y)
    yhat = estimator.predict(row[columns].to_frame().T.astype(float))[0]
    if incremental:
        yhat += np.log(row.baseline) if target == "variance" else row.baseline
    return float(
        np.clip(yhat, y.min(), y.max())
        if target == "return"
        else np.exp(np.clip(yhat, y.min(), y.max()))
    )


def forecast(r, features, h, cfg):
    records = []
    for i in range(252, len(r) - h, h):
        history = r.iloc[max(1, i - 756) : i].dropna().to_numpy()
        future = r.iloc[i + 1 : i + h + 1].to_numpy()
        rv = float(np.mean(history[-63:] ** 2))
        weights = 0.94 ** np.arange(62, -1, -1)
        row = {
            "day": r.index[i],
            "end": r.index[i + h],
            "cut": r.index[i - 1],
            "variance": float(np.mean(future**2)),
            "ret": float(np.prod(1 + future) - 1),
            "hist": rv,
            "ewma": float(np.average(history[-63:] ** 2, weights=weights)),
        }
        row.update(features.iloc[i].to_dict())
        row["garch"] = np.nan
        if row["day"] >= pd.Timestamp(cfg["validation_start"]):
            fit = arch_model(history * 100, mean="Zero", p=1, q=1, rescale=False).fit(
                disp="off", show_warning=False
            )
            if fit.convergence_flag == 0:
                # Condition on t-1. The first realized target return is t+1.
                row["garch"] = float(
                    fit.forecast(horizon=h + 1).variance.iloc[-1, 1:].mean() / 10000
                )
        records.append(row)
    table = pd.DataFrame(records).rename(columns={"ret": "return"}).set_index("day")
    out = {}
    for target in ["variance", "return"] if h == 21 else ["variance"]:
        t = table.copy()
        t["baseline"] = (
            t["hist"]
            if target == "variance"
            else [
                matured(t, day, cfg["final_start"])["return"].mean() * 0.5
                for day in t.index
            ]
        )
        for day, row in t[t.index >= cfg["validation_start"]].iterrows():
            past = matured(t, day, cfg["final_start"])
            assert past.empty or past.end.max() < day
            for name in features:
                for mode in ["alone", "increment"]:
                    t.loc[day, mode + "_" + name] = ridge(
                        past,
                        row,
                        [name],
                        target,
                        mode == "increment",
                        cfg["ridge_alpha"],
                    )
            if h == 21 and target == "return" and len(past) >= cfg["min_train"]:
                y = past["return"].le(-0.05).astype(int)
                t.loc[day, "frequency"] = (y.sum() + 1) / (len(y) + 2)
                if y.nunique() == 2:
                    prob = make_pipeline(StandardScaler(), LogisticRegression(C=1))
                    prob.fit(past[["realized"]], y)
                    t.loc[day, "probability"] = prob.predict_proba(
                        t.loc[[day], ["realized"]]
                    )[0, 1]
                t.loc[day, ["lower", "upper"]] = (
                    past["return"].quantile([0.1, 0.9]).to_numpy()
                )
        out[target] = t
    return out
