"""Extended French research bank, with ordered and conditional follow-ups."""

from dataclasses import dataclass

from . import questionnaire_pilot as pilot

MAX_CARDS = 40


@dataclass(frozen=True)
class Prompt:
    id: str
    block: str
    text: str
    trigger: str
    like: str
    passed: str


@dataclass(frozen=True)
class Ladder:
    prompts: tuple[Prompt, ...]
    levels: tuple[int, ...]


PORTFOLIO_CASES = (
    ("Court · resserré", 1, 3, 6, 12),
    ("Court · dispersé", 1, 3, 8, 16),
    ("Intermédiaire · resserré", 3, 9, 12, 24),
    ("Intermédiaire · dispersé", 3, 9, 16, 32),
    ("Long · resserré", 5, 15, 20, 40),
    ("Long · dispersé", 5, 15, 25, 50),
)
DECLINE_CONTEXTS = (
    "le plan et les perspectives restent inchangés et mes dépenses sont couvertes",
    "une dépense importante approche et la réserve en CHF la couvre intégralement",
    "les marchés baissent en même temps et aucune perspective n’a été révisée",
    "la baisse vient d’un actif détenu et une revue confirme que l’objectif reste finançable",
)
MIXED_STAKES = (50, 100, 200)
UNDERSTANDING = (
    (
        "Sur 10 000 CHF, une baisse de 10 % représente 1 000 CHF.",
        "correspondance entre pourcentage et CHF",
    ),
    (
        "Avec 20 000 CHF, une baisse de 15 % représente 1 500 CHF.",
        "correspondance entre pourcentage et CHF",
    ),
    (
        "Après une baisse de 20 %, un portefeuille ne peut plus baisser.",
        "absence de plancher imposé par une baisse passée",
    ),
    (
        "Une perte possible à 10 % de probabilité pourrait se produire dès le premier essai.",
        "distinction entre faible probabilité et impossibilité",
    ),
    (
        "Si deux événements indépendants ont chacun 50 % de chances de succès, réussir le premier ne garantit pas de réussir le suivant.",
        "indépendance",
    ),
    (
        "Un résultat moyen de +5 % permet aussi des résultats négatifs.",
        "distinction entre moyenne et garantie",
    ),
    (
        "Un portefeuille peut avoir un rendement espéré positif et finir en baisse.",
        "distinction entre espérance et résultat observé",
    ),
    (
        "Un retrait de 1 000 CHF indique que les placements ont perdu 1 000 CHF, même si les cours sont restés stables.",
        "distinction entre retrait et perte de marché",
    ),
    (
        "Passer de 10 000 à 8 000 CHF représente une baisse de 20 %.",
        "lecture d’une baisse à partir du solde initial",
    ),
    (
        "Après une baisse de 20 %, il faut une hausse de 20 % pour retrouver le point de départ.",
        "asymétrie des variations successives",
    ),
)
AMBIGUITY_CASES = (
    "un fonds diversifié",
    "un fonds actions",
    "un fonds obligataire",
    "un portefeuille mixte",
)


def _portfolio():
    for case, (name, years, centre, narrow, wide) in enumerate(PORTFOLIO_CASES):
        base = (
            f"Deux portefeuilles fictifs en CHF sur {years} an(s), avec les mêmes frais et possibilités de retrait. "
            f"A donne {centre - narrow:+d} % ou {centre + narrow:+d} % et B donne "
        )
        levels = tuple(step * years for step in range(5))
        yield Ladder(
            tuple(
                Prompt(
                    f"P{case + 1}{step}",
                    "Arbitrage de portefeuille",
                    base
                    + f"{centre + gain - wide:+d} % ou {centre + gain + wide:+d} %, "
                    "chaque résultat à une chance sur deux pour le portefeuille concerné. Je choisirais B.",
                    f"Compréhension établie. Série {name}. L’algorithme resserre l’écart de rendement testé.",
                    "Accepte ici la dispersion supérieure pour cette compensation.",
                    "Rejette B dans cette comparaison. Le seuil testé est insuffisant ou la préférence reste à préciser.",
                )
                for step, gain in enumerate(levels)
            ),
            levels,
        )


