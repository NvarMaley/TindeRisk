"""Run with streamlit run app/intake.py."""

from copy import deepcopy
from datetime import date
from pathlib import Path
import sys

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from riskmatch.intake import evaluate

st.set_page_config(page_title="RiskMatch · Your goal")
state = st.session_state
if "mandate" not in state:
    state.mandate = {"start": date.today(), "flows": [], "basis": "Future amount"}
    state.page = 0
    state.history = []
    state.next_flow = 0
d = state.mandate
before = deepcopy(d)
pages = [
    "Your goal",
    "Resources",
    "Protected money",
    "Expectations and preferences",
    "Your mandate",
    "Your risk interview",
]
page = state.page
st.title(pages[page])
if page < 4:
    st.caption(f"Step {page + 1} of 4")
    st.caption(
        "For amounts and rates, enter a number or a range such as 10000..15000. Use ? for unknown, pass to decline, or leave blank to answer later."
    )


def text(key, title, help=None):
    d[key] = st.text_input(title, d.get(key, ""), key="input_" + key, help=help)


def select(key, title, choices):
    val = d.get(key)
    chosen = st.selectbox(
        title,
        choices,
        index=choices.index(val) if val in choices else None,
        key="input_" + key,
    )
    d[key] = chosen


def day_field(key, title):
    d[key] = st.date_input(
        title,
        value=d.get(key),
        min_value=date(1900, 1, 1),
        max_value=date(2200, 12, 31),
        key="input_" + key,
    )


def cash_rows(kind, label):
    st.subheader(label)
    removed = None
    for row in [r for r in d["flows"] if r["kind"] == kind]:
        k = str(row["id"])
        with st.container(border=True):
            row["day"] = st.date_input(
                "Settlement date",
                value=row["day"],
                min_value=date(1900, 1, 1),
                max_value=date(2200, 12, 31),
                key="day" + k,
            )
            row["amount"] = st.text_input("Amount", row["amount"], key="amount" + k)
            if kind != "withdrawal":
                row["confirmed"] = st.checkbox(
                    "Confirmed and available on this date",
                    row["confirmed"],
                    key="conf" + k,
                )
            if st.button("Remove", key="remove" + k):
                removed = row
    if removed is not None:
        d["flows"].remove(removed)
        record()
        st.rerun()
    if st.button("Add " + kind):
        d["flows"].append(
            dict(id=state.next_flow, kind=kind, day=None, amount="", confirmed=False)
        )
        state.next_flow += 1
        record()
        st.rerun()


def record():
    if d != before:
        state.history.append(
            {"step": pages[page], "before": before, "after": deepcopy(d)}
        )


def load_demo_mandate():
    from riskmatch.demo import mandate

    state.mandate = mandate()
    state.next_flow = 1
    state.portable_case = True
    for key in list(state):
        if key.startswith(("input_", "day", "amount", "conf")) or key in (
            "monitor_selection",
            "demo_profile",
        ):
            state.pop(key, None)

    for field in ("goal", "currency", "start", "end", "target", "basis"):
        state["input_" + field] = state.mandate[field]


if page == 0:
    if not d.get("goal"):
        st.button("Load fictional course mandate", on_click=load_demo_mandate)
    text("goal", "What are you saving for?")
    select("currency", "Spending currency", ["CHF", "EUR", "USD", "GBP", "Other"])
    if d.get("currency") == "Other":
        text("currency_name", "Currency name or code")
    day_field("start", "Plan start")
    day_field("end", "Goal date")
    select(
        "flexibility",
        "Can the goal date move?",
        ["Fixed", "Flexible", "Unknown", "Prefer not to answer"],
    )
    text(
        "target",
        "Goal amount",
        "Amount needed at the goal date, in addition to protected withdrawals and emergency cash.",
    )
    select(
        "basis",
        "Goal amount expressed in",
        ["Future amount", "Today's purchasing power"],
    )
    if d.get("basis") == "Today's purchasing power":
        text(
            "inflation",
            "Annual inflation assumption (%)",
            "Enter a range to see how purchasing power changes the required return.",
        )
elif page == 1:
    text(
        "capital",
        "Starting capital",
        "Include only money already available at the plan start.",
    )
    st.caption(
        "Enter each future deposit once, on the date the money will be available. Only confirmed deposits enter the calculation."
    )
    cash_rows("goal deposit", "Deposits for the final goal")
    select(
        "goal_list",
        "Goal deposit schedule",
        ["Complete", "Unknown", "Prefer not to answer"],
    )
