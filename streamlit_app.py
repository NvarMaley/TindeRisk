"""Local English-language RiskMatch client profile pilot."""

import secrets
import time
from pathlib import Path

import streamlit as st

from riskmatch import intake
from riskmatch.profile_session import Interview

st.set_page_config(
    page_title="Client profile · RiskMatch", page_icon="◈", layout="centered"
)
ROOT = Path(__file__).resolve().parent
FORM_STEPS = (
    "Your goal",
    "Upcoming withdrawals",
    "Household reserve",
    "Investment preferences",
)
SESSION = st.session_state
card_widget = st.components.v2.component(
    "riskmatch_choice",
    html=(
        '<div class="deck"><div class="stack"><article class="card" tabindex="0" '
        'aria-keyshortcuts="ArrowLeft ArrowRight" aria-describedby="gesture"><div class="family"></div>'
        '<p class="scenario"></p><h2></h2><div class="stamp" aria-hidden="true"></div></article></div>'
        '<div class="legend" aria-hidden="true"><span>← No</span><span>Yes →</span></div>'
        '<p id="gesture">Swipe or drag the card. You can also use the ← and → keys.</p>'
        '<div class="assist"><button class="no">Answer no</button><button class="yes">Answer yes</button></div>'
        '<button class="skip" type="button">Pass this card</button></div>'
    ),
    css=(ROOT / "riskmatch/card.css").read_text(),
    js=(ROOT / "riskmatch/swipe.js").read_text(),
)


def change(screen):
    SESSION.screen = screen
    SESSION.pop("card_clock", None)
    st.rerun()


def begin():
    SESSION.screen = "intake"
    SESSION.step = 0
    SESSION.draft = intake.blank()
    SESSION.interview = None
    SESSION.pilot = False
    SESSION.assignment = None


