"""Versioned integration contracts; not validated financial models or API migrations."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from math import isfinite
from typing import Literal

SCHEMA_VERSION = "1.0.0"
Frequency = Literal["daily", "weekly", "monthly", "quarterly", "annual", "scenario"]
Currency = Literal["USD", "CHF"]


class Status(StrEnum):
    EXPERIMENTAL = "experimental"
    VALIDATED = "validated"
    UNAVAILABLE = "unavailable"
    INFEASIBLE = "infeasible"
    ERROR = "error"


@dataclass(frozen=True, kw_only=True)
class RunMetadata:
    """Common envelope; no personal data in provenance or diagnostics."""

    as_of: datetime
    run_id: str
    model_version: str
    units: tuple[tuple[str, str], ...]
    provenance: tuple[str, ...]
    status: Status = Status.EXPERIMENTAL
    warnings: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        if self.as_of.utcoffset() != timedelta(0):
            raise ValueError("as_of must be timezone-aware UTC")
        if not self.run_id or not self.model_version or not self.provenance or not self.units:
            raise ValueError("Missing version, units or provenance")
        if len(dict(self.units)) != len(self.units) or any(not k or not v for k, v in self.units):
            raise ValueError("Units must have unique, non-empty names and values")
        if self.schema_version != SCHEMA_VERSION or not isinstance(self.status, Status):
            raise ValueError("Unknown schema version or status")


@dataclass(frozen=True, kw_only=True)
class ConstraintSet:
    meta: RunMetadata
    constraint_id: str
    allowed_instruments: tuple[str, ...]
    gross_exposure_limit: float
    allow_short: bool
    allow_leverage: bool
    allow_derivatives: bool


@dataclass(frozen=True, kw_only=True)
class GoalSpec:
    meta: RunMetadata
    goal_id: str
    objective_id: str
    target_amount: float | None
    currency: Currency
    due_date: date | None
    priority: int


@dataclass(frozen=True, kw_only=True)
class ClientProfile:
    """Pseudonymous, local mandate reference; the complete mandate is chapter 01."""

    meta: RunMetadata
    profile_id: str
    base_currency: Currency
    constraints: ConstraintSet
    goals: tuple[GoalSpec, ...]


@dataclass(frozen=True, kw_only=True)
class Card:
    meta: RunMetadata
    card_id: str
    construct: str
    choices: tuple[str, ...]
    pair_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class MarketSnapshot:
    meta: RunMetadata
    universe_version: str
    dataset_hash: str
    instrument_ids: tuple[str, ...]
    frequency: Frequency
    completeness: tuple[tuple[str, int, int], ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    latest_observation: date | None = None


@dataclass(frozen=True, kw_only=True)
class ForecastBundle:
    meta: RunMetadata
    snapshot_id: str
    instrument_ids: tuple[str, ...]
    expected_returns: tuple[float, ...]  # decimal simple returns over the declared horizon
    horizon_periods: int
    frequency: Frequency
    currency: Currency
    distribution_ref: str | None = None

    def __post_init__(self):
        if len(self.instrument_ids) != len(self.expected_returns) or self.horizon_periods < 1:
            raise ValueError("Forecast shape or horizon mismatch")
        if not all(isfinite(x) for x in self.expected_returns):
            raise ValueError("Non-finite forecast")


@dataclass(frozen=True, kw_only=True)
class RiskReport:
    meta: RunMetadata
    snapshot_id: str
    instrument_ids: tuple[str, ...]
    covariance: tuple[tuple[float, ...], ...]
    frequency: Frequency
    currency: Currency
    loss_metrics: tuple[tuple[str, float], ...] = ()
    stress_losses: tuple[tuple[str, float], ...] = ()

    def __post_init__(self):
        n = len(self.instrument_ids)
        if len(self.covariance) != n or any(len(row) != n for row in self.covariance):
            raise ValueError("Covariance shape mismatch")
        if any(not isfinite(x) for row in self.covariance for x in row):
            raise ValueError("Non-finite covariance")


@dataclass(frozen=True, kw_only=True)
class StrategySpec:
    meta: RunMetadata
    strategy_id: str
    signal_version: str
    rebalance_frequency: Frequency
    benchmark_id: str
    required_data: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class OptimizerSpec:
    meta: RunMetadata
    optimizer_id: str
    objective_id: str
    constraint_id: str
    forecast_id: str | None
    risk_report_id: str | None
    parameters: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True, kw_only=True)
class PortfolioCandidate:
    meta: RunMetadata
    candidate_id: str
    profile_id: str
    strategy_id: str
    optimizer_id: str
    funded_weights: tuple[tuple[str, float], ...]  # fraction of NAV, not derivative notional
    futures_contracts: tuple[tuple[str, int], ...]
    collateral_amount: float
    currency: Currency
    constraint_id: str
    eligible: bool = False

    def __post_init__(self):
        if self.eligible and self.meta.status is not Status.VALIDATED:
            raise ValueError("Unvalidated candidate cannot be eligible")
        if any(not isfinite(w) for _, w in self.funded_weights):
            raise ValueError("Non-finite weight")


@dataclass(frozen=True, kw_only=True)
class Evaluation:
    meta: RunMetadata
    candidate_id: str
    benchmark_id: str
    period_start: date
    period_end: date
    metrics: tuple[tuple[str, float], ...]
    costs: float
    currency: Currency


@dataclass(frozen=True, kw_only=True)
class Selection:
    meta: RunMetadata
    candidate_id: str
    profile_id: str
    mandate_version: str
    consent: bool
    paper_only: Literal[True] = True

    def __post_init__(self):
        if self.paper_only is not True:
            raise ValueError("Real execution is out of scope")
