import streamlit as st

st.title("🍽️ Portfolio Menu")
st.info("The MVP strategies will be displayed here once the results have been precomputed.")
st.table(
    {
        "Strategy": ["Classic", "Balanced", "Connected", "Chameleon", "60/40"],
        "Scope": ["MVP", "MVP", "MVP", "Extension", "MVP / benchmark"],
        "Status": ["Under development"] * 5,
    }
)
