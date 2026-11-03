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
    "RiskMatch assigns you to a clear risk category, compares several investment "
    "strategies prepared at the same reference risk, and helps you follow the one you select."
)

st.info("Start with the **Profile** page in the menu on the left.")

with st.expander("How does the project work?"):
    st.markdown(
        "1. The questionnaire estimates risk tolerance and capacity.\n"
        "2. The lower of the two determines a risk category: Conservative, Balanced, Growth, or Aggressive.\n"
        "3. You compare strategies in that category using five historical measures and clear trade-offs.\n"
        "4. After selection, monitoring separates live results from historical evidence."
    )

st.caption(
    "Academic prototype — not financial advice. Historical performance is not a forecast."
)

