# Question Bank

The final bank of 60 questions will be stored in `bank.json`:

- block A: capacity and circumstances;
- block B: psychometric tolerance;
- block C: choice between two portfolios;
- block D: constraints and preferences.

Each question must have a stable identifier, a type, text, options, and calibration parameters. Do not change an identifier that is already in use without notifying the team: responses and tests reference these identifiers.

The fixed MVP questionnaire produces a capacity-capped internal volatility estimate and then assigns one client-facing category: Conservative, Balanced, Growth, or Aggressive. It must not present the continuous estimate as a guaranteed or exact risk level. Adaptive question selection remains an extension.


The [five profile dimensions](../docs/19_PROFILE_DIMENSIONS.md) guide the fixed questionnaire design.

## Fixed MVP draft · Step 3.0b

[fixed_mvp.json](fixed_mvp.json) contains 14 questions in English, the
language of the existing notebook. It has four capacity items, three
tolerance items, three knowledge and experience items, one objective item
and three constraint items. Each question and answer has a stable ID.

Use one answer for a single-choice item. For a multiple-choice item,
`none` and `unsure` each stand alone. For example, requesting an exclusion
and selecting “No exclusions from this list” would be contradictory. The
questions distinguish a loss that threatens a payment from discomfort
with a hypothetical loss. The `unsure` option captures uncertainty for
the scoring rules to resolve in 3.0c. The wording will be tested in 3.0e.
