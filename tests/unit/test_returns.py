from datetime import date, timedelta
from pathlib import Path
from math import expm1, fsum
import pytest

from riskmatch.market_data.returns import (
    price_return, log_return, total_return, compound, means, aggregate_periods,
    fx_return, real_return, cash_accrual, excess_return, bond_return, futures_pnl,
    time_weighted_return, money_weighted_return, tips_return,
)


def test_dividends_and_split_without_double_count():
    assert price_return(100,55)==pytest.approx(-0.45)
    assert total_return(100,55,split=2,distribution=2)==pytest.approx(.12)
    assert total_return(100,98,distribution=2)==pytest.approx(0)
    assert log_return(-1) is None
    with pytest.raises(ValueError):
        price_return(0,10)


def test_compounding_and_means():
    values=[.1,-.1,.05]
    assert compound(values)==pytest.approx(expm1(fsum(log_return(v) for v in values)))
    assert means(values,12)["geometric"]==pytest.approx((1+compound(values))**(1/3)-1)
    assert compound([.2,-1]) == -1
    with pytest.raises(ValueError):
        compound([.1,None])


def test_missing_session_and_fx_convention():
    a,b=date(2025,1,2),date(2025,1,3)
    assert aggregate_periods({a:.1},[a,b],"monthly")[(2025,1)] is None
    assert aggregate_periods({a:.1,b:.2},[a,b],"weekly")[a.isocalendar()[:2]]==pytest.approx(.32)
    assert fx_return(.1,.9,.95)==pytest.approx(fx_return(.1,1/.9,1/.95,inverse=True))
    assert real_return(.1,.02)==pytest.approx(1.1/1.02-1)


def test_cash_bond_futures_and_nav():
    start=date(2025,1,1)
    assert cash_accrual(.05,start,start+timedelta(days=3))==pytest.approx(.05*3/360)
    assert excess_return(.08,.03)==pytest.approx(.05)
    assert bond_return(98,99,1,.2,2)==pytest.approx(101.2/99-1)
    assert futures_pnl(-10,5,100,2)==3000
    assert tips_return(100,100,0,0,1,1.02)==pytest.approx(.02)
    assert time_weighted_return([100,165,181.5],[55,0])==pytest.approx(.21)
    assert money_weighted_return([(start,-100),(start+timedelta(days=365),110)])==pytest.approx(.1)
    with pytest.raises(ValueError,match="Ambiguous"):
        money_weighted_return([(start,-100),(start+timedelta(days=30),200),
            (start+timedelta(days=60),-110),(start+timedelta(days=365),20)])


def test_return_panel_does_not_bridge_missing_session(monkeypatch):
    import duckdb
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"scripts"))
    from build_return_panel import series_sql
    with duckdb.connect() as db:
        db.execute("""create table fixture(instrument varchar,observation_date date,close double,reported double);
            insert into fixture values ('X','2025-01-02',100,.01),('X','2025-01-06',110,.1);
            create table equity_calendar(session_date date,previous_day date);
            insert into equity_calendar values ('2025-01-02',null),('2025-01-03','2025-01-02'),('2025-01-06','2025-01-03')""")
        result=db.execute(series_sql("fixture","reported")+" order by end_date").fetchall()
        assert result[-1][-2:]==(None,None)


def test_split_adjusted_price_and_unverified_jump(monkeypatch):
    import duckdb
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"scripts"))
    from build_return_panel import series_sql
    with duckdb.connect() as db:
        db.execute("""create table fixture(instrument varchar,observation_date date,close double,reported double);
            insert into fixture values ('X','2025-01-02',10,null),('X','2025-01-03',84,.05),('X','2025-01-06',210,null);
            create table equity_calendar(session_date date,previous_day date);
            insert into equity_calendar values ('2025-01-02',null),('2025-01-03','2025-01-02'),('2025-01-06','2025-01-03');
            create table crsp_split_events(instrument varchar,observation_date date,factor double,ambiguous int);
            insert into crsp_split_events values ('X','2025-01-03',.125,0);
            create table public_split_events(instrument varchar,observation_date date,factor double,events int);
            insert into public_split_events values ('X','2025-01-03',.125,1)""")
        crsp=db.execute(series_sql("fixture","reported",adjustment="crsp_daily")+" order by end_date").fetchall()
        assert crsp[1][-2]==pytest.approx(.05)
        public=db.execute(series_sql("fixture","reported",adjustment="public")+" order by end_date").fetchall()
        assert public[1][-2]==pytest.approx(.05)
        assert public[2][-2] is None
