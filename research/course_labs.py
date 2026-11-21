"""Reproduce the six QARM exercises from the repository root with local teaching data."""

from pathlib import Path
import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import osqp
from scipy import sparse
from scipy.optimize import brentq, minimize
import statsmodels.api as sm
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/Data for laboratories-20261119"
OUTPUT = ROOT / "results/course_labs"
SIGMA = np.array(
    [
        [0.0225, 0.003, 0.015, 0.0225],
        [0.003, 0.04, 0.035, 0.024],
        [0.015, 0.035, 0.0625, 0.06],
        [0.0225, 0.024, 0.06, 0.09],
    ]
)
MEAN = np.array([0.05, 0.06, 0.08, 0.06])


def unrestricted(cov, mean, gamma):
    ones = np.ones_like(mean)
    inverse_one = np.linalg.solve(cov, ones)
    tilt = np.linalg.solve(cov, gamma * mean)
    return tilt + inverse_one * ((1 - tilt.sum()) / inverse_one.sum())


def vol(w, cov):
    return float(np.sqrt(w @ cov @ w))


def bounded_frontier(cov, mean, gammas):
    """Reuse one QP factorization over the entire fully invested long-only grid."""
    n = len(mean)
    solver = osqp.OSQP()
    bounds = sparse.vstack((np.ones((1, n)), sparse.eye(n)), format="csc")
    solver.setup(
        P=sparse.csc_matrix(np.triu(cov)),
        q=np.zeros(n),
        A=bounds,
        l=np.r_[1, np.zeros(n)],
        u=np.ones(n + 1),
        verbose=False,
        eps_abs=1e-7,
        eps_rel=1e-7,
        max_iter=30000,
    )
    weights = []
    for gamma in gammas:
        solver.update(q=-gamma * mean)
        result = solver.solve(raise_error=True)
        weights.append(result.x.copy())
    weights = np.array(weights)
    assert weights.min() > -1e-5 and np.allclose(weights.sum(axis=1), 1, atol=1e-5)
    return weights


def chart(name):
    plt.tight_layout()
    plt.savefig(OUTPUT / (name + ".png"), dpi=120)
    plt.close()


def markowitz():
    grid = np.linspace(-0.5, 3, 101)
    weights = [unrestricted(SIGMA, MEAN, g) for g in grid]
    gamma = brentq(lambda g: vol(unrestricted(SIGMA, MEAN, g), SIGMA) - 0.20, 0, 3)
    target = unrestricted(SIGMA, MEAN, gamma)
    rf = 0.015
    direction = np.linalg.solve(SIGMA, MEAN - rf)
    tangency = direction / direction.sum()
    np.testing.assert_allclose(
        tangency, [0.63631663, 0.19266966, 0.5027406, -0.33172689], atol=1e-7
    )
    assert abs(target @ MEAN - 0.0786565) < 1e-4
    plt.plot(
        [vol(w, SIGMA) for w in weights],
        [w @ MEAN for w in weights],
        label="Risky frontier",
    )
    gmv = unrestricted(SIGMA, MEAN, 0)
    plt.scatter(vol(gmv, SIGMA), gmv @ MEAN, label="Minimum variance")
    risky = np.linspace(0, 3, 101)
    plt.plot(
        risky * vol(tangency, SIGMA),
        rf + risky * (tangency @ MEAN - rf),
        label="Capital market line",
    )
    for g in np.linspace(0, 3, 101):
        w = g * direction
        cash = 1 - w.sum()
        assert np.isclose(
            w @ MEAN + cash * rf,
            rf + vol(w, SIGMA) * (tangency @ MEAN - rf) / vol(tangency, SIGMA),
        )
    plt.xlabel("Volatility")
    plt.ylabel("Expected return")
    plt.legend()
    chart("LN1-frontiers")
    return dict(
        target_return=float(target @ MEAN),
        target_gamma=gamma,
        tangency=tangency.tolist(),
    )


def beta(raw):
    series = raw.pivot(
        index="date", columns="ticker", values="daily_return"
    ).sort_index()
    assert len(series.columns) == 19
    (1 + series).cumprod().plot(legend=False)
    chart("LN2-raw-wealth")
    series["AAPL"].plot()
    chart("LN2-apple-returns")
    series["UVXY"].plot()
    chart("LN2-identified-anomaly")
    anomaly = (series.index == pd.Timestamp("2012-03-08", tz="UTC")) & series[
        "UVXY"
    ].eq(-1)
    assert anomaly.sum() == 1
    series.loc[anomaly, "UVXY"] = 0
    betas = {}
    for ticker in series:
        pair = pd.concat(
            [series["SPY"].rename("market"), series[ticker].rename("asset")], axis=1
        ).dropna()
        fit = sm.OLS(pair.asset, sm.add_constant(pair.market)).fit()
        betas[ticker] = float(fit.params["market"])
    np.testing.assert_allclose(
        [betas["AAPL"], np.mean(list(betas.values()))],
        [1.0323563487803322, 0.6499511439353759],
        atol=1e-8,
    )
    return dict(
        aapl=betas["AAPL"], equal_weight_beta=float(np.mean(list(betas.values())))
    )


