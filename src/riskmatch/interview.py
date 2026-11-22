"""Deterministic routes for the one-year, hypothetical RiskMatch interview."""

import json
from math import isclose, isfinite
from pathlib import Path

BANK = json.loads(
    (Path(__file__).resolve().parents[2] / "questions/profile_v1.json").read_text()
)
VERSION = BANK["version"]
CARDS = {card["id"]: card for card in BANK["cards"]}
CORE = "C01 C02 C03 C08 C04 C12 C05 C09 C06 C14 C10 C07 C13 C11 C15".split()
MAX_PROBES = 2
MAX_CARDS = 25
# Hypothetical one-year examples used only to illustrate ranking uncertainty.
# A: mean .03, variance .0025; B: mean .05, variance .0225. Tie at phi=2.
CROSSOVER = 2.0


def threshold(card):
    stake, sure = card["stake"], card["certain"]
    outcomes, probs = card["outcomes"], card["probabilities"]
    if (
        not isfinite(stake)
        or stake <= 0
        or len(outcomes) != len(probs)
        or not outcomes
        or any(not isfinite(p) or p <= 0 for p in probs)
        or not isclose(sum(probs), 1)
        or not all(isfinite(x) for x in [sure, *outcomes])
    ):
        raise ValueError("Invalid one-year lottery")
    if not min(outcomes) < sure < max(outcomes):
        return None
    returns = [x / stake - 1 for x in outcomes]
    mean = sum(p * r for p, r in zip(probs, returns))
    variance = sum(p * (r - mean) ** 2 for p, r in zip(probs, returns))
    if variance <= 0:
        return None
    value = 2 * (mean - (sure / stake - 1)) / variance
    return round(value, 12) if value > 1e-12 else None


def compatible(constraints):
    lows = [v for v, choice in constraints.values() if choice == "sure"]
    highs = [v for v, choice in constraints.values() if choice == "gamble"]
    low = max([0.0, *lows])
    high = min(highs, default=None)
    if high is not None and low > high:
        return low, high, "conflict", ()
    options = []
    if low <= CROSSOVER:
        options.append("variable")
    if high is None or high >= CROSSOVER:
        options.append("stable")
    status = (
        "insufficient"
        if not constraints
        else "one-sided"
        if not lows or not highs
        else "bounded"
    )
    return low, high, status, tuple(options)


def report(answers):
    choices = {i: CARDS[i]["answers"][v] for i, v in answers.items()}
    understood = any(choices.get(i) == "understood" for i in ("C01", "P01"))
    bounds = {
        i: (threshold(CARDS[i]), choice)
        for i, choice in choices.items()
        if understood and CARDS[i]["effect"] == "bound" and choice in ("sure", "gamble")
    }
    low, high, status, options = compatible(bounds)
    omissions = {
        i: compatible({k: v for k, v in bounds.items() if k != i}) for i in bounds
    }
    sensitive = [
        i
        for i, (_, _, s, opts) in omissions.items()
        if opts != options or (s == "conflict") != (status == "conflict")
    ]
    pairs = [
        (choices.get(a), choices.get(b)) for a, b in [("C08", "C10"), ("C09", "C11")]
    ]
    repeated = all(pair == ("gamble", "sure") for pair in pairs) or all(
        pair == ("sure", "gamble") for pair in pairs
    )
    return dict(
        low=low,
        high=high,
        status=status if understood else "comprehension unresolved",
        options=options,
        sensitive=sensitive,
        omissions=omissions,
        used=len(bounds),
        passes=sum(v == "pass" for v in answers.values()),
        understood=understood,
        loss_pattern=repeated,
        confirmed_loss=repeated and answers.get("B14") == "yes",
        liquidity=any(answers.get(i) == "yes" for i in ("B01", "B04", "B05", "B06")),
        discomfort=answers.get("B02") == "yes",
        belief=answers.get("B03") == "yes",
        monitoring=answers.get("C15", "unanswered"),
    )


def eligible(answers, form=0):
    if not answers:
        return ["C01"]
    if answers.get("C01") != "yes":
        if "P01" not in answers:
            return ["P01"]
        if answers["P01"] != "no":
            return []
    remaining = [i for i in CORE if i not in answers]
    if remaining:
        return remaining[:1]
    if len(answers) >= MAX_CARDS:
        return []
    r = report(answers)
    probes = []
    if (
        sum(i.startswith("T") for i in answers) < MAX_PROBES
        and r["used"]
        and r["status"] != "conflict"
        and len(r["options"]) > 1
    ):
        for i, c in CARDS.items():
            if i.startswith("T") and i not in answers:
                t = threshold(c)
                if t > r["low"] and (r["high"] is None or t < r["high"]):
                    probes.append(((int(i[1:]) - 1 - form) % 20, i))
    choices = []
    # Resolve a funding concern before adding optional portfolio questions.
    for i, c in CARDS.items():
        if not i.startswith("B") or i in answers:
            continue
        trig = c["trigger"]
        if trig == "loss pattern":
            ok = r["loss_pattern"]
        elif trig == "sensitive":
            ok = bool(r["sensitive"]) or r["status"] == "conflict"
        else:
            ok = any(
                answers.get(parent) == value
                for parent, value in (item.split(":") for item in trig.split("|"))
            )
        if ok:
            choices.append(i)
    priority = ["B01", "B04", "B05", "B06", "B02", "B03", "B14", "B15"]
    return (
        [i for i in priority if i in choices]
        + [i for _, i in sorted(probes)]
        + [i for i in choices if i not in priority]
    )


def current(log):
    """Replay edits by discarding superseded suffixes from the active path only."""
    answers = {}
    for event in log:
        if event["kind"] == "rewind":
            keys = list(answers)
            answers = {i: answers[i] for i in keys[: keys.index(event["id"])]}
        elif event["kind"] == "answer":
            answers[event["id"]] = event["answer"]
    return answers


def submit(log, card_id, answer, method, revision, form=0):
    answers = current(log)
    pool = eligible(answers, form)
    if (
        revision != len(log)
        or not pool
        or pool[0] != card_id
        or answer not in ("yes", "no", "pass")
    ):
        return False
    card = CARDS[card_id]
    log.append(
        dict(
            kind="answer",
            id=card_id,
            version=VERSION,
            step=len(answers) + 1,
            context=card["context"],
            wording=card["statement"],
            display="yes-right",
            form=form,
            answer=answer,
            choice=card["answers"][answer],
            method=method,
            eligible=pool,
        )
    )
    return True


def rewind(log, card_id):
    if card_id not in current(log):
        return False
    log.append(dict(kind="rewind", id=card_id, version=VERSION))
    return True
