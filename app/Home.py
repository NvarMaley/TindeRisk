"""Entry point for the RiskMatch application.

The application intentionally starts as a functional prototype:
computationally intensive results will be precomputed in the notebook and read from results/.
"""

import streamlit as st


st.set_page_config(
    page_title="RiskMatch",
    page_icon="💘",
    layout="wide",
)

st.title("💘 RiskMatch")
st.subheader("Swipe your risk. Choose your portfolio. Track it.")
st.write(
    "RiskMatch structures your risk profile, compares several investment strategies "
    "at the same risk level, and explains their differences."
)

st.info("Start with the **Profile** page in the menu on the left.")

with st.expander("How does the project work?"):
    st.markdown(
        "1. The questionnaire estimates risk tolerance and capacity.\n"
        "2. The engine translates this profile into a target volatility.\n"
        "3. The menu compares portfolios built with QARM tools.\n"
        "4. Monitoring displays drift, alerts, and the next rebalancing date."
    )

st.caption("Academic prototype — not financial advice.")

