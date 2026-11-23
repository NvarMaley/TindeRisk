"""Local research sheets. Row-level market data stays on the user's machine."""
import json
from pathlib import Path
import pandas as pd
from riskmatch_v2.archive_labels import read_snapshot
import streamlit as st

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/"reports/04-catalogue"
st.set_page_config(page_title="Catalogue · RiskMatch",page_icon="🍒",layout="wide")
st.title("Market Library")
result=json.loads((REPORT/"resultats.json").read_text())
st.caption(f"Vintage {result['version']} · Monthly historical measures in CHF")
p=ROOT/"data/local/4"/result["version"]
bridge_report = ROOT / "reports/actions-2026/resultats.json"
if bridge_report.is_file():
    bridge = json.loads(bridge_report.read_text())
    st.caption(f"Individual stocks on 30 October 2026 · {bridge['status']["complete"]} complete trajectories on {bridge['cohort']} End 2025 shares.")
if not (p/"manifest.json").exists():
    st.info("This copy contains the aggregate results. Individual sheets require the local private catalogue.")
    st.image(str(REPORT/"couverture-et-expositions.png"))
    st.stop()


@st.cache_data
def inventory(path):
    return read_snapshot(path/"instruments.parquet")


items=inventory(p)
query=st.text_input("Search by symbol, name or identifier",value="SPY").strip()
if not query:
    st.info("Enter a name, symbol or PERMNO.")
    st.stop()
matches=items.loc[items[["id","symbol","name"]].apply(
    lambda c:c.str.contains(query,regex=False,case=False,na=False)).any(axis=1)].copy()
if matches.empty:
    st.info("No match in this vintage.")
    st.stop()
matches["order"]=(matches.symbol.str.upper()!=query.upper()).astype(int)+matches.role.ne("instrument").astype(int)*2
matches=matches.sort_values(["order","id"]).set_index("id")
key=st.selectbox("Instrument or series",matches.index,
                 format_func=lambda k:f"{matches.at[k,'symbol'] or '—'} · {matches.at[k,'name'] or '—'} · {k}")
asset=matches.loc[key]
broad_path = ROOT/"reports/univers-complet/resultats.json"
version = json.loads(broad_path.read_text()) if broad_path.is_file() else {}
archive = ROOT/"data/local/univers"/version.get("snapshot", "unavailable")
review = archive/"post_collection_review.parquet"
economics_report = ROOT / "reports/econometrie/results.json"
economics = json.loads(economics_report.read_text()) if economics_report.is_file() else {}
research = ROOT / "data/local/econometrics" / economics.get("snapshot", "unavailable")
latest_sheets = research if (research/"sheets.parquet").is_file() and economics["source_snapshot"]==version.get("snapshot") else archive
status=pd.read_parquet(review if review.is_file() else p/"decision.parquet",filters=[("id","=",key)]).iloc[0]
st.write(f"{asset.asset_class} · {asset.role} · {asset.currency or "currency to be qualified"}")
if not status.eligible:
    st.caption("Decision of 23 November 2026 · excluded from the proposal")
    labels = {
        "SOURCE_INDISPONIBLE": "Source not available at decision date",
        "ROLE_NON_INVESTISSABLE": "Search series or entry to qualify",
        "SORTIE_OBSERVEE": "Output of the observed title",
        "IDENTITE": "Identity of the issuer to be checked",
        "PERIMETRE_US": "Exposure and space to be checked",
        "NEGOCIABILITE": "Negotiatability to be confirmed",
        "ACCES_COMPTE": "Account access to be confirmed",
        "LOT": "Unknown batch size",
        "REGLEMENT": "Settlement deadline to be confirmed",
        "LIQUIDITE_ORDRE": "Liquidity for size of unknown order",
        "FRAIS": "Unknown execution costs",
        "DOUBLON": "Economic identity to be reconciled",
        "CONDITIONS_CLASSE": "Incomplete instrument characteristics",
        "PRIX_NON_FRAIS": "Pre-last session or absent",
        "FX_NON_FRAIS": "Change prior to last session or absent",
        "HISTORIQUE_RISQUE": "Less than 36 months exploitable",
    }
    with st.expander("Why is this instrument ruled out?"):
        st.markdown("\n".join("- " + labels.get(code, code) for code in status.reasons.split("|")))