def input_screen():
    step, facts = SESSION.step, SESSION.draft
    st.caption(f"Client profile  /  Intake {step + 1} of 4")
    st.title(FORM_STEPS[step])
    if step == 0 and SESSION.interview is None:
        if st.button("Use the CHF example"):
            SESSION.draft = intake.sample()
            SESSION.form_epoch = SESSION.get("form_epoch", 0) + 1
            st.rerun()
        with st.expander("Resume from a profile file"):
            upload = st.file_uploader(
                "Local profile JSON", type="json", max_upload_size=1
            )
            if upload is not None and st.button("Restore this session"):
                try:
                    session = Interview.restore(upload.getvalue())
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    SESSION.interview = session
                    SESSION.draft = session.facts.copy()
                    change("interview")
    st.write(
        (
            "Choose one goal. You can leave amounts open or enter a range such as 40000–50000.",
            "How much money needs to be available before the end of the growth horizon?",
            "If income fell for six months, how would you cover essential expenses?",
            "Which activities must be excluded, and what would you like the portfolio to favor?",
        )[step]
    )
    updated = facts.copy()
    with st.form(f"intake_{step}_{SESSION.get('form_epoch', 0)}"):

        def field(key, label, help=None):
            updated[key] = st.text_input(
                label,
                value=facts[key],
                max_chars=300 if key in intake.TEXT else 50,
                help=help,
            )

        def select(key, label, options):
            updated[key] = st.selectbox(label, options, index=options.index(facts[key]))

        def flag(key, label):
            updated[key] = st.checkbox(label, value=facts[key])

        if step == 0:
            field(
                "project",
                "What are you saving for?",
                "A short goal name is enough. Avoid personal identifiers.",
            )
            select("currency", "Currency of the goal", intake.CURRENCIES)
            field(
                "other_currency",
                "Other currency code (if applicable)",
                "Use a three-letter code such as GBP.",
            )
            field("capital", "Starting investment")
            field("horizon", "Growth horizon in whole years")
            field(
                "goal",
                "Target for the growth investment at the end (optional)",
                "Exclude household reserves and money set aside for earlier withdrawals.",
            )
            field(
                "contribution",
                "Monthly contribution to the growth investment",
                "Exclude contributions already assigned to a withdrawal. Use 0 for none.",
            )
            field("wish", "Desired annual return in % (optional)")
        elif step == 1:
            field(
                "withdraw",
                "Amount needed at the first withdrawal",
                "Enter 0 for no planned withdrawal. A blank means unknown.",
            )
            field(
                "due",
                "Months until the withdrawal",
                "Enter 0 for an immediate withdrawal.",
            )
            field(
                "external",
                "Cash already set aside outside this investment for this withdrawal",
            )
            field(
                "saving", "Reliable monthly savings earmarked only for this withdrawal"
            )
            flag("flexible", "I could change the withdrawal date")
        elif step == 2:
            select("household", "How would you cover the essentials?", intake.HOUSEHOLD)
            field(
                "safety",
                "Reserve needed from this investment",
                "Exclude amounts already budgeted for the withdrawal. If covered elsewhere, the internal reserve is zero.",
            )
            flag("variable", "My income varies materially from month to month")
            flag(
                "employer", "My investments and income may depend on the same employer"
            )
        else:
            field(
                "exclusions",
                "Mandatory exclusions",
                "For example, companies producing tobacco.",
            )
            field(
                "preferences",
                "Other investment preferences",
                "For example, a preference for low emissions.",
            )
            field(
                "cap",
                "Agreed annual volatility ceiling for the investable sleeve in % (optional)",
                "Leave open if unfamiliar. Volatility measures variability. A 12% ceiling is not a maximum loss.",
            )
            if SESSION.interview is None:
                pilot = st.checkbox(
                    "Include the four research validation cards", value=SESSION.pilot
                )
                assignment = st.number_input(
                    "Pilot participant number (optional)",
                    min_value=0,
                    max_value=2**31 - 1,
                    value=SESSION.assignment,
                    step=1,
                    help="Use consecutive assigned numbers to balance presentation across participants.",
                )
        cols = st.columns(2)
        back = cols[0].form_submit_button("Back") if step else False
        forward = cols[1].form_submit_button(
            "Start cards" if step == 3 else "Continue", type="primary"
        )
    if forward or back:
        try:
            intake.validate_intake(updated)
        except ValueError as exc:
            st.error(str(exc))
            return
        SESSION.draft = updated
        if step == 3 and SESSION.interview is None:
            SESSION.pilot, SESSION.assignment = pilot, assignment
        if forward and step == 3:
            if SESSION.interview is None:
                seed = (
                    SESSION.assignment
                    if SESSION.pilot and SESSION.assignment is not None
                    else secrets.randbits(32)
                )
                SESSION.interview = Interview(updated, seed, SESSION.pilot)
            elif SESSION.interview.facts != updated:
                SESSION.interview.apply(dict(action="facts", facts=updated))
            change("interview")
        SESSION.step += 1 if forward else -1
        st.rerun()


def edit_facts(session):
    SESSION.draft = session.facts.copy()
    SESSION.form_epoch = SESSION.get("form_epoch", 0) + 1
    SESSION.step = 0
    change("intake")


def save_file(session, label):
    st.download_button(
        label,
        session.dump(),
        "profile.json",
        mime="application/json",
        on_click="ignore",
        help="This file contains the financial details and answers you provided. Keep your copy private.",
    )


