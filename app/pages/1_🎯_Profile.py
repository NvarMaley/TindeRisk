import streamlit as st

st.title("🎯 My Profile")
st.progress(0, text="Questionnaire under development — 0/15")
st.write(
    "Your answers will be combined with your financial capacity. The application will "
    "recommend a category rather than presenting a falsely precise risk number."
)
st.warning("The fixed questionnaire and scoring rules will be integrated here in step 3.")

st.subheader("Risk categories")
st.table(
    {
        "Category": ["Conservative", "Balanced", "Growth", "Aggressive"],
        "Risk range": ["4%–6%", "6%–9%", "9%–12%", "12%–15%"],
        "Reference": ["5%", "8%", "10%", "14%"],
    }
)
st.caption(
    "If your willingness and financial capacity disagree, the more conservative category applies."
)

st.session_state.setdefault("answers", {})
st.session_state.setdefault("profile", None)
st.session_state.setdefault("risk_band", None)
