"""Treasury-only fixed-income eligibility on already verified metadata.

No provider lookup or historical holdings verification is implemented here.
Callers must verify metadata and holdings as of the decision timestamp.
"""
from dataclasses import dataclass


TREASURY_TYPES = frozenset({"treasury_bill", "treasury_note", "treasury_bond", "tips"})


@dataclass(frozen=True)
class Holding:
    instrument_type: str
    issuer: str
    currency: str = "USD"


def treasury_eligible(holding: Holding) -> bool:
    return (
        holding.issuer == "US_TREASURY"
        and holding.instrument_type in TREASURY_TYPES
        and holding.currency == "USD"
    )


def treasury_etf_eligible(holdings: tuple[Holding, ...], *, verified_as_of: bool) -> bool:
    """Reject unverified, empty, cash-only or mixed underlying exposures.

    USD cash is allowed solely as ancillary holdings, not as qualifying bonds.
    """
    if not verified_as_of or not holdings:
        return False
    return any(treasury_eligible(h) for h in holdings) and all(
        treasury_eligible(h) or (h.instrument_type == "cash" and h.currency == "USD")
        for h in holdings
    )
