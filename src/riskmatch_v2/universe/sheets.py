"""Research sheets on identical windows ending at the mixed-universe decision."""

import duckdb
import numpy as np
import pandas as pd

from ..equity_extension.fetch import CAT, END
from ..library.statistics import sheet
from .data import BR


def sheets(panel, inventory):
    dates = pd.Series(panel.days, index=pd.to_datetime(panel.days))
    ends = dates.groupby(dates.index.to_period("M")).last().tail(121).to_numpy()
    fx = pd.Series(panel.fx, index=panel.days).reindex(ends).to_numpy()
    con = duckdb.connect()
    eq = con.execute(
        "SELECT 'PERMNO:'||permno as id,cast(day as varchar) AS day,usd FROM read_parquet(?) WHERE day>=CAST(? AS DATE)",
        [str(BR / "monthly_combined.parquet"), ends[0]],
    ).df()
    con.close()
    wide = eq.pivot(index="day", columns="id", values="usd").reindex(
        index=ends, columns=inventory.index
    )
    f = pd.read_parquet(CAT / "prices.parquet")
    f["id"] = f.id.str.rsplit("-", n=1).str[-1]
    funds = (
        f.pivot(index="day", columns="id", values="adjusted")
        .reindex(ends)
        .pct_change(fill_method=None)
    )
    wide[funds.columns] = funds
    beg = panel.dindex.get_indexer(ends)
    bi = np.arange(len(panel.funds), panel.stock0)
    # Reinvest each coupon in its own issue at that day's dirty mark.
    for i in range(1, len(ends)):
        sl = slice(beg[i - 1] + 1, beg[i] + 1)
        obs = panel.usd[sl, bi].astype(float)
        good = np.isfinite(panel.close[beg[i - 1], bi]) & np.isfinite(
            panel.close[beg[i], bi]
        )
        g = np.nanprod(1 + obs, axis=0) - 1
        wide.loc[ends[i], panel.names[bi]] = np.where(good, g, np.nan)
    results = []
    for name, r in wide.items():
        raw = r.to_numpy()
        for years in [1, 3, 5, 10]:
            m = years * 12
            results.append(
                dict(
                    id=name,
                    years=years,
                    end=END,
                    **sheet(m, raw[-m:], fx[-m - 1 :], ends[-m - 1 :]),
                )
            )
    return pd.DataFrame(results), (1 + wide).mul(
        pd.Series(fx, index=ends).pct_change(fill_method=None) + 1, axis=0
    ) - 1