def review(session):
    report = session.report()
    score, cap = report["tolerance"], report["capacity"]
    title = session.facts["project"] or "Your goal"
    st.caption("Client profile  /  Review")
    st.title("Your client profile")
    st.text(title)
    st.subheader("Risk tolerance")
    st.write(
        "Unresolved across all four pilot bands"
        if len(score["bands"]) == 4
        else " · ".join(score["bands"]) or "Undetermined"
    )
    if score["reason"]:
        st.info(score["reason"] + ". You can review your answers below.")
    else:
        hi = "open upper bound" if score["hi"] is None else f"{score['hi']:.2f}"
        st.write(
            f"Estimated aversion φ: {score['lo']:.2f} to {hi}, from {score['n']} understood trade-offs."
        )
    if score["n"]:
        with st.expander("Which choices shaped this estimate?"):
            for key, choice in session.answers.items():
                if key.startswith("A") and choice in (0, 1, 2):
                    threshold = session.cards[key]["phi_threshold"]
                    relation = ("at least", "at most", "close to")[choice]
                    st.text(
                        f"{key} · {session.cards[key]['answers'][choice]} → φ {relation} {threshold:.2f}"
                    )
            st.caption(
                "Indifference uses an illustrative ±10% range around the threshold."
            )
    st.caption(
        "These pilot bands describe choices across one-year scenarios. Their boundaries still need human calibration."
    )
    if score["observation"]:
        st.write(score["observation"])
    st.subheader("Funding the goal")
    m = cap["conservative_inputs"]

    def amount(value):
        return "Unknown" if value is None else f"{cap['currency']} {value:,.2f}"

    columns = st.columns(2)
    columns[0].metric("Capital to protect", amount(cap["reserve"]))
    columns[1].metric("Available for growth", amount(cap["free"]))
    st.caption(
        "Reserves include essential household needs and the earliest withdrawal after dedicated external funding. Ranges use the lower available capital and higher obligations. Reserves are shown at zero nominal interest."
    )
    r = cap["required_rate"]
    st.write(
        "Desired annual return",
        (session.facts["wish"] + "%") if session.facts["wish"] else "Open",
    )
    st.write(
        "Required annual return on the growth investment",
        f"{r:.2%}" if r is not None else "Undetermined",
    )
    if r is not None and cap["desired_return"] and r > cap["desired_return"][1] / 100:
        st.info(
            "Funding this target would require a higher return than you requested. Review contributions, the amount or the deadline."
        )
    st.caption(
        "The required rate uses end-of-month growth contributions and the stated target. It measures what the goal would require under these assumptions."
    )
    if m["cap"] is not None:
        st.write(f"Agreed ceiling for annual sleeve volatility: {m['cap']:g}%.")
    if score["follow"]:
        st.write("Your monitoring preference", score["follow"])
    st.write("Mandatory exclusions", cap["exclusions"] or "None stated")
    st.write("Other preferences", cap["preferences"] or "None stated")
    if cap["employer_review"]:
        st.write(cap["employer_review"])
    if cap["funding_gap"]:
        st.warning(
            f"Under these assumptions the reserves exceed starting capital by {amount(cap['funding_gap'])}."
        )
    if cap["reasons"]:
        st.subheader("Points to clarify")
        for reason in cap["reasons"]:
            st.write("• " + reason)
    if m["saving"] and m["withdraw"] and m["external"] is not None:
        st.write(
            "Withdrawal reserve if future earmarked savings stop",
            amount(max(0, m["withdraw"] - m["external"])),
        )
    with st.expander("Review intake and answers"):
        labels = {
            "project": "Goal",
            "currency": "Spending currency",
            "other_currency": "Other currency",
            "capital": "Starting capital",
            "goal": "Target growth balance",
            "wish": "Desired return (%)",
            "contribution": "Monthly growth contribution",
            "horizon": "Growth horizon (years)",
            "withdraw": "Withdrawal amount",
            "due": "Withdrawal in months",
            "external": "Dedicated cash outside the investment",
            "saving": "Monthly withdrawal savings",
            "flexible": "Flexible withdrawal date",
            "household": "How household costs are covered",
            "safety": "Internal household reserve",
            "variable": "Variable income",
            "employer": "Employer-linked exposure",
            "exclusions": "Mandatory exclusions",
            "preferences": "Other preferences",
            "cap": "Sleeve volatility ceiling (%)",
        }
        for field, label in labels.items():
            value = session.facts[field]
            if isinstance(value, bool):
                value = "Yes" if value else "No"
            if value or field != "other_currency":
                st.text(f"{label}: {value or 'Open'}")

        for key, choice in session.answers.items():
            c = session.items[key]
            st.text(
                f"{key} · {c['question']}\n{c['answers'][choice] if choice >= 0 else 'No preference or answer confirmed'}"
            )
    if session.stopped and st.button("Resume remaining cards"):
        session.apply(dict(action="resume"))
        change("interview")
    if session.answers:
        key = st.selectbox(
            "Card to correct",
            list(session.answers),
            format_func=lambda k: f"{k} · {session.cards[k]['question']}",
        )
        if st.button(
            "Revisit this card",
            help="Later answers will be collected again along the revised route.",
        ):
            session.apply(dict(action="revise", id=key))
            change("interview")
    if st.button("Edit factual intake"):
        edit_facts(session)
    if session.pilot:
        with st.expander("Pilot record"):
            st.write(
                "Review state",
                "Edited after the validation freeze"
                if session.revised_after_freeze
                else "Original route",
            )
            st.write(
                "Recorded card-response time (seconds)",
                round(report["elapsed_answer_seconds"], 1),
            )
            st.json(report["holdouts"])
    if session.confirmed:
        st.success("Profile reviewed and confirmed.")
    elif st.button("Confirm this profile", type="primary"):
        session.apply(dict(action="confirm"))
        st.rerun()
    save_file(session, "Download profile.json")


