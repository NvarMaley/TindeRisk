import pytest
import yaml
from pathlib import Path

from src.profiling import RISK_BANDS, assign_risk_band, category_from_profile


ROOT = Path(__file__).resolve().parents[1]


def test_risk_bands_match_shared_configuration():
    with (ROOT / "config.yaml").open(encoding="utf-8") as config_file:
        configured = yaml.safe_load(config_file)["risk_bands"]

    assert [band.key for band in RISK_BANDS] == list(configured)
    for band in RISK_BANDS:
        values = configured[band.key]
        assert band.label == values["label"]
        assert band.min_volatility == pytest.approx(values["min_volatility"])
        assert band.max_volatility == pytest.approx(values["max_volatility"])
        assert band.reference_volatility == pytest.approx(
            values["reference_volatility"]
        )


@pytest.mark.parametrize(
    ("volatility", "expected"),
    [
        (0.03, "conservative"),
        (0.04, "conservative"),
        (0.0599, "conservative"),
        (0.06, "balanced"),
        (0.0899, "balanced"),
        (0.09, "growth"),
        (0.1199, "growth"),
        (0.12, "aggressive"),
        (0.15, "aggressive"),
        (0.20, "aggressive"),
    ],
)
def test_risk_band_boundaries(volatility, expected):
    assert assign_risk_band(volatility).key == expected


def test_capacity_caps_higher_tolerance():
    effective, band = category_from_profile(
        tolerance_volatility=0.14,
        capacity_volatility=0.08,
    )

    assert effective == pytest.approx(0.08)
    assert band.key == "balanced"


@pytest.mark.parametrize("invalid", [0.0, -0.1, float("nan"), float("inf")])
def test_invalid_volatility_is_rejected(invalid):
    with pytest.raises(ValueError):
        assign_risk_band(invalid)


def test_sharpe_sensitivity_changes_category_and_capacity_can_limit_it():
    from src.profiling import tolerance_volatility

    baseline = tolerance_volatility(4, .35)
    higher = tolerance_volatility(4, .40)
    assert baseline == pytest.approx(.0875)
    assert higher == pytest.approx(.10)
    assert assign_risk_band(baseline).key == "balanced"
    assert assign_risk_band(higher).key == "growth"
    for tolerance in (baseline, higher):
        capped, band = category_from_profile(tolerance, .08)
        assert capped == .08
        assert band.key == "balanced"


@pytest.mark.parametrize("phi,sharpe", [(0, .35), (4, 0), (float("nan"), .35)])
def test_tolerance_volatility_rejects_invalid_calibration(phi, sharpe):
    from src.profiling import tolerance_volatility

    with pytest.raises(ValueError):
        tolerance_volatility(phi, sharpe)
