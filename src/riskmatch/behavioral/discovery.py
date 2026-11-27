"""Fixed experimental Discovery questionnaire and provisional score."""

from collections import Counter
from itertools import zip_longest
from math import floor

VERSION = "discovery-v3.0.0"
QUOTAS = {"mixed": 8, "gains": 6, "losses": 6, "rare": 4, "trajectory": 4, "checks": 2}
CHOICES = {"like", "dislike", "unsure", "skip"}
LABELS = {
    "mixed": ("Possible gains and losses", "Gains et pertes possibles"),
    "gains": ("Risk with gains", "Risque face aux gains"),
    "losses": ("Risk with losses", "Risque face aux pertes"),
    "rare": ("Rare events", "Événements rares"),
    "trajectory": ("Temporary declines", "Baisses temporaires"),
    "checks": ("Choice checks", "Vérification des choix"),
}


def alt(en, fr, *, outcomes=(), probabilities=(), horizon_days=0, path=None, cost=0):
    return dict(en=en, fr=fr, outcomes=list(outcomes), probabilities=list(probabilities),
                expected_payoff=sum(x*p for x,p in zip(outcomes,probabilities)) if outcomes and probabilities else None,
                horizon_days=horizon_days, path=path, annual_cost=cost)


def bank(currency="USD"):
    if currency not in {"USD", "CHF"}:
        raise ValueError("invalid_currency")
    blocks = {key: [] for key in QUOTAS}

    def card(id, block, dimension, a, b, scored=False, reference=10000, pair=None, swap=None):
        cards = blocks[block]
        cards.append(dict(id=id, version=VERSION, block_id=block, dimension=dimension,
                          currency=currency, reference_wealth=reference, canonical_a=a, canonical_b=b,
                          prudent_option="B" if scored else None, scored=scored, pair_id=pair,
                          swapped=len(cards) % 2 == 1 if swap is None else swap))

    def monetary(amount):
        word_en, word_fr = ("gain", "gagner") if amount > 0 else ("lose", "perdre")
        return word_en, word_fr, f"{abs(amount)} {currency}"

    def lottery(probability, amount, sure):
        word_en, word_fr, stake = monetary(amount)
        sure_en, sure_fr, certain = monetary(sure)
        return (
            alt(f"take a {probability}% chance to {word_en} {stake}, with no change otherwise",
                f"accepter {probability} % de chances de {word_fr} {stake}, avec un solde inchangé sinon",
                outcomes=(amount, 0), probabilities=(probability / 100, 1 - probability / 100)),
            alt(f"{sure_en} {certain} for sure", f"{sure_fr} {certain} à coup sûr",
                outcomes=(sure,), probabilities=(1,)),
        )

    unchanged = alt("keep your balance unchanged", "garder ton solde inchangé",
                    outcomes=(0,), probabilities=(1,))
    # Two ranges of stakes with four gain-to-loss ratios each.
    for i, (gain, loss) in enumerate(((150, 100), (500, 500), (100, 100), (1000, 500),
                                      (200, 100), (625, 500), (125, 100), (750, 500)), 1):
        gamble = alt(f"take a 50% chance to gain {gain} {currency} and a 50% chance to lose {loss} {currency}",
                     f"accepter 50 % de chances de gagner {gain} {currency} et 50 % de risques de perdre {loss} {currency}",
                     outcomes=(gain, -loss), probabilities=(.5, .5))
        card(f"MX{i:02}", "mixed", "mixed_loss_choices", gamble, unchanged, swap=i in {3, 4, 7, 8})

    gain_tasks = ((50, 200, 100), (25, 400, 80), (75, 160, 120),
                  (50, 600, 240), (25, 800, 220), (75, 400, 330))
    loss_tasks = ((50, -200, -100), (75, -160, -100), (25, -400, -100),
                  (50, -600, -320), (25, -800, -180), (75, -400, -330))
    for block, prefix, dimension, tasks in (("gains", "GN", "gain_risk", gain_tasks),
                                            ("losses", "LS", "loss_risk", loss_tasks)):
        for i, task in enumerate(tasks, 1):
            card(f"{prefix}{i:02}", block, dimension, *lottery(*task), scored=True)

    for i, task in enumerate(((1, -1000, -10), (1, 1000, 10),
                              (5, -1000, -50), (5, 1000, 50)), 1):
        card(f"RR{i:02}", "rare", "rare_loss" if task[1] < 0 else "rare_gain",
             *lottery(*task), scored=True, swap=i in {2, 3})

    for i, (deeper, smaller, ending) in enumerate((
        ((94, 85), (97, 95), (95, 112)),
        ((83, 91), (94, 97), (100, 116)),
        ((93, 82), (93, 93), (90, 120)),
        ((80, 85), (90, 97), (98, 108)),
    ), 1):
        def path_option(levels):
            low, high = ending
            first, second = levels
            return alt(f"{first} at 3 months, {second} at 6 months, then {low} or {high} at 1 year",
                       f"{first} à 3 mois, {second} à 6 mois, puis {low} ou {high} à 1 an",
                       outcomes=(low-100, high-100), probabilities=(.5, .5),
                       horizon_days=365, path=[100, first, second, low, high])
        card(f"TR{i:02}", "trajectory", "trajectory_tolerance",
             path_option(deeper), path_option(smaller), scored=True, reference=100)

    card("CT01", "checks", "comprehension",
         alt("answer «1 time on average»", "répondre « 1 fois en moyenne »"),
         alt("answer «10 times on average»", "répondre « 10 fois en moyenne »"), reference=0)
    anchor = blocks["gains"][0]
    card("CT02", "checks", "decision_consistency", anchor["canonical_a"], anchor["canonical_b"],
         pair=anchor["id"], swap=True)

    # Fixed order interleaves the five financial blocks. Keep the repeat at the end.
    groups = (blocks[name] for name in ("gains", "mixed", "trajectory", "losses", "rare"))
    items = [card for row in zip_longest(*groups) for card in row if card is not None]
    items.insert(5, blocks["checks"][0])
    items.append(blocks["checks"][1])
    return items


