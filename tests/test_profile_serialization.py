import json

import pytest

from src.profile_output import build_profile
from src.profile_serialization import export_profile, import_profile


@pytest.fixture
def answers():
    return {
        "F01": "2_to_lt_5y", "F02": "none", "F03": "ge_6m", "F04": "no_payment",
        "F05": "increase_risk", "F06": "ge_20pct", "F07": "larger_swings",
        "F08": ["funds"], "F09": "can_decline", "F10": "gain_25", "F11": "growth",
        "F12": ["energy", "gold"], "F13": "disallow", "F14": "cap_25pct",
    }


@pytest.mark.parametrize("overrides", [
    {},
    {"F04": "lt_5pct", "F12": ["unsure"], "F13": "unsure", "F14": "unsure"},
])
def test_exported_file_round_trip_preserves_calibration_and_constraints(tmp_path, answers, overrides):
    # A saved calibration can differ from a later project default.
    expected = build_profile({**answers, **overrides}, reference_sharpe=.30)
    path = tmp_path / "profile.json"
    path.write_text(export_profile(expected), encoding="utf-8")
    restored = import_profile(path.read_bytes())
    assert restored == expected
    assert restored["risk"]["reference_sharpe"] == .30
    assert export_profile(restored) == path.read_text(encoding="utf-8")


@pytest.mark.parametrize("field,value,reason", [
    ("schema_version", 2, "schema version"),
    ("schema_version", True, "schema version"),
    ("questionnaire_version", "0.2", "questionnaire version"),
    ("scoring_version", "2.0", "scoring version"),
])
def test_reject_incompatible_versions(answers, field, value, reason):
    profile = build_profile(answers, reference_sharpe=.35)
    profile[field] = value
    with pytest.raises(ValueError, match=reason):
        import_profile(json.dumps(profile))


@pytest.mark.parametrize("section,field,value", [
    ("risk", "effective_volatility", .12),
    ("constraints", "allow_borrowing", True),
])
def test_reject_derived_values_that_disagree_with_answers(answers, section, field, value):
    profile = build_profile(answers, reference_sharpe=.35)
    profile[section][field] = value
    for operation, payload in ((import_profile, json.dumps(profile)), (export_profile, profile)):
        with pytest.raises(ValueError, match="do not match"):
            operation(payload)


@pytest.mark.parametrize("payload,reason", [
    ('{"schema_version": 1, "schema_version": 2}', "duplicate JSON key"),
    ('{"value": NaN}', "non-finite"),
    ('{"value": 1e500}', "non-finite"),
    ('{"schema_version":', "invalid profile JSON"),
    (b"\xff", "UTF-8"),
])
def test_reject_malformed_or_ambiguous_files(payload, reason):
    with pytest.raises(ValueError, match=reason):
        import_profile(payload)
