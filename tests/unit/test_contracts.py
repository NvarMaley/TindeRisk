from datetime import datetime, timezone

import pytest

from riskmatch.contracts import ForecastBundle, PortfolioCandidate, RunMetadata, Status, RiskReport
from riskmatch.eligibility import REGISTRY, assess


def metadata(**overrides):
    defaults = dict(as_of=datetime(2026, 11, 24, tzinfo=timezone.utc), run_id="synthetic-test",
                    model_version="fixture-v1", units=(("return", "decimal"),),
                    provenance=("synthetic-fixture",))
    return RunMetadata(**(defaults | overrides))


def test_metadata_requires_utc_and_provenance():
    with pytest.raises(ValueError):
        metadata(as_of=datetime(2026, 11, 24))
    with pytest.raises(ValueError):
        metadata(provenance=())
    with pytest.raises(ValueError):
        metadata(units=(("return", "decimal"), ("return", "percent")))


def test_forecasts_and_risk_are_separate_and_dimension_checked():
    common = dict(meta=metadata(), snapshot_id="synthetic", instrument_ids=("A", "B"),
                  frequency="monthly", currency="USD")
    assert ForecastBundle(**common, expected_returns=(0.01, 0.02), horizon_periods=1).expected_returns
    assert RiskReport(**common, covariance=((0.01, 0), (0, 0.02))).covariance
    with pytest.raises(ValueError):
        ForecastBundle(**common, expected_returns=(0.01,), horizon_periods=1)
    with pytest.raises(ValueError):
        RiskReport(**common, covariance=((0.01,),))


def test_candidate_cannot_be_eligible_before_validation():
    args = dict(candidate_id="candidate", profile_id="fictional", strategy_id="STR01",
                optimizer_id="OPT01", funded_weights=(("A", 1.0),), futures_contracts=(),
                collateral_amount=0, currency="USD", constraint_id="fixture", eligible=True)
    with pytest.raises(ValueError):
        PortfolioCandidate(meta=metadata(), **args)
    assert PortfolioCandidate(meta=metadata(status=Status.VALIDATED), **args).eligible


def test_catalog_and_fail_closed_requirements():
    assert set(REGISTRY) == {f"{prefix}{n:02}" for prefix, count in
                             (("OPT", 22), ("STR", 19), ("FAC", 13), ("DYN", 10))
                             for n in range(1, count + 1)}
    req = REGISTRY["OPT01"]
    kwargs = dict(instruments=frozenset({"equity_etf"}), data=req.data,
                  frequency="monthly", capacity_verified=True)
    assert not assess("OPT01", **kwargs).eligible
    assert assess("OPT01", **kwargs, validated_methods=frozenset({"OPT01"})).eligible
    assert not assess("unknown", **kwargs).eligible
    assert not assess("OPT01", **(kwargs | {"instruments": frozenset({"corporate_bond"})}),
                      validated_methods=frozenset({"OPT01"})).eligible
    result = assess("OPT01", **(kwargs | {"instruments": frozenset({"treasury_etf"})}),
                    validated_methods=frozenset({"OPT01"}))
    assert "treasury_exposure_unverified" in result.reasons
    futures = assess("STR06", data=frozenset(), instruments=frozenset({"eligible_us_futures"}),
                     frequency="monthly", uses_leverage=True)
    assert {"margin_unverified", "insufficient_frequency", "leverage_not_allowed",
            "derivatives_not_allowed", "capacity_unverified"} <= set(futures.reasons)
