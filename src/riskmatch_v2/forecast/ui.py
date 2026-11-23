"""Public forecast notices and effective weights for the research desk."""

import json

import pandas as pd
import streamlit as st


def render(root):
    folder = root / "reports/12-forecasts"
    results = json.loads((folder / "results.json").read_text())
    registry = pd.DataFrame(json.loads((folder / "registry.json").read_text()))
    st.subheader("Forecast evidence")
    st.caption(
        "SPY in CHF · market cutoff 30 October 2026 · evidence reviewed 23 November 2026"
    )
    target = st.radio(
        "Forecast target",
        ["21-session return", "21-session variance", "63-session variance"],
        horizontal=True,
    )
    horizon = int(target.split("-")[0])
    measure = target.split()[-1]
    rows = registry[
        (registry.target == measure)
        & (registry.horizon == horizon)
        & registry.name.str.startswith("increment_")
    ].copy()
    rows["Signal"] = rows.name.str.removeprefix("increment_")
    unit = (
        "21-session return (%)" if measure == "return" else "Annualized volatility (%)"
    )
    for source, label in [("estimate", "Model"), ("reference", "Reference")]:
        value = rows[source] if measure == "return" else (252 * rows[source]) ** 0.5
        rows[label] = (100 * value).round(2)
    st.caption(unit)
    st.dataframe(
        rows[
            ["family", "Signal", "Model", "Reference", "direction", "weight", "reason"]
        ].rename(
            columns={
                "family": "Family",
                "direction": "Forecast vs reference",
                "weight": "Allocation weight",
                "reason": "Admission decision",
            }
        ),
        hide_index=True,
    )
    st.caption(
        "Each direction compares an experimental forecast with its historical reference. All tested signals have zero allocation weight."
    )
    with st.expander("Coverage across the US asset library"):
        coverage = json.loads((folder / "cross-asset.json").read_text())
        by_class = pd.DataFrame(coverage["by_class"])
        st.dataframe(
            by_class[(by_class.target == measure) & (by_class.horizon == horizon)][
                ["class", "inventory", "with_eight"]
            ].rename(
                columns={
                    "class": "Asset class",
                    "inventory": "Reviewed",
                    "with_eight": "At least eight paired outcomes",
                }
            ),
            hide_index=True,
        )
        st.caption(
            "A coverage count is descriptive. The full statistical and funded admission test applies to SPY in CHF."
        )
    ports = {p["name"]: p for p in results["portfolios"]}
    choice = st.selectbox("Portfolio risk notice", list(ports))
    port = ports[choice]
    st.table(
        pd.DataFrame(
            [
                {
                    "Horizon (sessions)": n["horizon"],
                    "Reference risk over horizon (%)": round(100 * n["horizon_rms"], 2)
                    if n["horizon_rms"] is not None
                    else None,
                    "Observed sessions": n["n"],
                }
                for n in port["notices"]
            ]
        )
    )
    st.caption(
        f"Joint conditional shock on CHF 35,000: CHF {port['joint_chf']:,.0f}. Risk estimates use the current portfolio weights and a 63-session historical variance."
    )
