"""Streamlit view for a confirmed portrait and its annual risk request."""
import streamlit as st

from riskmatch_v2.risk_review import POLICY, assess, band_at, centered_target, request, suggested


LABELS = {"minimum": "Minimum risk", "cap": "Volatility cap", "target_band": "Target range",
          "unknown": "I remain undecided"}


def number(x):
    return f"{x:,.2f}".removesuffix(".00")


def span(bounds, scale=1):
    if bounds is None:
        return "undetermined"
    a, b = (number(bounds[k] * scale) for k in ("low", "high"))
    return a if a == b else f"{a} to {b}"


def describe(r):
    label = LABELS[r["mode"]]
    if r["mode"] == "cap":
        label += f" of {number(r['high']*100)}%"
    if r["mode"] == "target_band":
        high = r["high"]
        label += f" from {number(r['low']*100)}%"
        if high is not None:
            label += f" to {number(high*100)}% " + ("(exclusive)" if r["high_exclusive"] else "(inclusive)")
    return f"{label} · CHF {r['basis']}"


def show_risk(interview, on_save=None):
    snapshot = interview.versions[-1]
    initial, reason = suggested(snapshot["portrait"])
    previous = snapshot.get("risk_review")
    selection = previous["choice"] if previous else initial
    prefix = f"risk-{snapshot.get('portrait_version', snapshot['version'])}"
    st.subheader("What annual volatility do you accept?")
    st.caption("Volatility measures the dispersion of returns. A ceiling allows for any lower level. A target band also has a minimum to reach.")
    st.write("Proposed starting point · " + describe(initial))
    st.caption(reason)
    with st.expander("Annual volatility marks of the investment sleeve in CHF"):
        for b in POLICY["bands"]:
            end = f"less than {number(100*b['high'])}%" if b["high"] is not None else "and beyond"
            st.write(f"{b['label']} · from {number(100*b['low'])} % {end}")
    mode = st.selectbox("Your request", list(LABELS), index=list(LABELS).index(selection["mode"]),
                        format_func=LABELS.get, key=prefix+"mode")
    basis = st.radio("Apply the risk limit to", ["investment sleeve","household"], horizontal=True,
                     index=int(selection["basis"] == "household"), key=prefix+"base")
    try:
        if mode == "cap":
            pct = st.number_input("Annual ceiling (%)", min_value=0., value=selection["high"]*100 if selection["high"] is not None else None,
                                  key=prefix+"cap")
            choice = request(mode, basis, ceiling_pct=pct)
        elif mode == "target_band":
            formats = ["Two bounds", "Centre and margin"]
            if basis == "investment sleeve":
                formats.append("Designated range")
            method = st.radio("How to specify the target range", formats, index=2 if selection["band"] and basis=="investment sleeve" else 0,
                              horizontal=True, key=prefix+"method"+basis)
            if method == "Designated range":
                labels = [b["label"] for b in POLICY["bands"]]
                band = st.selectbox("Benchmark", labels, index=labels.index(selection["band"]) if selection["band"] else None,
                                    key=prefix+"band")
                choice = request(mode, basis, band=band)
            elif method == "Centre and margin":
                center = st.number_input("Target (%)", min_value=0., value=None, key=prefix+"centre")
                margin = st.number_input("Margin (percentage points)", min_value=0., value=None, key=prefix+"marge")
                choice = centered_target(basis, center, margin)
            else:
                low = st.number_input("Lower bound (%)", min_value=0., value=None if selection["low"] is None else selection["low"]*100, key=prefix+"low")
                high = st.number_input("Upper bound (%)", min_value=0., value=None if selection["high"] is None else selection["high"]*100, key=prefix+"high")
                choice = request(mode, basis, low_pct=low, high_pct=high)
        else:
            choice = request(mode, basis)
    except ValueError as error:
        st.info(str(error))
        return
    st.write("Review your request · " + describe(choice))
    if basis == "investment sleeve" and choice["high"] is not None and not choice["band"]:
        st.caption(f"Benchmark at the upper end of your application · {band_at(choice['high'])}.")
    preview = assess(snapshot, choice, accept=False, bills="unknown", comfort="unknown")
    other = preview["equivalent"]
    if other:
        translated = choice | other | {"band": None}
        st.caption("Equivalent with nominal fixed reserve · " + describe(translated))
    st.markdown("**If the investment sleeve would drop...**")
    st.caption("Two hypothetical independent shocks applied to the initial capital. The CHF reserve keeps its nominal value.")
    for row in preview["stresses"]:
        st.write(f"At {row['months']} months · decrease in {number(100*row['loss_fraction'])} % on the investment sleeve · "
                 f"loss of {span(row['loss_chf'])} CHF · share of initial household capital (%): {span(row['household_fraction'],100)}.")
    if not preview["stresses"]:
        st.info("Specify the amounts and flows of the portrait to calculate these scenarios.")
    if preview["dated_cash"]:
        with st.expander("Cash available on each date"):
            st.caption("Assumption of calculation · invest the lower end of the investment sleeve at the start and keep the rest in CHF.")
            for row in preview["dated_cash"]:
                st.write(f"{row['date']} · {row['phase']} · {span(row['cash_chf'])} CHF")
    for message in preview["reasons"]:
        st.write(message)
    responses = ["unknown", "yes", "no"]
    # Re-ask for explicit consent when the declared exposure or its basis changes.
    suffix = f"{prefix}-{mode}-{basis}-{choice['low']}-{choice['high']}-{choice['high_exclusive']}"
    saved = previous if previous and previous["choice"] == choice else {}
    bills = st.radio("In these scenarios, could you pay your expenses on schedule?", responses,
                     index=responses.index(saved.get("bills","unknown")), key=suffix+"bills", horizontal=True)
    comfort = st.radio("Would you be comfortable keeping the investment sleeve after these drops?", responses,
                       index=responses.index(saved.get("comfort","unknown")), key=suffix+"confort", horizontal=True)
    result = assess(snapshot, choice, accept=mode != "unknown", bills=bills, comfort=comfort)
    for message in result["issues"]:
        st.caption(message)
    if result["alternative"]:
        st.info(result["alternative"]["reason"] + " You can select \"Minimum Risk\" above.")
    decision = "Save my indecision" if mode == "unknown" else "Confirm my risk request"
    if st.button(decision, key=prefix+"save"):
        interview.save_risk(choice, accept=mode != "unknown", bills=bills, comfort=comfort)
        if on_save:
            on_save()
        st.rerun()
    if previous:
        st.write(f"Latest recorded decision · {describe(previous['choice'])} · {previous['state']}.")
        if previous["ready_for_feasibility"] and not on_save:
            st.page_link("pages/3_Feasibility.py",label="Examine feasibility")