elif page == 2:
    text(
        "buffer",
        "Emergency cash to keep available",
        "Enter 0 if the reserve is fully held elsewhere.",
    )
    cash_rows("withdrawal", "Payments due before or on the goal date")
    st.caption(
        "For funding on a payment date, use that date only if the money settles before the bill is due. Enter future money earmarked for these payments. Exclude amounts already in starting capital or entered as goal deposits. Excess earmarked cash stays outside the final goal."
    )
    cash_rows("bill funding", "External funding for these payments")
    select(
        "bill_list",
        "Withdrawal and funding schedule",
        ["Complete", "Unknown", "Prefer not to answer"],
    )
elif page == 3:
    text("desired", "Desired annual nominal return (%)")
    text(
        "exclusions",
        "Investments to exclude",
        "Hard limits that any future allocation must respect.",
    )
    text(
        "preferences",
        "Investment preferences",
        "Preferences to consider among eligible investments.",
    )
elif page == 5:
    from profile_ui import interview

    interview(d)
    st.stop()
else:
    result = evaluate(d)
    ccy = (
        d.get("currency_name", "")
        if d.get("currency") == "Other"
        else d.get("currency") or ""
    )
    st.write(
        d.get("goal") or "Goal pending",
        "·",
        ccy,
        "·",
        d.get("end") or "Goal date pending",
    )
    for k, msg in result["issues"].items():
        st.error(f"{k}: {msg}")
    if result["capacity"]:
        for case, title in zip(
            result["capacity"], ["Lower funding need", "Higher funding need"]
        ):
            with st.expander(title, expanded=True):
                st.write(
                    f"Protected today: {case['protected']:,.2f} {ccy} · Available to invest: {case['investable']:,.2f} {ccy}"
                )
                if case["shortfall"]:
                    st.warning(
                        f"Funding shortfall: {case['shortfall']:,.2f} {ccy}. First affected date: {case['first_shortfall']}."
                    )
                st.dataframe(case["rows"], hide_index=True)
        delayed = result["delayed"]
        st.write(
            f"If confirmed bill funding settles 30 days later, the higher-need scenario requires {delayed['required']:,.2f} {ccy} in opening reserves."
        )
    else:
        st.info(
            "To estimate your reserve, complete the currency, start date, capital, emergency cash and dated payment schedule."
        )
    st.write("Desired annual return (%)", d.get("desired") or "Unanswered")
    if result["rates"]:
        for case, title in zip(
            result["rates"], ["Lower funding need", "Higher funding need"]
        ):
            desc = (
                f"{case['rate']:.2%} per year"
                if case["status"] == "solved"
                else case["status"]
            )
            st.write(f"Required return · {title}: {desc}")
    else:
        st.info(
            "The required return also needs a goal date, a target, a complete deposit schedule and any applicable inflation assumption."
        )
    st.caption(
        "Required returns use actual days / 365, annual compounding and zero interest on protected cash. A calculated rate is a funding requirement."
    )
    st.write("Hard exclusions", d.get("exclusions") or "Unanswered")
    st.write("Preferences", d.get("preferences") or "Unanswered")
    with st.expander("Review answers and corrections for this session"):
        st.json({"answers": d, "changes": state.history}, expanded=False)

page_fields = [{"end", "target", "inflation"}, {"capital"}, {"buffer"}, {"desired"}]
if page in (1, 2):
    for index, row in enumerate(d["flows"], 1):
        if (row["kind"] == "goal deposit") == (page == 1):
            page_fields[page].update({f"Flow {index} amount", f"Flow {index} date"})
issues = (
    {
        key: message
        for key, message in evaluate(d)["issues"].items()
        if key in page_fields[page]
    }
    if page < 4
    else {}
)
if page < 4:
    for k, msg in issues.items():
        st.error(f"{k}: {msg}")
record()
a, b = st.columns(2)
if page and a.button("Back"):
    state.page -= 1
    st.rerun()
if page < 4 and b.button("Review mandate" if page == 3 else "Continue", type="primary"):
    if not issues:
        state.page += 1
        st.rerun()

if page == 4 and b.button("Open risk interview", type="primary"):
    state.page = 5
    st.rerun()
