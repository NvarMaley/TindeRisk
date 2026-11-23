"""Behavioural calibration for the client studio, version 1 (theoretical policy)."""

from datetime import date
from math import isfinite

from .interview import CARDS, gamble_bounds, intersection, route, understood
from .matching.mandate import MARKET_DAY
from .risk_review import POLICY

# A like always endorses the first-person proposition. Orientations retain the bank's
# original yes/no coding so its conditional branches and gamble bounds still apply.
STATEMENTS = {
    "C01": "Even on a fair coin toss, I could lose this round.",
    "C02": "After three wins, I could still lose the next independent toss.",
    "T01": "With my bills covered, I would accept big swings in my investments.",
    "T02": "A temporary CHF 2,000 loss on CHF 10,000 would change my last answer.",
    "G00": "I can set aside CHF 1,000 for a year and compare two fictional offers.",
    "G04": "I stand by my choices, even though they point in different directions.",
    "T03": "I would like to reconsider my answer about big swings.",
    "L00": "When judging a loss, I first think about the amount I paid.",
    "L01": "I would keep CHF 1,000 for sure over an equal chance of CHF 900 or CHF 1,100.",
    "L02": "I would take zero gain over a 50/50 chance of losing or gaining CHF 100.",
    "L03": "I would keep CHF 2,000 for sure over an equal chance of CHF 1,800 or CHF 2,200.",
    "L04": "I would take no change over a 50/50 chance of losing or gaining CHF 200.",
    "L05": "I would like to revisit the same choice expressed in two different ways.",
    "D01": "After a 15% fall, I would consider selling.",
    "D02": "I would sell after that fall to pay a bill.",
    "D03": "Even with my bills covered, the discomfort would make me sell.",
    "D04": "I would sell because I expect prices to fall further.",
    "D06": "I would review the plan mainly to check whether my goal is still reachable.",
    "D05": "I would compare a portfolio that explicitly reduces exposure to a shock.",
    "H01": "I could move my goal date if reaching it took longer.",
    "H02": "I could accept a smaller final amount.",
    "S01": "I like checking the value of my investments frequently.",
    "S02": "Between scheduled reviews, a risk alert would be enough for me.",
    "S03": "In a blend, I want to follow each strategy separately.",
}
for key in ("G01", "G02", "G03"):
    g = CARDS[key]["gamble"]
    STATEMENTS[key] = (
        f"I would take a certain CHF {g['certain']:,} over a 50/50 chance "
        f"of CHF {g['low']:,} or CHF {g['high']:,}."
    )

GIST = {
    "Comprehension": "Checks whether the uncertainty in the examples is understood.",
    "Stated tolerance": "Describes comfort with fluctuations and whether a concrete loss changes that view.",
    "Certain outcome or gamble": "Compares a guaranteed amount with the same uncertain payoff.",
    "Reference point": "Checks how framing the same gain or loss changes a choice.",
    "Response to a loss": "Separates a need for cash from discomfort or a market belief.",
    "Flexibility": "Describes room to change the goal or its timing.",
    "Tracking": "Describes a monitoring preference. It carries no risk-score weight.",
}


# Outcomes are equally likely in each fictional one-year comparison.
# For two equiprobable outcomes their population standard deviation is half the spread.
COMPARISON_OUTCOMES = {
    "V01": ((-2, 6), (-5, 11)),
    "V02": ((-2, 6), (-12, 20)),
}
COMPARISON_ANSWERS = ("lower", "wider", "neither", "skip")

ACTIONS = {
    "keep": ("Keep the portfolio", "no"),
    "reduce": ("Reduce the risk", "yes"),
    "review": ("Review the plan before acting", "skip"),
    "certain": ("Take the guaranteed amount", "yes"),
    "gamble": ("Take the 50/50 option", "no"),
}
CHOICE_IDS = {
    "D01": ("keep", "reduce", "review"),
    **dict.fromkeys(("G01", "G02", "G03"), ("certain", "gamble")),
}


def _binary(answers):
    return {
        key: ACTIONS[value][1] if value in ACTIONS else value
        for key, value in answers.items()
    }


def _choice_row(key):
    ids = CHOICE_IDS.get(key)
    if not ids:
        return {}
    if key == "D01":
        text = "Your portfolio is down 15%. What would you do next?"
        options = [(choice, ACTIONS[choice][0]) for choice in ids]
    else:
        g = CARDS[key]["gamble"]
        text = f"On a fictional CHF {g['stake']:,} investment for one year, which outcome would you choose?"
        options = [
            ("certain", f"CHF {g['certain']:,} guaranteed"),
            ("gamble", f"50/50 chance of CHF {g['low']:,} or CHF {g['high']:,}"),
        ]
    return {"text": text, "choices": options}


