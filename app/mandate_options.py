"""Apply the dated full-universe research estimates to a confirmed CHF cash ladder."""

import json
import re
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
from riskmatch.intake import evaluate
from riskmatch.universe import ASSETS


def show(root, draft):
    st.header("Your CHF allocation")
    if draft.get("currency") != "CHF":
        st.info(
            "These estimates use CHF. A spending-currency model is required for this mandate."
        )
        return
    result = evaluate(draft)
    if result["issues"] or not result["capacity"]:
        st.info(
            "Complete the dated payment schedule and correct outstanding mandate fields."
        )
        return
    budget = result["capacity"][1]
    st.write(
        f"Protected CHF {budget['protected']:,.2f} · investable CHF {budget['investable']:,.2f}."
    )
    if budget["shortfall"] > 0 or budget["investable"] <= 0:
        st.info(
            f"Funding shortfall CHF {budget['shortfall']:,.2f}. No funds available for ETFs."
        )
        return
    try:
        from research.frontier.engine import Frontier
    except ModuleNotFoundError:
        st.info(
            "The research optimizer requires the packages in requirements-frontier.txt."
        )
        return
    known = draft.get("exclusions", "").strip()
    exclusions = (
        []
        if known.lower() in ("", "none", "aucune", "aucun")
        else re.split(r"[,;\s]+", known.upper())
    )
    if set(exclusions) - set(ASSETS):
        st.warning(
            "Your written exclusion requires a holdings-level review. Allocation suspended."
        )
        return
    selected = st.multiselect(
        "Additional ETF exclusions", [a for a in ASSETS if a not in exclusions]
    )
    cap = st.select_slider(
        "Annual volatility ceiling on investable funds",
        [0.0, 0.04, 0.08, 0.12, 0.16],
        value=0.08,
        format_func=lambda x: f"{x:.0%}",
    )
    folder = root / "research/universe/results/frontier"
    records = json.loads((folder / "training.json").read_text())
    past = [r for r in records if date.fromisoformat(r["origin"]) <= draft["start"]]
    if not past:
        st.info("No archived estimates predate the start of this mandate.")
        return
    r = past[-1]
    screen = (
        pd.read_csv(folder / "eligibility.csv")
        .query("scenario == 'base'")
        .set_index(["origin", "asset"])
    )
    mask = [
        bool(screen.at[(r["origin"], a), "eligible"]) and a not in exclusions + selected
        for a in ASSETS
    ]
    method = st.selectbox("Allocation objective", ["robust", "classical"])
    model = Frontier(
        np.array(r["annual_mean"]),
        np.array(r["covariance"]),
        np.array(r["mean_uncertainty"]),
        mask,
    )
    solution = model.solve(cap, float(method == "robust"))
    if solution["status"] not in {"optimal", "optimal_inaccurate", "exact cash"}:
        st.warning("No verified feasible allocation under these limits.")
        return
    sleeve = budget["investable"]
    st.caption(
        f"Research snapshot {r['origin']}. This calculation uses the adverse cash-ladder estimate and your chosen ceiling. Your interview and soft preferences do not set this ceiling automatically."
    )
    st.table(
        pd.DataFrame(
            {
                "ETF": ASSETS,
                "Eligible": mask,
                "Allocation CHF": [
                    round(sleeve * solution[f"w{i}"], 2) for i in range(len(ASSETS))
                ],
            }
        )
    )
    st.write(
        f"Modeled entry fees CHF {sleeve * solution['fee']:,.2f} · remaining cash CHF {sleeve * solution['cash']:,.2f}. Estimated annual sleeve return {solution['net_mean']:.2%}, volatility {solution['vol']:.2%}."
    )