if version:
    mixed_id = key.rsplit("-",1)[-1] if key.startswith("ETF-") else "UST:"+key[7:-1] if key.startswith("ISIN:US") else key
    if (archive/"sheets.parquet").is_file():
        row=read_snapshot(archive/"membership.parquet",filters=[("day","=",version["date"]),("id","=",mixed_id)])
        if not row.empty:
            st.subheader("Multi-asset study as at 30 October 2026")
            record=row.iloc[0]
            st.write(f"{"Submitted to the engine" if record.included else record.reason} · {record.observations} Daily observations common to the factors in 504 sessions.")
            recent=pd.read_parquet(latest_sheets/"sheets.parquet",filters=[("id","=",mixed_id)])
            st.dataframe(recent[["years","observations","annual_mean","volatility","cagr","max_drawdown"]].rename(columns={"years":"Years","observations":"Months observed","annual_mean":"Annualized average","volatility":"Volatility","cagr":"Annualized compound return","max_drawdown":"Maximum withdrawal"}),hide_index=True)
            with st.expander("Correlation with another title"):
                universe=read_snapshot(archive/"membership.parquet",filters=[("day","=",version["date"])],columns=["id","symbol"])
                choices=universe.set_index("id").symbol.to_dict()
                peer=st.selectbox("Comparison security",list(choices),index=list(choices).index("SPY"),format_func=lambda k:f"{choices[k]} · {k}")
                years=st.select_slider("Comparison window (years)",options=[1,3,5,10],value=3)
                if peer!=mixed_id:
                    pair=pd.read_parquet(latest_sheets/"monthly_all_chf.parquet",columns=[mixed_id,peer]).tail(12*years).dropna()
                    if len(pair)>2:
                        st.write(f"{len(pair)} mois communs en CHF · Pearson {pair.corr().iloc[0,1]:.3f} · Spearman {pair.rank().corr().iloc[0,1]:.3f} · annualized covariance {12*pair.cov().iloc[0,1]:.5f}.")
                    else:st.caption("Less than three joint observations.")
            if latest_sheets == research:
                with st.expander("Sensitivity to oil and rates, crises and volatility"):
                    sensitivity=pd.read_parquet(research/"sensitivities.parquet",filters=[("id","=",mixed_id)])
                    if sensitivity.empty:
                        st.write("Estimate not available for this title as at 30 October 2026.")
                    else:
                        view=sensitivity.query("window==252 and offset==0 and lag==0").set_index("factor")
                        labels={"market_usd":"US market +1%","usd_chf":"Dollar en CHF +1 %","wti_usd":"WTI +10 USD/baril","yield_10y_pp":"Rates at 10 years + 100 bps"}
                        multipliers=pd.Series({"market_usd":1,"usd_chf":1,"wti_usd":1000,"yield_10y_pp":100})
                        impact=view[["beta","low95","high95"]].mul(multipliers,axis=0).rename(index=labels,columns={"beta":"Effect in%","low95":"Low point 95%","high95":"High peak 95%"})
                        st.caption("The same day, other constant factors. The interval measures uncertainty on the estimated sensitivity.")
                        st.dataframe(impact)
                    crises=read_snapshot(research/"crises.parquet",filters=[("id","=",mixed_id)])
                    if not crises.empty:
                        st.dataframe(crises[["episode","return_chf","observed_drawdown"]].set_index("episode").mul(100).rename(columns={"return_chf":"return in CHF (%)","observed_drawdown":"Maximum observed decrease (%)"}))
                    forecasts=pd.read_parquet(research/"forecasts.parquet",filters=[("id","=",mixed_id)])
                    if not forecasts.empty:
                        st.caption("Volatility annualized at the end of October. A positive QLIKE gain indicates a lower historical error for the exponential mean.")
                        st.dataframe(forecasts.drop(columns="id").rename(columns={"horizon":"Horizon (sessions)","windows":"Checked windows","qlike_gain":"Gain QLIKE","hist_vol":"Historical Vol. (Dec.)","ewma_vol":"Exponential flight (Dec.)"}),hide_index=True)
                    alert=pd.read_parquet(research/"momentum.parquet").reindex([mixed_id]).iloc[0]
                    if pd.notna(alert.momentum_z):
                        st.caption(f"Acceleration of the prices in USD over 63 sessions · score {alert.momentum_z:.2f}, exploratory threshold 2.")
