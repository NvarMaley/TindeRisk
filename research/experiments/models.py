"""Monthly forecasts under the registered readiness and label-availability gates."""

import numpy as np
import pandas as pd
from arch import arch_model
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch

ASSETS = ["SPY", "IEF", "GLD"]
EW = np.full(3, 1 / 3)
BASE = {
    "H01": "sample covariance",
    "H02": "rolling 63",
    "H03": "slope OLS",
    "H04": "expanding mean",
    "H05": "four-characteristic rank",
    "H06": "no-view anchor",
    "H07": "monthly",
}
CAND = {
    "H01": ["Ledoit-Wolf"],
    "H02": ["EWMA", "GARCH-t"],
    "H03": ["slope + macro PC"],
    "H04": ["OLS", "ridge"],
    "H05": ["elastic net", "boosting"],
    "H06": ["signed view or anchor"],
    "H07": ["quarterly", "5pp band"],
}
MACRO = ["CPIAUCSL", "UNRATE", "INDPRO"]
COLUMNS = {
    "slope OLS": ["T10Y2Y"],
    "slope + macro PC": ["T10Y2Y", *MACRO],
    "expanding mean": [],
    "OLS": ["T10Y2Y", "BAA10Y"],
    "ridge": ["T10Y2Y", "BAA10Y"],
}


def macro_fit(train, row, arm):
    cols = COLUMNS[arm]
    fit = train.dropna(subset=["target", *cols])
    if len(fit) < 36 or row[cols].isna().any():
        return np.nan, len(fit)
    if not cols:
        return fit.target.mean(), len(fit)
    x = fit[cols].to_numpy()
    z = row[cols].to_numpy(dtype=float)[None, :]
    if arm == "slope + macro PC":
        scaler = StandardScaler().fit(x[:, 1:])
        pc = PCA(n_components=1, svd_solver="full").fit(scaler.transform(x[:, 1:]))
        x = np.column_stack((x[:, 0], pc.transform(scaler.transform(x[:, 1:]))))
        z = np.column_stack((z[:, 0], pc.transform(scaler.transform(z[:, 1:]))))
    if arm == "ridge":
        scaler = StandardScaler().fit(x)
        x, z = scaler.transform(x), scaler.transform(z)
    model = Ridge(alpha=1.0) if arm == "ridge" else LinearRegression()
    return model.fit(x, fit.target).predict(z)[0], len(fit)


def minimum_variance(cov):
    scaled = cov / np.trace(cov)
    fit = minimize(
        lambda w: w @ scaled @ w,
        EW,
        jac=lambda w: 2 * scaled @ w,
        bounds=[(0, 1)] * 3,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        method="SLSQP",
        options={"ftol": 1e-12},
    )
    if not fit.success:
        raise ValueError(fit.message)
    return fit.x


def garch_risk(series, horizon):
    fitted = arch_model(
        100 * series, mean="Zero", vol="Garch", p=1, q=1, dist="t", rescale=False
    ).fit(disp="off", show_warning=False)
    params = fitted.params
    persistence = params["alpha[1]"] + params["beta[1]"]
    std = fitted.std_resid.dropna()
    info = {
        "convergence": int(fitted.convergence_flag),
        "persistence": persistence,
        "nu": params["nu"],
        "ljung_box_p": acorr_ljungbox(std, lags=[10]).lb_pvalue.iloc[0],
        "squared_ljung_box_p": acorr_ljungbox(std**2, lags=[10]).lb_pvalue.iloc[0],
        "arch_lm_p": het_arch(std, nlags=10)[1],
    }
    variances = (
        fitted.forecast(horizon=horizon, reindex=False).variance.iloc[-1].to_numpy()
        / 10000
    )
    admissible = (
        not fitted.convergence_flag
        and params["nu"] > 2
        and persistence < 1
        and np.isfinite(variances).all()
        and (variances > 0).all()
    )
    return (variances.mean() if admissible else np.nan), info


