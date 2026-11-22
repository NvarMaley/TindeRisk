from datetime import date

import streamlit as st
from riskmatch.catalogue import approved
from riskmatch.demo import allocations, matches, difference_interval


def show():
    st.title("Fictional portfolio options")
    st.caption(
        "Portable course demonstration · CHF 50,000 · provider-free simulated inputs"
    )
    d = st.session_state.get("mandate", {})
    if not matches(d):
        st.warning(
            "The confirmed example requires CHF 50,000, a CHF 15,000 payment in one year, and the eight-year fictional goal. Review the mandate before choosing."
        )
        return
    st.write(
        "CHF 15,000 is protected. CHF 35,000 funds the allocation and its entry fee."
    )
    profile = st.session_state.get("demo_profile", "unresolved")
    st.write("Risk interval · " + profile)
    cap = st.radio(
        "Sleeve volatility limit",
        [0.08, 0.04],
        format_func=lambda x: f"{x:.0%}",
        horizontal=True,
    )
    data = allocations(cap)
    st.table(
        [
            dict(
                Option=name,
                Equities=f"{w[0]:.1%}",
                Treasuries=f"{w[1]:.1%}",
                Gold=f"{w[2]:.1%}",
                Entry_fee=f"CHF {fee:.2f}",
                Cash=f"CHF {cash:,.2f}",
            )
            for name, (w, fee, cash) in data.items()
        ]
    )
    scope = (date(2026, 11, 23), "CHF", "illustrative CHF 50000")
    try:
        manual = approved("demo/manual/v1", *scope, "synthetic local demonstration")
        signal = approved(
            "H06/v2/cross-instrument sentiment", *scope, "live recommendations"
        )
    except (ValueError, OSError):
        st.error("Catalogue verification unavailable. Example selection suspended.")
        return
    if not manual or signal:
        st.warning("This walkthrough requires the signed manual-only catalogue scope.")
        return
    low, high = difference_interval(data)
    if low <= 0 <= high:
        st.info(
            f"No signal has independent approval. The no-view baseline applies. The illustrative 95% range for the annual return difference is {low:.1%} to {high:.1%}; the choice remains open."
        )
        st.caption(
            "Fictional expected returns and covariance, three independent years assumed, entry fees included."
        )
    arm = st.selectbox("Choose an example portfolio", list(data))
    if st.button("Save example selection"):
        st.session_state.monitor_selection = dict(
            arm=arm, cap=cap, weights=data[arm][0], profile=profile
        )
        st.switch_page("pages/2_Portfolio_monitor.py")
