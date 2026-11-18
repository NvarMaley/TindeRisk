"""Build the fixed grid of paired choices for the adaptive questionnaire."""

STARTING_CHF = 1_000
CARD_COUNT = 24
MIN_AVERSION = .5
MAX_AVERSION = 20.


def build_swipe_cards() -> list[dict]:
    """Generate hypothetical one-year pairs using model units behind the scenes."""
    cards = []
    for index in range(CARD_COUNT):
        phi = round(MIN_AVERSION * (MAX_AVERSION / MIN_AVERSION) ** (index / (CARD_COUNT - 1)), 12)
        # Vary the spread, while bounding it at high thresholds so that the
        # wider option still has a worse outcome in the bad state.
        volatility_a = min((.05, .06, .07, .08)[index % 4], .30 / phi)
        volatility_b = min((.12, .14, .13, .15)[index % 4], .85 / phi)
        mean_a = .20 * volatility_a
        mean_b = mean_a + .5 * phi * (volatility_b**2 - volatility_a**2)
        options = {}
        for label, mean, volatility in (("A", mean_a, volatility_a), ("B", mean_b, volatility_b)):
            options[label] = {
                "mu": round(mean, 12),
                "sigma": round(volatility, 12),
                "outcomes_chf": [round(STARTING_CHF * (mean - volatility), 2),
                                 round(STARTING_CHF * (mean + volatility), 2)],
            }
        cards.append({
            "id": f"C{index + 1:02}",
            "bloc": "C",
            "type": "swipe",
            "dimension": "tolerance",
            "texte": "Which option would you choose for CHF 1,000 over one year?",
            "options": options,
            "params": {
                "phi_seuil": phi,
                "starting_chf": STARTING_CHF,
                "horizon_years": 1,
                "outcome_probabilities": [.5, .5],
                "display_order": ["A", "B"] if index % 2 == 0 else ["B", "A"],
                "skip_label": "Skip this card",
            },
            "condition": None,
        })
    return cards