def stability(raw, seed):
    std = np.array([0.2, 0.21, 0.1])
    cov3 = np.outer(std, std) * (0.8 + 0.2 * np.eye(3))
    m3 = np.array([0.08, 0.08, 0.05])
    gamma = brentq(lambda g: vol(unrestricted(cov3, m3, g), cov3) - 0.15, 0, 4)
    series = raw[raw.ticker.ne("UVXY")].pivot(
        index="date", columns="ticker", values="daily_return"
    )
    logs = np.log1p(series)
    # Match the supplied lab's compounding convention on its daily log-return panel.
    mean = np.expm1(252 * np.log1p(logs.mean().to_numpy()))
    annual_vol = logs.std().to_numpy() * np.sqrt(252)
    cov = logs.corr().to_numpy() * np.outer(annual_vol, annual_vol)
    ew = np.ones(len(mean)) / len(mean)
    np.testing.assert_allclose(
        [ew @ mean, vol(ew, cov)], [0.0779432517062751, 0.2263117647657294], atol=1e-8
    )
    grid = np.linspace(-0.5, 3, 501)
    short = np.array([unrestricted(cov, mean, g) for g in grid])
    long_grid = np.linspace(-0.5, 1.5, 501)
    long = bounded_frontier(cov, mean, long_grid)
    for name, w, g in [("unrestricted", short, grid), ("long-only", long, long_grid)]:
        plt.scatter(np.sqrt(np.einsum("ij,jk,ik->i", w, cov, w)), w @ mean, c=g, s=4)
        plt.xlabel("Annual volatility")
        plt.ylabel("Lab annualized return")
        chart("LN3-frontier-" + name)
        plt.stackplot(g, w.T)
        plt.xlabel("Risk tolerance parameter")
        chart("LN3-composition-" + name)
    rng = np.random.default_rng(seed)
    grid = np.linspace(-0.5, 1.5, 101)
    total = np.zeros((len(grid), len(mean)))
    for i in range(500):
        sample = rng.multivariate_normal(mean, cov, 100, check_valid="raise")
        trial = bounded_frontier(
            np.cov(sample, rowvar=False), sample.mean(axis=0), grid
        )
        total += trial
        if i == 0:
            pd.DataFrame(
                {"Original": mean, "Sample": sample.mean(axis=0)}, index=logs.columns
            ).plot.bar()
            chart("LN3-first-draw")
    average = total / 500
    assert np.allclose(average.sum(axis=1), 1)
    plt.stackplot(grid, average.T)
    plt.xlabel("Risk tolerance parameter")
    chart("LN3-resampled")
    return dict(
        target_gamma=gamma,
        equal_weight_vol=vol(ew, cov),
        draws=500,
        portfolios_per_draw=len(grid),
    )


def black_litterman():
    anchor = np.array([0.4, 0.3, 0.2, 0.1])
    phi = 0.25 / vol(anchor, SIGMA)
    implied = 0.03 + phi * SIGMA @ anchor
    picks = np.array([[1, 0, 0, 0], [0, 1, -1, 0]])
    views = np.array([0.04, -0.01])
    noise = np.diag([0.1**2, 0.05**2])

    def portfolio(tau, precise=False):
        prior = tau * SIGMA
        posterior = implied + prior @ picks.T @ np.linalg.solve(
            picks @ prior @ picks.T + noise, views - picks @ implied
        )
        if precise:
            return bounded_frontier(SIGMA, posterior, [1 / phi])[0]
        # The teaching output uses SLSQP's default stopping tolerance at the anchor.
        fit = minimize(
            lambda w: 0.5 * w @ SIGMA @ w - w @ posterior / phi,
            anchor,
            method="SLSQP",
            bounds=[(0, 1)] * 4,
            constraints=[dict(type="eq", fun=lambda w: w.sum() - 1)],
        )
        assert fit.success, fit.message
        return fit.x

    def tracking(tau):
        return vol(portfolio(tau) - anchor, SIGMA)

    tau = brentq(lambda t: tracking(t) - 0.02, 0, 1)
    np.testing.assert_allclose(
        [vol(anchor, SIGMA), phi], [0.15349267083479914, 1.6287422626782593], atol=1e-9
    )
    np.testing.assert_allclose(
        [tracking(0.05), tau], [0.013212510637878089, 0.09612848941361753], atol=1e-5
    )
    return dict(
        implied_phi=phi,
        tracking_at_point05=tracking(0.05),
        tau_for_two_percent=tau,
        tighter_solver_tracking=vol(portfolio(0.05, precise=True) - anchor, SIGMA),
    )


