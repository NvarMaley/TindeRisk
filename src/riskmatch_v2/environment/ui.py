"""Published mandate comparisons for the multi-asset research desk."""

import json

import pandas as pd
import streamlit as st


def render(root):
    folder = root / "reports/11-environment"
    result = json.loads((folder / "results.json").read_text())
    labels = [pair["criterion"] for pair in result["pairs"]]
    label = st.radio("Confirmed research mandate", labels, horizontal=True)
    pair = result["pairs"][labels.index(label)]
    st.caption(
        "CHF 35,000 · October 2026 market estimates · issuer review on 23 November 2026"
    )
    if label == "Chevron exclusion":
        st.write(
            "Exclude Chevron in direct stocks and fund holdings. Suspend positions with unidentified issuers."
        )
    else:
        st.write(
            "Invest CHF 21,000 in measured stocks and seek a 20% reduction in US point-source emissions per USD million of revenue."
        )
    rows = []
    for role in ["reference", "variant"]:
        r = pair[role]
        rows.append(
            {
                "Portfolio": role.title(),
                "Annual net estimate (%)": r["net"] * 100,
                "Volatility (%)": r["risk"] * 100,
                "Entry fee (CHF)": r["fee_chf"],
                "Unidentified issuers (%)": r["unknown_gross"] * 100,
                "Carbon coverage (%)": r["covered"] * 100,
                "Measured intensity (tCO₂e/USD m)": r["intensity"],
            }
        )
    st.dataframe(pd.DataFrame(rows).round(2), hide_index=True)
    st.caption(
        f"Carbon comparison · {pair['intensity_comparison']}. Coverage is a percentage of the full CHF capital."
    )
    st.image(
        str(
            folder
            / (
                "issuer-coverage.png"
                if label == "Chevron exclusion"
                else "mandate-comparison.png"
            )
        )
    )