def _declines():
    levels = (5, 12, 15, 25, 30)
    for case, context in enumerate(DECLINE_CONTEXTS):
        yield Ladder(
            tuple(
                Prompt(
                    f"R{case + 1}{step}",
                    "Réaction après une baisse",
                    f"Après une baisse de {loss} %, je garderais mon portefeuille jusqu’à la prochaine revue si {context}.",
                    "Maintien nuancé ou incertain après les scénarios de 10 % et 20 %. Contexte tenu fixe dans la série.",
                    "Maintien déclaré jusqu’à la revue dans ce scénario.",
                    "Le maintien jusqu’à la revue ne convient pas. Le motif reste à vérifier.",
                )
                for step, loss in enumerate(levels)
            ),
            levels,
        )


def _losses():
    multipliers = (1, 1.25, 1.75, 2.5, 3, 4)
    for case, loss in enumerate(MIXED_STAKES):
        levels = tuple(round(loss * x) for x in multipliers)
        yield Ladder(
            tuple(
                Prompt(
                    f"LX{case + 1}{step}",
                    "Sensibilité aux pertes",
                    f"Avec de l’argent fictif, j’accepterais une chance sur deux de perdre {loss} CHF "
                    f"et une chance sur deux de gagner {reward} CHF plutôt que garder mon montant initial.",
                    "Préférence pour la certitude, hésitation ou changement entre les deux gains de départ.",
                    "Accepte le pari mixte à ce rapport gain sur perte.",
                    "Rejette le pari mixte à ce rapport. La réponse ne permet pas d’isoler l’aversion aux pertes.",
                )
                for step, reward in enumerate(levels)
            ),
            levels,
        )


def _ambiguity():
    for case, name in enumerate(AMBIGUITY_CASES):
        for step, (loss, gain) in enumerate(((6, 12), (10, 20), (15, 30))):
            yield Prompt(
                f"A{case + 1}{step}",
                "Ambiguïté",
                f"Deux versions fictives de {name} peuvent perdre {loss} % ou gagner {gain} % sur la même période. "
                "Dans la première, les chances sont connues et égales. Dans la seconde, elles sont inconnues. "
                "Je préfère la version aux chances connues.",
                "Hésitation, préférence marquée pour la certitude ou incohérence de cadrage.",
                "Préfère ici les probabilités connues. Cela guide l’explication des scénarios.",
                "Ne privilégie pas ici la version aux probabilités connues. L’indifférence reste possible.",
            )


def _understanding():
    for i, (text, concept) in enumerate(UNDERSTANDING, 1):
        correct = f"Réponse correcte sur {concept}."
        incorrect = f"Réponse incorrecte sur {concept}. Reformuler avant d’interpréter les arbitrages."
        if i in (2, 3, 8, 10):
            correct, incorrect = incorrect, correct
        yield Prompt(
            f"CX{i:02}",
            "Compréhension et perception",
            text,
            "Compréhension encore indéterminée après C01 et C02.",
            correct,
            incorrect,
        )


def _framing():
    for case, (stake, swing) in enumerate(
        ((2000, 100), (2000, 300), (5000, 250), (5000, 750))
    ):
        start = f"Avec une mise fictive de {stake} CHF, "
        for mode, wording in enumerate(
            (
                (
                    f"je préfère finir à {stake} CHF avec certitude plutôt qu’avoir une chance sur deux de finir "
                    f"à {stake - swing} CHF ou {stake + swing} CHF."
                ),
                (
                    f"je préfère que mon argent reste inchangé plutôt qu’avoir une chance sur deux de perdre "
                    f"ou gagner {swing} CHF."
                ),
            )
        ):
            yield Prompt(
                f"FX{case + 1}{mode}",
                "Cadrage",
                start + wording,
                "Réponses différentes ou incertaines sur les deux formulations du pilote.",
                "Préférence pour la certitude dans cette formulation. Comparer avec la carte jumelle.",
                "Choix du pari dans cette formulation. Comparer avec la carte jumelle.",
            )


PORTFOLIO = tuple(_portfolio())
DECLINES = tuple(_declines())
LOSSES = tuple(_losses())
AMBIGUITY = tuple(_ambiguity())
UNDERSTANDING_PROMPTS = tuple(_understanding())
FRAMING_PROMPTS = tuple(_framing())
FOLLOW_UPS = (
    UNDERSTANDING_PROMPTS
    + tuple(
        p
        for pool in (PORTFOLIO, DECLINES, LOSSES)
        for ladder in pool
        for p in ladder.prompts
    )
    + AMBIGUITY
    + FRAMING_PROMPTS
)

