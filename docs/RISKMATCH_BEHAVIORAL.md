# RiskMatch Discovery — Behavioral Protocol

## Objective and Limits
Measure stated and revealed willingness to accept financial risk in simulated situations. Separate financial capacity, subjective tolerance, risk required by goals, knowledge and experience. Swipes do not reveal actual cognitive mechanisms or diagnose excitement or addiction. Biases are hypotheses to test, not personal labels. No biometric collection or exploitation of vulnerabilities.

## Initial Bank: 60 Cards, Target Session of 30

| Block | Per session | Bank | Target measure |
|---|---:|---:|---|
| Lotteries and trade-offs | 8 | 16 | risk-return preferences, certainty equivalents |
| Gains/losses and framing | 6 | 12 | loss sensitivity, framing |
| Paths and drawdowns | 6 | 12 | fluctuation tolerance, reaction to losses |
| Uncertainty and horizon | 4 | 8 | ambiguity, patience, horizon |
| Management preferences | 4 | 8 | stability, income, frequency, style |
| Consistency repeated pairs | 2 | 4 | within-session reliability |

Implemented in `src/riskmatch/behavioral/discovery.py` as `discovery-v2.0.0`; counts are design choices, not a scientific conclusion. Each session samples exactly 30 from 60 using a stored 32-bit seed and currency. Include both members of three framing pairs and the two original lottery anchors for the two repeated cards. Sample two ambiguity and two time items. Balance swapping in each block; randomize which canonical option appears first in the question. Separate paired items where possible. Persist seed, version, response locale and order (reproducible from seed); the engine recomputes scoring server-side. Existing fixed-deck saves retain their old version and interpretation. Pilot 30 cards, then adjust based on reliability, fatigue and precision. Independent mandatory financial questionnaire: capital, debt, reserves, horizon, income, withdrawals, experience, tolerable losses and restrictions.

## Card Mechanics

Both options appear in one question with equal emphasis. Yes (right, stored as `like`) accepts the proposed switch to displayed A. No (left, stored as `dislike`) keeps the starting option, displayed B. The canonical options are swapped across the session, so either button can select the prudent option. Unsure = do not know; skip = nonresponse. Show the safe alternative explicitly in lotteries. Present probabilities/amounts consistently, controlled random order and comparable units; no animations rewarding large gains. No jackpot, confetti, streak, real money, risk reward or artificial urgency. Response time does not measure excitement; optional and consented only in a future study, never initial score.

## Examples From the Current Bank

The table shows canonical alternatives in French for a CHF session. The order in the app depends on the session seed.

| ID | Canonical A | Canonical B | What the card compares |
|---|---|---|---|
| L01 | tenter de gagner 100 CHF avec 50 % de chances, et ne rien gagner sinon | gagner 40 CHF à coup sûr | Certain gain vs. lottery |
| L13 | tenter ta chance : 50 % de chances de gagner 200 CHF et 50 % de risques de perdre 100 CHF | gagner 40 CHF à coup sûr | Possible gain or loss |
| F01 | garder 1000 CHF dans 80 % des cas et 900 CHF dans les 20 % restants | garder 980 CHF à coup sûr | Amount kept |
| F02 | risquer de perdre 100 CHF dans 20 % des cas, sans rien perdre sinon | perdre 20 CHF à coup sûr | Same outcomes as F01, framed as losses |
| D01 | 92 après 6 mois, puis 90 ou 114 après un an | 98 après 6 mois, puis 98 ou 108 après un an | Midyear decline and one-year outcomes |
| A01 | tenter de gagner 100 CHF sans savoir quelles sont tes chances | tenter de gagner 100 CHF avec une chance sur deux | Unknown vs. known probability |
| H01 | recevoir 102 CHF dans un an, montant garanti | recevoir 100 CHF aujourd’hui, montant garanti | Guaranteed payment now or later |
| P01 | faire le point sur tes placements une fois par mois | faire le point sur tes placements une fois par an | Portfolio review frequency |
| C01 | tenter de gagner 100 CHF avec 50 % de chances, et ne rien gagner sinon | gagner 40 CHF à coup sûr | Repeat of L01 |

D01 starts at 100. Within each option, the two one-year outcomes are equally likely and include a 0.5% fee. A01 pays zero if there is no win under either option. Both H01 payments are guaranteed. Ambiguity and time choices are reported separately from the aversion score.

## Three-Level Scoring

**MVP:** only prespecified, balanced, documented directional risk items. For item i, a_i=1 if prudent response and 0 if risk-taking. p=Σ w_i a_i/Σ w_i over valid answers; score=1+29p (rounded for display). Equal weights initially. Exclude unsure/skip and flag missingness. Do not score with fewer than 70% of scored items answered (provisional threshold). Keep other dimensions separate. Show missing-response sensitivity bounds; not a validated confidence interval.

**Research:** fit IRT/logistic P(prudent response)=sigmoid(a_i(θ−b_i)); test discrimination, difficulty, dimensionality and invariance. Calibrate on an independent sample, map θ monotonically to 1–30 and version transformation. If data do not support one dimension, show multidimensional profile and limit use of aggregate score.

