"""Conservative, pre-validation requirements for the planned financial catalog."""

from dataclasses import dataclass


FUNDED = frozenset({"equity_etf", "treasury_etf", "reit_etf", "usd_cash", "us_equity", "us_treasury"})
FUTURES = frozenset({"eligible_us_futures"})
FREQUENCIES = {"annual": 0, "quarterly": 1, "monthly": 2, "weekly": 3, "daily": 4}
BASE = frozenset({"pit_universe", "total_returns", "costs", "liquidity"})


@dataclass(frozen=True)
class MethodRequirement:
    instruments: frozenset[str]
    data: frozenset[str]
    minimum_frequency: str
    short_required: bool = False
    margin_required: bool = False


def _row(extra=(), *, instruments=FUNDED, frequency="monthly", short=False, margin=False):
    return MethodRequirement(instruments, BASE | frozenset(extra), frequency, short, margin)


_OPT = [(), ("market_cap",), ("covariance",), ("mean", "covariance", "risk_free"),
        ("mean", "covariance", "utility_parameter"), ("mean", "covariance"),
        ("mean", "covariance", "views", "view_uncertainty", "market_weights"),
        ("covariance", "risk_budgets"), ("covariance",), ("covariance", "risk_budgets"),
        ("covariance",), ("loss_scenarios",), ("return_scenarios", "threshold"),
        ("return_scenarios", "threshold"), ("ordered_return_paths",),
        ("mean", "covariance", "uncertainty_set"), ("return_history", "resampling_spec"),
        ("return_scenarios", "ambiguity_set"), ("return_scenarios", "loss_bounds"),
        ("mean", "covariance"), ("covariance", "benchmark_weights"),
        ("mean", "covariance", "benchmark_weights")]

_STR = [
    _row(("benchmark_weights",)),
    _row(("alpha_signal", "benchmark_weights")),
    _row(("alpha_signal", "borrow"), short=True, frequency="daily"),
    _row(("alpha_signal", "borrow", "beta"), short=True, frequency="daily"),
    _row(("pit_macro", "signal"), instruments=FUNDED | FUTURES),
    _row(("futures_chain", "roll", "margin", "volatility"), instruments=FUTURES, frequency="daily", margin=True),
    _row(("validated_sleeves", "covariance", "risk_budgets")),
    _row(("spread_history", "borrow"), short=True, frequency="daily"),
    _row(("pit_factor_scores",)),
    _row(("pit_factor_scores", "benchmark_weights")),
    _row(("net_carry", "funding"), instruments=FUNDED | FUTURES),
    _row(("return_history",)),
    _row(("return_history", "stationarity"), frequency="daily"),
    _row(("strategic_weights", "signal")),
    _row(("benchmark_weights", "validated_sleeves", "risk_budgets")),
    _row(("volatility", "target_volatility"), frequency="daily"),
    _row(("covariance", "macro_scenarios")),
    _row(("filtered_regime_probabilities",)),
    _row(("futures_chain", "roll", "margin", "stress_scenarios"), instruments=FUNDED | FUTURES, frequency="daily", margin=True),
]
_FAC = [("benchmark_returns",), ("pit_fundamentals", "market_cap"), ("market_cap",),
        ("return_history",), ("pit_fundamentals",), ("return_history",),
        ("pit_fundamentals",), ("pit_fundamentals",), ("net_carry", "funding"),
        ("treasury_curve", "duration"), ("treasury_curve",), ("bid_ask", "volume"),
        ("pit_inflation", "inflation_expectations")]
_DYN = [("filtered_regime_probabilities",), ("prior", "likelihood"), ("covariance", "risk_budgets"),
        ("scenario_tree", "cash_flows"), ("return_scenarios", "cash_flows"),
        ("state_transition", "cash_flows"), ("return_scenarios", "cash_flows"),
        ("validated_simulator", "guardrails"), ("validated_models", "oos_weights"),
        ("uncertainty_set", "state_transition")]

REGISTRY = {
    **{f"OPT{i:02}": _row(x) for i, x in enumerate(_OPT, 1)},
    **{f"STR{i:02}": x for i, x in enumerate(_STR, 1)},
    **{f"FAC{i:02}": _row(x) for i, x in enumerate(_FAC, 1)},
    **{f"DYN{i:02}": _row(x) for i, x in enumerate(_DYN, 1)},
}


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reasons: tuple[str, ...]


def assess(method_id: str, *, instruments: frozenset[str], data: frozenset[str], frequency: str,
           validated_methods: frozenset[str] = frozenset(), capacity_verified: bool = False,
           treasury_exposure_verified: bool = False, allow_short: bool = False, uses_short: bool = False,
           allow_leverage: bool = False, uses_leverage: bool = False,
           allow_derivatives: bool = False, margin_verified: bool = False) -> Eligibility:
    """Fail closed; inputs summarize independently validated evidence, not user preferences."""
    req = REGISTRY.get(method_id)
    if req is None:
        return Eligibility(False, ("unknown_method",))
    reasons = []
    if method_id not in validated_methods:
        reasons.append("method_not_validated")
    if not instruments or not instruments <= req.instruments:
        reasons.append("incompatible_instruments")
    if instruments & {"treasury_etf", "us_treasury"} and not treasury_exposure_verified:
        reasons.append("treasury_exposure_unverified")
    reasons.extend(f"missing_data:{x}" for x in sorted(req.data - data))
    if FREQUENCIES.get(frequency, -1) < FREQUENCIES[req.minimum_frequency]:
        reasons.append("insufficient_frequency")
    if not capacity_verified:
        reasons.append("capacity_unverified")
    if (req.short_required or uses_short) and not allow_short:
        reasons.append("short_not_allowed")
    if uses_leverage and not allow_leverage:
        reasons.append("leverage_not_allowed")
    if req.margin_required or instruments & FUTURES:
        if not allow_derivatives:
            reasons.append("derivatives_not_allowed")
        if not margin_verified:
            reasons.append("margin_unverified")
        reasons.extend(f"missing_data:{x}" for x in sorted({"futures_chain", "roll", "margin"} - data))
    return Eligibility(not reasons, tuple(dict.fromkeys(reasons)))
