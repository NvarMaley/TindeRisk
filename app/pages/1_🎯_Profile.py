import json

import streamlit as st
import yaml

from src.paths import QUESTIONS, ROOT
from src.profile_output import build_profile

CAPACITY_DESCRIPTIONS = {
    "F01": "how long you plan to keep the money invested",
    "F02": "money you may need to withdraw soon",
    "F03": "the savings available for essential expenses",
    "F04": "a planned payment that a loss could affect",
}

st.title("🎯 My Profile")
st.info(
    "RiskMatch is an academic prototype. The questionnaire has not been "
    "psychometrically validated or certified. Use the risk category as an educational estimate."
)

draft = json.loads((QUESTIONS / "fixed_mvp.json").read_text(encoding="utf-8"))
config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
st.write(draft["instructions"])
with st.form("fixed_profile"):
    answers = {}
    for card in draft["questions"]:
        key = card["id"]
        options = {choice["id"]: choice["text"] for choice in card["options"]}
        if card["type"] == "multiple":
            answers[key] = st.multiselect(card["text"], list(options), format_func=options.__getitem__, key=key)
        else:
            answers[key] = st.radio(card["text"], list(options), index=None,
                                    format_func=options.__getitem__, key=key)
    submitted = st.form_submit_button("See my risk category")

if submitted:
    st.session_state["profile"] = None
    st.session_state["risk_band"] = None
    st.session_state["answers"] = {}
    if any(choice is None or choice == [] for choice in answers.values()):
        st.warning("Please answer each question. Choose “I am not sure” if you need more information.")
    else:
        try:
            profile = build_profile(answers, reference_sharpe=config["reference_sharpe"])
        except ValueError:
            st.warning("Please check the multiple-choice answers. Choose “none” or “unsure” on its own.")
        else:
            st.session_state["answers"] = profile["answers"]
            st.session_state["profile"] = profile
            category = profile["risk"]["category"]
            if category and profile["risk"]["reference_check_passed"]:
                st.session_state["risk_band"] = category["id"]

profile = st.session_state.get("profile")
if profile:
    risk = profile["risk"]
    category = risk["category"]
    if category:
        lower, upper = category["range"]
        st.subheader(f'{category["id"].capitalize()} · {lower:.0%}–{upper:.0%}')
        st.write("This range describes typical annual ups and downs. Losses can be larger.")
    else:
        st.subheader("Below the available risk categories")
        st.write("This profile calls for a lower risk level than the prepared portfolios cover.")

    if risk["capacity_volatility"] < risk["tolerance_volatility"]:
        reasons = ", ".join(CAPACITY_DESCRIPTIONS[key] for key in risk["binding_capacity_items"])
        st.write(f"Your financial situation limits the risk level because of {reasons}.")
    else:
        st.write("Your answers about how much fluctuation you would accept set the risk level.")

    if risk["clarification_items"]:
        st.warning("Clarify your undecided risk and constraint answers before using a portfolio reference.")
    elif not risk["reference_check_passed"]:
        st.info("A prepared portfolio reference does not fit your risk limit.")
    with st.expander("Technical details"):
        st.metric("Risk aversion (φ)", f'{risk["risk_aversion"]:.2f}')
        st.write(f'Tolerance target: {risk["tolerance_volatility"]:.2%}')
        st.write(f'Capacity ceiling: {risk["capacity_volatility"]:.2%}')
        st.write(f'Effective risk target: {risk["effective_volatility"]:.2%}')
        if category:
            st.write(f'Catalogue volatility reference: {category["reference_volatility"]:.2%}')
