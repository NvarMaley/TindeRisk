import streamlit as st

st.title("🔍 Analysis")
st.write(
    "This optional page explains the evidence behind the simple portfolio cards. "
    "It is not required to make a selection."
)

with st.expander("Technical details", expanded=False):
    st.markdown(
        "- Portfolio weights and risk contributions\n"
        "- Sortino and Calmar ratios\n"
        "- Expected Shortfall and concentration\n"
        "- Turnover, costs, tracking error, and information ratio\n"
        "- Common-period walk-forward backtest and prespecified subperiods\n"
        "- Black-Litterman views or regime diagnostics only when validated"
    )

st.info("Validated analysis artifacts have not been generated yet.")
