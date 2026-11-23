"""Dated equity screens and a matched ETF vs ETF-plus-stocks experiment."""

import numpy as np
import pandas as pd

from ..archive_labels import read_snapshot
from ..econometrics import ecb_series
from ..equity_extension.fetch import CAT
from ..universe.data import BR, US, Panel
from .audit import records

SECTORS = [
    "Agriculture",
    "Mining",
    "Construction",
    "Manufacturing",
    "Transport and utilities",
    "Wholesale",
    "Retail",
    "Finance and real estate",
    "Services",
    "Public administration",
]


def sector_group(values):
    prefix = pd.to_numeric(values, errors="coerce") // 100
    return (
        pd.cut(prefix, [0, 9, 14, 17, 39, 49, 51, 59, 67, 89, 97], labels=SECTORS)
        .astype("string")
        .fillna("Unclassified")
    )


def round_trip(growth, weights, fee):
    """Initial notionals as fractions of capital, with entry and exit fees paid in CHF."""
    invested = weights.sum()
    if invested * (1 + fee) > 1 + 1e-12:
        raise ValueError("Entry fees exceed the cash reserve")
    return 1 - invested - fee * invested + (growth @ weights) * (1 - fee)


def portfolios(panel, reg, fx, cfg):
    horizon = cfg["holding_sessions"]
    rows, positions = [], []
    etfdata = pd.read_parquet(CAT / "prices.parquet")
    etf = etfdata[etfdata.id.str.endswith("-SPY")].set_index("day")
    for day, group in reg.groupby("day"):
        pick = (
            group[group.pass_research]
            .sort_values(["turnover_usd", "id"], ascending=[False, True])
            .head(cfg["stock_slots"])
        )
        if len(pick) != cfg["stock_slots"]:
            raise ValueError("Insufficient eligible stocks for the fixed rule")
        i = panel.dindex.get_loc(day)
        fund_obs = etf.reindex(panel.days[i - 20 : i + 1])
        fund_turn = (fund_obs.close * fund_obs.volume).mean()
        assert (
            cfg["capital_chf"] * cfg["invested_fraction"] / fx[i]
            <= cfg["max_turnover_participation"] * fund_turn
        )
        for label, stock_w in [
            ("SPY only", 0.0),
            ("SPY plus stocks", cfg["stock_fraction_in_mixed_book"]),
        ]:
            w = pd.Series({"SPY": cfg["invested_fraction"] - stock_w})
            if stock_w:
                w = pd.concat([w, pd.Series(stock_w / len(pick), index=pick.id)])
            positions.extend(
                {"day": day, "book": label, "id": k, "weight": v} for k, v in w.items()
            )
            row = {
                "day": day,
                "book": label,
                "entry": None,
                "end": None,
                "net_return": None,
                "reason": "Horizon beyond frozen market data",
            }
            last = i + 1 + horizon
            if last < len(panel.days):
                cols = panel.names.get_indexer(w.index)
                assert min(cols) >= 0
                entry = i + 1
                row.update(
                    entry=panel.days[entry],
                    end=panel.days[last],
                    reason="Missing required mark or return",
                )
                marks = panel.close[entry : last + 1, cols]
                local = panel.usd[entry + 1 : last + 1, cols].astype(float)
                if (
                    np.isfinite(local).all()
                    and (marks > 0).all()
                    and np.isfinite(fx[[entry, last]]).all()
                ):
                    gross = np.prod(1 + local, axis=0) * fx[last] / fx[entry]
                    row.update(
                        reason="Complete",
                        net_return=round_trip(gross, w.values, cfg["fee_one_way"]) - 1,
                    )
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(positions)


