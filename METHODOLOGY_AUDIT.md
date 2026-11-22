# Methodology audit · 22 November 2026

## Finding

The project has a credible sequence from household mandate through dated research, constrained allocation and execution. The main risks found in the design were overly optimistic evaluation on selected participants or dates, reuse of a preferred specification, and a mismatch between the risk measured in a card or a market model and the risk experienced by the household. The 59 design tasks reviewed in this audit have a named bias, a control and a matching evidence slot in the notebook. The 104 local Markdown files match the previously inventoried source versions. The checklist index documents their relevance; focused comparisons below address decisions with a material consequence for the project.

| Area | What the previous protocol covered | What the audit changed and how to verify it |
|---|---|---|
| Questionnaire | Common core, explicit alternatives, passes, held-out choices and simulated routes | Under the revised scope, 2.3.2 documents plausible interpretations, confounding and the permitted profile change. Behavioral prevalence and causal effects are unknown. |
| Market panel | As-of joins, delistings, FX and common samples | 3.1–3.2 measure entry backfill, non-synchronous closes and linkage by size/sector. Compare eligible, matched and full fallback samples. Check whether rank or mandate suitability changes under alternative coverage. |
| Conditional forecasts | Chronological splits, GARCH diagnostics, loss and interval scoring | H01 distinguishes integrated variance from cumulative-return variance. H02 keeps failed fits in the deployed policy. H03 refits generated factors when estimating uncertainty. The H04 notebook now emits forecasts for the latest origin before a label exists and evaluates outcomes separately. |
| Hypothesis testing | HAC, bootstrap and multiplicity registration | 1.2, 5.2 and 7.2 add simulation-based design power, joint date resampling across competing rules, explicit equivalence margins and independent confirmation. Report economic magnitude and sensitivity, including a negative or inconclusive finding. |
| Factor and event studies | Sorts, risk adjustment, abnormal returns and event clustering | H05 handles estimated first-pass betas and conditional use of GRS. H06 adds dated matched placebo events. Do not interpret an unmatched placebo or a joint alpha test with singular covariance as investment evidence. |
| Client allocation | Cost scenarios, solver diagnostics and phi bounds | 6.1–6.2 close the budget including fees, compare frontiers on common constraints and account for the risky sleeve's share of household wealth. Assess terminal funding and cash at the exact due date separately. |
| Monitoring | Timing, stale feeds, cash flows and confirmations | 8.1–8.2 distinguish as-received and revised values. Track a shadow hold path for all eligible proposals, including declines. Adoption is selected by clients, limiting causal interpretation. |

## Course sections driving the corrections

The empirical decision map in [methodology guide 01](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_01.md) gives distinct methods for these questions. F0.7 covers selection, survivorship and anticipation, F5.1 covers power and testing errors, F7.6 covers dependence-preserving resampling, X10 covers spanning, T22 covers equivalence, E1.2 and E1.5 cover GRS and Shanken, and V7 covers Reality Check/SPA. Use the assumptions of each test and record what fails. A comparison of *constrained net* frontier points is an economic extension of the spanning question and needs its own paired out-of-sample evaluation.

The [behavioral course](Theory/Course_Notes/W13_Behavioral_Finance_Guide_FR.md) informs the wording and interpretation of decline scenarios. The [household finance guide](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_34.md) informs funding capacity and liability timing. The [covariance and stability notes](Theory/Course_Notes/QARM2_LN3_Cours_Explique.md) motivate perturbation of moments and weights. The [transaction-cost guide](Theory/Course_Notes/guide_couts_transaction_trading.md) motivates funded trades, full-cost implementation and matched comparisons. The [factor guide](Theory/Course_Notes/guide_modeles_factoriels_capm_fama_french.md) and [aggregate predictability guide](Theory/Course_Notes/guide_predictibilite_agregee_marche.md) distinguish cross-sectional inference from prospective prediction.

## How to use deeper models

