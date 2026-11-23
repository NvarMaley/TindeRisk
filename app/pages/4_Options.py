"""Comparable historical options and multi-portfolio combinations."""

import json
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/06-options"
result = json.loads((REPORT / "resultats.json").read_bytes())
cfg = json.loads((ROOT / "config/options-6.json").read_bytes())
st.set_page_config(page_title="Options · RiskMatch", page_icon="🍒", layout="wide")
st.title("Compare my options")
if (ROOT/"reports/univers-complet/resultats.json").is_file():
    scope=st.radio("Comparison universe",["All selected assets","Environmental mandate study","Forecast evidence","Control study · 13 ETFs"],horizontal=True)
    if scope=="Forecast evidence":
        from riskmatch_v2.forecast.ui import render
        render(ROOT)
        st.stop()
    if scope=="Environmental mandate study":
        from riskmatch_v2.environment.ui import render
        render(ROOT)
        st.stop()
    if scope=="All selected assets":
        from riskmatch_v2.universe.ui import render
        render(ROOT)
        st.stop()
st.caption(
    "Simulation in CHF · capital of 50,000 CHF including 15,000 CHF protected · estimate as at 30 October 2026"
)
st.info(
    f"Account of 23 November 2026 · {result['admission']['eligible']} eligible instrument. The options below are historical simulations."
)
session = st.session_state.get("interview")
preferred = "Goal"
if session and session.versions:
    last = session.versions[-1]
    declared = last["portrait"]["preferences"].get("P06") or []
    if any(row["priority"] == "high" for row in declared):
        preferred = "Diversification"
        st.caption(
            "card P06 indicates a high priority for diversification. You can confirm or modify the priority of this simulation."
        )
profile = st.radio(
    "Comparison priority",
    list(cfg["profiles"]),
    index=list(cfg["profiles"]).index(preferred),
    horizontal=True,
)
cards = result["cards"]
aliases = result["aliases"]
local = (ROOT / "data/local/4" / cfg["catalogue"] / "prices.parquet").is_file()
desk = None
if local:
    try:
        import numpy as np
        from riskmatch_v2.options.desk import research_desk
        from riskmatch_v2.options.compare import mix_search
        from riskmatch_v2.options.study import blended_card
    except ImportError:
        local = False
from riskmatch_v2.options.scoring import rank

if local:

    @st.cache_resource(show_spinner=False)
    def load_desk(low, high, excluded, snapshot):
        return research_desk(low, high, excluded, result)

    with st.expander("Addressing Risk Demand and Exclusions"):
        with st.form("mandat"):
            low = st.number_input(
                "Minimum investment sleeve volatility (%)", 0.0, 150.0, 0.0, 0.5
            )
            high = st.number_input(
                "Maximum investment sleeve volatility (%)", 0.0, 150.0, 12.0, 0.5
            )
            excluded = st.multiselect(
                "Excluded funds", list(next(iter(cards.values()))["weights"])
            )
            if st.form_submit_button("Applying my mandate"):
                st.session_state["options_request"] = (low, high, tuple(excluded))
    low, high, excluded = st.session_state.get("options_request", (0.0, 12.0, ()))
    if low > high:
        st.error("The low bound exceeds the ceiling.")
        st.stop()
    # The published desk already contains the common reference replay.
    if low or high != 12.0 or excluded:
        with st.spinner("Calculation of variants and annual replay..."):
            desk = load_desk(low / 100, high / 100, excluded, result["snapshot"])
        if "reason" in desk:
            st.write(f"{desk['status']} · {desk['reason']}")
            st.stop()
        cards, aliases = desk["cards"], desk["aliases"]
        skipped = {n: len(days) for n, days in desk["unavailable"].items() if days}
        if skipped:
            st.caption(
                f"Annual decisions without target available, weight retained · {skipped}"
            )
    st.caption(f"Terms of reference considered {low:g} to {high:g} % volatility")
scoring = rank(
    {n: c for n, c in cards.items() if n not in aliases},
    cfg["profiles"][profile],
    cfg,
    research=True,
)
rows = []
for n, c in cards.items():
    if n in aliases:
        continue
    r = scoring["rows"].get(n, {})
    rows.append(
        {
            "Option": n,
            "Estimated return (%)": 100 * c["net"],
            "Estimated volatility (%)": 100 * c["vol"],
            "Annualized net history (%)": 100 * c["cagr"],
            "Loss of scenario (%)": 100 * c["loss"],
            "Score / 100": r.get("total"),
            "Groupe": r.get("group"),
            "Statut": "In the mandate" if c["valid"] else "Non-mandate",
        }
    )
