"""Scoring rules for the five-block studio profile."""

BLOCK_CARDS = {
    "P01": (
        "Risk comprehension and perception",
        "Which example can fluctuate more over one year?",
        "Each option has two equally likely outcomes.",
        (("narrow", "A · −2% or +6%"), ("wide", "B · −12% or +20%")),
    ),
    "P02": (
        "Risk comprehension and perception",
        "Now compare the distance between the two outcomes. Which range is wider?",
        "Each range runs from a possible loss to a possible gain.",
        (("wide", "A · −8% or +12%"), ("narrow", "B · −1% or +3%")),
    ),
    "M01": (
        "Loss sensitivity",
        "Would you take a 50/50 chance of losing CHF 100 or gaining CHF 150?",
        "The alternative is to keep the same amount of money.",
        (("accept", "Take the chance"), ("refuse", "Keep the same amount")),
    ),
    "M02": (
        "Loss sensitivity",
        "Would you take a 50/50 chance of losing CHF 100 or gaining CHF 250?",
        "The possible loss stays at CHF 100. Only the possible gain changes.",
        (("accept", "Take the chance"), ("refuse", "Keep the same amount")),
    ),
    "A01": (
        "Ambiguity",
        "Which fictional offer would you choose?",
        "Both pay CHF 100 if you win and CHF 0 otherwise. You can skip this question.",
        (
            ("known", "Known chance of winning · 50%"),
            ("unknown", "Chance of winning · unknown"),
            ("either", "Either offer"),
        ),
    ),
}

BLOCKS = (
    (
        "comprehension",
        "Risk comprehension and perception",
        ("C01", "C02", "P01", "P02"),
    ),
    ("tradeoff", "Return–risk trade-off", ("V01", "V02", "G11", "G12")),
    ("loss", "Loss sensitivity", ("L00", "M01", "M02")),
    (
        "drawdown",
        "Reaction after a decline",
        ("D01", "D02", "D03", "D04", "D05", "D06"),
    ),
    ("ambiguity", "Ambiguity", ("A01",)),
)


def assess_blocks(answers, *, understood):
    perception = answers.get("P01")
    if perception == "narrow" and answers.get("P02") == "wide":
        perception = "wide"
    comprehension = (
        (100 if perception == "wide" else 50 if perception == "narrow" else None)
        if understood
        else 0
        if answers.get("C01") == answers.get("C02") == "no"
        else None
    )
    first, second = (answers.get(key) for key in ("V01", "V02"))
    if (first, second) == ("lower", "wider"):
        tradeoff = None
    elif "neither" in (first, second):
        tradeoff = None if "wider" in (first, second) else 0
    elif all(choice in ("lower", "wider") for choice in (first, second)):
        tradeoff = 50 * (int(first == "wider") + int(second == "wider"))
    else:
        tradeoff = None

    loss = {
        ("accept", "accept"): 0,
        ("refuse", "accept"): 50,
        ("refuse", "refuse"): 100,
    }.get((answers.get("M01"), answers.get("M02")))
    drawdown = {"keep": 100, "review": 50, "reduce": 0}.get(answers.get("D01"))
    ambiguity = {"known": 0, "either": 50, "unknown": 100}.get(answers.get("A01"))
    scores = (comprehension, tradeoff, loss, drawdown, ambiguity)
    blocks = [
        {"id": key, "label": label, "score": score, "cards": ids}
        for (key, label, ids), score in zip(BLOCKS, scores, strict=True)
    ]

    # Missing secondary measures are omitted. Both return–risk choices drive the label.
    parts = [
        (score, weight)
        for score, weight in (
            (tradeoff, 7),
            (drawdown, 2),
            (None if loss is None else 100 - loss, 1),
        )
        if score is not None
    ]
    overall = (
        round(
            sum(score * weight for score, weight in parts)
            / sum(weight for _, weight in parts)
        )
        if comprehension == 100 and tradeoff is not None and len(parts) >= 2
        else None
    )
    return blocks, overall
