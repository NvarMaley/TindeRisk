"""Export and import a fixed profile under the v1 JSON contract."""

import json
import math

from jsonschema import Draft202012Validator, ValidationError

from .paths import ROOT
from .profile_output import (
    PROFILE_SCHEMA_VERSION,
    QUESTIONNAIRE_VERSION,
    SCORING_VERSION,
    build_profile,
)


def _validate_profile(profile: object) -> dict:
    if not isinstance(profile, dict):
        raise ValueError("profile must be a JSON object")
    version = profile.get("schema_version")
    if type(version) is not int or version != PROFILE_SCHEMA_VERSION:
        raise ValueError(f"unsupported profile schema version: {version!r}")
    if profile.get("questionnaire_version") != QUESTIONNAIRE_VERSION:
        raise ValueError("unsupported profile questionnaire version")
    if profile.get("scoring_version") != SCORING_VERSION:
        raise ValueError("unsupported profile scoring version")

    schema = json.loads((ROOT / "schemas/profile_v1.schema.json").read_text(encoding="utf-8"))
    try:
        Draft202012Validator(schema).validate(profile)
    except ValidationError as error:
        field = ".".join(str(part) for part in error.absolute_path) or "profile"
        raise ValueError(f"invalid profile field: {field}") from error

    try:
        expected = build_profile(
            profile["answers"], reference_sharpe=profile["risk"]["reference_sharpe"],
        )
    except (ValueError, OverflowError) as error:
        raise ValueError("profile answers or calibration cannot be scored") from error
    if profile != expected:
        raise ValueError("profile results do not match its answers and calibration")
    return expected


def export_profile(profile: dict) -> str:
    """Return a validated JSON snapshot suitable for a UTF-8 file."""
    return json.dumps(_validate_profile(profile), indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _finite_float(number: str) -> float:
    value = float(number)
    if not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    return value


def import_profile(payload: str | bytes) -> dict:
    """Read a v1 UTF-8 snapshot and verify its derived fields by rescoring."""
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("profile file must be UTF-8") from error
    try:
        profile = json.loads(payload, object_pairs_hook=_unique_object,
                             parse_float=_finite_float, parse_constant=_finite_float)
    except (json.JSONDecodeError, RecursionError) as error:
        raise ValueError("invalid profile JSON") from error
    return _validate_profile(profile)