if key.startswith("ETF-"):
    stats=read_snapshot(p/"fund_sheets.parquet",filters=[("id","=",key)])
elif key.startswith("PERMNO:"):
    stats=read_snapshot(p/"stock_sheets.parquet",filters=[("permno","=",int(key.split(':')[1]))])
else:
    stats=pd.DataFrame()
if stats.empty and (not version or not (archive/"sheets.parquet").is_file() or row.empty):
    st.info("History of total returns in CHF insufficient for these sheets.")
elif not stats.empty:
    st.subheader("Observed history")
    cols={"years":"Window (years)","start":"Start","end":"End","observations":"Usable months",
          "expected":"Anticipated months","annual_mean":"Annualized average (%)","cagr":"Annualized (%)",
          "variance":"Annual variance (decimal return squared)","volatility":"Volatility (%)","max_drawdown":"Maximum drawdown (%)",
          "recovery_days":"Time to recovery (days)","recovery_state":"Recovery"}
    sample=stats[list(cols)].copy()
    for name in ("annual_mean","cagr","volatility","max_drawdown"):
        sample[name]=100*sample[name]
    st.dataframe(sample.rename(columns=cols),hide_index=True)
    st.caption("Variance uses available monthly returns. Compound return requires an unbroken local return series and exchange rates at both endpoints. The maximum decrease uses the observed monthly valuations.")
if key.startswith("ETF-"):
    c=next(x for x in result["coverage"] if x["fund"]==asset.symbol)
    st.write(f"Net weight assigned to an issuer on 23 November · {c['assigned_net']:.2%}")
    corr=pd.read_parquet(p/"fonds_3a_pearson.parquet")[asset.symbol].sort_values(ascending=False)
    st.bar_chart(corr.rename("Three-year correlation"))

# The 2026 research bridge has a separate vintage from the original admission register.
if key.startswith("PERMNO:"):
    if bridge_report.is_file():
        bundle = ROOT / "data/local/actions-2026" / bridge["end"] / bridge["snapshot"]
        if (bundle / "inventory.parquet").is_file():
            pid = int(key.split(":")[1])
            rows = read_snapshot(bundle / "inventory.parquet", filters=[("permno", "=", pid)])
            if not rows.empty:
                row = rows.iloc[0]
                st.subheader("Historical extension in 2026")
                st.write(f"{row.issuer} · {row.status} · arrested on 30 October 2026")
                if pd.isna(row.symbol):
                    st.caption(row.detail)
                else:
                    st.caption(f"{row.symbol} · {int(row.sessions_traded)} sessions with positive prices and volume on {bridge['sessions']}.")
                    monthly = pd.read_parquet(bundle / "monthly_extension.parquet", filters=[("permno", "=", pid)])
                    monthly = monthly.sort_values("day").set_index("day")[["usd","chf"]].mul(100)
                    st.bar_chart(monthly.rename(columns={"usd":"USD return (%)","chf":"CHF return (%)"}))