PERCEPTION = tuple(
    Prompt(
        f"PX{i}",
        "Compréhension et perception",
        statement,
        "La compréhension est établie. La variante d’étude détermine le risque examiné.",
        "Ce risque compte davantage dans la perception déclarée.",
        "Le joueur ne reconnaît pas cette priorité. La réponse renseigne la perception sans points.",
    )
    for i, statement in enumerate(
        (
            "À rendement espéré égal, un portefeuille pouvant perdre davantage me paraît plus risqué.",
            "À perte maximale égale, un portefeuille qui peut baisser plus souvent me paraît plus risqué.",
            "Un placement en USD sans couverture me paraît plus risqué pour un objectif en CHF.",
            "À possibilités de gain identiques, une forte concentration sur une entreprise me paraît plus risquée.",
            "À variation de cours identique, un placement difficile à vendre rapidement me paraît plus risqué.",
            "Deux actifs dont les pertes arrivent généralement en même temps me paraissent moins diversifiants.",
        ),
        1,
    )
)
DECLINE_MOTIVES = tuple(
    Prompt(
        f"RX{i}",
        "Réaction après une baisse",
        statement,
        "Le maintien est incertain ou le joueur déclare vouloir réduire le risque après revue.",
        "Ce motif peut expliquer la décision. Le profil présente cette lecture sans recalculer la capacité de perte.",
        "Le joueur ne confirme pas ce motif. Aucun motif opposé n’est déduit automatiquement.",
    )
    for i, statement in enumerate(
        (
            "Je réduirais surtout la position pour obtenir des liquidités si la réserve en CHF ne suffisait plus.",
            "Je réduirais surtout la position si les nouvelles prévisions rendaient mon objectif difficile à financer.",
            "Même sans changer les prévisions ni la réserve, une nouvelle baisse me ferait réduire la position pour retrouver du confort.",
            "Je réexaminerais surtout une baisse lorsqu’elle vient d’une seule position devenue trop importante.",
        ),
        1,
    )
)
FOLLOW_UPS += PERCEPTION + DECLINE_MOTIVES

# The same eight blocks retain the anchor cards' original scoring.
ANCHOR_BLOCKS = (
    pilot.COMPREHENSION,
    pilot.TOLERANCE,
    pilot.GAMBLES,
    pilot.STRESS,
    pilot.MIXED_LOSSES,
    pilot.FRAMING,
    pilot.FLEXIBILITY,
    pilot.MONITORING,
)