| Candidate | Evidence and decision needed before adopting it |
|---|---|
| Dynamic conditional correlation | Establish univariate variance fits, positive-definite forecast covariance and enough independent origins. Compare the multivariate forecast with static shrinkage on identical weights and then net allocations. |
| Nonlinear forecasts, Gaussian processes and sequence models | Define the forecast target and available history. Compare a training-only challenger against a simple registered model on common dates. Charge all tuning attempts to the same selection family. |
| Clustering or regime switching | Freeze how a new observation receives a regime from past information. Compare filtered regimes with the unconditional risk model. Check rare-regime sample size and instability after refitting. |
| Reinforcement learning or derivative-specific PINNs | Reopen for a decision requiring a sequential execution simulator or a derivative valuation equation respectively. Record the simulator or boundary conditions, baseline and falsification case before dedicating research effort. |

## Selected extension from guides 00–06

Tasks 6.1.3–6.2.2 and 7.2.1 operationalize dual sensitivity (00), specification sensitivity (01), robust optimization and out-of-sample utility (04), and reverse stress (05). Guide 02 spanning remains conditional on testing an extra asset. For guide 03, call yield-curve regressions empirical sensitivities; key-rate revaluation needs cash flows or published key-rate durations. Guide 06 requires matching actual or modeled costs across arms. Risks specific to the extension are tuning the uncertainty radius on evaluation dates, confusing uncertainty of means with return covariance, comparing differently funded positions, and assigning probabilities to hypothetical funding failures. The synthetic notebook checks isolate numerical behavior. Empirical validation remains open.

## Corrective actions at the client decision

Tasks 2.1.2 and 9.1.1 test whether preferences and liquidity have distinct effects. Tasks 2.2.5 and 2.3.2 retain uncertainty and illustrate the information supplied by a follow-up. Tasks 5.2.3 and 6.2.2 prevent horizon extrapolation and define no-signal or unresolved outcomes. Tasks 6.1.2 and 7.2.1 isolate the allocator's contribution with identical mandates and fair controls. Task 8.2.1 distinguishes an inconclusive discretionary trade from a binding liquidity change. The notebook includes synthetic counterfactuals and hold/fallback decisions; market evidence remains open. Questionnaire cases are theoretical throughout.

## Evidence still required

This is a design and code-example audit. The [local import review](data/README_data.md) records which market files have arrived. Quantifying remaining bias needs validated point-in-time inputs, independently observed forecast errors and evidence of fills and costs for the market studies. The questionnaire analysis is limited to theory and synthetic routes. For each study report the size of the exposed sample, estimated direction of bias, change in outcome under the alternative specification, residual uncertainty and the resulting decision. Preserve the simple fallback when the evidence cannot distinguish the candidates.


## Final cross-check against the course method inventory

All 59 task IDs in the methodological review retain a named bias control and a notebook evidence slot. Seven tasks gained targeted checks. The review identified material gaps in group-specific interpretation of common cards, back-adjustment of price levels, serial dependence in horizon risk, finite tail-test information, dynamic covariance eligibility, overlapping forecast losses and liquidity at execution. The checklist records the associated outcome, comparator and fallback. Guide 01 (V4), guide 04 (4.4.7) and guide 05 (5.5.12 and 5.5.15) distinguish forecast tests, dynamic dependence and conditional extreme-risk extensions. The tool-selection table shows when these tools can change a client decision. No empirical superiority or individual calibration follows from this review.


## Seven-signal research extension · 22 November 2026

The primary specifications were committed before scoring. Publication-delay and instrument-influence checks were recorded after the first replay and are secondary. The French portfolio spreads have a different endpoint from stock rank IC. The Apple filing verifies one dated security and leaves the population-level test open. The frozen Fed download lacks historical vintages. The family correction covers seven comparisons in this extension, and the inspected history supplies zero independent outcome months. [Protocol](research/robustness/PROTOCOL.md) · [Results, research uses and admission decisions](research/robustness/README.md)