def session(seed, currency="USD"):
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("invalid_seed")
    presented = []
    for order, item in enumerate(bank(currency), 1):
        swap = item["swapped"]
        a, b = (item["canonical_b"], item["canonical_a"]) if swap else (item["canonical_a"], item["canonical_b"])
        en, fr = LABELS[item["block_id"]]
        presented.append({**item, "block": en, "a": a["en"], "b": b["en"],
                          "fr": {"block": fr, "a": a["fr"], "b": b["fr"]},
                          "display_a": a, "display_b": b, "presented_order": order,
                          "prudent_response": ("like" if swap else "dislike") if item["scored"] else None})
    assert Counter(c["block_id"] for c in presented) == QUOTAS
    return dict(version=VERSION,seed=seed,currency=currency,session_id=f"{VERSION}:{seed}:{currency}",cards=presented)


def canonical_choice(card, response):
    if response not in {"like","dislike"}:
        return None
    display_a=response=="like"
    return "A" if display_a != card["swapped"] else "B"


def round_score(value):
    return floor(value+.5)


def mixed_gain_thresholds(cards, decisions):
    series = {}
    for card in cards:
        if card["dimension"] != "mixed_loss_choices":
            continue
        gain, loss = card["canonical_a"]["outcomes"]
        series.setdefault(-loss, []).append((gain, decisions[card["id"]]))

    results = []
    for loss, choices in sorted(series.items()):
        refused = max((gain for gain, choice in choices if choice == "B"), default=None)
        accepted = min((gain for gain, choice in choices if choice == "A"), default=None)
        if refused is not None and accepted is not None:
            status = "range" if refused < accepted else "inconsistent"
        elif accepted is not None:
            status = "atMost"
        elif refused is not None:
            status = "above"
        else:
            status = "unanswered"
        results.append({"loss": loss, "status": status, "max_refused_gain": refused,
                        "min_accepted_gain": accepted, "answered": sum(choice is not None for _, choice in choices),
                        "total": len(choices)})
    return results


def score(seed, currency, responses, confidence=None, locales=None):
    if not isinstance(responses,dict) or any(v not in CHOICES for v in responses.values()):
        raise ValueError("Invalid responses")
    cards=session(seed,currency)["cards"]
    ids={c["id"] for c in cards}
    if not set(responses)<=ids:
        raise ValueError("unknown_card")
    if confidence is not None and (type(confidence) is not int or not 1<=confidence<=5):
        raise ValueError("invalid_confidence")
    if locales is not None and (not isinstance(locales,dict) or not set(locales)<=ids or any(x not in {"en","fr"} for x in locales.values())):
        raise ValueError("invalid_locale")
    scored=[c for c in cards if c["scored"]]
    decisions={c["id"]:canonical_choice(c,responses.get(c["id"])) for c in cards}
    n=sum(decisions[c["id"]] is not None for c in scored)
    prudent=sum(decisions[c["id"]]=="B" for c in scored)
    total=len(scored)
    dimensions={}
    for name in ("mixed_loss_choices","gain_risk","loss_risk","rare_gain","rare_loss","trajectory_tolerance"):
        subset=[c for c in cards if c["dimension"]==name]
        resolved=[decisions[c["id"]] for c in subset if decisions[c["id"]] is not None]
        dimensions[name]={"answered":len(resolved),"total":len(subset),"canonical_b_fraction":resolved.count("B")/len(resolved) if resolved else None}
    repeat=next(c for c in cards if c["pair_id"])
    original, repeated = decisions[repeat["pair_id"]], decisions[repeat["id"]]
    checked=original is not None and repeated is not None
    comprehension=next(c for c in cards if c["dimension"]=="comprehension")
    read=decisions[comprehension["id"]]
    counts=Counter(responses.values())
    return dict(version=VERSION,style_profile="000",score=round_score(1+29*prudent/n) if n/total>=.7 else None,
                coverage=n/total,answered=n,total_scored=total,prudent_fraction=prudent/n if n else None,
                sensitivity=[round_score(1+29*prudent/total),round_score(1+29*(prudent+total-n)/total)],
                counts={**{k:counts[k] for k in CHOICES},"unpresented":len(cards)-len(responses)},
                dimensions=dimensions,confidence=confidence,
                mixed_gain_thresholds=mixed_gain_thresholds(cards, decisions),
                inconsistencies=[repeat["id"]] if checked and original!=repeated else [],pairs_checked=int(checked),
                comprehension_correct=None if read is None else read=="A",
                status="experimental",session_id=f"{VERSION}:{seed}:{currency}")
