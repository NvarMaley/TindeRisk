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

## Adaptive cards · Step 3.1a

The [adaptive bank](bank.json) now contains ten Block A cards. A01–A04
reuse the fixed questionnaire's capacity choice IDs for horizon, near-term
withdrawals, separate savings and a payment threatened by loss. Their
`params.fixed_question` field identifies the corresponding fixed question.
The six other cards provide context. A08 records the purpose of investing,
and A09 records experience. The fixed capacity calculation still uses F01–F04.

### Professional and research references

- [Vanguard's Investor Questionnaire](https://investor.vanguard.com/tools-calculators/investor-questionnaire)
  uses objectives, investment experience, time horizon, risk tolerance and
  financial situation when suggesting an allocation. We use those dimensions
  to organize the cards.
- The [FCA suitability overview](https://www.fca.org.uk/firms/assessing-suitability)
  and the [FCA assessment instructions](https://www.fca.org.uk/publication/documents/instructions-iaat-licensing-agreement.pdf)
  distinguish willingness to accept risk from the ability to absorb a loss.
  Block A supplies the financial ceiling. It leaves willingness to Blocks B and C.
- [Grable and Lytton](https://static.arnaudsylvain.fr/2017/03/Grable-Lyton-1999-Financial-Risk-revisited.pdf)
  developed a multi-item financial tolerance instrument. Block B will use
  original questions based on everyday investment situations.
- [Holt and Laury](https://www.aeaweb.org/articles?id=10.1257%2F000282802762024700)
  use repeated pairs of risky prospects to infer a preference from choices.
  Block C adapts the paired-choice idea to the project's mean–variance model.
  It will use the same starting amount, time period and scenario probabilities
  within each pair. Its hypothetical choices need their own testing.

Keep each screen to one short prompt. Use short answer labels for circumstances
and two side-by-side options for a portfolio trade-off. Present the same
information in the same format on both sides and vary which side contains the
higher-risk option when implementing the swipe cards. An illustrative card
could start with CHF 1,000 and two equally likely one-year outcomes. One
option shows –CHF 50 or +CHF 90; the other shows –CHF 150 or +CHF 220.
The calculation of risk aversion stays behind the cards.