def forecast(frozen, market, features, cash):
    usd = market.pivot(index="session", columns="asset", values="usd_return")[ASSETS]
    chf = market.pivot(index="session", columns="asset", values="chf_return")[ASSETS]
    cash = cash.set_index("session").usd_cash_proxy
    f = features.pivot(index="session", columns="series", values="value")
    available = features.groupby("session").available_at.max()
    tables = {}
    for study, asset in [("H03", "IEF"), ("H04", "SPY")]:
        rows = []
        for per, d in usd.groupby(usd.index.to_period("M")):
            bill = cash.reindex(d.index)
            target = (
                (1 + d[asset]).prod() - (1 + bill).prod()
                if d[asset].notna().all() and bill.notna().all()
                else np.nan
            )
            rows.append((str(per), d.index[-1], target))
        t = pd.DataFrame(
            rows, columns=["holding_month", "label_end", "target"]
        ).set_index("holding_month")
        origins = (
            frozen.loc[(frozen.study == study) & (frozen.arm == BASE[study])]
            .set_index("holding_month")
            .origin
        )
        t = t.join(origins, how="inner")
        tables[study] = t.join(f, on="origin")
    subs = frozen[frozen.study.isin(["H01", "H02", "H03", "H04"])]
    rows = []
    targets = {}
    months = {str(k): v for k, v in chf.groupby(chf.index.to_period("M"))}
    for r in subs.itertuples():
        study, month, arm = r.study, r.holding_month, r.arm
        garch_info = {}
        prediction = target = condition = shrink = np.nan
        n = 0
        training_end = pd.NaT
        days = months[month]
        horizon = len(days)
        feature_available = pd.NaT
        if study in tables:
            tab = tables[study]
            row = tab.loc[month]
            target = row.target
            train = tab[tab.label_end < r.origin]
            if r.input_ready:
                prediction, n = macro_fit(train, row, arm)
                used = train.dropna(subset=["target", *COLUMNS[arm]])
                training_end = used.label_end.max()
                if COLUMNS[arm]:
                    feature_available = available.get(r.origin)
                if pd.notna(feature_available) and feature_available >= r.decision_at:
                    raise ValueError("Unreleased feature")
                if np.isfinite(prediction):
                    w = np.zeros(3)
                    w[ASSETS.index("IEF" if study == "H03" else "SPY")] = float(
                        prediction > 0
                    )
                    targets[study, arm, month] = w
        else:
            sleeve = days @ EW
            target = (sleeve**2).sum() if r.outcome_complete else np.nan
            if r.input_ready:
                size = 756 if study == "H01" or arm == "GARCH-t" else 63
                window = chf.loc[: r.origin].tail(size)
                grid = window.dropna()
                n = len(grid)
                training_end = grid.index[-1]
                if study == "H01":
                    if arm == "Ledoit-Wolf":
                        model = LedoitWolf().fit(grid)
                        cov = model.covariance_
                        shrink = model.shrinkage_
                    else:
                        cov = grid.cov().to_numpy()
                    condition = np.linalg.cond(cov)
                    var = EW @ cov @ EW
                    weights = minimum_variance(cov)
                elif arm == "GARCH-t":
                    var, garch_info = garch_risk(grid @ EW, horizon)
                    weights = (
                        EW * min(1, 0.10 / np.sqrt(252 * var))
                        if np.isfinite(var)
                        else None
                    )
                else:
                    series = window @ EW
                    decay = 0.94 ** np.arange(len(series) - 1, -1, -1)
                    valid = series.notna()
                    var = (
                        series.var()
                        if arm == "rolling 63"
                        else np.average(series[valid] ** 2, weights=decay[valid])
                    )
                    weights = EW * min(1, 0.10 / np.sqrt(252 * var))
                prediction = horizon * var
                if weights is not None:
                    targets[study, arm, month] = weights
        rows.append(
            dict(
                study=study,
                arm=arm,
                holding_month=month,
                phase=r.phase,
                origin=r.origin,
                decision_at=r.decision_at,
                end=days.index[-1],
                horizon_sessions=horizon,
                currency="USD" if study in tables else "CHF",
                n_train=n,
                train_last=training_end,
                feature_available=feature_available,
                point=prediction,
                actual=target,
                condition=condition,
                shrinkage=shrink,
                input_ready=r.input_ready,
                **garch_info,
            )
        )
    return pd.DataFrame(rows), targets, tables