def _offers(answers, ladder, *, increasing, rounds=3, low=None, high=None):
    """Choose a midpoint within the informative scenario range after each response."""
    options = dict(zip(ladder.levels, ladder.prompts, strict=True))
    lower = low if low is not None else min(options) - 1
    upper = high if high is not None else max(options) + 1
    for _ in range(rounds):
        available = [k for k in options if lower < k < upper]
        if not available:
            return
        level = available[len(available) // 2]
        card = options.pop(level)
        yield card
        answer = answers.get(card.id)
        if answer not in ("yes", "no"):
            return
        if (answer == "yes") == increasing:
            upper = level
        else:
            lower = level


def _follow_ups(index, known, *, form, horizon):
    if index == 0:
        if "yes" in (known.get("C01"), known.get("C02")):
            yield PERCEPTION[form % len(PERCEPTION)]
        else:
            for offset in (0, 5):
                yield UNDERSTANDING_PROMPTS[
                    (form + offset) % len(UNDERSTANDING_PROMPTS)
                ]
    elif index == 2 and "G01" in known:
        horizon_pair = 0 if horizon <= 2 else 2 if horizon <= 4 else 4
        yield from _offers(known, PORTFOLIO[horizon_pair + form % 2], increasing=True)
    elif index == 3 and not (known.get("D01") == known.get("D02") == "yes"):
        context = DECLINES[form % len(DECLINES)]
        if known.get("D01") == "yes" and known.get("D02") == "no":
            # Only the unchanged-plan context matches the base scenarios.
            yield from _offers(known, DECLINES[0], increasing=False, low=10, high=20)
        else:
            yield from _offers(known, context, increasing=False)
        if known.get("D03") != "no":
            yield DECLINE_MOTIVES[form % len(DECLINE_MOTIVES)]
    elif index == 4 and "L01" in known:
        if not (known.get("L01") == known.get("L02") == "yes"):
            yield from _offers(known, LOSSES[form % len(LOSSES)], increasing=True)
    elif index == 5 and "F01" in known:
        first, second = known.get("F01"), known.get("F02")
        if first != second or "skip" in (first, second):
            offset = 2 * (form % (len(FRAMING_PROMPTS) // 2))
            pair = FRAMING_PROMPTS[offset : offset + 2]
            yield from pair if form // 4 % 2 == 0 else reversed(pair)
        if first != second or known.get("G01") != "no" or known.get("G02") != "no":
            yield AMBIGUITY[form % len(AMBIGUITY)]


_DRAWDOWN_CHOICES = (
    ("keep", "Je garde le portefeuille", "yes"),
    ("reduce", "Je réduis le risque", "no"),
    ("review", "Je revois le plan avant d’agir", "skip"),
)
_PORTFOLIO_CHOICES = (
    ("portfolio_a", "Je choisis le portefeuille A", "no"),
    ("portfolio_b", "Je choisis le portefeuille B", "yes"),
)
_CERTAINTY_CHOICES = (
    ("certain", "Je choisis le montant certain", "yes"),
    ("gamble", "Je choisis le pari", "no"),
)
_MIXED_CHOICES = (
    ("retain_stake", "Je garde ma mise", "no"),
    ("take_mixed_gamble", "J’accepte le pari", "yes"),
)


def decision_options(card_id):
    """Named options for decisions where a generic Pass would be ambiguous."""
    if card_id in {"D01", "D02"} or (card_id.startswith("R") and card_id[1:].isdigit()):
        return _DRAWDOWN_CHOICES
    if card_id.startswith("P") and card_id[1:].isdigit():
        return _PORTFOLIO_CHOICES
    if card_id.startswith(("G", "F")):
        return _CERTAINTY_CHOICES
    if card_id.startswith("L"):
        return _MIXED_CHOICES
    return ()


def _canonical(answers):
    return {
        key: next(
            (binary for value, _, binary in decision_options(key) if response == value),
            response,
        )
        for key, response in answers.items()
    }


def next_card(answers, *, form=0, horizon=5, limit=MAX_CARDS):
    """Return the next prompt and active answers. A form controls study counterbalancing."""
    if (
        type(form) is not int
        or form < 0
        or type(limit) is not int
        or not 8 <= limit <= MAX_CARDS
    ):
        raise ValueError("Invalid research form or card limit.")
    answers = _canonical(answers)
    anchor_next, anchors = pilot.next_card(answers)
    next_id = anchor_next.id if anchor_next else None
    active = {}
    for index, block in enumerate(ANCHOR_BLOCKS):
        for card in block:
            if len(active) >= limit:
                return None, active
            if card.id == next_id:
                return card, active
            if card.id in anchors:
                active[card.id] = anchors[card.id]
        # Keep a live view that excludes unanswered and obsolete relaunches.
        for card in _follow_ups(index, active, form=form, horizon=horizon):
            if len(active) >= limit:
                return None, active
            if card.id not in answers:
                return card, active
            answer = answers[card.id]
            if answer not in pilot.ANSWERS:
                raise ValueError(f"Invalid answer for {card.id}.")
            active[card.id] = answer
    return None, active


def assess(answers, **route):
    """Keep anchor scores comparable and report all selected follow-ups independently."""
    remaining, active = next_card(answers, **route)
    report = pilot.assess(active)
    if remaining is None and report["status"] == "en_cours":
        report["status"] = "limite_atteinte"
    decisions = {
        key: label
        for key in active
        for value, label, _ in decision_options(key)
        if answers[key] == value
    }
    follow_up_choices = {}
    for card in FOLLOW_UPS:
        if card.id in active:
            answer = active[card.id]
            reading = {"yes": card.like, "no": card.passed, "skip": "Indéterminé."}[
                answer
            ]
            if answers[card.id] == "review":
                reading = "Réexaminer le plan avant d’agir. Le seuil de baisse reste à préciser."
            follow_up_choices[card.id] = {
                "block": card.block,
                "answer": answer,
                "reading": reading,
                "decision": decisions.get(card.id),
            }
    return report | {
        "next": remaining.id if remaining else None,
        "extended_count": len(active),
        "follow_ups": follow_up_choices,
        "decisions": decisions,
    }
