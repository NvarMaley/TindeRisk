"""Freeze input eligibility separately from later outcome coverage for each registered arm."""

import pandas as pd

from .availability import eligible_session
from .markets import SLEEVE, dated_csv
from .timing import next_session_open


def fill_action(quote, fx):
    return (
        "historical quote proxy"
        if pd.notna(quote) and quote > 0 and pd.notna(fx) and fx > 0
        else "hold; retry next eligible session"
    )


def sentiment_inputs(data, output, calendar):
    raw = pd.read_csv(
        next(data.glob("Data for laboratories*/*.csv")), parse_dates=["date"]
    )
    raw = raw[raw.ticker.isin(["AAPL", "SPY"])].copy()
    raw["session"] = (
        pd.to_datetime(raw.date, utc=True).dt.tz_localize(None).dt.normalize()
    )
    if raw.duplicated(["ticker", "session"]).any():
        raise ValueError("Nonunique lab ticker/day")
    levels = dated_csv(data / "raw/ln7_public_aapl_spy_prices.csv")
    sessions = calendar.loc[levels.index.min() : "2020-03-23"].index
    lab = raw.pivot(index="session", columns="ticker", values="daily_return").reindex(
        sessions
    )
    price_returns = levels.reindex(sessions).pct_change(fill_method=None)
    # Source overlap is reported; before 2011 prices supply the warm-up. Never fill a missing lab return with a stale mark.
    combined = lab.copy()
    combined.loc[:"2010-12-31"] = price_returns.loc[:"2010-12-31"]
    combined.index.name = "session"
    combined.reset_index().to_parquet(output / "sentiment_returns.parquet", index=False)
    tagged = raw[raw.ticker.eq("AAPL")].copy()
    tagged["available_at"] = next_session_open(tagged.session, calendar)
    tagged["published_at"] = pd.Series(
        pd.NaT, dtype="datetime64[ns, UTC]", index=tagged.index
    )
    tagged["direction"] = tagged.Type.map({"Good": 1, "Bad": -1, "Neutral": 0})
    tagged[
        ["session", "available_at", "published_at", "Type", "direction", "N"]
    ].to_parquet(output / "sentiment_events.parquet", index=False)
    compared = (lab - price_returns).stack()
    return (
        combined,
        tagged,
        {
            "overlap_returns": len(compared),
            "max_abs_return_gap": float(compared.abs().max()),
        },
    )


def split(study, month):
    year = month.year
    end_years = (
        (2002, 2013, 2018)
        if study == "H05"
        else (2010, 2015, 2017)
        if study == "H06"
        else (2009, 2015, 2019)
    )
    return next(
        (
            label
            for limit, label in zip(end_years, ("warm-up", "development", "validation"))
            if year <= limit
        ),
        "historical replay",
    )


