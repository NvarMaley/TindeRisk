"""Rebuild the dated Step 1 audit outputs from the authorized local vintage."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from data_audit import audit_local
from research.historical_gics import LN7_COMPANIES, audit_ln7_companies, _match_history, GICS_CODES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "processed"


def build():
    audit_local(ROOT)
    prices = pd.read_parquet(OUT/"prices.parquet")
    provenance = pd.read_parquet(OUT/"market_observation_provenance.parquet")
    returns = prices.pct_change(fill_method=None).iloc[1:]
    rf = pd.read_parquet(OUT/"rf_daily.parquet").iloc[:,0]
    def fred(key):
        return pd.read_csv(DATA/f"raw/{key}.csv", index_col=0, parse_dates=True).iloc[:,0]
    expected = fred("DTB3").dropna().reindex(rf.index,method="ffill")/25200
    np.testing.assert_allclose(expected,rf)
    np.testing.assert_allclose(returns.sub(rf,axis=0),pd.read_parquet(OUT/"excess_returns.parquet"))
    np.testing.assert_allclose(np.log1p(returns),pd.read_parquet(OUT/"log_returns.parquet"))
    catalogue=[]
    def add(key,series,provider,unit,frequency,rule,rights,vintage):
        valid=series.dropna()
        catalogue.append(dict(series=key,source=provider,unit=unit,frequency=frequency,
                              first_observation=str(valid.index.min())[:10],last_observation=str(valid.index.max())[:10],
                              observed=len(valid),missing_on_source_grid=int(series.isna().sum()),handling=rule,rights=rights,vintage=vintage))
    for key in prices:
        add(key,prices[key],"Yahoo Finance","adjusted USD/share","session","No price filling; current-vintage corporate actions","Local research",str(provenance.loc[provenance.series.eq(key),"downloaded_at_utc"].max()))
    panel=pd.DataFrame({"decision_date":prices.index})
    for key,unit in dict(DTB3="percent annual discount rate",T10Y2Y="percentage points",BAA10Y="percentage points",VIXCLS="index points",CPIAUCSL="index",INDPRO="index",UNRATE="percent").items():
        monthly=key in ("CPIAUCSL","INDPRO","UNRATE")
        observations=provenance[provenance.series.eq(key)].dropna(subset=["value"]).sort_values("available_date")
        rule=observations.availability_rule.iloc[0]
        add(key,fred(key),"FRED",unit,"monthly" if monthly else "daily",rule,"Series-specific terms",str(observations.downloaded_at_utc.max()))
        observations=observations[["available_date","observation_date","value"]].add_prefix(key+"_")
        panel=pd.merge_asof(panel,observations,left_on="decision_date",right_on=key+"_available_date",direction="backward",allow_exact_matches=False)
        assert (panel[key+"_available_date"].dropna()<panel.loc[panel[key+"_available_date"].notna(),"decision_date"]).all()
    panel.to_parquet(OUT/"dated_macro_research.parquet",index=False)
    public=DATA/"raw/public_phase2"
    manifest=json.loads((public/"manifest.json").read_text())
    for entry in manifest["files"]:
        key=entry["series"]
        unit={"DEXSZUS":"CHF/USD","DTWEXBGS":"index","DCOILWTICO":"USD/barrel","PCOPPUSDM":"USD/metric ton"}.get(key,"percent")
        series=pd.read_csv(public/f"{key}.csv",index_col=0,parse_dates=True).iloc[:,0]
        add(key,series,"FRED",unit,"monthly" if key=="PCOPPUSDM" else "daily","Retain missing quotes","Series-specific terms",manifest["retrieved_utc"])
    fx=pd.read_csv(public/"DEXSZUS.csv",index_col=0,parse_dates=True).iloc[:,0].reindex(prices.index)
    converted=(prices.SPY*fx).pct_change(fill_method=None)
    pd.testing.assert_series_equal(converted,((1+returns.SPY)*(1+fx.pct_change(fill_method=None))-1).reindex(prices.index),check_names=False)
    statements=json.loads((DATA/"raw/fomc/statements.json").read_text())["statements"]
    assert all(pd.Timestamp(x["publication_date"]) and x["paragraphs"] and x["source_url"].startswith("https://www.federalreserve.gov/") for x in statements)
    days=pd.read_csv(next((DATA/"Data for laboratories-20261119").glob("*.csv")),usecols=["date","ticker"])
    days=days[days.ticker.isin(LN7_COMPANIES)]
    # Link identifiers first. Sector effective dates alone cannot prove historical publication.
    linked=audit_ln7_companies(days,DATA/"additional_data/raw/wrds",OUT/"stocktwits_gics_history.csv")
    history=pd.read_csv(DATA/"raw/GICS.zip",dtype="string")
    history=history.loc[history.indtype.eq("GICS"),["gvkey","gsector","indfrom","indthru"]].rename(columns=dict(gsector="effective_sector",indfrom="effective_from",indthru="effective_through"))
    assert history.effective_sector.isin(GICS_CODES).all()
    for col in ["effective_from","effective_through"]:
        history[col]=pd.to_datetime(history[col])
    assert history.effective_from.notna().all() and not history.effective_through.lt(history.effective_from).any()
    linked["effective_sector"],issue=_match_history(linked,history[history.gvkey.isin(linked.gvkey.dropna())],"gvkey","effective_sector")
    linked["effective_status"]=linked.status.where(linked.gvkey.isna(),issue.fillna("effective_match"))
    linked.to_parquet(OUT/"ln7_company_sector_days.parquet",index=False)
    counts=linked.groupby([linked.date.dt.year.rename("year"),linked.effective_sector.fillna("unmapped"),"effective_status"]).size().rename("firm_days")
    counts.to_csv(OUT/"ln7_sector_attrition.csv")
    assert counts.sum()==len(days)
    coverage=pd.read_csv(OUT/"series_coverage.csv")
    pd.DataFrame(catalogue).to_csv(OUT/"series_catalogue.csv",index=False)
    report=dict(price_sessions=len(prices),assets=len(prices.columns),fomc_documents=len(statements),macro_panel_sessions=len(panel),
                coverage_entries=len(coverage),sector_status=linked.effective_status.value_counts().to_dict(),publication_verified=int(linked.gics_sector.notna().sum()),
                fx_comparisons=int(converted.notna().sum()),adjusted_price_moves_over_20pct=int(returns.abs().gt(.2).sum().sum()))
    (OUT/"collection_audit.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    print(json.dumps(build(),indent=2))