def add_controls(df):
    extra = []
    for study, part in df.groupby("study"):
        wide = part.pivot(index="holding_month", columns="arm", values="point")
        # GARCH has no eligible fit. The volatility combination is explicitly rolling plus EWMA.
        components = {
            "H01": ["sample covariance", "Ledoit-Wolf"],
            "H02": ["rolling 63", "EWMA"],
            "H03": ["slope OLS", "slope + macro PC"],
            "H04": ["expanding mean", "OLS", "ridge"],
        }[study]
        row = part[part.arm == BASE[study]].copy()
        avg = wide[components].mean(axis=1, skipna=False)
        row["arm"] = "equal forecast combination"
        row["point"] = row.holding_month.map(avg)
        row["input_ready"] = row.point.notna()
        row[["condition", "shrinkage", "n_train"]] = np.nan
        extra.append(row)
    out = pd.concat([df, *extra], ignore_index=True).sort_values(
        ["study", "arm", "origin"]
    )
    refs = (
        out[out.arm.eq(out.study.map(BASE))].set_index(["study", "holding_month"]).point
    )
    keys = pd.MultiIndex.from_frame(out[["study", "holding_month"]])
    out["deployed_point"] = out.point.fillna(
        pd.Series(refs.reindex(keys).to_numpy(), index=out.index)
    )
    out["action"] = np.select(
        [out.point.notna(), out.deployed_point.notna()],
        ["own forecast", "reference fallback"],
        default="unresolved",
    )
    for col in ["lower", "upper"]:
        out[col] = np.nan
    for (_, _), group in out[out.study.isin(["H03", "H04"])].groupby(["study", "arm"]):
        for row in group.itertuples():
            past = group[group.end < row.origin]
            errors = (past.actual - past.deployed_point).dropna()
            if len(errors) >= 24 and np.isfinite(row.deployed_point):
                out.loc[row.Index, ["lower", "upper"]] = (
                    row.deployed_point + np.quantile(errors, [0.1, 0.9])
                )
    for col, pt in [("loss", "point"), ("deployed_loss", "deployed_point")]:
        out[col] = (out.actual - out[pt]) ** 2
        risk = out.study.isin(["H01", "H02"])
        ratio = out.loc[risk, "actual"] / out.loc[risk, pt]
        out.loc[risk, col] = ratio - np.log(ratio) - 1
    return out


def macro_refit_check(table, out):
    """Refit the entire H03 transform/forecast pipeline on joint training blocks."""
    latest = table.iloc[-1].copy()
    latest["target"] = np.nan
    arm = "slope + macro PC"
    train = table[table.label_end < latest.origin]
    reference, n = macro_fit(train, latest, arm)
    samples = []
    for length in (1, 3, 6):
        rng = np.random.default_rng(503)
        for draw in range(199):
            starts = rng.integers(
                0, len(train) - length + 1, (len(train) + length - 1) // length
            )
            ix = (starts[:, None] + np.arange(length)).ravel()[: len(train)]
            result, valid = macro_fit(train.iloc[ix], latest, arm)
            samples.append(
                {
                    "holding_month": latest.name,
                    "training_end": train.label_end.max(),
                    "block": length,
                    "draw": draw,
                    "training_complete": valid,
                    "original_n": n,
                    "reference": reference,
                    "refit": result,
                }
            )
    pd.DataFrame(samples).to_csv(out / "macro_refits.csv", index=False)
