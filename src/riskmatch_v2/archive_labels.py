"""Read display labels from the original immutable research snapshots.

Identifiers, market observations, free-text client fields and archive hashes are preserved.
"""

LEGACY_LABELS = {
    "Rendement": "Return",
    "Robuste": "Robust",
    "Couverture": "Hedge",
    "Référence 60/40": "60/40 benchmark",
    "Action directe": "Individual stock",
    "ETF actions": "Equity ETF",
    "ETF Trésor": "Treasury ETF",
    "Trésor direct": "Direct Treasury",
    "Or (GLD)": "Gold (GLD)",
    "observé": "observed",
    "projection factorielle": "factor projection",
    "complet": "complete",
    "partiel": "partial",
    "sans raccord": "unmatched",
    "sortie documentée": "documented exit",
    "événement à vérifier": "event to verify",
    "candidat": "candidate",
    "moins de 252 rendements communs sur 504 séances": "less than 252 common returns in 504 sessions",
    "émission ultérieure": "Subsequent issue",
    "statut ou cours CRSP": "CRSP status or prices",
    "cours de décision absent": "missing decision-date price",
    "inachevée": "unrecovered",
    "indisponible": "unavailable",
    "récupérée": "recovered",
    "source à qualifier": "source pending review",
    "facteur": "factor",
    "Banques américaines, mars 2023": "US Banks, March 2023",
    "Invasion de l’Ukraine, premier mois": "Invasion of Ukraine, first month",
    "variation quotidienne extrême": "extreme daily variation",
    "nom à confirmer": "name to be confirmed",
    "rendements de raccord incompatibles": "incompatible connection returns",
    "aucune séance publiée": "no sessions issued",
    "cours de raccord incompatible": "incompatible connection prices",
    "recouvrement insuffisant": "insufficient recovery",
    "instrument/devise/place": "instrument/currency/place",
    "rachat en numéraire, trajectoire quotidienne à compléter": "cash buyback, daily trajectory to complete",
}

LABEL_COLUMNS = (
    "option",
    "class",
    "status",
    "reason",
    "stress_source",
    "recovery_state",
    "episode",
    "secondary_check",
    "detail",
    "role",
)


def read_snapshot(path, **options):
    import pandas as pd

    frame = pd.read_parquet(path, **options)
    for column in frame.columns.intersection(LABEL_COLUMNS):
        frame[column] = frame[column].replace(LEGACY_LABELS)
        if column == "detail":
            frame[column] = frame[column].map(
                lambda value: (
                    " | ".join(
                        LEGACY_LABELS.get(part, part) for part in value.split(" | ")
                    )
                    if isinstance(value, str)
                    else value
                )
            )
    return frame
