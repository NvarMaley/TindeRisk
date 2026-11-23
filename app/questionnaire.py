"""RiskMatch's local five-screen simulated client journey."""

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

import streamlit as st
from identity import NAMES, hero
from risk import show_risk
from survey import correction, render

from riskmatch_v2.interview import Interview
from riskmatch_v2.matching.ledger import Ledger
from riskmatch_v2.matching.mandate import MARKET_DAY, mandate, restore

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data/local/13/accounts"
st.set_page_config(
    page_title="RiskMatch · Portfolio studio",
    page_icon="🍒",
    layout="wide",
    initial_sidebar_state="collapsed",
)
state = st.session_state


def navigate(screen):
    state.rm13_route = screen
    st.rerun()


def open_dossier(book):
    state.clear()
    state.rm13_token = book.token
    latest = book.latest_mandate()
    state.interview = (
        restore(latest["payload"]["interview_versions"])
        if latest
        else Interview(date.fromisoformat(MARKET_DAY))
    )
    if latest and not latest["active"]:
        state.interview.confirmed = False
    state.match_day = book.latest_day() or MARKET_DAY
    state.token = uuid4().hex
    state.edit = None


if "rm13_token" not in state:
    open_dossier(Ledger.create(DIRECTORY))
try:
    ledger = Ledger(DIRECTORY, state.rm13_token)
except ValueError:
    open_dossier(Ledger.create(DIRECTORY))
    st.rerun()
iv = state.interview
if "rm13_route" in state:
    state.rm13_nav = state.pop("rm13_route")
screen = state.get("rm13_nav", "Profile")
hero(screen, state.match_day)
screen = (
    st.segmented_control(
        "Portfolio journey",
        NAMES,
        default="Profile",
        selection_mode="single",
        key="rm13_nav",
        label_visibility="collapsed",
    )
    or "Profile"
)
day = state.match_day


def persist():
    """A changed budget cannot silently move funds in the existing portfolio."""
    review = iv.versions[-1].get("risk_review", {})
    if not review.get("ready_for_feasibility"):
        ledger.invalidate_mandate()
        return
    latest = ledger.latest_mandate()
    opening = latest["payload"].get("funded_opening_chf") if latest else None
    payload = mandate(iv, day, opening)
    if opening is None and not payload["blocked_reason"]:
        opening = payload["capital_chf"]
        ledger.flow(day, opening, event_id="opening-sleeve")
    payload["funded_opening_chf"] = opening
    ledger.save_mandate(payload)


def mandate_screen():
    if not iv.confirmed:
        st.info(
            "Complete the active cards and confirm your answers to set the investment mandate."
        )
        if st.button("Return to my profile"):
            navigate("Profile")
        return
    st.caption(
        f"Questionnaire version {iv.versions[-1]['version']} · historical study dated {iv.as_of}"
    )
    current = ledger.current_mandate()
    if current:
        left, right = st.columns(2)
        left.metric("Investment sleeve", f"CHF {current['capital_chf']:,.0f}")
        right.metric("Protected reserve", f"CHF {current['reserve_chf']:,.0f}")
        if current["blocked_reason"]:
            st.warning(current["blocked_reason"])
        elif st.button("Compare portfolios", type="primary"):
            navigate("Compare")
    show_risk(iv, on_save=persist)
    correction(iv)


if screen == "Profile":
    render(iv, ledger, navigate)
elif screen == "Mandate":
    mandate_screen()
else:
    latest = ledger.latest_mandate()
    current = latest["payload"].copy() if latest else {}
    if latest:
        current["version"] = latest["version"]
    if not latest or not latest["active"]:
        current["blocked_reason"] = (
            "Confirm the latest investment mandate before making a new selection."
        )
    account = ledger.account(day)
    if (not latest or current.get("blocked_reason")) and not (
        screen == "Portfolio" and account["portfolio_version"]
    ):
        st.info(
            current.get("blocked_reason") or "Confirm the investment mandate first."
        )
        if st.button("Open mandate"):
            navigate("Mandate")
    else:
        from riskmatch_v2.matching import ui
        from riskmatch_v2.matching.engine import Market

        if not account["quotes"] and screen == "Compare":
            market = Market()
            ledger.mark(day, market.quotes(day))
            account = ledger.account(day)
        {
            "Compare": ui.render_compare,
            "Portfolio": ui.render_tracking,
            "Review": ui.render_review,
        }[screen](ledger, account, current, navigate)

with st.expander("Demo data and access"):
    st.caption(
        "Use fictional information. Draft answers stay in this browser session. Confirmed mandates, simulated trades and closing marks are saved locally in a private SQLite dossier. A recovery key grants access to that dossier."
    )
    if st.toggle("Show my recovery key", key="rm13_reveal"):
        st.code(ledger.token, language=None)
    if st.button("Prepare dossier export"):
        state.rm13_export = json.dumps(ledger.export(), ensure_ascii=False, indent=2)
    if "rm13_export" in state:
        st.download_button(
            "Download prepared dossier",
            state.rm13_export,
            "riskmatch-demo.json",
            "application/json",
        )
    with st.form("resume_demo"):
        capability = st.text_input(
            "Recovery key for another saved demo", type="password"
        )
        if st.form_submit_button("Reopen saved demo"):
            try:
                book = Ledger(DIRECTORY, capability.strip())
            except ValueError:
                st.error("This key does not open a saved demo.")
            else:
                open_dossier(book)
                navigate(
                    "Portfolio"
                    if book.account(state.match_day)["portfolio_version"]
                    else "Profile"
                )
    remove = st.checkbox(
        "Delete this fictional dossier, including all its versions and simulated trades"
    )
    if st.button("Delete dossier", disabled=not remove):
        ledger.delete()
        state.clear()
        st.rerun()
