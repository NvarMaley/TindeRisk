import streamlit as st

st.title("🎯 My Profile")
st.progress(0, text="Questionnaire under development — 0/15")
st.warning("The question bank and adaptive engine will be integrated here in step 3.")

st.session_state.setdefault("answers", {})
st.session_state.setdefault("profile", None)
