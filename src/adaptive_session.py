"""Pick the next informative card and manage a bounded adaptive session."""

from collections.abc import Mapping

import numpy as np

from .adaptive_profile import DEFAULT_SHARPNESS, AversionPosterior, card_model
from .fixed_profile import assess_financial_capacity
from .profiling import RiskTarget, risk_target
from .questionnaire import available_constraint_cards, load_question_bank

MAX_CARDS = 15
PRECISION_THRESHOLD = .20
MIRROR_ID = "C_mirror"


def tolerance_formats(asked: Mapping) -> tuple[str, ...]:
    """Protect the two-card minimum across both tolerance formats."""
    count_b = sum(key.startswith("B") for key in asked)
    count_c = sum(key.startswith("C") and key != MIRROR_ID for key in asked)
    if count_b < 2 <= count_c:
        return ("B",)
    if count_c < 2 <= count_b:
        return ("C",)
    return ("B", "C")


class VarianceSelector:
    """Cache likelihood rows on a shared grid for selection and updating."""

    def __init__(self, theta: np.ndarray, cards: tuple[dict, ...],
                 sharpness: float = DEFAULT_SHARPNESS):
        self.cards = {card["id"]: card for card in cards if card["bloc"] in ("B", "C")}
        self.models = {key: card_model(theta, card, sharpness) for key, card in self.cards.items()}
        self.ids = tuple(self.cards)
        self.likelihoods = np.stack([
            np.pad(matrix, ((0, 4 - len(matrix)), (0, 0)))
            for _, matrix in self.models.values()
        ])

    def choose(self, posterior: AversionPosterior, answered: Mapping,
               allowed: tuple[str, ...] = ("B", "C")) -> dict:
        """Minimize expected posterior variance among eligible unanswered items."""
        usable = [i for i, key in enumerate(self.ids) if key not in answered and key[0] in allowed]
        if not usable:
            raise ValueError("no eligible tolerance cards")
        matrices = self.likelihoods[usable]
        probability = np.einsum("ijk,k->ij", matrices, posterior.mass)
        first_moment = np.einsum("ijk,k->ij", matrices, posterior.mass * posterior.theta)
        # The unconditional second moment is shared by all items, so
        # maximizing the expected squared posterior mean minimizes variance.
        score = np.divide(first_moment**2, probability, out=np.zeros_like(probability),
                          where=probability > 0).sum(axis=1)
        return self.cards[self.ids[usable[int(score.argmax())]]]

    def observe(self, posterior: AversionPosterior, key: str, answer: str) -> AversionPosterior:
        if answer == "unsure":
            return posterior
        choices, rows = self.models[key]
        return posterior.update(rows[choices.index(answer)])


class AdaptiveSession:
    """Four capacity cards, eligible constraint cards and adaptive tolerance."""

    def __init__(self):
        self.cards = load_question_bank()
        self.answers = {}
        self.posterior = AversionPosterior.prior()
        self.selector = VarianceSelector(self.posterior.theta, self.cards)
        self.original_swipe = None
        self.inconsistent = False

    @property
    def message(self) -> str | None:
        if self.inconsistent:
            return "Your choices differed when the options switched sides. The risk estimate uses a softer response model."
        return None

    def next_card(self) -> dict | None:
        for card in self.cards[:4]:
            if card["id"] not in self.answers:
                return card
        pending = available_constraint_cards(self.answers)
        if pending:
            return pending[0]

        informative = [key for key in self.answers if key in self.selector.cards]
        count_b = sum(key.startswith("B") for key in informative)
        count_c = len(informative) - count_b
        enough = count_b >= 2 and count_c >= 2
        if len(self.answers) >= MAX_CARDS:
            return None
        precision_reached = enough and self.posterior.summary()["theta_sd"] < PRECISION_THRESHOLD

        if MIRROR_ID not in self.answers and self.original_swipe is not None and (
                len(self.answers) == MAX_CARDS - 1 or precision_reached):
            original = self.selector.cards[self.original_swipe]
            order = original["params"]["display_order"][::-1]
            return {**original, "id": MIRROR_ID,
                    "params": {**original["params"], "display_order": order}}
        if precision_reached:
            return None

        return self.selector.choose(self.posterior, self.answers, tolerance_formats(self.answers))

    def estimated_target(self, reference_sharpe: float) -> RiskTarget:
        """Apply the financial ceiling to the posterior median after completion."""
        if self.next_card() is not None:
            raise ValueError("complete the adaptive session before classifying it")
        if not any(key in self.selector.cards and response != "unsure"
                   for key, response in self.answers.items()):
            raise ValueError("at least one tolerance response is required")
        capacity_answers = {
            card["params"]["fixed_question"]: self.answers[card["id"]]
            for card in self.cards[:4]
        }
        capacity = assess_financial_capacity(capacity_answers)
        return risk_target(self.posterior.summary()["phi_median"],
                           reference_sharpe, capacity.volatility)

    def answer(self, key: str, choice: str | list[str]) -> None:
        card = self.next_card()
        if card is None or card["id"] != key:
            raise ValueError("answer must match the next eligible card")
        options = card["options"]
        if card["type"] == "multiple":
            exclusive = set(card["params"]["exclusive_option_ids"])
            valid = (isinstance(choice, list) and bool(choice)
                     and all(isinstance(value, str) and value in options for value in choice)
                     and len(set(choice)) == len(choice)
                     and (len(choice) == 1 or not set(choice) & exclusive))
        else:
            valid = isinstance(choice, str) and (
                choice in options or (card["type"] == "swipe" and choice == "unsure"))
        if not valid:
            raise ValueError("invalid answer for this card")
        self.answers[key] = choice.copy() if isinstance(choice, list) else choice
        if key == MIRROR_ID:
            self.inconsistent = choice not in ("unsure", self.answers[self.original_swipe])
            if self.inconsistent:
                self.selector = VarianceSelector(self.posterior.theta, self.cards, DEFAULT_SHARPNESS / 2)
                self.posterior = AversionPosterior.prior()
                for original, response in self.answers.items():
                    if original in self.selector.cards:
                        self.posterior = self.selector.observe(self.posterior, original, response)
        elif key in self.selector.cards:
            self.posterior = self.selector.observe(self.posterior, key, choice)
            if card["bloc"] == "C" and choice != "unsure" and self.original_swipe is None:
                self.original_swipe = key
