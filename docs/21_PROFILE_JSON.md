# Step 3.0d · Fixed profile JSON v1

The fixed scorer produces the versioned JSON object defined by
[profile_v1.schema.json](../schemas/profile_v1.schema.json).
Call `src.profile_output.build_profile(answers, reference_sharpe=...)` with
the submitted choice IDs and the project's configured reference Sharpe.
The notebook generates a synthetic example and validates it against the
schema. Identical inputs to the same scoring version produce the same
profile.

| Top-level field | Meaning |
| --- | --- |
| `schema_version` | Integer format version. This contract uses 1. |
| `questionnaire_version` | Answer vocabulary version, currently `"0.1"`. |
| `scoring_version` | Fixed rules used for the score, currently `"1.0"`. |
| `answers` | One entry per stable question ID, with a choice ID or an array of choice IDs. |
| `risk` | Calibration input, score, limits, risk category and reasons for clarification. |
| `constraints` | Requested investment exclusions, borrowing preference and ETF weight cap. |

All volatility values are annual decimals such as `0.08` for 8%.
`risk.capacity_caps` records each ceiling, and `binding_capacity_items`
lists every answer tied for the minimum. `risk.category` is either the
category object with its current range and reference, or `null` below
the catalogue range. A category can exist while its reference is blocked.
Use `reference_check_passed` to check the numerical limit and unresolved
answers before any allocation. A portfolio still has to satisfy constraints
in the allocation step. The recorded reference is the catalogue value.
Achieved volatility belongs to the portfolio result.

`constraints.excluded_groups` uses the fixed questionnaire IDs `energy`,
`gold` and `treasuries`. The empty array means the client selected no
exclusions. `allow_borrowing` is an explicit permission or exclusion.
`max_etf_weight` is the selected 20%, 25% or standard 35% target cap,
expressed as a decimal. For each constraint, `null` signals an undecided
answer. The allocator will translate the exclusion groups to eligible
assets and enforce applicable project limits.

Keep this schema stable for v1. Any incompatible field or type change
requires a new schema version. Changes to answer vocabulary or scoring
must be tracked by their respective versions. The transport rules are defined below.

## Step 3.0g · File round trip

Use `src.profile_serialization.export_profile(profile)` to produce UTF-8
JSON text. Read a saved file as bytes and pass it to
`src.profile_serialization.import_profile(payload)`. These functions are
the file codec. The application upload and download controls are tracked
in Step 7.7.

Both directions check the format, questionnaire and scoring versions.
The currently supported combination is `1 / "0.1" / "1.0"`. Unsupported
combinations raise a version-specific error. A v1 snapshot preserves its
recorded reference Sharpe even if the current configuration has a new
default. Rescoring under a new assumption is a separate operation.

Import rejects malformed JSON, duplicate keys, non-finite numbers and
unknown or invalid fields. Both directions recompute the score and
constraints from the recorded choices and calibration and reject inconsistent
derived fields. This is a consistency check. A file's origin still requires
separate verification if that becomes a product requirement.

The notebook saves a synthetic profile in a temporary file, reimports it
and checks exact equality. It also demonstrates rejection of an unknown
format version and an edited effective volatility.
