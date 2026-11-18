import json
from dataclasses import replace

import numpy as np
import pytest

from src.adaptive_profile import AversionPosterior, card_model, ordered_probabilities, swipe_probabilities
from src.paths import QUESTIONS
from src.questionnaire import load_question_bank


def test_complete_bank_and_invalid_branch(tmp_path):
    bank = load_question_bank()
    assert len(bank) == len({card["id"] for card in bank}) == 60
    malformed = json.loads((QUESTIONS / "bank.json").read_text())
    malformed["blocks"]["D"]["questions"][1]["condition"]["equals"] = "missing"
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(malformed))
    with pytest.raises(ValueError, match="prerequisite"):
        load_question_bank(path)


def test_swipe_indifference_and_ordered_direction():
    card = load_question_bank()[40]
    assert card["bloc"] == "C"
    threshold = card["params"]["phi_seuil"]
    pair = swipe_probabilities(np.log([threshold / 2, threshold, threshold * 2]), card)
    np.testing.assert_allclose(pair.sum(axis=0), 1)
    assert pair[1, 0] > .5 and pair[1, 1] == pytest.approx(.5) and pair[1, 2] < .5
    scale = ordered_probabilities([-2, 0, 2], 1.2, [1, 0, -1])
    np.testing.assert_allclose(scale.sum(axis=0), 1)
    assert (scale >= 0).all() and np.all(np.diff(scale[-1]) < 0)
    with pytest.raises(ValueError, match="descending"):
        ordered_probabilities([0], 1, [-1, 0, 1])


def test_posterior_updates_and_skips():
    prior = AversionPosterior.prior()
    b = load_question_bank()[10]
    _, likelihoods = card_model(prior.theta, b)
    cautious = prior.update(likelihoods[0])
    assert cautious.mass.sum() == pytest.approx(1)
    assert cautious.summary()["phi_median"] > prior.summary()["phi_median"]
    assert prior.update(None) is prior
    with pytest.raises(ValueError, match="zero probability"):
        prior.update(np.zeros_like(prior.mass))
