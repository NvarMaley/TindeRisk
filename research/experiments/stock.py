"""Measure the price-only component that survives the historical filing gate."""

import duckdb


def momentum_component(universe, out):
    with duckdb.connect() as db:
        db.register("universe", universe)
        # Holding month h: use returns from h−12 through h−2 and skip h−1.
        cohort = db.sql("""
            with monthly as (
                select *, date_trunc('month',day) as mo from universe
            ), formation as (
                select *, count(ret) over w as n, product(1+ret) over w - 1 as momentum
                from monthly window w as (partition by permno order by mo
                range between interval 11 months preceding and interval 1 month preceding)
            )
            select s.mo + interval 1 month as holding, s.permno,
                   case when s.n=11 then s.momentum end as momentum, f.ret as realized
            from formation s left join monthly f on s.permno=f.permno
                and f.mo=s.mo + interval 1 month
            where s.market_candidate and s.best_link_count=1 and s.mo
                between date '2018-12-01' and date '2025-11-01'
            order by holding,s.permno
        """).df()
    rows = []
    for month, g in cohort.groupby("holding"):
        both = g.dropna(subset=["momentum", "realized"])
        rows.append(
            {
                "holding_month": str(month)[:7],
                "linked_candidates": len(g),
                "complete_formation": g.momentum.count(),
                "paired_outcomes": len(both),
                "diagnostic_rank_ic": both.momentum.rank().corr(both.realized.rank()),
            }
        )
    import pandas as pd

    pd.DataFrame(rows).to_csv(out / "price_only_component.csv", index=False)
