"""Consented local demonstration portfolio."""

import os
import secrets
import sys
from pathlib import Path
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from riskmatch.monitor import UPDATES, advance, create, erase, history, snapshot

st.set_page_config(page_title="RiskMatch · Portfolio monitor", layout="wide")
st.title("Portfolio monitor")
st.caption("Fictional CHF account · simulated close and FX feed · local storage")
if "monitor_key" not in st.session_state:
    chosen = st.session_state.get("monitor_selection")
    if chosen:
        st.write(
            f"Selected allocation: {chosen['arm']}. CHF 15,000 reserved for the bill, CHF 35,000 available before fees."
        )
        consent = st.checkbox(
            "Store this fictional mandate and allocation on this app host"
        )
        if st.button("Confirm and open demo account", disabled=not consent):
            k = st.session_state.setdefault(
                "new_monitor_key", secrets.token_urlsafe(32)
            )
            create(**chosen, consent=consent, token=k)
            st.session_state.monitor_key = k
            st.rerun()
    else:
        st.info(
            "Choose an allocation on Portfolio options and save the example choice first."
        )
    with st.form("recover"):
        key = st.text_input("Demo recovery key", type="password")
        if st.form_submit_button("Reopen saved account"):
            try:
                history(key)
                st.session_state.monitor_key = key
                st.rerun()
            except ValueError:
                st.error("Unknown demo recovery key.")
    st.stop()
token = st.session_state.monitor_key
s, events = history(token)
q = UPDATES[s["cursor"]]
snap = snapshot(s)
st.write(
    f"{s['arm']} · mandate v{s['version']} · selected {s['selected']}. Model {s['model']}."
)
from riskmatch.monitor import quote_status

status = quote_status(q)
if status != "fresh":
    st.warning(
        f"{status}. Last reliable valuation {snap['last_reliable']}. Trading proposals suspended."
    )
st.caption(
    f"Last refresh {q['asof']} · feed observation {s['quote']['observed']} · FX observation {s['quote']['fx_observed']}"
)
cols = st.columns(3)
cols[0].metric("Total value", f"CHF {snap['wealth']:,.2f}")
cols[1].metric("Protected CHF", f"{s['reserve']:,.2f}")
cols[2].metric("Net time-weighted return", f"{s['index'] - 1:.2%}")
st.write(
    f"Current investable wealth is {snap['sleeve'] / (s['goal'] * (1 + s['inflation']) ** s['years']):.1%} of the illustrative nominal terminal goal of CHF {s['goal'] * (1 + s['inflation']) ** s['years']:,.0f}."
)
st.table(
    pd.DataFrame(
        {
            "ETF": ["SPY", "IEF", "GLD"],
            "Units": s["units"],
            "Current weight": snap["weights"],
            "Selected weight": s["weights"],
        }
    )
)
marks = pd.DataFrame([e for e in events if "index" in e])
st.line_chart(marks.set_index("time")[["wealth", "flow"]])
st.line_chart(marks.set_index("time")[["index", "drawdown"]])
st.dataframe(marks[["time", "status", "flow", "fee", "market_pnl", "fx_pnl", "wealth"]])
if st.button("Receive next feed update", disabled=s["cursor"] >= len(UPDATES) - 1):
    advance(token, s["cursor"])
    st.rerun()
with st.expander("Local access and deletion"):
    st.write(
        "Keep this private recovery key to reopen this fictional account. Anyone with the key can use it."
    )
    st.code(token)
    if st.button("Close session"):
        st.session_state.pop("monitor_key", None)
        st.session_state.pop("new_monitor_key", None)
        st.rerun()
    confirm = st.checkbox("Delete this saved fictional account and its events")
    if st.button("Delete account", disabled=not confirm):
        erase(token)
        st.session_state.pop("monitor_key", None)
        st.session_state.pop("new_monitor_key", None)
        st.rerun()

from riskmatch.reviews import prepare, respond, revise, shadows
from datetime import date

st.subheader("Review the allocation")
with st.expander("Update the fictional mandate"):
    with st.form("revision"):
        due = st.date_input(
            "Payment due",
            value=max(date.fromisoformat(s["due"]), date.fromisoformat(q["day"])),
            min_value=date.fromisoformat(q["day"]),
        )
        bill = st.number_input(
            "Required CHF payment", min_value=0.0, value=float(s["bill"])
        )
        limit = st.selectbox(
            "Revised sleeve volatility limit",
            [0.04, 0.08],
            index=int(s["cap"] == 0.08),
            format_func=lambda v: f"{v:.0%}",
        )
        if st.form_submit_button("Confirm mandate revision"):
            revise(token, s["version"], bill, due.isoformat(), limit)
            st.rerun()
sale = st.checkbox("ETF sales available", value=True)
delay = st.checkbox("Sale proceeds settle next demo session", value=True)
if st.button("Compare holding and trading", disabled=status != "fresh"):
    st.session_state["monitor_review"] = prepare(token, sale, delay)
    st.rerun()
review = st.session_state.get("monitor_review")
if review and any(e.get("review_id") == review["review_id"] for e in events):
    if review["status"] == "suspended":
        st.warning(
            "Review suspended. A fresh authorized quote and catalogue entry are required."
        )
    else:
        st.write(
            f"{review['reason']}. Hold risk {review['risk']:.2%}, proposed risk {review['post_risk']:.2%}. "
            f"Trade CHF {review['turnover']:,.2f}, modeled fees CHF {review['fee']:,.2f}. "
            f"Uncovered bill holding CHF {review['hold_shortfall']:,.2f}, after proposal CHF {review['trade_shortfall']:,.2f}."
        )
        st.caption(
            f"Fictional one-year goal wealth estimate: hold CHF {review['hold_goal_wealth']:,.2f}, proposal CHF {review['trade_goal_wealth']:,.2f}."
        )
        for label, action in [
            ("Confirm simulated change", "accept"),
            ("Decline change", "decline"),
            ("Record hold", "hold"),
        ]:
            disabled = (
                action == "accept"
                and (
                    review["status"] != "proposal"
                    or review["sale_allowed"] != sale
                    or review["delayed"] != delay
                )
            ) or status != "fresh"
            if st.button(label, disabled=disabled):
                st.session_state["monitor_receipt"] = respond(
                    token, review["review_id"], action
                )
                st.session_state.pop("monitor_review", None)
                st.rerun()
if st.session_state.get("monitor_receipt"):
    st.write("Last review response · " + st.session_state.monitor_receipt)
with st.expander("Review decisions and shadow holdings"):
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "event": e["kind"],
                    "time": e["time"],
                    "decision": e.get("action", e.get("status")),
                }
                for e in events
                if e["kind"] in ["review", "decision", "mandate"]
            ]
        )
    )
    st.dataframe(pd.DataFrame(shadows(events)))
