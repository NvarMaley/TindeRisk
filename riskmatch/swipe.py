"""Turn a canonical scenario into a single statement with a stable yes/no gesture."""


def prompt(card, order, step, facts):
    key = card["id"]
    if key.startswith(("A", "L", "V")):
        if key.startswith("V"):
            stake, certain, outcomes = (
                card[k] for k in ("stake_CHF", "certain_CHF", "outcomes_CHF")
            )
        else:
            stake, certain, outcomes = (
                card[k] for k in ("stake", "certain", "outcomes")
            )
        probabilities = card.get("probabilities", [0.5, 0.5])
        lottery = " or ".join(
            f"CHF {value:,} ({p:.0%} chance)"
            for value, p in zip(outcomes, probabilities, strict=True)
        )
        yes = order[1]
        context = f"Invest CHF {stake:,} for one year. The guaranteed balance is CHF {certain:,}. With the uncertain investment, you finish with {lottery}."
        if step == 2:
            return {
                "context": context,
                "text": "I would need more explanation to compare these outcomes.",
                "left": -1,
                "right": 3,
                "pass": -1,
            }
        if step == 1:
            return {
                "context": context,
                "text": "Both outcomes work equally well for me.",
                "left": None,
                "right": 2,
                "pass": -1,
            }
        return {
            "context": context,
            "text": "I would take the guaranteed balance."
            if yes == 0
            else "I would take the uncertain investment.",
            "left": order[0],
            "right": yes,
            "pass": None,
        }
    data = card["swipe"]
    steps = data["statements"]
    if key == "F07" and facts["currency"] != "Undecided":
        currency = facts["currency"]
        code = (
            facts["other_currency"].strip().upper() if currency == "Other" else currency
        )
        if code:
            index = ["CHF", "EUR", "USD", "Other"].index(currency)
            return {
                "context": data["context"],
                "text": f"I expect to pay this expense in {code}.",
                "right": index,
                "left": -1,
                "pass": -1,
            }
    current = steps[step]
    return {
        "context": data["context"],
        "text": current["text"],
        "right": current["agree"],
        "left": current.get("disagree", None if step + 1 < len(steps) else -1),
        "pass": -1,
    }
