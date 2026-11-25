from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from riskmatch.market_data.universe import Holding
from riskmatch.market_data.security_master import (
    load_catalog, TickerAlias, resolve_ticker, InvestabilityRecord, HoldingSnapshot, assess_etf,
    coverage_matrix, read_adjusted_csv, universe_report, StockMembership, select_stock_universe,
    TreasurySecurity, FuturesContract, BENCHMARKS, STRATEGY_BENCHMARK, rate_coverage, reported_coverage,
)

ROOT = Path(__file__).resolve().parents[2]
D = date(2026, 11, 24)


def instruments():
    return {i.ticker: i for i in load_catalog()[1]}


def test_catalog_and_benchmark_types():
    items = list(instruments().values())
    assert 15 <= sum(i.asset_class in {"equity_etf", "reit_etf"} for i in items) <= 30
    assert {i.ticker for i in items if i.asset_class == "treasury_etf"} == {"BIL", "SHY", "IEF", "TLT", "TIP"}
    assert all(i.domicile == "US" and i.currency == "USD" and i.source.startswith("https://") for i in items)
    assert len(STRATEGY_BENCHMARK) == 19 and set(STRATEGY_BENCHMARK.values()) <= set(BENCHMARKS)
    assert BENCHMARKS["cash"]["kind"] == "nontradable_discount_yield"


def test_ticker_reuse_and_publication_cutoff():
    first = TickerAlias("id1", "TEST", date(2000,1,1), date(2010,1,1), date(2000,1,1), "synthetic")
    second = TickerAlias("id2", "TEST", date(2011,1,1), None, date(2011,1,2), "synthetic")
    assert resolve_ticker([first,second],"TEST",date(2005,1,1)) == "id1"
    assert resolve_ticker([first,second],"TEST",date(2011,1,1)) is None
    assert resolve_ticker([first,second],"TEST",date(2012,1,1)) == "id2"
    with pytest.raises(ValueError):resolve_ticker([first,first],"TEST",date(2005,1,1))


def test_verified_treasury_eligibility_and_dated_liquidity():
    i = instruments()["IEF"]
    r = InvestabilityRecord(i.security_id, D, D, D, i.inception, None, True, 2e6, .0015, 2e8, (), "synthetic")
    h = HoldingSnapshot(i.security_id, D, D, D, (Holding("treasury_note", "US_TREASURY"),), True, "synthetic")
    assert assess_etf(i,D,[r],[h],data_validated=True)["eligible"]
    assert not assess_etf(i,D,[r],[h])["eligible"]
    assert "treasury_holdings_unverified" in assess_etf(i,D,[r],[],data_validated=True)["reasons"]
    mixed=replace(h,holdings=h.holdings+(Holding("corporate_bond","CORP"),))
    assert "treasury_only_violation" in assess_etf(i,D,[r],[mixed],data_validated=True)["reasons"]
    assert "liquidity_below_screen" in assess_etf(i,D,[replace(r,adv_usd=1)],[h],data_validated=True)["reasons"]
    assert "investability_unverified" in assess_etf(i,date(2026,11,23),[r],[h],data_validated=True)["reasons"]
    assert "investability_unverified" in assess_etf(i,date(2026,11,25),[r],[h],data_validated=True)["reasons"]
    assert "outside_universe" in assess_etf(replace(i,asset_class="corporate_bond"),D,[r],[h],data_validated=True)["reasons"]


def test_coverage_excludes_prelisting_and_future():
    observations = read_adjusted_csv(ROOT / "configs/universe-coverage-example.csv")
    result = coverage_matrix(list(instruments().values()), observations, source="synthetic", as_of=date(2018,6,20))
    assert result["XLC"]["prelaunch_rejected"] == 2
    assert result["XLC"]["observed"] == 1 and result["XLC"]["source_grid_sessions"] == 2
    assert result["XLC"]["missing_fraction"] == .5
    assert result["IEF"]["missing"] == 1
    assert result["SPY"]["missing_fraction"] == 0
    older = coverage_matrix(list(instruments().values()), observations, source="synthetic", as_of=date(2018,6,18))
    assert older["XLC"]["source_grid_sessions"] == 0 and older["XLC"]["observed"] == 0
    with pytest.raises(ValueError, match="duplicate_observation"):
        coverage_matrix(list(instruments().values()), observations+observations,source="synthetic",as_of=D)


def test_missing_local_sources_and_rate_proxy(tmp_path):
    r = universe_report(D,price_path=tmp_path/"missing.csv",rate_path=tmp_path/"missing-rate.csv",records_dir=tmp_path,summary_path=tmp_path/"missing-summary.csv")
    assert r["eligible_count"] == 0 and r["source_status"] == "local_source_unavailable"
    assert all(x["coverage"] is None for x in r["rows"])
    rate=tmp_path/"rate.csv";rate.write_text("observation_date,DTB3\n2026-11-20,3.2\n2026-11-21,.\n2026-11-25,4.1\n")
    result=rate_coverage(D,rate)
    assert result["observed"]==1 and result["missing"]==1 and result["kind"]=="nontradable_discount_yield"


def test_stock_expansion_is_point_in_time():
    rows=[StockMembership(str(i),D,D,D,1000+i,True,True) for i in range(400)]
    rows.append(StockMembership("future",D,date(2026,11,25),date(2026,11,26),1e12,True,True))
    rows[399]=replace(rows[399],delisting_date=D)
    r=select_stock_universe(rows,D,300)
    assert r["complete"] and r["count"] == 300
    assert r["security_ids"][0] == "CRSP-PERMNO:398"
    assert "CRSP-PERMNO:future" not in r["security_ids"] and "CRSP-PERMNO:399" not in r["security_ids"]
    assert not select_stock_universe(rows,D,1000)["complete"]


def test_prior_summary_is_not_raw_coverage_and_no_lookahead(tmp_path):
    path=tmp_path/"summary.csv"
    path.write_text("series,frequency,first_observation,last_observation,observed,missing_on_source_grid\nSPY,daily,2005-01-03,2026-11-18,100,2\nOUTSIDE,daily,2005-01-03,2026-11-18,100,0\n")
    summary=reported_coverage(list(instruments().values()),path,D)
    assert set(summary)=={"SPY"} and summary["SPY"]["status"]=="reported_unvalidated"
    assert not reported_coverage(list(instruments().values()),path,date(2026,11,21))
    report=universe_report(D,price_path=tmp_path/"no.csv",rate_path=tmp_path/"no-rate.csv",records_dir=tmp_path,summary_path=path)
    assert report["source_status"]=="local_summary_only" and report["eligible_count"]==0


def test_treasury_and_expiry_contract_schema():
    treasury=TreasurySecurity("synthetic-id",Holding("tips","US_TREASURY"),date(2020,1,1),date(2030,1,1),.02,"synthetic")
    assert treasury.eligible(D)
    assert not replace(treasury,holding=Holding("corporate_bond","CORP")).eligible(D)
    futures=FuturesContract("ES","synthetic-contract",date(2026,12,31),date(2026,12,30),10,.5,"USD","cash",D,"synthetic")
    assert futures.valid_specification(D)
    assert not futures.eligible(D)
    assert not futures.valid_specification(date(2027,1,1))
    assert not replace(futures,root="OPTION").valid_specification(D)
    assert not replace(futures,multiplier=0).valid_specification(D)
