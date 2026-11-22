from pathlib import Path
from secrets import randbelow
import streamlit as st
from streamlit.components.v1 import declare_component
from riskmatch.interview import CARDS, current, eligible, report, rewind, submit
from riskmatch.intake import evaluate

swipe = declare_component(
    "riskmatch_choice", path=str(Path(__file__).with_name("swipe"))
)


def band(low, high):
    return f"φ ≥ {low:.2f}" if high is None else f"{low:.2f} ≤ φ ≤ {high:.2f}"


def interview(d):
    s = st.session_state
    log = s.setdefault("interview_events", [])
    answers = current(log)
    if "probe_form" not in s:
        s.probe_form = randbelow(20)
    pool = eligible(answers, s.probe_form)
    ended = s.get("interview_paused", False)
    if pool and not ended:
        ident = pool[0]
        card = CARDS[ident]
        st.caption(
            f"Scenario {len(answers) + 1} · one-year figures are hypothetical CHF amounts"
        )
        if ident == "P01":
            st.info(CARDS["C01"]["feedback"] + " Try a second example.")
        event = swipe(
            id=ident,
            revision=len(log),
            context=card["context"],
            statement=card["statement"],
            key="choice_surface",
            default=None,
        )
        if event and submit(
            log,
            event.get("id"),
            event.get("answer"),
            event.get("method"),
            event.get("revision"),
            s.probe_form,
        ):
            st.rerun()
        if st.button("Finish with my current answers"):
            log.append(dict(kind="stop", step=len(answers)))
            s.interview_paused = True
            st.rerun()
    else:
        profile_result(d, answers)
        if pool and st.button("Resume interview"):
            log.append(dict(kind="resume", step=len(answers)))
            s.interview_paused = False
            st.rerun()
    if answers:
        with st.expander("Review or correct a choice"):
            selected = st.selectbox(
                "Previously answered scenario",
                list(answers),
                format_func=lambda i: f"{i} · {CARDS[i]['statement']} · {answers[i]}",
                index=len(answers) - 1,
            )
            st.caption(
                "Changing a choice reopens the following scenarios so that the route reflects your correction."
            )
            st.write(CARDS[selected]["context"])
            if st.button("Answer this scenario again"):
                rewind(log, selected)
                s.interview_paused = False
                st.rerun()
    if st.button("Review my payments and reserves"):
        s.page = 2
        st.rerun()


def profile_result(d, answers):
    r = report(answers)
    st.subheader("One-year risk tolerance")
    st.caption(
        "In these hypothetical choices, higher φ means giving more weight to avoiding fluctuations."
    )
    if r["status"] == "conflict":
        st.warning(
            f"Your choices imply both φ ≥ {r['low']:.2f} and φ ≤ {r['high']:.2f}. Your personal ranking is unresolved."
        )
    elif r["status"] in ("insufficient", "comprehension unresolved"):
        st.info("Tolerance is undetermined. More understood choices are needed.")
        if "P01" in answers and not r["understood"]:
            st.write(CARDS["P01"]["feedback"])
    else:
        st.write(f"Values compatible with your choices: {band(r['low'], r['high'])}.")
        st.caption(
            "This range shows which values fit your answers under the one-year model."
        )
    st.subheader("Financial capacity")
    c = evaluate(d)["capacity"]
    if c:
        ccy = (
            d.get("currency_name")
            if d.get("currency") == "Other"
            else d.get("currency")
        )
        st.write(
            f"Protected today (lower / higher funding need): {c[0]['protected']:,.2f} / {c[1]['protected']:,.2f} {ccy}. Available to invest: {c[1]['investable']:,.2f}–{c[0]['investable']:,.2f} {ccy}."
        )
        if c[1]["shortfall"]:
            st.warning(
                f"Higher-need funding shortfall: {c[1]['shortfall']:,.2f} {ccy} on {c[1]['first_shortfall']}."
            )
        st.caption(
            "These scenarios use the amounts you entered and confirmed funding dates."
        )
    else:
        st.info(
            "Funding capacity is pending completion of your payment schedule and amounts."
        )
    if r["liquidity"]:
        st.warning(
            "Your answers suggest a cash need. Review your payments and confirm any changes to update the reserve."
        )
    st.write("Hard exclusions", d.get("exclusions") or "Unanswered")
    st.subheader("Choices and review preferences")
    st.caption("These answers describe what you might do in the scenarios shown.")
    for flag, msg in [
        (
            "discomfort",
            "You endorsed wanting smaller fluctuations even with expenses covered.",
        ),
        ("belief", "You linked selling to an expectation of further losses."),
        (
            "confirmed_loss",
            "You confirmed that falling below the starting amount mattered in the paired comparisons.",
        ),
    ]:
        if r[flag]:
            st.write(msg)
    if r["loss_pattern"] and not r["confirmed_loss"]:
        st.write(
            "Your choices switched in two paired comparisons. The reason remains open."
        )
    st.write("Notification when weights drift:", r["monitoring"])
    if answers.get("B13") == "yes":
        st.write("You prefer a scheduled review.")
    if answers.get("B12") == "yes":
        st.write("You would like estimated trading costs in alerts.")
    st.subheader("Strength of evidence")
    st.write(
        f"{r['used']} scored choices · {r['passes']} unsure · {len(answers)} scenarios answered"
    )
    if r["used"]:
        st.caption(
            "Sensitivity uses two illustrative one-year alternatives on the same stake: 3% return and 5% volatility, or 5% return and 15% volatility. They tie at φ = 2."
        )
        if r["sensitive"] or r["status"] == "conflict":
            st.write("A personal ranking is unresolved. Review the choices below.")
        elif r["options"]:
            st.write("Compatible examples:", ", ".join(r["options"]))
        with st.expander("Effect of omitting one choice at a time"):
            st.table(
                [
                    {
                        "Omitted": i,
                        "Compatible range": band(lo, hi)
                        if status != "conflict"
                        else "Conflict",
                        "Possible examples": ", ".join(opts) or "Unresolved",
                    }
                    for i, (lo, hi, status, opts) in r["omissions"].items()
                ]
            )
            union = set().union(
                *(opts for lo, hi, status, opts in r["omissions"].values())
            )
            st.write(
                "Examples possible across these interpretations:",
                ", ".join(sorted(union)) or "Unresolved",
            )
    if answers.get("B15") == "yes":
        st.write(
            "You indicated that a choice felt close. You can revisit the original offers."
        )
