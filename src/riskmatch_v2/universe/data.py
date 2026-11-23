"""Dated selection and comparable prices/returns, preserving unresolved observations."""

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from riskmatch_v2.archive_labels import read_snapshot

from ..equity_extension.fetch import CAT, END
from ..library.build import US
from ..library.sources import checked
from .treasury import BASE

EQ = BASE / "crsp_daily_2014_2025.parquet"
BR_REPORT = Path("reports/actions-2026/resultats.json")
BR = (
    Path("data/local/actions-2026")
    / END
    / json.loads(BR_REPORT.read_text())["snapshot"]
)


def historical():
    import hashlib

    dep = json.loads(Path("config/faisabilite-5.json").read_text())["sha256_crsp_dsf"]
    meta = EQ.with_suffix(".json")
    if EQ.exists() and meta.exists():
        saved = json.loads(meta.read_bytes())
        if (
            saved["crsp"] == dep
            and saved["code"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        ):
            checked(EQ, saved["parquet"])
            return
    BASE.mkdir(parents=True, exist_ok=True)
    source = Path("data/local/5/raw/crsp_dsf.csv")
    checked(
        source,
        json.loads(Path("config/faisabilite-5.json").read_text())["sha256_crsp_dsf"],
    )
    conn = duckdb.connect()
    conn.execute("SET threads=4")
    conn.execute("SET memory_limit='1800MB'")
    conn.execute("SET temp_directory=?", [str(BASE / "scratch")])
    sql = f"""WITH monthly AS (
    SELECT DISTINCT permno FROM read_parquet(?) WHERE {US}
    ), prices AS (SELECT TRY_CAST(PERMNO AS INTEGER) permno, CAST(DlyCalDt AS DATE) AS day,
    TRY_CAST(DlyRet AS DOUBLE) AS ret,TRY_CAST(DlyPrc AS DOUBLE) AS price
    FROM read_csv(?,all_varchar=true) WHERE DlyCalDt BETWEEN '2014-10-01' AND '2025-12-31')
    SELECT p.permno, p.day, max(ret) FILTER(WHERE ret>=-1) AS usd, max(price) FILTER(WHERE price>0) AS close
    FROM prices p JOIN monthly m ON p.permno=m.permno
    GROUP BY p.permno,p.day HAVING count(*)=1"""
    temp = EQ.with_suffix(".tmp")
    conn.sql(
        sql, params=[str(CAT / "stock_months.parquet"), str(source)]
    ).write_parquet(str(temp), compression="zstd")
    conn.close()
    temp.replace(EQ)
    meta.write_text(
        json.dumps(
            dict(
                crsp=dep,
                code=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                parquet=hashlib.sha256(EQ.read_bytes()).hexdigest(),
            )
        )
    )


if __name__ == "__main__":
    historical()


class Panel:
    def __init__(self):
        from .treasury import history, terms

        funds = pd.read_parquet(CAT / "prices.parquet")
        funds["name"] = funds.id.str.rsplit("-", n=1).str[-1]
        self.funds = sorted(funds.name.unique())
        self.days = np.array(
            sorted(set(funds.day[funds.day.between("2014-10-01", END)]))
        )
        self.dindex = pd.Index(self.days)
        self.fx = (
            pd.read_parquet(CAT / "fx.parquet")
            .set_index("day")
            .value.reindex(self.days)
            .to_numpy()
        )
        self.register = read_snapshot(BR / "inventory.parquet").set_index("permno")
        self.bonds = terms()
        bonds = history(self.days.tolist())
        self.months = pd.read_parquet(
            CAT / "stock_months.parquet",
            columns=[
                "permno",
                "day",
                "ticker",
                "issuer",
                "country_flag",
                "share_type",
                "security_type",
                "subtype",
                "exchange",
                "trading",
                "price_day",
            ],
        )
        self.months = self.months.query(
            US.replace("='", "=='").replace(" AND ", " and ").replace(" IN ", " in ")
        )
        ids = np.union1d(self.months.permno.unique(), self.register.index.to_numpy())
        self.names = pd.Index(
            [
                *self.funds,
                *["UST:" + x for x in self.bonds.index],
                *["PERMNO:" + str(x) for x in ids],
            ]
        )
        self.stock0 = len(self.funds) + len(self.bonds)
        self.classes = np.array(
            [
                "Equity ETF"
                if x not in ("GLD", "IEF", "TLT")
                else "Gold (GLD)"
                if x == "GLD"
                else "Treasury ETF"
                for x in self.funds
            ]
            + ["Direct Treasury"] * len(self.bonds)
            + ["Individual stock"] * len(ids)
        )
        self.pids = ids
        shape = (len(self.days), len(self.names))
        self.close = np.full(shape, np.nan, np.float32)
        self.usd = np.full(shape, np.nan, np.float32)
        self.coupons = np.zeros((len(self.days), len(self.bonds)), np.float32)
        self.model_bond = np.full_like(self.coupons, np.nan)
        self._put(
            funds[funds.day.isin(self.days)].rename(columns={"return_usd": "usd"})
        )
        self._put(bonds)
        for name, g in bonds.groupby("name"):
            j = self.names.get_loc(name) - len(self.funds)
            di = self.dindex.get_indexer(g.day)
            self.coupons[di, j] = g.income
            prev = self.dindex.get_indexer(g.previous.fillna(""))
            ok = (prev == di - 1) & (prev >= 0)
            self.model_bond[di[ok], j] = g.usd.to_numpy()[ok]
        conn = duckdb.connect()
        reader = conn.execute(
            "SELECT permno,CAST(day AS VARCHAR) as day,usd,close FROM read_parquet(?)",
            [str(EQ)],
        ).fetch_record_batch(200000)
        for batch in reader:
            g = batch.to_pandas()
            self._put_stocks(g)
        conn.close()
        extension = pd.read_parquet(BR / "daily_extension.parquet")
        extension["day"] = extension.day.dt.strftime("%Y-%m-%d")
        ev = pd.read_parquet(BR / "events.parquet")
        for r in ev.loc[ev.kind.eq("splits")].itertuples():
            mask = extension.permno.eq(r.permno) & extension.day.lt(r.day)
            extension.loc[mask, "close"] *= r.numerator / r.denominator
        from .sources import additional_admissions

        self.recovered = additional_admissions(self.register, extension)
        self._put_stocks(extension)
        self.months["day"] = pd.to_datetime(self.months.day).dt.strftime("%Y-%m-%d")
        self.months["price_day"] = pd.to_datetime(self.months.price_day).dt.strftime(
            "%Y-%m-%d"
        )
        self.year_days = [
            self.dindex[self.dindex.str.startswith(str(y) + "-10")][-1]
            for y in range(2017, 2027)
        ]
        self.factors = [self.names.get_loc(x) for x in ("SPY", "IEF", "GLD")]
        pts = funds.pivot(index="day", columns="name", values="adjusted")
        fxraw = pd.read_parquet(CAT / "fx.parquet").set_index("day").value
        self.shock = (pts.loc["2008-11-20"] * fxraw["2008-11-20"]) / (
            pts.loc["2008-09-12"] * fxraw["2008-09-12"]
        ) - 1
        self.observed_shocks = crash_observations()
        self.observed_shocks.update(self.shock.to_dict())
        from .treasury import bond_shock

        self.observed_shocks.update(bond_shock(self.bonds, fxraw))
        self.ledger = {}
        for row in self.months.loc[self.months.day.isin(self.year_days)].itertuples():
            self.ledger.setdefault(row.day, {})["PERMNO:" + str(row.permno)] = (
                row.trading == "A" and row.price_day == row.day,
                row.ticker,
                row.issuer,
            )
        self.ledger[END] = {
            "PERMNO:" + str(i): (
                r.status == "complete" or i in self.recovered,
                r.symbol if pd.notna(r.symbol) else r.ticker_2025,
                r.issuer,
            )
            for i, r in self.register.iterrows()
        }

    def _put(self, g):
        i = self.dindex.get_indexer(g.day)
        j = self.names.get_indexer(g.name)
        assert min(i) >= 0 and min(j) >= 0
        self.close[i, j] = g.close
        self.usd[i, j] = g.usd

    def _put_stocks(self, g):
        i = self.dindex.get_indexer(g.day)
        j = np.searchsorted(self.pids, g.permno) + self.stock0
        assert min(i) >= 0 and (self.pids[j - self.stock0] == g.permno).all()
        self.close[i, j] = g.close
        self.usd[i, j] = g.usd

    def history(self, day, rows=756):
        end = self.dindex.get_loc(day) + 1
        start = end - rows
        y = self.usd[start:end].astype(float)
        y[:, len(self.funds) : self.stock0] = self.model_bond[start:end]
        # A daily return needs a valid preceding session; exclude resumptions with a price gap.
        prev = self.close[start - 1 : end - 1]
        y[~np.isfinite(prev)] = np.nan
        ratio = self.fx[start:end] / self.fx[start - 1 : end - 1]
        return (1 + y) * ratio[:, None] - 1

    def inventory(self, day):
        i = self.dindex.get_loc(day)
        items = []
        for j, name in enumerate(self.names[: self.stock0]):
            reason = "candidate"
            if j >= len(self.funds):
                term = self.bonds.loc[name[4:]]
                if pd.isna(term.issue_date):
                    reason = "Unidentified emission"
                elif term.issue_date > day:
                    reason = "Subsequent issue"
            items.append((name, name, name, reason))
        for name, (eligible, tick, issuer) in self.ledger[day].items():
            reason = "candidate" if eligible else "CRSP status or prices"
            if day == END and not eligible:
                reason = self.register.loc[int(name[7:]), "status"]
            items.append((name, tick, issuer, reason))
        table = pd.DataFrame(
            items, columns=["id", "symbol", "issuer", "reason"]
        ).set_index("id")
        col = self.names.get_indexer(table.index)
        no_price = ~(self.close[i, col] > 0)
        table.loc[no_price & table.reason.eq("candidate"), "reason"] = (
            "missing decision-date price"
        )
        table["class"] = self.classes[col]
        if day == END:
            table["secondary_check"] = [
                self.recovered.get(int(k[7:])) if k.startswith("PERMNO:") else None
                for k in table.index
            ]
        return table


def cash_exits(panel):
    """Only cash consideration with a terminal-month total return or official cash terms."""
    sql = """SELECT m.permno,cast(m.day as varchar) AS day,r.usd FROM read_parquet(?) m
      JOIN read_parquet(?) r USING (permno,day) WHERE m.del_flag!='N' AND m.exit_payment='CASH'
      AND m.return_flag='DE' AND r.usd>=-1 AND m.day>=DATE '2017-10-31'"""
    db = duckdb.connect()
    rows = db.execute(
        sql, [str(CAT / "stock_months.parquet"), str(CAT / "stock_returns.parquet")]
    ).fetchall()
    # The monthly security row can disappear before month-end while the distribution
    # file still records the dated terminal cash entitlement. Exclude mixed consideration.
    terminal_cash = db.execute(
        """WITH ends AS (
              SELECT permno, max(security_end) AS last_day FROM read_parquet(?) GROUP BY permno
           )
           SELECT e.permno, cast(e.ex_date AS VARCHAR), max(e.dividend)
           FROM read_parquet(?) e JOIN ends USING (permno)
           WHERE e.ex_date BETWEEN ends.last_day AND ends.last_day + INTERVAL '7 days'
           AND e.ex_date >= DATE '2017-10-31'
           GROUP BY e.permno,e.ex_date
           HAVING count(*)=1 AND bool_and(e.distribution_type='CP' AND e.payment_type='USD'
               AND e.share_factor=-1 AND e.dividend>0 AND e.payment_date <= e.ex_date)
           """,
        [str(CAT / "identifiers.parquet"), str(CAT / "stock_events.parquet")],
    ).fetchall()
    db.close()
    result = {}
    for pid, day, total in rows:
        if day not in panel.dindex:
            continue
        key = "PERMNO:" + str(pid)
        col = panel.names.get_indexer([key])[0]
        if col < 0:
            continue
        ix = panel.dindex.get_loc(day)
        start = panel.dindex.searchsorted(day[:7] + "-01")
        gross = np.nanprod(1 + panel.usd[start : ix + 1, col].astype(float))
        if gross > 0:
            result.setdefault(day, {})[key] = ("total", float((1 + total) / gross))
    for pid, day, amount in terminal_cash:
        if day in panel.dindex and "PERMNO:" + str(pid) in panel.names:
            result.setdefault(day, {})["PERMNO:" + str(pid)] = ("cash", amount)
    for pid, r in panel.register.dropna(subset=["exit_cash_usd"]).iterrows():
        result.setdefault(r.event_date, {})["PERMNO:" + str(pid)] = (
            "cash",
            r.exit_cash_usd,
        )
    return result


def crash_observations():
    """Total CHF return in the original 2008 stress, only on a complete daily USD path."""
    import exchange_calendars as xcals

    cache = BASE / "crsp_stress_2008.parquet"
    start, end = "2008-09-12", "2008-11-20"
    cal = xcals.get_calendar("XNYS", start="2008-09-01", end="2008-11-30")
    days = cal.sessions_in_range(start, end).strftime("%Y-%m-%d").tolist()
    if not cache.is_file():
        db = duckdb.connect()
        raw = Path("data/local/5/raw/crsp_dsf.csv")
        df = db.execute(
            """SELECT try_cast(PERMNO AS INTEGER) AS permno,DlyCalDt AS day,
          max(try_cast(DlyRet as double)) AS ret,max(try_cast(DlyPrc as double)) AS price
          FROM read_csv(?,all_varchar=true) WHERE DlyCalDt BETWEEN ? AND ?
          GROUP BY 1,2 HAVING count(*)=1""",
            [str(raw), start, end],
        ).df()
        db.close()
        good = df.pivot(index="day", columns="permno", values="ret").reindex(days[1:])
        anchors = df[df.day.eq(start) & df.price.gt(0)].permno
        good = good.loc[
            :, good.notna().all() & good.ge(-1).all() & good.columns.isin(anchors)
        ]
        fx = pd.read_parquet(CAT / "fx.parquet").set_index("day").value
        value = (1 + good).prod() * fx[end] / fx[start] - 1
        value.rename("shock").to_frame().to_parquet(cache)
    return {
        "PERMNO:" + str(k): float(v) for k, v in pd.read_parquet(cache).shock.items()
    }
