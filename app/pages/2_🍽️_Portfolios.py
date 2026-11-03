import streamlit as st

st.title("🍽️ Portfolio Menu")
st.write(
    "Compare strategies prepared for your risk category. Every validated card will use "
    "the same reference risk, historical period, and cost assumptions."
)

risk_band = st.session_state.get("risk_band")
if risk_band is None:
    st.info("Complete the Profile page first. No category has been assigned yet.")
else:
    st.success(f"Your category: {risk_band}")

strategies = {
    "Classic": (
        "Balances estimated risk and return.",
        "Sensitive to expected-return estimates.",
    ),
    "Balanced (ERC)": (
        "Diversifies risk contributions without forecasting returns.",
        "May allocate heavily to lower-volatility assets.",
    ),
    "Connected (BL)": (
        "Combines a strategic prior with documented market views.",
        "Depends on the validity and confidence of those views.",
    ),
    "60/40 benchmark": (
        "Simple, transparent, and easy to explain.",
        "A fixed capital split does not guarantee diversified risk.",
    ),
}

for strategy, (advantage, limitation) in strategies.items():
    with st.container(border=True):
        st.subheader(strategy)
        columns = st.columns(5)
        labels = [
            "Historical return",
            "Realized risk",
            "Net Sharpe",
            "Max drawdown",
            "Annual cost",
        ]
        for column, label in zip(columns, labels, strict=True):
            column.metric(label, "—")
        st.write(f"✅ **Advantage:** {advantage}")
        st.write(f"⚠️ **Limitation:** {limitation}")

st.caption(
    "Metrics will appear only after validated backtest artifacts are available. "
    "Historical results are not forecasts, and no strategy is universally best."
)
