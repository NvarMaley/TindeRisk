import streamlit as st

from src.portfolio_catalogue import profile_volatility_preview

st.title("🍽️ Portfolio Menu")
st.write(
    "Compare strategies prepared for your risk category. Every validated card will use "
    "the same reference risk, historical period, and cost assumptions."
)

risk_band = st.session_state.get("risk_band")
profile = st.session_state.get("profile")
estimates = {}
if risk_band is None:
    st.info("Complete the Profile page first. No category has been assigned yet.")
else:
    st.success(f"Your category: {risk_band}")
    if profile:
        try:
            date, estimates = profile_volatility_preview(profile, risk_band)
        except RuntimeError:
            st.info("The optimizer could not produce a valid allocation for these inputs.")
        except (OSError, ValueError):
            st.info("Portfolio risk estimates are unavailable. Check the prepared portfolio data.")
        else:
            st.caption(f"Portfolio risk estimates as of {date:%d %B %Y}, using your investment constraints.")

strategies = {
    "classic": ("Classic",
        "Balances estimated risk and return.",
        "Sensitive to expected-return estimates.",
    ),
    "erc": ("Balanced (ERC)",
        "Diversifies risk contributions without forecasting returns.",
        "May allocate heavily to lower-volatility assets.",
    ),
    "black_litterman": ("Connected (BL)",
        "Combines a strategic prior with documented market views.",
        "Depends on the validity and confidence of those views.",
    ),
    "benchmark_60_40": ("60/40 benchmark",
        "Simple, transparent, and easy to explain.",
        "A fixed capital split does not guarantee diversified risk.",
    ),
}

for strategy, (title, advantage, limitation) in strategies.items():
    with st.container(border=True):
        st.subheader(title)
        if strategy in estimates:
            estimate = estimates[strategy]
            if estimate is None:
                st.info("Your exclusions leave no eligible ETF for this strategy.")
            else:
                allocation = estimate.allocation
                estimate_col, reference_col = st.columns(2)
                estimate_col.metric("Estimated annual volatility", f"{allocation.achieved_volatility:.2%}",
                                    delta=f"{100 * estimate.reference_gap:+.2f} pp vs reference",
                                    delta_color="off")
                reference_col.metric("Category reference", f"{estimate.band.reference_volatility:.2%}")
                band = estimate.band
                st.caption(f"{estimate.band_position.capitalize()} the category range "
                           f"of {band.min_volatility:.0%}–{band.max_volatility:.0%}.")
                if allocation.cash_weight < -1e-9:
                    st.caption(f"Borrowed cash: {-allocation.cash_weight:.1%} of portfolio capital.")
        columns = st.columns(5)
        labels = [
            "Historical return",
            "Realized risk",
            "Net Sharpe",
            "Max drawdown",
            "Annual cost",
        ]
        for column, label in zip(columns, labels, strict=True):
            column.metric(label, "—")
        st.write(f"✅ **Advantage:** {advantage}")
        st.write(f"⚠️ **Limitation:** {limitation}")

st.caption(
    "Historical metrics await validated backtest results. "
    "Historical results are not forecasts, and no strategy is universally best."
)
