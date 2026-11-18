# Chapter 3 · Adaptive questionnaire and validation

## 3.1e · Bank contract

`src.questionnaire.load_question_bank()` checks the 60 cards, stable IDs,
block types, prompts and prerequisites. A condition can use a choice from
an earlier single-choice card. The block tests verify sector choices,
ordered options, and the swipe grid and its displayed outcomes.

## 3.2a–3.3 · From choices to an aversion estimate

The grid uses 200 evenly spaced values of log aversion between log(0.3)
and log(30), with a normal prior centered at log(3) and SD 1.1.
For a swipe, P(B) is the sigmoid of 180 times the mean–variance utility
difference B minus A. Canonical choice IDs stay fixed when the display
swaps sides. For a Block B response, P(response ≥ k) is the sigmoid of
`a × (b_k − theta)`. Subtract adjacent cumulative probabilities to
obtain the four choice probabilities.

| Block B theme | Initial slope | Offset from log(3) |
| --- | ---: | ---: |
| Reaction | 1.1 | +0.05 |
| Loss comfort | 1.2 | 0 |
| Risk mix | 1.0 | −0.05 |
| Trade-off | 1.2 | +0.10 |

Add the theme offset to log(3), then add 0.8, 0 and −0.8 to obtain the
three descending cutoffs. These are hand-set model assumptions for the
prototype. The posterior multiplies its current mass by the selected
answer's likelihood and renormalizes. A skip leaves it intact. Summaries
include the mean, median and SD in log units and a central 80% interval
in aversion units.

## 3.4–3.6 · Adaptive session

Start with A01–A04 and the eligible D cards so required capacity and
constraint answers fit inside the 15-card budget. Then choose the
unanswered B or C card that minimizes expected posterior variance, while
reserving enough slots for two B and two C presentations. Finish at
15 presented cards or once the B/C quotas are reached and posterior
log-aversion SD falls below 0.20. If a swipe was answered, reserve a slot
for the first answered swipe shown again with reversed sides. The repeat
checks consistency and is excluded from the likelihood update. A
different choice prompts a neutral message and halves swipe sharpness,
then recomputes the posterior from the original answers.

The adaptive path is available as a Python session and in the notebook
for experimentation. The Streamlit form uses the fixed questionnaire.
The experimental results need participant validation before promoting the adaptive flow.

## 3.8–3.8d · Calibrated target and displayed category

A completed adaptive session supplies the posterior median aversion. The
target is the smaller of the Tobin tolerance estimate (reference
Sharpe divided by aversion) and the capacity ceiling. Exact internal
boundaries belong to the band above them. Targets below 4% fall below
the catalogue range. The existing categories and references remain in
the shared configuration. The portfolio scaling helper takes supplied
long-only risky weights and an annual covariance, mixes the sleeve with
cash, applies exposure and per-ETF limits, and recalculates achieved
volatility on the actual risk weights. Portfolio selection still has
to supply an eligible risky sleeve.

The Profile form shows the category, range and financial explanation.
The technical expander holds aversion and precise volatility values.
The portfolio menu receives a category only when the reference can pass
the profile's risk and clarification checks.

## 3.9a–3.9d · Simulation

Run `python -m src.build_adaptive_simulation` for the CSV and plot under
`results/`. Each scenario uses 1,000 latent aversions drawn uniformly in
log units from 0.5 to 20. Discrete capacity ceilings are shared across
the designs, as are the synthetic answers. Every estimate uses the
same fitted model. Random and preset fixed orders use up to 15 B/C
cards. The preset order serves as an experimental control with equal
question budgets. The 14-item Streamlit questionnaire has its own
scoring rule. The whole-bank reference uses all 44 B/C cards. The
remaining 16 cards supply capacity or context, so they do not add
likelihood observations. The experiment compares designs at equal
informative-card counts. Adaptive uses the session's B/C format quotas. The interactive session spends part of its
15 presentations on capacity, constraints and the mirror.

| Reference simulation | Informative cards | Log-aversion RMSE | Target MAE (points) | Category agreement with simulator |
| --- | ---: | ---: | ---: | ---: |
| Adaptive | 6 | 0.334 | 0.314 | 89.8% |
| Random | 6 | 0.464 | 0.622 | 81.0% |
| Fixed order | 6 | 0.543 | 0.907 | 71.5% |
| Adaptive | 15 | 0.250 | 0.226 | 92.0% |
| Random | 15 | 0.320 | 0.392 | 87.6% |
| Fixed order | 15 | 0.309 | 0.387 | 88.6% |
| Whole bank | 44 | 0.204 | 0.210 | 91.6% |

With high simulated swipe noise, 15-card adaptive RMSE rises to 0.436
versus 0.431 for the fixed order. The adaptive design has lower target
MAE (0.515 versus 0.584 points). Shifting the simulator's Block B cutoffs
while fitting the original cutoffs raises its RMSE to 0.283. The trials
measure recovery under chosen assumptions.

## 3.10–3.11 · Participant work

The [fixed pilot protocol](22_PROFILE_PILOT.md) is ready for the 3.0e
comprehension and retest sessions. For 3.10, recruit 40–60 consenting
students and use voluntary fictional-case responses where preferred.
Use the same published bank version throughout data collection. Offer
the full bank in short sessions, randomize the order of B/C cards and
balance the side of the wider choice. Record the questionnaire version,
canonical choice, display order, skips and session identifier. Summarize
item comprehension and check ordered response use. With a small
sample, begin with pooled calibration and inspect rare choices before
estimating item-specific parameters or removing questions. Reserve a
separate group or use participant-level cross-validation for exploratory
evaluation.

For 3.11, counterbalance the order of the fixed and adaptive paths and
collect the same independent preference task for both. Use unseen,
balanced paired scenarios and test whether each method predicts those
choices. Compare completion time, skips, test–retest agreement and
held-out choice accuracy on paired participants. Report denominators,
uncertainty, and the agreement between methods. Retain only consented
aggregate findings in Git. These steps remain open until participant
data exist.
