"""Card intake for the simulator, sharing the original 41-card bank and routing."""

import json
from pathlib import Path
from uuid import uuid4

import streamlit as st
from streamlit.components.v1 import declare_component

from riskmatch_v2.interview import CARDS, derive, read_version, route
from riskmatch_v2.matching.mandate import example_profile

ROOT = Path(__file__).resolve().parents[1]
card_widget = declare_component(
    "riskmatch_card", path=str(Path(__file__).parent / "card")
)


def refresh(edit=None):
    st.session_state.edit = edit
    st.session_state.token = uuid4().hex
    st.rerun()


def correction(interview):
    active = route(interview.answers)
    if not interview.answers:
        return
    with st.expander("Review or correct a response"):
        selected = st.selectbox(
            "Card to be reviewed",
            [k for k in active if k in interview.answers],
            format_func=lambda k: f"{k} · {CARDS[k]['text']}",
        )
        st.write("Registered reply", interview.answers[selected])
        if st.button("Fix this card"):
            st.session_state.rm13_route = "Profile"
            refresh(selected)


def render(interview, ledger, navigate):
    state = st.session_state
    active = route(interview.answers)
    remaining = [k for k in active if k not in interview.answers]
    current = state.get("edit") or next(iter(remaining), None)
    if current:
        st.progress(
            (len(active) - len(remaining)) / len(active),
            text=f"{len(active) - len(remaining)} of {len(active)} active cards answered",
        )
        result = card_widget(
            card=CARDS[current],
            token=state.token,
            previous=interview.answers.get(current),
            key="active_card",
        )
        if result and result.get("token") == state.token:
            try:
                old = len(interview.history)
                interview.record(current, result["value"])
                if len(interview.history) != old:
                    ledger.invalidate_mandate()
            except (TypeError, ValueError) as exc:
                st.error(str(exc))
                if st.button("Try this card again"):
                    refresh(current)
            else:
                follow = {
                    "G04": ("no", "G01"),
                    "T03": ("yes", "T01"),
                    "L05": ("yes", "L01"),
                }.get(current)
                refresh(follow[1] if follow and result["value"] == follow[0] else None)
    else:
        portrait = derive(interview.answers, interview.as_of)
        st.subheader("Your summary")
        for key, label in (
            ("reserve_chf", "Protected reserve"),
            ("investable_chf", "Investable balance"),
        ):
            amount = portrait["liquidity"][key]
            if amount:
                interval = f"{amount['low']:,.2f}"
                if amount["high"] != amount["low"]:
                    interval += f" to {amount['high']:,.2f}"
                st.write(f"{label} · CHF {interval}")
        for issue in portrait["clarifications"]:
            st.info(issue)
        with st.expander("Answers, behavioural evidence and preferences"):
            st.json(portrait)
        if not interview.confirmed and st.button(
            "Confirm this version of my answers", type="primary"
        ):
            interview.confirm()
            navigate("Mandate")
        if interview.confirmed and st.button("Open my mandate", type="primary"):
            navigate("Mandate")
    if not interview.answers and st.button(
        "Try a fictional profile",
        help="Fill the cards with client A from the funding study. You can review every answer before confirming.",
    ):
        state.interview = example_profile(ROOT)
        refresh()
    correction(interview)
    if interview.versions:
        with st.expander("Questionnaire versions"):
            version = st.selectbox(
                "Saved version",
                range(1, len(interview.versions) + 1),
                index=len(interview.versions) - 1,
            )
            st.download_button(
                "Export this version to JSON",
                json.dumps(interview.versions[version - 1], indent=2),
                f"mandate-v{version}.json",
                "application/json",
            )
    with st.expander("Inspect a previous questionnaire export"):
        upload = st.file_uploader("Fictional mandate JSON", type="json")
        if upload:
            try:
                st.json(read_version(upload.getvalue()))
            except (TypeError, ValueError, UnicodeError) as exc:
                st.error(str(exc))