def analyse(db, base, cfg, parent):
    membership = read_snapshot(base / "membership.parquet")
    reg = membership[membership["class"].eq("Individual stock")].copy()
    reg["permno"] = reg.id.str[7:].astype(int)
    panel = Panel()
    fx = (
        pd.Series(panel.fx, index=panel.days)
        .combine_first(ecb_series(parent).reindex(panel.days))
        .to_numpy()
    )
    dated = reg[["permno", "day"]].drop_duplicates()
    db.register("dates_and_ids", dated)
    hist = db.sql(f"""select d.day,m.permno,m.sector,m.volume,m.price from dates_and_ids d join '{CAT}/stock_months.parquet' m
           on d.permno=m.permno and m.day=cast(d.day as date) where {US}""").df()
    calendar = (
        pd.Series(1, index=panel.days).groupby(pd.Index(panel.days).str[:7]).size()
    )
    hist["turnover_usd"] = hist.volume * hist.price / hist.day.str[:7].map(calendar)
    hist["volume_basis"] = "Monthly volume x closing price / sessions"
    final = cfg["decision"]
    cutoff = panel.dindex.get_loc(final)
    days = panel.days[cutoff - 20 : cutoff + 1]
    ext = pd.read_parquet(
        BR / "daily_extension.parquet", columns=["permno", "day", "close", "volume"]
    )
    ext["day"] = pd.to_datetime(ext.day).dt.strftime("%Y-%m-%d")
    ext = ext.loc[ext.day.isin(days)].copy()
    ext["turnover_usd"] = (ext.close * ext.volume).where(
        ext.volume.gt(0) & ext.close.gt(0)
    )
    g = ext.groupby("permno").turnover_usd
    # Use the full 21-session denominator, treating reported zero trading as zero;
    # do not pass a security whose volume or price is missing on any session.
    ext["dollars"] = (ext.close * ext.volume).where(ext.close.gt(0) & ext.volume.ge(0))
    t = ext.groupby("permno").dollars.agg(["count", "sum"])
    good = (g.count() >= 18) & t["count"].eq(len(days))
    last = ext[ext.day.eq(final)].set_index("permno")
    end = t.assign(turnover_usd=(t["sum"] / len(days)).where(good)).join(
        last.close.rename("price")
    )
    end = end.join(
        db.sql(
            f"""select permno,sector from '{CAT}/stock_months.parquet' where day='2025-12-31' and {US}"""
        )
        .df()
        .set_index("permno")
    )
    end = end.reset_index().assign(
        day=final, volume_basis="Observed daily turnover over 21 sessions"
    )
    cols = ["permno", "day", "sector", "turnover_usd", "price", "volume_basis"]
    measurements = pd.concat([hist[cols], end[cols]], ignore_index=True)
    reg = reg.merge(
        measurements, on=["day", "permno"], how="left", validate="one_to_one"
    )
    reg["sector_group"] = sector_group(reg.sector)
    reg["fx"] = reg.day.map(pd.Series(fx, index=panel.days))
    ticket = (
        cfg["capital_chf"] * cfg["stock_fraction_in_mixed_book"] / cfg["stock_slots"]
    )
    reg["participation"] = ticket / (
        reg.fx * reg.turnover_usd.where(reg.turnover_usd > 0)
    )
    reg["screen_reason"] = np.select(
        [
            ~reg.included,
            reg.price.isna() | reg.fx.isna(),
            ~reg.turnover_usd.gt(0),
            reg.price * reg.fx > ticket,
            reg.participation > cfg["max_turnover_participation"],
        ],
        [
            reg.reason,
            "Missing price or FX",
            "Missing or zero verified volume",
            "One share exceeds stock ticket",
            "Turnover limit exceeded",
        ],
        default="Pass",
    )
    reg["pass_research"] = reg.screen_reason.eq("Pass")
    reg["live_order_allowed"] = False
    book, picks = portfolios(panel, reg, fx, cfg)
    finalids = set(reg.loc[(reg.day == final) & reg.pass_research, "permno"])
    endpoint = reg[reg.day.eq(final)]
    # Independent of lot size and history threshold: count confirmed October
    # close/active identities on our cohort even when the research ticket fails.
    quoted = set(
        endpoint.loc[
            (endpoint.included | endpoint.reason.str.startswith("less than 252"))
            & endpoint.price.gt(0),
            "permno",
        ]
    )
    reg["quoted_in_final_cohort"] = reg.permno.isin(quoted)
    reg["also_passes_final"] = reg.permno.isin(finalids)
    stats = (
        reg.assign(
            quoted=reg.pass_research & reg.quoted_in_final_cohort,
            surviving_screen=reg.pass_research & reg.also_passes_final,
        )
        .groupby("day")
        .agg(
            reviewed=("permno", "size"),
            model=("included", "sum"),
            liquid_affordable=("pass_research", "sum"),
            also_pass_final=("surviving_screen", "sum"),
            quoted_at_end=("quoted", "sum"),
        )
        .reset_index()
    )
    sectors = (
        reg.groupby(["day", "sector_group", "screen_reason"])
        .size()
        .rename("securities")
        .reset_index()
    )
    return reg, book, picks, stats, sectors


