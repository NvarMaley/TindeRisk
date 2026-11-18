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
must be tracked by their respective versions. File import, export and
compatibility behavior are tracked in 3.0g.
