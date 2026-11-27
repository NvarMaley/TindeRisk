# Draft Exploratory Behavioral Pilot Protocol

Draft dated 2026-11-24; not externally preregistered, approved, or recruiting. Version `discovery-v3.0.0`. The current local Web App is simulation-only and must not collect real respondent records. Real pilot deployment requires an independently reviewed consent, access control, rights and retention workflow first.

## Research questions and outcomes

Primary descriptive outcomes: response coverage, item choice proportions, completion/dropout, comprehension and paired consistency. Secondary exploratory outcomes: test-retest stability, corrected item-total association, factor dimensionality, omega only if a single-factor model is defensible, language/placement differences and prediction of held-out simulated choices. No clinical or advisory interpretation. Predefine exclusions (no consent, invalid session/version, duplicate participant IDs, missing resolved responses reported rather than imputed). Do not exclude responses merely because they disagree with the proposed score.

## Design

- Cognitive interviews and accessibility review first: ask participants to paraphrase probabilities, reference wealth, costs, sure alternative and swipe mapping; capture misunderstanding, not assumed bias. Test EN/FR comprehension independently.
- Exploratory pilot 30–50 consenting adult volunteers after review; not a sufficient sample for definitive IRT or DIF conclusions. Determine a larger confirmatory sample by simulation/power analysis and independent expert advice.
- Use the fixed 30-item questionnaire in its common order and record version and response language. Test order effects in a separate experimental condition if needed. Report sparse answers explicitly.
- Repeat the same version after a prespecified interval (proposed 1–2 weeks); record interval, not sensitive activities. Independent simulated choice task must not reuse scored choices. No real-money incentives tied to risk and no excitation measurements.
- Optional time/fatigue only with separate consent, aggregate analysis, and no timing-based individual score. Use short comprehension probes and open-ended feedback; allow stopping at any point.

## Consent, privacy and withdrawal

Provide purpose, voluntary nature, estimated duration, fictional choices, no investment recommendation, data fields, retention, who has access and withdrawal contact in plain EN/FR. Do not collect names, financial records, demographic or biometric information beyond separately justified and consented study needs. Use random participant IDs with contact/consent linkage stored separately, least-privilege encrypted storage, no Git/notebook/log publication of raw responses. Proposed retention: delete identifiable linkage and raw study data within 90 days of study completion unless a reviewed protocol specifies otherwise; retain only explicitly consented non-identifying aggregates. Explain any limits to withdrawal after irreversible anonymization. Real recruitment, consent documents, retention and applicable legal/ethics obligations require independent review before collection.

## Analysis plan

1. Report denominators, nonresponse and dropout, item difficulty (choice proportions), corrected item-total associations with uncertainty, comprehension/readability issues and time/fatigue only if consented.
2. Assess dimensionality before combining items. Test-retest across linked forms; bootstrap at person level. Report omega model and uncertainty only for defensible constructs; separate mixed gain/loss decisions, rare events, trajectory choices and confidence where appropriate.
3. Split participants, never responses, into pre-specified train/validation/test sets. Fit logistic/IRT alternatives on training only with anchor linking; examine language and placement DIF after controlling ability, report estimates/uncertainty and sample-size limitations; no automatic demographic inference. Freeze analysis choices before final test.
4. Test predictive improvement versus simple baselines on independent simulated choices with held-out people. Report calibration, log loss, uncertainty and null results. No financial suitability linkage absent independently established validity; keep all experiments including failures.

Technical dry run: `src/riskmatch/behavioral/pilot_analysis.py` and the notebook use fully synthetic generated panels, not volunteer records. They demonstrate the analysis pipeline only. Real study steps CH02.16–20 remain pending.