def historical(db, reg, cfg):
    # Annual membership for the whole extract (including securities absent in 2026).
    octs = db.sql(f"""select permno,cast(day as varchar) as day,sector,ticker,trading,cast(price_day as varchar) price_day,
       local_return, price from '{CAT}/stock_months.parquet' where {US} and month(day)=10""").df()
    end = set(reg.loc[(reg.day == cfg["decision"]) & reg.pass_research, "permno"])
    octs["active"] = (
        octs.trading.eq("A") & octs.price.gt(0) & octs.day.eq(octs.price_day)
    )
    octs["in_final_screen"] = octs.permno.isin(end)
    octs["sector_group"] = sector_group(octs.sector)
    reason = np.select(
        [~octs.trading.eq("A"), ~octs.price.gt(0), octs.day.ne(octs.price_day)],
        ["Inactive", "No price", "Stale price"],
        default="Dated active",
    )
    octs["reason"] = reason
    octs["quoted_subset"] = octs.active & octs.permno.isin(
        reg[reg.quoted_in_final_cohort].permno.unique()
    )
    octs["survivor_subset"] = octs.active & octs.in_final_screen
    annual = (
        octs.groupby("day")
        .agg(
            reviewed=("permno", "size"),
            active=("active", "sum"),
            also_pass_final=("survivor_subset", "sum"),
            quoted_at_end=("quoted_subset", "sum"),
        )
        .reset_index()
    )
    detailed = (
        octs.groupby(["day", "sector_group", "reason"])
        .size()
        .rename("securities")
        .reset_index()
    )
    # Select specific historical cases from consecutive October cohorts. Verify
    # entries and exits using dated security intervals rather than disappearance alone.
    life = (
        db.sql(
            f"""select permno,min(security_from) listed,max(security_end) last_day from '{CAT}/identifiers.parquet' group by permno"""
        )
        .df()
        .set_index("permno")
    )
    cases = octs[octs.active].merge(life, on="permno")
    first = (
        cases[(cases.listed.dt.year == 2018) & cases.day.str.startswith("2018")]
        .sort_values("permno")
        .iloc[0]
    )
    last = (
        cases[(cases.last_day.dt.year == 2019) & cases.day.str.startswith("2018")]
        .sort_values("permno")
        .iloc[0]
    )
    pairs = octs[octs.active].copy()
    pairs["year"] = pairs.day.str[:4].astype(int)
    prior = pairs.assign(year=pairs.year + 1)
    change = pairs.merge(prior, on=["permno", "year"], suffixes=("", "_before"))
    change = change[
        (change.year <= 2021)
        & (change.year >= 2017)
        & change.sector_group.ne(change.sector_group_before)
        & change.sector_group.ne("Unclassified")
        & change.sector_group_before.ne("Unclassified")
    ]
    change = change.sort_values(["year", "permno"]).iloc[0]
    return (
        annual,
        detailed,
        {
            "entry": {
                "ticker": first.ticker,
                "permno": int(first.permno),
                "listed": str(first.listed.date()),
                "observed": first.day,
            },
            "exit": {
                "ticker": last.ticker,
                "permno": int(last.permno),
                "last": str(last.last_day.date()),
                "observed": last.day,
            },
            "reclassification": {
                k: str(change[k])
                for k in [
                    "permno",
                    "ticker",
                    "day_before",
                    "sector_group_before",
                    "sector_before",
                    "day",
                    "sector_group",
                    "sector",
                ]
            },
        },
    )


def issuer_overlap(picks, final, cfg):
    """Look through the mixed book at the later, explicitly dated SPY disclosure."""
    from ..library.sources import issuer_code

    holds = pd.read_parquet(CAT / "holdings.parquet").query("fund=='SPY'")
    if holds.day.nunique() != 1:
        raise ValueError("Select exactly one SPY holdings date")
    bridge = pd.read_parquet(BR / "inventory.parquet", columns=["permno", "cusip_2025"])
    held = (
        picks[
            (picks.day == cfg["decision"])
            & (picks.book == "SPY plus stocks")
            & picks.id.str.startswith("PERMNO")
        ]
        .merge(final[["id", "permno", "symbol"]], on="id")
        .merge(bridge, on="permno", validate="one_to_one")
    )
    held["issuer"] = held.cusip_2025.map(issuer_code)
    direct = held.dropna(subset=["issuer"]).groupby("issuer").weight.sum()
    fund = holds.dropna(subset=["issuer"]).groupby("issuer").weight.sum()
    spy = picks[
        (picks.day == cfg["decision"])
        & (picks.book == "SPY plus stocks")
        & (picks.id == "SPY")
    ].weight.item()
    indirect = spy * fund.reindex(direct.index)
    exposure = pd.concat(
        [direct.rename("direct"), indirect.rename("through_spy")], axis=1
    )
    return {
        "holdings_date": holds.day.iloc[0],
        "disclosed": holds.available.max(),
        "direct_issuers": len(direct),
        "also_in_spy": int(indirect.notna().sum()),
        "direct_weight_identified": direct.sum(),
        "overlap_weight": indirect.sum(),
        "issuers": records(
            exposure.join(held.groupby("issuer").symbol.agg(", ".join)).reset_index()
        ),
    }
