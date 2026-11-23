"""Translate a confirmed questionnaire and risk decision into the CHF simulation mandate."""

import json
from datetime import date
from pathlib import Path

from ..interview import CARDS, Answer, Interview, route

MARKET_DAY = "2026-10-30"


def example_profile(root):
    case = json.loads((Path(root) / "reports/07-funding/client-A.json").read_text())
    interview = Interview(date.fromisoformat(MARKET_DAY))
    for key in CARDS:
        if key in route(interview.answers):
            interview.record(key, case["answers"].get(key, "skip"))
    return interview


def restore(versions):
    latest = versions[-1]
    return Interview(
        date.fromisoformat(latest["as_of"]),
        latest["answers"].copy(),
        [Answer(**item) for item in latest["changes"]],
        list(versions),
        True,
    )


def mandate(interview, day, opening_capital=None):
    if not interview.confirmed:
        raise ValueError("Confirm the current answers first.")
    snap = interview.versions[-1]
    review = snap.get("risk_review", {})
    if not review.get("ready_for_feasibility"):
        raise ValueError("Confirm a risk request and resolve the open questions first.")
    portrait = snap["portrait"]
    pocket = review["investable_chf"]["low"]
    reserve = review["reserve_chf"]["low"]
    choice = review["choice"]
    bounds = (
        review["equivalent"]
        if choice["basis"] == "household" and review["equivalent"]
        else choice
    )
    goal = portrait["goal"]["amount"] or {}
    due = goal.get("date")
    problems = []
    if (
        not due
        or due <= day
        or goal.get("currency") != "CHF"
        or goal.get("low") != goal.get("high")
    ):
        problems.append("Confirm one dated future goal in CHF on F05.")
    if opening_capital is not None and abs(opening_capital - pocket) > 0.005:
        problems.append(
            "The revised opening budget differs from the funded sleeve. Reconcile the opening capital and protected reserve before trading."
        )
    checks = portrait["mandatory_checks"]
    if checks:
        problems.append(
            "These mandatory instructions require a verified portfolio-level check: "
            + ", ".join(f"{r['card']} ({r['scope']})" for r in checks)
            + "."
        )
    for key in ("P07", "P08"):
        if portrait["preferences"][key] is None:
            problems.append(
                f"Confirm the exclusions on {key}, or record an empty list."
            )
    desired = portrait["goal"]["desired_annual_pct"] or {}
    if desired.get("strength") == "mandatory":
        problems.append(
            "A mandatory return requirement needs a feasibility review before matching."
        )
    flows = portrait["facts"]["flows"] or []
    scheduled = [v for v in flows if v.get("date") and day < v["date"] <= (due or day)]
    if any(v["currency"] != "CHF" or v["low"] != v["high"] for v in scheduled):
        problems.append("Specify exact CHF cash flows to compare the terminal goal.")
    deposits = sum(
        v["low"]
        for v in scheduled
        if v["direction"] == "contribution" and v["certainty"] == "confirmed"
    )
    withdrawals = sum(v["high"] for v in scheduled if v["direction"] == "withdrawal")
    # Leave the protected reserve outside the risky portfolio. Any withdrawals beyond it
    # are also deducted when evaluating the terminal goal.
    return {
        "day": day,
        "as_of": snap["as_of"],
        "capital_chf": pocket,
        "reserve_chf": reserve,
        "reserve_at_goal_chf": max(0, reserve - withdrawals),
        "savings_chf": deposits - max(0, withdrawals - reserve),
        "goal_chf": goal.get("low") or 0.0,
        "goal_date": due or day,
        "flows": flows,
        "low": bounds.get("low") or 0.0,
        "high": bounds.get("high"),
        "high_exclusive": choice["high_exclusive"],
        "mode": choice["mode"],
        "risk_basis": choice["basis"],
        "constraints": checks,
        "preferences": portrait["preferences"],
        "existing_exposures": portrait["existing_exposures"],
        "desired_return": desired,
        "loss_capacity_chf": review["capacity_loss_chf"],
        "blocked_reason": " ".join(problems),
        "interview_versions": interview.versions,
    }