def sample_manifest(data, out, cal, market, features, cash, firm_counts):
    close = market.pivot(index="session", columns="asset", values="adjusted_usd")
    opening = market.pivot(
        index="session", columns="asset", values="chart_open_proxy_usd"
    )
    chf = market.pivot(index="session", columns="asset", values="chf_return")[SLEEVE]
    usd = market.pivot(index="session", columns="asset", values="usd_return")
    fx = market[market.asset.eq("SPY")].set_index("session").chf_per_usd
    f = features.pivot(index="session", columns="series", values="value")
    cash_daily = cash.set_index("session").usd_cash_proxy
    complete_day = chf.notna().all(axis=1)
    months = {period: part for period, part in cal.groupby(cal.index.to_period("M"))}
    lab, events, sentiment_stats = sentiment_inputs(data, out, cal)
    firms = firm_counts.set_index(firm_counts.month.dt.to_period("M"))
    periods = pd.period_range("1998-01", "2026-10", freq="M")
    rows = []
    known_outcomes = dict.fromkeys(
        ("slope OLS", "slope + macro PC", "expanding mean", "OLS", "ridge"), 0
    )
    for period in periods:
        prev, holding = months[period - 1], months[period]
        origin, first = prev.index[-1], holding.index[0]
        decision = prev.close.iloc[-1]
        scheduled = holding.open.iloc[0]
        for study in ("H01", "H02", "H03", "H04", "H05", "H06", "H07"):
            begin, end = {
                "H05": ("1998-01", "2025-12"),
                "H06": ("2010-01", "2020-02"),
            }.get(study, ("2005-01", "2026-10"))
            if not pd.Period(begin, "M") <= period <= pd.Period(end, "M"):
                continue
            phase = split(study, period)
            history = complete_day.loc[:origin]
            year3 = history.tail(756)
            short = history.tail(63)
            # The broad market calendar, including ineligible origins, is the denominator.
            hdays = holding.index
            available = f.loc[origin] if origin in f.index else pd.Series(dtype=float)
            n_assets = len(SLEEVE)
            view = None
            first_proxy = pd.NaT
            if study in ("H01", "H02", "H07"):
                targets = complete_day.reindex(hdays).fillna(False)
                proxy = fill_action(
                    opening.reindex([first])[SLEEVE].min(axis=1, skipna=False).iloc[0],
                    fx.get(first),
                )
                first_proxy = eligible_session(opening.reindex(hdays)[SLEEVE], fx)
                full756 = len(year3) == 756 and year3.sum() >= 719
                full63 = len(short) == 63 and short.sum() >= 60
                if study == "H01":
                    arms = {"sample covariance": full756, "Ledoit-Wolf": full756}
                elif study == "H02":
                    arms = {
                        "rolling 63": full63,
                        "EWMA": full63,
                        "GARCH-t": len(year3) == 756 and year3.all(),
                    }
                else:
                    complete = (
                        origin in close.index
                        and close.loc[origin, SLEEVE].notna().all()
                        and pd.notna(fx.get(origin))
                    )
                    arms = dict.fromkeys(("monthly", "quarterly", "5pp band"), complete)
                fallback = (
                    "use rolling 63 when eligible; otherwise unresolved"
                    if study == "H02"
                    else "hold current feasible mix"
                )
            elif study in ("H03", "H04"):
                ticker = "IEF" if study == "H03" else "SPY"
                targets = (
                    usd[ticker].reindex(hdays).notna()
                    & cash_daily.reindex(hdays).notna()
                )
                # Only previously completed labels strictly before the decision are counted below.
                slope = pd.notna(available.get("T10Y2Y"))
                if study == "H03":
                    all_macro = all(
                        pd.notna(available.get(k))
                        for k in ("UNRATE", "INDPRO", "CPIAUCSL")
                    )
                    arms = {"slope OLS": slope, "slope + macro PC": slope and all_macro}
                else:
                    spread = slope and pd.notna(available.get("BAA10Y"))
                    arms = {"expanding mean": True, "OLS": spread, "ridge": spread}
                arms = {
                    name: bool(ok and known_outcomes[name] >= 36)
                    for name, ok in arms.items()
                }
                proxy = fill_action(opening[ticker].get(first), 1)
                first_proxy = eligible_session(
                    opening.reindex(hdays)[[ticker]], pd.Series(1.0, index=hdays)
                )
                n_assets, fallback = (
                    1,
                    "use baseline if available; otherwise unresolved",
                )
            elif study == "H05":
                n_assets = (
                    int(firms.loc[period - 1, "linked_common"])
                    if period - 1 in firms.index
                    else 0
                )
                observed_stocks = (
                    int(firms.loc[period - 1, "next_returns"])
                    if period - 1 in firms.index
                    else 0
                )
                targets = pd.Series([n_assets > 0 and n_assets == observed_stocks])
                arms = dict.fromkeys(
                    ("four-characteristic rank", "elastic net", "boosting"), False
                )
                proxy, fallback = (
                    "unverified stock fills",
                    "withhold strategy; missing filing vintages",
                )
            else:
                n_assets = 2
                targets = lab.reindex(hdays).notna().all(axis=1)
                previous = lab.loc[:origin].tail(252)
                risk_ready = len(previous) >= 126 and previous.dropna().shape[0] >= 126
                seen = events[
                    (events.available_at < decision)
                    & (events.available_at >= prev.open.iloc[0])
                    & events.direction.notna()
                ]
                view = int(seen.iloc[-1].direction) if len(seen) else 0
                arms = {
                    "no-view anchor": risk_ready,
                    "signed view or anchor": risk_ready,
                }
                proxy, fallback = (
                    "returns-only replay; no fill price",
                    "use neutral anchor for absent or neutral view",
                )
            for arm, ready in arms.items():
                ready = bool(ready and phase != "warm-up")
                rows.append(
                    {
                        "study": study,
                        "arm": arm,
                        "holding_month": str(period),
                        "phase": phase,
                        "origin": origin,
                        "decision_at": decision,
                        "first_scheduled_execution_at": scheduled,
                        "execution_at": pd.NaT,
                        "first_quote_proxy_session": first_proxy,
                        "eligible_assets": n_assets,
                        "input_ready": ready,
                        "paired_with_reference": ready
                        and bool(next(iter(arms.values()))),
                        "paired_inputs": bool(
                            all(arms.values()) and phase != "warm-up"
                        ),
                        "outcome_slots": len(targets) if study != "H05" else n_assets,
                        "observed_slots": int(targets.sum())
                        if study != "H05"
                        else observed_stocks,
                        "outcome_complete": bool(targets.all()),
                        "quote_check": proxy,
                        "fallback": fallback,
                        "view_direction": view,
                        "valid_last_756": int(year3.sum())
                        if study in ("H01", "H02")
                        else None,
                    }
                )
        # The current origin for the next loop is the LAST session of this holding month.
        # Its complete label is contemporaneous there, so add the preceding month's label only.
        prior_days = prev.index
        for study, ticker in (("H03", "IEF"), ("H04", "SPY")):
            if (
                len(prior_days)
                and usd[ticker].reindex(prior_days).notna().all()
                and cash_daily.reindex(prior_days).notna().all()
            ):
                training_origin = months[period - 2].index[-1]
                train = (
                    f.loc[training_origin]
                    if training_origin in f.index
                    else pd.Series(dtype=float)
                )
                sets = (
                    {
                        "slope OLS": ["T10Y2Y"],
                        "slope + macro PC": ["T10Y2Y", "UNRATE", "INDPRO", "CPIAUCSL"],
                    }
                    if study == "H03"
                    else {
                        "expanding mean": [],
                        "OLS": ["T10Y2Y", "BAA10Y"],
                        "ridge": ["T10Y2Y", "BAA10Y"],
                    }
                )
                for method, required in sets.items():
                    known_outcomes[method] += all(
                        pd.notna(train.get(k)) for k in required
                    )
    manifest = pd.DataFrame(rows)
    manifest["execution_at"] = pd.to_datetime(manifest.execution_at, utc=True)
    manifest["reference_pair_complete"] = (
        manifest.paired_with_reference & manifest.outcome_complete
    )
    manifest["paired_scoring_inputs"] = (
        manifest.paired_inputs & manifest.outcome_complete
    )
    manifest.to_parquet(out / "samples.parquet", index=False)
    manifest.groupby(["study", "phase", "arm"]).agg(
        origins=("origin", "size"),
        input_ready=("input_ready", "sum"),
        reference_pairs=("reference_pair_complete", "sum"),
        paired_inputs=("paired_inputs", "sum"),
        complete_outcomes=("outcome_complete", "sum"),
        paired_scoring_inputs=("paired_scoring_inputs", "sum"),
    ).reset_index().to_csv(out / "sample_coverage.csv", index=False)
    costs = manifest[
        ["study", "origin", "decision_at", "first_scheduled_execution_at"]
    ].drop_duplicates()
    costs.merge(
        pd.DataFrame({"cost_bp_per_traded_notional": [0, 10, 25]}), how="cross"
    ).assign(basis="assumed; actual fee, FX charge and fill unverified").to_parquet(
        out / "cost_scenarios.parquet", index=False
    )
    return sentiment_stats