st.dataframe(pd.DataFrame(rows).round(2), hide_index=True)
st.caption(
    f"Historical grid · {scoring['coverage']} % of documented weights. Two tolerance points between scores. A loss of negative scenario is a gain."
)
with st.expander("Availability of forecasts at 12 months"):
    st.table(pd.Series(result["signal_status"], name="Validation by family"))
if aliases:
    st.caption(f"Options grouped according to their weight · {aliases}")
name = st.selectbox("Examine an option", [r["Option"] for r in rows])
c = cards[name]
st.bar_chart(pd.Series(c["weights"]) * 100, y_label="Weight of investment sleeve (%)")
if name in scoring["rows"]:
    st.dataframe(
        pd.DataFrame(
            {
                "Sous-score": scoring["rows"][name]["subscores"],
                "Weight (%)": {k: 100 * v for k, v in scoring["weights"].items()},
                "Contribution": scoring["rows"][name]["contributions"],
            }
        ).round(2)
    )
st.caption(
    f"Cash after costs {c['cash']:.2%} · initial costs {cfg['pocket'] * c['fee']:.2f} CHF · return according to the three models {c['interval'][0]:.2%} to {c['interval'][1]:.2%}."
)
st.subheader("Compose multiple portfolios")
if not local:
    label = st.selectbox("Calculated mixtures", list(result["mixes"]))
    mix = result["mixes"][label]
else:
    choices = list(scoring["rows"])
    selected = st.multiselect(
        "Options to combine", choices, default=choices[: min(2, len(choices))]
    )
    if not selected:
        st.info("Select at least one option.")
        st.stop()
    with st.form("parts"):
        criterion = st.selectbox(
            "Choice of shares", ["Manual", "Return", "Minimum risk", "Sharpe"]
        )
        parts = [
            st.number_input(
                "Share (%) · " + n,
                0.0,
                100.0,
                float(100 / len(selected)),
                key="share_" + n,
            )
            for n in selected
        ]
        floor = st.number_input(
            "Minimum share per option for research (%)", 0.0, 100.0, 0.0, step=1.0
        )
        submit = st.form_submit_button("Evaluate mixture")
    if not submit:
        st.stop()
    if criterion == "Manual" and abs(sum(parts) - 100) > 1e-6:
        st.error("The shares must total 100%.")
        st.stop()
    with st.spinner("Verification of shares, orders and replay..."):
        if desk is None:
            desk = load_desk(0.0, 0.12, (), result["snapshot"])
        shares = np.array(parts) / 100
        try:
            if criterion != "Manual":
                search = mix_search(
                    desk["models"],
                    [desk["targets"][n] for n in selected],
                    criterion=criterion,
                    low=low / 100,
                    high=high / 100,
                    minimum=floor / 100,
                )
                st.write(search["status"].capitalize())
                if "parts" not in search:
                    st.stop()
                shares = search["parts"]
            mix = blended_card(
                desk["models"],
                desk["targets"],
                selected,
                shares,
                desk["plans"],
                desk["tape"],
                desk["shock"],
                desk["cfg"],
            )
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
c = mix["card"]
st.write(" · ".join(f"{k} {v:.1%}" for k, v in mix["parts"].items()))
if not c["valid"]:
    st.warning(
        "The mix comes out of the warrant. The nearest eligible option by weight: "
        + str(mix["alternative"])
    )
else:
    st.write(
        f"Estimated return {c['net']:.2%} · volatility {c['vol']:.2%} · annualized net history {c['cagr']:.2%}"
    )
    grid = rank({"mix": c}, cfg["profiles"][profile], cfg, research=True)
    st.write(
        f"Search score {grid['rows']['mix']['total']:.1f}/100 · {mix['rounding']['status']}"
    )
    st.bar_chart(pd.Series(c["weights"]) * 100, y_label="Aggregate weight (%)")
    rounded = mix["rounding"].get("indicators")
    if rounded:
        st.caption(
            f"Score after rounding {mix['rounding']['scores'][profile]:.1f}/100 · simulated whole shares · risk {rounded['vol']:.2%} · fees {cfg['pocket'] * rounded['fee']:.2f} CHF · External reserve {cfg['reserve']:,.0f} CHF."
        )
