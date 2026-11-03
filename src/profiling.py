"""Risk capacity, continuous calibration, and client-facing risk bands (step 3)."""

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class RiskBand:
    """A stable client-facing category backed by a reference volatility."""

    key: str
    label: str
    min_volatility: float
    max_volatility: float
    reference_volatility: float


RISK_BANDS = (
    RiskBand("conservative", "Conservative", 0.04, 0.06, 0.05),
    RiskBand("balanced", "Balanced", 0.06, 0.09, 0.08),
    RiskBand("growth", "Growth", 0.09, 0.12, 0.10),
    RiskBand("aggressive", "Aggressive", 0.12, 0.15, 0.14),
)


def assign_risk_band(volatility: float) -> RiskBand:
    """Map a positive annualized volatility estimate to a stable risk band.

    Lower bounds are inclusive and upper bounds are exclusive, except for the
    final band. Estimates outside the displayed range are assigned to the
    nearest category; the original estimate must still be retained for audit.
    """

    if not math.isfinite(volatility) or volatility <= 0:
        raise ValueError("volatility must be a positive finite number")

    if volatility < RISK_BANDS[0].min_volatility:
        return RISK_BANDS[0]

    for band in RISK_BANDS[:-1]:
        if band.min_volatility <= volatility < band.max_volatility:
            return band

    if volatility < RISK_BANDS[-1].min_volatility:
        return RISK_BANDS[-2]
    return RISK_BANDS[-1]


def category_from_profile(
    tolerance_volatility: float,
    capacity_volatility: float,
) -> tuple[float, RiskBand]:
    """Apply the capacity cap, then return the internal estimate and category."""

    if not math.isfinite(tolerance_volatility) or tolerance_volatility <= 0:
        raise ValueError("tolerance_volatility must be a positive finite number")
    if not math.isfinite(capacity_volatility) or capacity_volatility <= 0:
        raise ValueError("capacity_volatility must be a positive finite number")

    effective_volatility = min(tolerance_volatility, capacity_volatility)
    return effective_volatility, assign_risk_band(effective_volatility)