def deck(answers, *, portfolio_check=False):
    if not isinstance(answers, dict) or any(
        v not in COMPARISON_ANSWERS
        if k in COMPARISON_OUTCOMES and portfolio_check
        else k not in STATEMENTS
        or v not in ("yes", "no", "skip", *CHOICE_IDS.get(k, ()))
        for k, v in answers.items()
    ):
        raise ValueError("Invalid calibration response.")

    active = [k for k in route(_binary(answers)) if k in STATEMENTS]
    if answers.get("D01") == "review":
        active.insert(active.index("D01") + 1, "D06")
    families = {
        k: CARDS[k]["family"] if k in CARDS else "Response to a loss" for k in active
    }
    rows = [
        {
            "id": k,
            "text": STATEMENTS[k],
            "family": families[k],
            "help": GIST[families[k]],
            **_choice_row(k),
        }
        for k in active
    ]
    if portfolio_check and understood(_binary(answers)):
        for key, outcomes in COMPARISON_OUTCOMES.items():
            options = [
                (choice, f"{name} · {loss:+d}% or {gain:+d}%")
                for choice, name, (loss, gain) in zip(
                    ("lower", "wider"),
                    ("Portfolio A", "Portfolio B"),
                    outcomes,
                    strict=True,
                )
            ]
            rows.append(
                {
                    "id": key,
                    "text": "Which portfolio would you choose for your investable money?",
                    "family": "Portfolio cross-check",
                    "help": "One fictional year in CHF. Each result has a 50/50 chance. Both options have the same fees and access to cash. This choice carries no score points.",
                    "choices": [*options, ("neither", "Neither · keep cash")],
                }
            )
            active.append(key)
    return rows, {k: answers[k] for k in active if k in answers}


def money(value, label, *, minimum=0, maximum=1_000_000_000):
    try:
        n = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Enter a number for {label}.") from None
    if isinstance(value, bool) or not isfinite(n) or not minimum <= n <= maximum:
        raise ValueError(f"Check the amount for {label}.")
    return n


def intake(raw):
    start = date.fromisoformat(MARKET_DAY)
    capital = money(raw.get("capital"), "available capital", minimum=1)
    protected = money(raw.get("protected"), "protected cash", maximum=capital)
    goal = money(raw.get("goal"), "target amount", minimum=1)
    try:
        due = date.fromisoformat(raw.get("due", ""))
    except (TypeError, ValueError):
        raise ValueError("Enter a valid goal date.") from None
    if not start < due or due.year - start.year > 80:
        raise ValueError(
            "The goal date must be after the research close and within 80 years."
        )
    flow = money(raw.get("expense", 0), "planned withdrawal")
    cash = max(protected, flow)
    if cash > capital:
        raise ValueError("The planned withdrawal exceeds the available capital.")
    flow_date = raw.get("expense_date")
    if flow:
        try:
            valid = start < date.fromisoformat(flow_date) <= due
        except (TypeError, ValueError):
            valid = False
        if not valid:
            raise ValueError(
                "Date the planned withdrawal between the opening close and the goal."
            )
    reserve_rate = raw.get("reserve_rate")
    reserve_rate = (
        0.0
        if reserve_rate in ("", None)
        else money(reserve_rate, "CHF savings rate", minimum=-10, maximum=20) / 100
    )
    growth = 1 + reserve_rate
    reserve_at_goal = cash * growth ** ((due - start).days / 365.25)
    if flow:
        spending_day = date.fromisoformat(flow_date)
        remaining_years = (due - spending_day).days / 365.25
        reserve_at_goal -= flow * growth**remaining_years
        if reserve_at_goal < -0.005:
            raise ValueError(
                "Set aside more cash to cover the planned spending at this savings rate."
            )
    loss = money(raw.get("loss"), "loss capacity", maximum=capital)
    target = raw.get("target")
    target = (
        None
        if target in ("", None)
        else money(target, "desired annual return", minimum=-99, maximum=200) / 100
    )
    import re

    exclusions = raw.get("exclusions", "")
    if not isinstance(exclusions, str) or len(exclusions) > 500:
        raise ValueError("Enter up to 500 characters of excluded tickers.")
    exclusions = [x for x in re.split(r"[\s,]+", exclusions.strip().upper()) if x]
    if any(not re.fullmatch(r"[A-Z0-9.\-^/]{1,20}", x) for x in exclusions):
        raise ValueError("Use US tickers separated by commas for exclusions.")
    moral = raw.get("moral", "none")
    if moral not in ("none", "low_emissions", "exclude_chevron"):
        raise ValueError("Unknown environmental preference.")
    classes = {
        "all": None,
        "funds": ["Equity ETF", "Treasury ETF", "Gold (GLD)"],
        "direct": ["Individual stock", "Direct Treasury"],
        "treasury": ["Direct Treasury", "Treasury ETF"],
    }
    universe = raw.get("universe", "all")
    if universe not in classes:
        raise ValueError("Choose an available investment universe.")
    free = raw.get("mandatory", "")
    if not isinstance(free, str) or len(free) > 280:
        raise ValueError("Limit other mandatory rules to 280 characters.")
    flows = (
        [
            {
                "date": flow_date,
                "currency": "CHF",
                "direction": "withdrawal",
                "certainty": "confirmed",
                "low": flow,
                "high": flow,
            }
        ]
        if flow
        else []
    )
    return {
        "capital_chf": capital - cash,
        "total_chf": capital,
        "reserve_chf": cash,
        "reserve_at_goal_chf": max(0.0, reserve_at_goal),
        "reserve_rate": reserve_rate,
        "goal_chf": goal,
        "goal_date": due.isoformat(),
        "loss_capacity_chf": loss,
        "target_return": target,
        "savings_chf": 0.0,
        "flows": flows,
        "exclusions": exclusions,
        "exclude_chevron": moral == "exclude_chevron",
        "prefer_lower_emissions": moral == "low_emissions",
        "blocked_reason": (
            "Your additional mandatory rule needs verified coverage: " + free.strip()
        )
        if free.strip()
        else "",
        "allowed_classes": classes[universe],
        "as_of": MARKET_DAY,
    }


