"""Candidate calibration for research. The client studio keeps its current policy."""

from dataclasses import dataclass
from itertools import product

ANSWERS = ("yes", "no", "skip")


@dataclass(frozen=True)
class Card:
    id: str
    text: str


COMPREHENSION = (
    Card("C01", "Même avec une pièce équilibrée, je peux perdre au prochain lancer."),
    Card(
        "C02",
        "Après trois victoires, la manche suivante peut encore être perdue si le tirage est indépendant.",
    ),
)
TOLERANCE = (
    Card(
        "T01",
        "J’accepterais des fluctuations importantes si je n’avais pas besoin de cet argent pendant cinq ans.",
    ),
    Card(
        "T02",
        "Je choisirais un placement plus régulier même si son rendement espéré était plus faible.",
    ),
)
GAMBLES = (
    Card(
        "G01",
        "Sur une mise fictive de 1 000 CHF, je préfère recevoir 1 020 CHF avec certitude plutôt qu’une chance sur deux de recevoir 900 CHF ou 1 200 CHF.",
    ),
    Card(
        "G02",
        "Sur la même mise, je préfère recevoir 1 040 CHF avec certitude plutôt que tenter le même pari, 900 CHF ou 1 200 CHF à chances égales.",
    ),
    Card(
        "G03",
        "Sur la même mise, je préfère recevoir 1 030 CHF avec certitude plutôt que tenter le même pari, 900 CHF ou 1 200 CHF à chances égales.",
    ),
)
STRESS = (
    Card(
        "D01",
        "Après une baisse de 10 %, je garderais le portefeuille jusqu’à la prochaine revue si mes dépenses et mon objectif restent couverts.",
    ),
    Card(
        "D02",
        "Dans la même situation, après une baisse de 20 %, je garderais le portefeuille jusqu’à la prochaine revue.",
    ),
    Card(
        "D03",
        "Même si une revue confirme que mon objectif reste finançable, la baisse me donnerait envie de réduire le risque.",
    ),
)
MIXED_LOSSES = (
    Card(
        "L01",
        "Avec de l’argent fictif, j’accepterais une chance sur deux de perdre 100 CHF et une chance sur deux de gagner 150 CHF.",
    ),
    Card(
        "L02",
        "Avec de l’argent fictif, j’accepterais une chance sur deux de perdre 100 CHF et une chance sur deux de gagner 200 CHF.",
    ),
)
FRAMING = (
    Card(
        "F01",
        "Sur une mise de 1 000 CHF, je préfère finir à 1 000 CHF avec certitude plutôt qu’avoir une chance sur deux de finir à 900 CHF ou 1 100 CHF.",
    ),
    Card(
        "F02",
        "Sur la même mise, je préfère que mon argent reste inchangé plutôt qu’avoir une chance sur deux de perdre ou gagner 100 CHF.",
    ),
)
FLEXIBILITY = (
    Card(
        "H01",
        "Si mon objectif était difficile à atteindre, je pourrais repousser la date.",
    ),
    Card(
        "H02",
        "Si mon objectif était difficile à atteindre, je pourrais réduire le montant visé.",
    ),
)
MONITORING = (
    Card("S01", "J’aime vérifier souvent la valeur de mes placements."),
    Card("S02", "Entre deux revues prévues, une alerte de risque me suffirait."),
)
BANK = (
    COMPREHENSION
    + TOLERANCE
    + GAMBLES
    + STRESS
    + MIXED_LOSSES
    + FRAMING
    + FLEXIBILITY
    + MONITORING
)


def _comprehension(a):
    return COMPREHENSION[:1] if a.get("C01") == "yes" else COMPREHENSION


def _understands(a):
    return "yes" in (a.get("C01"), a.get("C02"))


def _gambles(a):
    first, second = (a.get(key) for key in ("G01", "G02"))
    return GAMBLES[:2] if first == second and first in ("yes", "no") else GAMBLES


def _stress(a):
    return STRESS[:2] if a.get("D01") == a.get("D02") == "yes" else STRESS


def _monitoring(a):
    return MONITORING if a.get("S01") == "yes" else MONITORING[:1]


def next_card(answers):
    """Replay the route in order. Only active earlier answers can open a branch."""
    seen = {}

    def groups():
        yield _comprehension({})
        yield TOLERANCE
        if _understands(seen):
            yield GAMBLES
        yield STRESS
        if _understands(seen):
            yield MIXED_LOSSES
            yield FRAMING
        yield FLEXIBILITY
        yield MONITORING

    conditional = {
        "C02": lambda: len(_comprehension(seen)) == 2,
        "G03": lambda: len(_gambles(seen)) == 3,
        "D03": lambda: len(_stress(seen)) == 3,
        "S02": lambda: len(_monitoring(seen)) == 2,
    }
    for group in groups():
        for card in group:
            if card.id in conditional and not conditional[card.id]():
                continue
            if card.id not in answers:
                return card, seen
            if answers[card.id] not in ANSWERS:
                raise ValueError(f"Invalid answer for {card.id}.")
            seen[card.id] = answers[card.id]
    return None, seen


