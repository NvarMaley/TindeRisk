"""Client-facing exploration of the frozen section 6.2 example."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="RiskMatch · Portfolio options", layout="wide")
DATA = Path(__file__).resolve().parents[2] / "research/options/results"


@st.cache_data
def table(name):
    return pd.read_csv(DATA / (name + ".csv"))


names = {
    "cash": "CHF cash",
    "60/40": "60/40 shares and bonds",
    "classical": "Maximum estimated net return",
    "robust": "Return adjusted for estimation uncertainty",
    "equal weight": "Equal ETF weights",
    "risk parity": "Equal risk contributions",
    "risky minimum variance": "Minimum-risk ETF mix",
    "concentration-aware GMV": "Minimum-risk mix with concentration cap",
}
st.title("Portfolio options")
st.write("Illustrative CHF household · 30 October 2026")
st.write(
    "Of CHF 50,000, CHF 15,000 is reserved for a payment in one year. Compare ways to invest the remaining CHF 35,000. The example assumes a goal of CHF 65,000 in today's purchasing power in eight years."
)
cap = st.radio(
    "Annual volatility limit on the investable CHF 35,000",
    [0.08, 0.04],
    format_func=lambda x: f"{x:.0%}",
    horizontal=True,
)
options = table("options").query("cap == @cap").set_index("arm")
goal = table("goal_scenarios").query("cap == @cap")
overview = options[
    [
        "historical_household_mean",
        "monthly_p10",
        "monthly_p90",
        "joint_shock_pnl_chf",
        "entry_fee_chf",
    ]
].copy()
overview = overview.join(
    goal.query("scenario == 'base'").set_index("arm").gap_frequency
)
overview.index = overview.index.map(names)
overview.columns = [
    "Historical annual mean",
    "Next month · low",
    "Next month · high",
    "Joint shock CHF",
    "Entry fees CHF",
    "Goal missed in paths",
]
st.dataframe(
    overview.style.format(
        {
            k: "{:.2%}"
            for k in [
                "Historical annual mean",
                "Next month · low",
                "Next month · high",
                "Goal missed in paths",
            ]
        }
        | {"Joint shock CHF": "{:,.0f}", "Entry fees CHF": "{:,.2f}"}
    )
)
st.caption(
    "Historical means cover seven separate annual household outcomes. The next-month range uses the middle 80% of the preceding 36 monthly observations. The joint shock combines a 10% equity fall, a 1-point nominal yield rise, a 0.5-point rise in breakeven inflation and a 5% USD fall. Goal frequencies come from 2,000 simulated paths."
)
arm = st.selectbox(
    "Explore an allocation",
    options.index.tolist(),
    index=options.index.tolist().index("60/40"),
    format_func=names.get,
)
r = options.loc[arm]
st.subheader(names[arm])
sharpe = f"{r.sharpe:.2f}" if pd.notna(r.sharpe) else "undefined at zero volatility"
st.write(
    f"Annual household estimates · net return {r.annual_household_mean:.2%}, volatility {r.annual_household_vol:.2%}, Sharpe versus CHF cash at zero interest {sharpe}."
)
st.write(
    f"SPY shares CHF {r.SPY_chf:,.0f} · IEF Treasuries CHF {r.IEF_chf:,.0f} · GLD gold CHF {r.GLD_chf:,.0f}. "
    f"Additional liquid CHF {r.available_sleeve_cash:,.0f}. Modeled entry fees CHF {r.entry_fee_chf:,.2f}. The separate CHF 15,000 reserve is accessible at par."
)
st.write(
    f"Across seven historical years, household returns ranged from {r.historical_household_min:.1%} to {r.historical_household_max:.1%}. "
    f"The one-month range contained the subsequent outcome in {int(r.coverage_hits)} of {int(r.coverage_count)} earlier decisions."
)
st.write(
    f"Applying the worst observed joint month to these holdings gives CHF {r.worst_month_pnl_chf:,.0f}"
    + (f" ({r.worst_month})." if pd.notna(r.worst_month) else ".")
)
st.subheader("Goal funding")
labels = {
    "base": "8 years · CHF 100/month · 2% inflation",
    "save CHF 250": "Save CHF 250 each month",
    "10 years": "Extend the goal to 10 years",
    "CHF 55,000 goal": "Lower the real target to CHF 55,000",
    "zero inflation": "0% inflation",
    "4% inflation": "4% inflation",
    "reversed years": "Reverse the order of the sampled years",
}
scenario = st.selectbox("Funding assumption", list(labels), format_func=labels.get)
g = goal[(goal.arm == arm) & (goal.scenario == scenario)].iloc[0]
cols = st.columns(3)
cols[0].metric("Goal at the due date", f"CHF {g.nominal_target:,.0f}")
cols[1].metric("Median available after sale", f"CHF {g.median_chf:,.0f}")
cols[2].metric("Paths below goal", f"{g.gap_frequency:.1%}")
st.write(
    f"Across the simulated paths the mean shortfall is CHF {g.mean_gap_chf:,.0f}. Among paths that miss, it is CHF {g.mean_gap_when_short_chf:,.0f}."
    if g.gap_frequency
    else "All simulated paths fund this target."
)
st.caption(
    "Simulations draw joint 12-month blocks of ETF returns and USD/CHF. Deposits stay in CHF until annual rebalancing. Trades and final sales cost 0.10% of traded amounts. These frequencies depend on the historical sample."
)
with st.expander("Base funding path and zero-return calculation"):
    path = table("funding_path").query("arm == @arm and cap == @cap")
    st.write(
        "Base case · available goal money after modeled sale costs, excluding the protected withdrawal (nominal CHF)"
    )
    st.line_chart(path.set_index("date")[["p10", "median", "p90"]])
    a = table("goal_adjustments").query("arm == @arm and cap == @cap").iloc[0]
    st.write(
        f"With zero market growth and 2% inflation, the eight-year goal requires CHF {a.monthly_chf_needed:,.2f} each month. Saving CHF 100 supports a target of CHF {a.affordable_real_target:,.0f} in today's money."
    )
with st.expander("Withdrawal and settlement"):
    for case in (
        table("reverse_stress").query("arm == @arm and cap == @cap").itertuples()
    ):
        st.write(
            f"{case.case.capitalize()} · CHF {case.bill:,.0f} due · {case.status}"
            + (
                f" at a simultaneous {case.loss_boundary:.1%} loss on all ETF positions."
                if pd.notna(case.loss_boundary)
                else "."
            )
            + (
                f" Initial gap CHF {case.initial_shortfall:,.0f}."
                if case.initial_shortfall
                else ""
            )
        )
    st.caption(
        "At one year the stress assumes flat markets before the shock and settled sales after costs. The accelerated payment is due immediately after investment, before ETF sales settle."
    )
st.subheader("Risk preference comparison")
profiles = json.loads((DATA / "design.json").read_text())["profiles"]
profile_name = st.selectbox(
    "Hypothetical card responses", [p["case"] for p in profiles]
)
profile = next(p for p in profiles if p["case"] == profile_name)
other = st.selectbox(
    "Compare with", options.index.drop(arm).tolist(), format_func=names.get
)
if profile["status"] == "bounded":
    basis = st.radio(
        "Wealth used for the annual score", ["household", "sleeve"], horizontal=True
    )
    pct = table("pairwise").query("cap == @cap and basis == @basis")
    q = pct[
        ((pct["first"] == arm) & (pct.second == other))
        | ((pct["first"] == other) & (pct.second == arm))
    ].iloc[0]
    order = [names[q["first"]], names[q.second]]
    verdict = {
        "first throughout": order[0]
        + " has the higher modeled score throughout the interval.",
        "second throughout": order[1]
        + " has the higher modeled score throughout the interval.",
        "numerical tie": "The modeled scores coincide within numerical tolerance.",
        "crossover": f"The modeled ordering switches at φ = {q.crossover:.2f}.",
        "tie at endpoint": "The two modeled scores meet at an endpoint.",
    }
    st.write(
        f"The card choices imply φ between {profile['low']:.2f} and {profile['high']:.2f}. "
        + verdict[q.result]
    )
    if basis == "household":
        history = table("ranking_history")
        matched = history[
            (history.cap == cap)
            & (history["first"] == q["first"])
            & (history.second == q.second)
        ].iloc[0]
        if matched.estimated != matched.historical:
            st.info(
                "The ordering changes when the same score uses the seven historical annual outcomes. The evidence leaves the choice open."
            )
        else:
            st.caption(
                "The ordering agrees with the score calculated from the seven historical annual outcomes."
            )
    st.caption(
        "The cards use a hypothetical CHF 1,000 stake. Dropping either of the two choices leaves a one-sided interval. Transfer to this household is unverified. The comparison is conditional on the displayed model."
    )
else:
    st.info(
        "These answers leave risk preference unresolved. Both allocations remain available to compare."
    )
if st.button("Keep this example choice for this session"):
    st.session_state["example_option_choice"] = (names[arm], cap)
if "example_option_choice" in st.session_state:
    title, limit = st.session_state["example_option_choice"]
    st.write(f"Your saved example choice · {title}, {limit:.0%} sleeve risk limit.")