def _comparison_policy(active, band, cash_only):
    first, second = (active.get(k) for k in COMPARISON_OUTCOMES)
    base, medium = (abs(b - a) / 200 for a, b in COMPARISON_OUTCOMES["V01"])
    wide = (
        abs(COMPARISON_OUTCOMES["V02"][1][1] - COMPARISON_OUTCOMES["V02"][1][0]) / 200
    )
    inconsistent = first == "lower" and second == "wider"
    if cash_only or "neither" in (first, second):
        ceiling, status = 0.0, "Cash only"
    elif inconsistent or "skip" in (first, second):
        ceiling = medium if first == "wider" else base
        status = "Needs confirmation"
    else:
        ceiling = (
            wide if first == second == "wider" else medium if first == "wider" else base
        )
        status = (
            "Different from the score"
            if ceiling < band["low"]
            or (band["high"] is not None and ceiling > band["high"])
            else "Consistent with the score"
        )
    cap = ceiling if band["high"] is None else min(ceiling, band["high"])
    return {"status": status, "scenario_ceiling": ceiling, "allocation_ceiling": cap}


def calibrate(facts, answers, *, portfolio_check=False):
    cards, active = deck(answers, portfolio_check=portfolio_check)
    if any(c["id"] not in active for c in cards):
        raise ValueError("Finish the active calibration cards first.")
    a = _binary(active)
    phi = intersection(gamble_bounds(a))
    # Equal-weight the three domains, not the number of routed questions.
    bets = [
        100 * (a[k] == "no") for k in ("G01", "G02", "G03") if a.get(k) in ("yes", "no")
    ]
    stated = None if a.get("T01") not in ("yes", "no") else 100 * (a["T01"] == "yes")
    if a.get("T02") == "yes":
        stated = None  # Changed declaration has no known direction.
    stress = (
        100
        if a.get("D01") == "no" or a.get("D03") == "no"
        else 0
        if a.get("D03") == "yes"
        else None
    )
    domains = {
        "Stated comfort": stated,
        "Choices under uncertainty": round(sum(bets) / len(bets)) if bets else None,
        "Holding through discomfort": stress,
    }
    valid = [v for v in domains.values() if v is not None]
    usable = (
        understood(a)
        and len(bets) >= 2
        and phi["state"] != "contradiction"
        and len(valid) >= 2
    )
    score = round(sum(valid) / len(valid)) if usable else None
    band = POLICY["bands"][min(4, score // 20)] if usable else None
    horizon = (
        date.fromisoformat(facts["goal_date"]) - date.fromisoformat(MARKET_DAY)
    ).days / 365.25
    # Portfolio volatility describes dispersion, not a drawdown or a loss guarantee.
    flex = [100 * (a[k] == "yes") for k in ("H01", "H02") if a.get(k) in ("yes", "no")]
    frame = [
        (a.get(x), a.get(y))
        for x, y in (("L01", "L02"), ("L03", "L04"))
        if a.get(x) in ("yes", "no") and a.get(y) in ("yes", "no")
    ]
    blocked = facts["blocked_reason"]
    if not usable:
        blocked = (
            blocked
            or "There is insufficient consistent evidence for a volatility band. Revisit the comprehension and certain-outcome cards."
        )
    elif not facts["capital_chf"]:
        blocked = (
            blocked
            or "Your protected cash covers the whole budget. No money remains for risky positions."
        )
    low, high = (band["low"], band["high"]) if band else (0, 0)
    cash_only = facts["loss_capacity_chf"] == 0
    cap_note = (
        "Your loss capacity is zero. The allocation engine can propose only CHF cash."
        if cash_only
        else "The aggressive research band is open-ended. Stress and cash constraints still apply."
        if band and high is None
        else ""
    )
    check = (
        _comparison_policy(active, band, cash_only)
        if portfolio_check and band
        else None
    )
    if check:
        cap_note = (
            "The portfolio comparisons carry no score points. The search uses the more cautious ceiling "
            "indicated by the comparisons or the score, with no required minimum volatility. "
            "Financial loss capacity is checked separately."
        )
    policy = facts | {
        "low": 0 if cash_only or check else low,
        "high": check["allocation_ceiling"] if check else (0 if cash_only else high),
        "high_exclusive": False,
        "mode": "minimum"
        if cash_only or (check and check["allocation_ceiling"] == 0)
        else "target_band",
        "blocked_reason": blocked,
    }

    def observation(key, yes, no):
        return (
            yes
            if a.get(key) == "yes"
            else no
            if a.get(key) == "no"
            else "No clear response."
        )

    downside = observation(
        "D01",
        "A fall may prompt a sale.",
        "You leaned toward holding after a 15% fall.",
    )
    detail = (
        observation(
            "D03",
            "Discomfort was a reason to sell.",
            "Discomfort alone was not a reason to sell.",
        )
        if a.get("D01") == "yes"
        else "Based on the simulated 15% decline."
    )
    if active.get("D01") == "review":
        downside = "You would review the plan before acting."
        detail = observation(
            "D06",
            "Your main reason is to check whether the goal is still reachable.",
            "You would review the plan for a reason other than checking the goal.",
        )
    elif active.get("D01") == "reduce":
        downside = "You would reduce the portfolio’s risk after the fall."
        motives = [
            label
            for key, label in (
                ("D02", "cash needs"),
                ("D03", "discomfort"),
                ("D04", "expecting a further fall"),
            )
            if a.get(key) == "yes"
        ]
        if motives:
            detail = "Reasons you selected: " + ", ".join(motives) + "."
    readings = [
        {"name": "Downside response", "value": downside, "detail": detail},
        {
            "name": "Goal flexibility",
            "value": observation(
                "H01", "You could extend the horizon.", "Your target date matters."
            ),
            "detail": observation(
                "H02",
                "You could also reduce the goal.",
                "You prefer to keep the target amount.",
            ),
        },
        {
            "name": "Framing",
            "value": f"{sum(x == y for x, y in frame)} of {len(frame)} equivalent pairs agreed."
            if frame
            else "Too little paired evidence.",
            "detail": "The same payoff was shown as an ending balance and as a gain or loss.",
        },
        {
            "name": "Monitoring",
            "value": observation(
                "S01",
                "You prefer frequent updates.",
                "You prefer less frequent updates.",
            ),
            "detail": "Monitoring frequency does not set the risk band.",
        },
    ]
    return policy, {
        "portfolio_check": check,
        "score": score,
        "band": band["label"] if band else "Undetermined",
        "low": low,
        "high": high,
        "cap_note": cap_note,
        "domains": domains,
        "flexibility": round(sum(flex) / len(flex)) if flex else None,
        "readings": readings,
        "bounds": phi,
        "horizon_years": round(horizon, 1),
        "evidence": [
            c
            | {
                "answer": active[c["id"]],
                **(
                    {"text": STATEMENTS[c["id"]]}
                    if active[c["id"]] in ("yes", "no")
                    else {}
                ),
            }
            for c in cards
        ],
        "blocked_reason": blocked,
        "policy_version": "studio-2" if portfolio_check else "studio-1",
        "facts": facts,
    }
