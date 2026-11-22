"""Numerical replay of selected QARM lab checkpoints, adapted from the project's archived course_labs.py."""

from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/Data for laboratories-20261119"
FIXTURES = {
    "sentratio_and_price_closetoclose_adj2.pkl": "bdafbf3fbab0067e6d12860e04acdc31c6589c9d655a44e2e7fa197efa51d577",
    "sentratio_and_price_for_pf2.pkl": "867f9ce5ec4f334a9ecea18b9c0f70cd3065e0eff85fee7afc62361daa1107d2",
    "sentratio_and_price_st.csv": "2fc7c7bdfe2395057ad701a4864c1c9f6465b669e70afe747e5178c242c75067",
}

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


def markowitz():
    gamma = brentq(lambda g: vol(unrestricted(SIGMA, MEAN, g), SIGMA) - 0.20, 0, 3)
    target = unrestricted(SIGMA, MEAN, gamma)
    rf = 0.015
    direction = np.linalg.solve(SIGMA, MEAN - rf)
    tangency = direction / direction.sum()
    np.testing.assert_allclose(
        tangency, [0.63631663, 0.19266966, 0.5027406, -0.33172689], atol=1e-7
    )
    assert abs(target @ MEAN - 0.0786565) < 1e-4
    return dict(target_return=float(target @ MEAN), tangency=tangency.tolist())


def beta(raw):
    series = raw.pivot(
        index="date", columns="ticker", values="daily_return"
    ).sort_index()
    assert len(series.columns) == 19
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
        slope = np.linalg.lstsq(
            np.column_stack([np.ones(len(pair)), pair.market]), pair.asset, rcond=None
        )[0][1]
        betas[ticker] = float(slope)
    np.testing.assert_allclose(
        [betas["AAPL"], np.mean(list(betas.values()))],
        [1.0323563487803322, 0.6499511439353759],
        atol=1e-8,
    )
    return dict(
        aapl=betas["AAPL"], equal_weight_beta=float(np.mean(list(betas.values())))
    )


def stability(raw):
    std = np.array([0.2, 0.21, 0.1])
    cov3 = np.outer(std, std) * (0.8 + 0.2 * np.eye(3))
    m3 = np.array([0.08, 0.08, 0.05])
    gamma = brentq(lambda g: vol(unrestricted(cov3, m3, g), cov3) - 0.15, 0, 4)
    obtained_vol = vol(unrestricted(cov3, m3, gamma), cov3)
    np.testing.assert_allclose(obtained_vol, 0.15, atol=1e-10)
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
    # Fixed diagonal shrinkage sanity check on an independent two-asset fixture.
    empirical = np.array([[4.0, 2.0], [2.0, 9.0]]) / 100
    shrunk = 0.75 * empirical + 0.25 * np.diag(np.diag(empirical))
    np.testing.assert_allclose(shrunk[0], [0.04, 0.015], atol=1e-12)
    return dict(
        assets=len(mean),
        equal_weight_vol=vol(ew, cov),
        equal_weight_return=float(ew @ mean),
        example_gamma=gamma,
        achieved_vol=obtained_vol,
        course_gamma_vol=vol(unrestricted(cov3, m3, 0.5070231995512946), cov3),
        shrunk_cross_covariance=float(shrunk[0, 1]),
    )


def black_litterman():
    anchor = np.array([0.4, 0.3, 0.2, 0.1])
    phi = 0.25 / vol(anchor, SIGMA)
    implied = 0.03 + phi * SIGMA @ anchor
    picks = np.array([[1, 0, 0, 0], [0, 1, -1, 0]])
    views = np.array([0.04, -0.01])
    noise = np.diag([0.1**2, 0.05**2])

    def portfolio(tau):
        prior = tau * SIGMA
        posterior = implied + prior @ picks.T @ np.linalg.solve(
            picks @ prior @ picks.T + noise, views - picks @ implied
        )
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
    return dict(
        residual_pairs=len(joined),
        max_error=float((joined.estimated - joined.abnormal_return).abs().max()),
        supplied_event_counts=counts,
        start=str(raw.date.min()),
        end=str(raw.date.max()),
    )


def identical_assets():
    # Perfectly correlated clones must have the same portfolio volatility at every split.
    covariance = np.full((2, 2), 0.04)
    for fraction in (0.0, 0.2, 0.5, 0.8, 1.0):
        weights = np.array([fraction, 1.0 - fraction])
        np.testing.assert_allclose(vol(weights, covariance), 0.2, atol=1e-12)
        contributions = weights * (covariance @ weights) / 0.2
        np.testing.assert_allclose(contributions, 0.2 * weights, atol=1e-12)
    return dict(volatility=0.2, splits=5)


if __name__ == "__main__":
    # Check local archive identities before deserializing the trusted classroom fixtures.
    for name, expected in FIXTURES.items():
        with (DATA / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError(f"Unrecognized teaching fixture: {name}")
    raw = pd.read_csv(DATA / "sentratio_and_price_st.csv", parse_dates=["date"])
    results = dict(
        LN1=markowitz(),
        LN2=beta(raw),
        LN3=stability(raw),
        LN4=black_litterman(),
        LN5=risk_budget(),
        LN6=identical_assets(),
        LN7=sentiment(),
    )
    print(json.dumps(results, indent=2, allow_nan=False))
