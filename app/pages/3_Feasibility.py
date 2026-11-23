"""Section 5 research desk and the account's dated admission decision."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from riskmatch_v2.feasibility.account import solve_account

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/"reports/05-faisabilite"
st.set_page_config(page_title="Feasibility · RiskMatch",page_icon="🍒",layout="wide")
broad_path=ROOT/"reports/univers-complet/resultats.json"
if broad_path.is_file():
    st.subheader("Feasibility on the selected universe")
    broad=json.loads(broad_path.read_text())
    st.caption("Each eligible research instrument can enter the solution. Volatility and net return are estimates for the investment sleeve in CHF.")
    st.dataframe(pd.DataFrame(broad["subsets"]).T.rename(columns={"offered":"Instruments submitted","held":"Positions selected","net":"Estimated return","vol":"Estimated volatility","status":"Certificate"}))
    with st.expander("Risk bands on the entire universe"):
        st.dataframe(pd.DataFrame(broad["frontier"]).T)
    st.markdown("[Compare allocations across the full universe](./Options)")
st.title("Feasibility of portfolio")
d=json.loads((REPORT/"resultats.json").read_bytes())
live=d["live"]
st.subheader("Your mandate")
st.write(f"On 23 November 2026, {live['count']} instrument passes the controls of the account on {live['examined']:,} entries examined.")
session=st.session_state.get("interview")
if session and session.versions:
    register=ROOT/"data/local/4/4.0-2026-11-23/decision.parquet"
    if register.exists():
        gate=solve_account(session.versions[-1],pd.read_parquet(register),live["date"])
        st.write(gate["status"].capitalize())
        if "pocket_chf" in gate:
            st.caption(f"Stock of {gate['pocket_chf']:,.0f} CHF · reserve of {gate['reserve_chf']:,.0f} CHF")
else:
    st.caption("The questionnaire confirms the investment sleeve and the level of risk required.")
st.subheader("Historical simulation on the 13 funds")
st.caption("prices at 30 October 2026 · hypothetical charges of 10 pb per amount processed · external reserve at the investment sleeve.")
st.image(str(REPORT/"frontiere.png"))
folder=ROOT/"data/local/5"/d["version"]/d["snapshot"]
if not (folder/"etf_moments.npz").is_file():
    st.info("The graph and the reference results are available here. Custom recalculation uses local market inputs.")
    st.stop()
try:
    import numpy as np
    from riskmatch_v2.feasibility.study import market
    from riskmatch_v2.feasibility.engine import Frontier
    from dataclasses import replace
except ImportError:
    st.info("To recalculate a simulation, install the catalog options and makeability.")
    st.stop()
with np.load(folder/"etf_moments.npz",allow_pickle=False) as z:
    cfg=json.loads((ROOT/"config/faisabilite-5.json").read_bytes())
    p=market(z["ids"].tolist(),z["mu"],z["root"],cfg)
with st.form("simulation"):
    mode=st.radio("Request on the CHF investment sleeve",["Volatility cap","Band","Minimum risk"],horizontal=True)
    low=st.number_input("Low band point (%)",0.,200.,8.,step=.5)
    high=st.number_input("Ceiling or high bound (%)",0.,200.,12.,step=.5)
    exclusions=st.multiselect("Excluded funds",p.names)
    run=st.form_submit_button("Calculate Feasibility")
if run:
    if mode=="Band" and low>high:
        st.error("The low bound exceeds the high bound.")
        st.stop()
    cap=p.hi.copy()
    for fund in exclusions:
        cap[p.names.index(fund)]=0.
    engine=Frontier(replace(p,hi=cap))
    r=engine.solve(minimum=True) if mode=="Minimum risk" else engine.solve(low=low/100 if mode=="Band" else 0.,high=high/100)
    st.write({"optimal":"Optimum checked to model accuracy","impossible":"Impossible demand according to the calculated bound",
              "candidate":"Verified candidate, uncertain optimality","non_concluant":"Inconclusive research"}[r["status"]])
    st.caption(r["proof"])
    if r["candidate"]:
        c=r["candidate"]
        st.write(f"Estimated volatility {c['risk']:.2%} · annual estimated net return {c['net']:.2%} · CHF cash after costs {c['cash']:.2%}")
        allocation=pd.Series(c["weights"],index=p.names)
        if (allocation>1e-6).any():
            st.bar_chart(allocation[allocation>1e-6]*100,y_label="Weight of investment sleeve (%)")
        else:
            st.caption("The investment sleeve stays in cash.")
    elif r["max_risk_bound"] is not None:
        st.write(f"Higher volatility point for these constraints: {r['max_risk_bound']:.2%}.")