def risk_budget():
    std = np.array([0.3, 0.25, 0.2, 0.15])
    cov = np.outer(std, std) * (0.7 + 0.3 * np.eye(4))
    ew = np.full(4, 0.25)
    c = -8
    sol = minimize(
        lambda w: 0.5 * w @ cov @ w,
        ew,
        jac=lambda w: cov @ w,
        bounds=[(1e-9, 1)] * 4,
        constraints=[
            dict(type="ineq", fun=lambda w: np.log(w).sum() - c, jac=lambda w: 1 / w)
        ],
        method="SLSQP",
        options={"ftol": 1e-13},
    )
    assert sol.success, sol.message
    w = sol.x / sol.x.sum()
    absolute = w * (cov @ w) / vol(w, cov)
    relative = absolute / vol(w, cov)
    np.testing.assert_allclose(relative, 0.25, atol=1e-6)
    np.testing.assert_allclose(vol(ew, cov), 0.19866743568083822)
    return dict(
        equal_weight_vol=vol(ew, cov),
        equal_weight_contributions=(ew * (cov @ ew) / vol(ew, cov)).tolist(),
        erc=w.tolist(),
        absolute_contributions=absolute.tolist(),
        relative_contributions=relative.tolist(),
    )


def sentiment():
    raw = pd.read_pickle(DATA / "sentratio_and_price_closetoclose_adj2.pkl")
    supplied = pd.read_pickle(DATA / "sentratio_and_price_for_pf2.pkl")
    market = raw.loc[raw.ticker.eq("SPY")].set_index("date").daily_return
    raw["market"] = raw.date.map(market)
    assert raw.ticker.nunique() == 19
    raw.loc[raw.ticker.eq("AAPL")].plot(x="date", y="N")
    chart("LN7-apple-volume")
    raw.groupby("date").N.sum().plot()
    chart("LN7-total-volume")
    results = []
    for ticker, group in raw.sort_values("date").groupby("ticker"):
        frame = group.set_index("date")
        xy = frame[["market", "daily_return"]].dropna()
        for date, row in xy.loc["2011":].iterrows():
            prior = xy.iloc[
                xy.index.searchsorted(
                    date - pd.Timedelta(days=365), side="right"
                ) : xy.index.searchsorted(date)
            ]
            if len(prior):
                slope, offset = np.linalg.lstsq(
                    np.column_stack([prior.market, np.ones(len(prior))]),
                    prior.daily_return,
                    rcond=None,
                )[0]
            else:
                slope, offset = 1.0, 0.0
            results.append(
                (ticker, date, row.daily_return - offset - slope * row.market)
            )
    model = pd.DataFrame(results, columns=["ticker", "date", "estimated"])
    joined = model.merge(
        supplied[["ticker", "date", "abnormal_return"]],
        on=["ticker", "date"],
        validate="one_to_one",
    ).dropna()
    assert len(joined) == supplied.abnormal_return.notna().sum() == 37950
    np.testing.assert_allclose(
        joined.estimated, joined.abnormal_return, rtol=0, atol=1e-10
    )
    events = supplied[supplied.Event3]
    counts = events.Type.value_counts().to_dict()
    assert counts == {"Good": 454, "Bad": 383, "Neutral": 294}
    apple = supplied[supplied.ticker.eq("AAPL")]
    plt.plot(apple.date, apple.N, linewidth=0.6)
    for label, group in apple[apple.Event3].groupby("Type"):
        plt.scatter(group.date, group.N, label=label, s=10)
    plt.legend()
    chart("LN7-events")
    ordered = supplied.sort_values(["ticker", "date"]).copy()
    cumulative = ordered.groupby("ticker").abnormal_pol.cumsum()
    ordered["CAP"] = cumulative - cumulative.groupby(ordered.ticker).shift(14)
    cap = (
        ordered.pivot(index="date", columns="ticker", values="CAP")
        .iloc[14:]
        .replace(0, np.nan)
    )
    returns = ordered.pivot(
        index="date", columns="ticker", values="daily_return"
    ).reindex_like(cap)
    center, delta = cap.mean(axis=1), 1.96 * cap.std(axis=1)
    positions = [cap.gt(center + delta, axis=0), cap.lt(center - delta, axis=0)]
    forward = returns.fillna(0).shift(-1)
    paths = {}
    for name, mask, sign in zip(
        ["Bullish", "Short bearish"], positions, [1, -1], strict=True
    ):
        mask = mask & returns.notna()
        paths[name] = sign * forward.where(mask).mean(axis=1).iloc[:-1].fillna(0)
    paths["SPY"] = forward.SPY.iloc[:-1]
    wealth = np.log1p(pd.DataFrame(paths)).cumsum()
    wealth.plot()
    chart("LN7-strategy")
    return dict(
        residual_pairs=len(joined),
        max_abs_error=float((joined.estimated - joined.abnormal_return).abs().max()),
        event_counts=counts,
        holding_sessions=1,
    )


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(DATA / "sentratio_and_price_st.csv", parse_dates=["date"])
    seed = yaml.safe_load((ROOT / "config.yaml").read_text())["seeds"][
        "course_resampling"
    ]
    results = {}
    for label, run in [
        ("LN1", markowitz),
        ("LN2", lambda: beta(source)),
        ("LN3", lambda: stability(source, seed)),
        ("LN4", black_litterman),
        ("LN5", risk_budget),
        ("LN7", sentiment),
    ]:
        results[label] = run()
        print(label, results[label], flush=True)
    (OUTPUT / "checks.json").write_text(
        json.dumps(results, indent=2, allow_nan=False) + "\n"
    )