**Finance:** separately estimate γ or λ from choices between wealth distributions. CRRA U(W)=W^(1−γ)/(1−γ), W>0; log W at γ=1. Model P(A)=sigmoid(κ[EU(A)−EU(B)]) with decision noise κ. Alternatives: prospect theory (reference point, loss sensitivity, probability weighting), without conflating coefficients. Mean-variance λ depends on horizon, units, choices and constraints; 1–30 is not λ. Compare OOS models and report uncertainty.

## Experimental Validation

1. Psychometrics/behavioral-finance specialist review, cognitive interviews and accessibility.
2. Exploratory pilot (e.g. 30–50 volunteers, insufficient for definitive validation); measure understanding, dropout, time and distributions.
3. Determine sample size via power analysis/IRT simulation; consent, diversity and preregistration.
4. Test-retest and internal consistency where appropriate (omega), convergent validity with licensed instrument, discriminant validity and prediction of independent choices.
5. Differential item functioning by language/order; calibration and uncertainty. Person-level train/validation/test split.
6. Version items, parameters and decisions; no validated-service deployment without independent review. Reassess after major client changes.

Concepts to study: expected utility, prospect theory (Kahneman & Tversky), Holt–Laury lottery tasks, Grable–Lytton financial tolerance scales and IRT. Check rights before reproducing existing questionnaires.

## Data Contract
Card: id, version, locale, dimension, alternatives, probability, payoff, score_direction, scoring_weight, pair_id. Response: pseudonymous_session_id, card_id/version, choice, presented_order, optional_consent_latency. Profile: score, score_version, coverage, sensitivity_range, dimensions, inconsistencies, suitability_status. Deterministic, auditable calculation independent of portfolio swipes.

## Chapter 02 implementation and scientific boundaries

| Construct / hypothesis | Observable task | What cannot be inferred |
|---|---|---|
| Risk tolerance / expected utility | Known-probability gains or mixed lotteries vs certainty equivalent; varying expected payoff | A single pure risk parameter; choices also depend on payoff size and beliefs |
| Loss sensitivity / prospect theory | Reference-wealth gain/loss presentations with economically equivalent pair outcomes, plus mixed lotteries | Clinical loss aversion or a unique individual loss-aversion parameter |
| Framing | Canonical alternatives compared across economically identical wording pairs | Causal framing effect from one person or one pair |
| Trajectory / recency hypothesis | Equal horizon and costs, explicit intermediate drawdown and two terminal outcomes | Recency bias; future randomized path/order comparisons needed |
| Anchoring hypothesis | Explicit reference wealth and fixed safe alternatives; future randomized anchor manipulation | No anchoring measurement in current score |
| Ambiguity | Known vs unknown probability, same payoff | General risk tolerance; excluded from 1–30 score |
| Time preference | Certain current vs delayed amount | Risk tolerance; excluded from score |
| Style | Management preference choices | No common ordinal style dimension; descriptive B share only |
| Confidence | Optional self-report 1–5 after session | No inference from response time or missing answers |
| Consistency | Compare canonical option across repeated pairs, accounting for swaps | Not a diagnosis or reliability coefficient from two pairs |

Twenty items (8 lottery, 6 framing, 6 trajectory) contribute equal exploratory weight. `p = prudent resolved choices / resolved scored items`, `score = floor(1 + 29p + 0.5)`, minimum coverage 14/20. Both unsure and skip are unscored, counted separately. Sensitivity bounds assign all missing scored answers to risky or prudent alternatives: `round(1+29 k/20)` and `round(1+29(k+20−n)/20)`. This is an extreme-case range, not a confidence interval. Framing pair and repeat discrepancies report counts and denominators, not diagnoses. Canonical B means the lower-risk option only on scored items; ambiguity B means known probability, time B means immediate payment, style B is merely the reference option. Do not infer capacity or suitability. The API has `/api/discovery/session` and `/api/discovery/score`; no database persistence. UI consent, keyboard/touch, undo, optional confidence, withdrawal/reset and bilingual report are implemented. No timing is collected.

### Separate utility exploration (CH02.15)

For normalized terminal wealth w>0, CRRA utility is `(w^(1−γ)−1)/(1−γ)` or log(w) at γ=1. Prospect-style value is `x^α` for gains and `−λ_loss |x|^α` for losses relative to displayed reference wealth; use objective probabilities only, not fitted probability weighting. For known-probability monetary choices, compare expected utility/value and a logistic Bernoulli likelihood `P(A)=sigmoid(τ[U(A)−U(B)])`. Fixed temperature τ=10 and small parameter grids; report best grid and near-best likelihood region only. At least seven resolved items. No person-level parameter calibration, no link to optimizer λ, no change to financial capacity. Implemented in `utility.py`, exercised on synthetic extreme responses.

### Pilot and analysis readiness (CH02.16–20)

See [draft pilot protocol](BEHAVIORAL_PILOT.md). `pilot_analysis.py` implements an entirely artificial complete anchor panel, item choice proportions, corrected item-total correlation, test/retest bootstrap interval, exploratory one-factor omega approximation and correlation eigenvalues. Logistic readiness uses disjoint person-level 60/20/20 splits, anchors not target items, language and presentation-order indicators, language×anchor interaction and independent simulated-choice log-loss versus intercept-only baseline. This is logistic exploration with an anchor proxy, not a calibrated latent IRT model; sparse randomized-session missingness needs a pilot-specific design. No real volunteers, cognitive interviews, pilot reliability or predictive validity results exist. CH02.16–20 remain open for actual study evidence and independent review.
