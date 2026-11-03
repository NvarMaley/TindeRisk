import streamlit as st

st.title("📡 Monitoring")
st.write(
    "Follow what happened after your selection. Live results are kept separate from "
    "the historical evidence used to compare strategies."
)

selection = st.session_state.get("selection")
if selection is None:
    st.info("Select a prepared portfolio before starting monitoring.")
else:
    st.success("A portfolio selection is active.")

st.markdown(
    "Monitoring will show:\n"
    "- value and return since selection;\n"
    "- benchmark comparison and current drawdown;\n"
    "- current weights and drift from targets;\n"
    "- rolling realized risk versus the selected category;\n"
    "- rebalancing alerts and the latest data timestamp."
)

st.caption("Daily end-of-day prices are sufficient for this academic prototype.")