def _score(answers, keys, favourable, minimum=1):
    values = [
        100 * (answers[k] == direction)
        for k, direction in zip(keys, favourable, strict=True)
        if answers.get(k) in ("yes", "no")
    ]
    return round(sum(values) / len(values)) if len(values) >= minimum else None


def assess(answers):
    """Return descriptive scores, evidence and issues from active answers."""
    remaining, a = next_card(answers)
    understood = _understands(a)
    conflict_g = any(
        a.get(lo) == "yes" and a.get(hi) == "no"
        for lo, hi in (("G01", "G03"), ("G01", "G02"), ("G03", "G02"))
    )
    conflict_d = a.get("D01") == "no" and a.get("D02") == "yes"
    conflict_l = a.get("L01") == "yes" and a.get("L02") == "no"
    paired = all(a.get(k) in ("yes", "no") for k in ("F01", "F02"))
    scores = {
        "comprehension": 100
        if understood
        else 0
        if a.get("C01") == a.get("C02") == "no"
        else None,
        "tolerance": _score(a, ("T01", "T02"), ("yes", "no"), 2),
        "arbitrage": None
        if conflict_g
        else _score(a, ("G01", "G02", "G03"), ("no",) * 3, 2),
        "maintien": None if conflict_d else _score(a, ("D01", "D02"), ("yes",) * 2, 2),
        "reticence_pertes": None
        if conflict_l
        else _score(a, ("L01", "L02"), ("no",) * 2, 2),
        "concordance_cadrage": 100 * (a["F01"] == a["F02"]) if paired else None,
        "souplesse": _score(a, ("H01", "H02"), ("yes",) * 2),
        "suivi_frequent": _score(a, ("S01",), ("yes",)),
    }
    evidence = {
        key: {
            "answered": sum(a.get(card.id) in ("yes", "no") for card in cards),
            "shown": sum(card.id in a for card in cards),
        }
        for key, cards in zip(
            scores,
            (
                COMPREHENSION,
                TOLERANCE,
                GAMBLES,
                STRESS,
                MIXED_LOSSES,
                FRAMING,
                FLEXIBILITY,
                MONITORING,
            ),
            strict=True,
        )
    }
    core = [scores[k] for k in ("tolerance", "arbitrage", "maintien")]
    overall = (
        round(sum(core) / len(core))
        if not remaining and understood and None not in core
        else None
    )
    flags = [
        label
        for issue, label in (
            (not understood, "comprehension_a_revoir"),
            (conflict_g, "arbitrages_incoherents"),
            (conflict_d, "reaction_aux_baisses_a_revoir"),
            (conflict_l, "choix_de_pertes_mixtes_a_revoir"),
            (
                paired and scores["concordance_cadrage"] == 0,
                "reponse_sensible_au_cadrage",
            ),
            (a.get("D03") == "yes", "inconfort_apres_revue"),
            (
                None not in core and max(core) - min(core) >= 67,
                "ecart_entre_dimensions",
            ),
        )
        if issue
    ]
    return {
        "scores": scores,
        "evidence": evidence,
        "willingness": overall,
        "alerts_suffice": a.get("S02"),
        "status": "en_cours"
        if remaining
        else "a_revoir"
        if overall is None
        else "a_confirmer"
        if "ecart_entre_dimensions" in flags
        else "interpretable",
        "flags": flags,
        "active_answers": a,
        "answered": sum(answer != "skip" for answer in a.values()),
        "shown": len(a),
    }


def _terminal(route):
    """Enumerate a small block including Uncertain and yield each complete branch."""

    def traverse(a):
        missing = next((card for card in route(a) if card.id not in a), None)
        if missing is None:
            yield a
            return
        for answer in ANSWERS:
            yield from traverse(a | {missing.id: answer})

    return list(traverse({}))


def count_routes():
    """Count first-pass terminal histories by length, factoring independent blocks."""
    comprehension = _terminal(_comprehension)
    stress = _terminal(_stress)
    monitoring = _terminal(_monitoring)
    gambles = _terminal(_gambles)
    totals = {}
    for c, d, s in product(comprehension, stress, monitoring):
        qualifies = _understands(c)
        fixed = (
            (TOLERANCE, FLEXIBILITY, MIXED_LOSSES, FRAMING)
            if qualifies
            else (TOLERANCE, FLEXIBILITY)
        )
        fixed_count = sum(map(len, fixed))
        for g in gambles if qualifies else ({},):
            length = fixed_count + len(c) + len(d) + len(s) + len(g)
            totals[length] = totals.get(length, 0) + len(ANSWERS) ** fixed_count
    return dict(sorted(totals.items()))