def cards_screen():
    session = SESSION.interview
    stage, key = session.current()
    if stage == "review":
        review(session)
        return
    card = session.items[key]
    st.caption(
        "Client profile  /  "
        + ("Pilot validation" if stage == "validation" else "Questionnaire")
    )
    st.title("Your investment choices" if stage == "profile" else "Independent choices")
    if stage == "validation":
        st.write(
            f"Your profile is frozen. Independent choice {len(session.checks) + 1} of {len(session.frozen)}."
        )
    elif key == "C2":
        st.info(session.cards["C1"]["feedback"] + " Try this second example.")
    elif key == "C1":
        st.write(
            "Start with a practice card. Swipe right for yes, left for no. All amounts are hypothetical."
        )
    else:
        st.caption(
            f"{len(session.answers)} answered · common and follow-up cards depend on your route."
        )
    statement = session.statement()
    nonce = f"{key}_{len(session.events)}"
    if SESSION.get("card_clock", (None,))[0] != nonce:
        SESSION.card_clock = (nonce, time.monotonic())
    result = card_widget(
        key=nonce,
        data=dict(
            id=key,
            nonce=nonce,
            text=statement["text"],
            context=statement["context"],
            family=card.get("family", "Independent transfer").capitalize(),
            passLabel="I can’t choose"
            if statement["pass"] is None
            else "Pass this card",
        ),
        on_picked_change=lambda: None,
    )
    picked = result.picked
    if picked and picked["nonce"] == nonce and picked["id"] == key:
        seconds = round(max(0, time.monotonic() - SESSION.card_clock[1]), 2)
        session.apply(
            dict(
                action="swipe",
                id=key,
                step=session.step,
                direction=picked["direction"],
                seconds=seconds,
            )
        )
        st.rerun()
    if session.step and st.button("Back to the first statement"):
        session.apply(dict(action="restart_card", id=key))
        st.rerun()
    if (
        stage == "profile"
        and not session.step
        and session.answers
        and st.button("Previous card")
    ):
        session.apply(dict(action="revise", id=next(reversed(session.answers))))
        st.rerun()
    with st.expander("Session options"):
        save_file(session, "Save progress")
        if stage == "profile" and st.button("End early and review factual profile"):
            session.apply(dict(action="stop", id=key))
            change("interview")
        if st.button("Edit the goal and constraints"):
            edit_facts(session)


if "screen" not in SESSION:
    begin()
st.markdown("**RiskMatch**")
if SESSION.screen == "intake":
    input_screen()
else:
    cards_screen()
