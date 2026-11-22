# Questionnaire evaluation · protocol v1 · 22 November 2026

Participant collection is deferred. The [simulation table](synthetic_participants.csv) and [per-card counts and evaluation metrics](simulation_summary.json) contain synthetic records only. The [participant template](participant_template.csv) is empty. Use Python 3.12.6 from the repository root to reproduce them:

```sh
python research/simulate_interview.py --table research/questionnaire_validation/synthetic_participants.csv > research/questionnaire_validation/simulation_summary.json
python tests/test_questionnaire_pilot.py
```

## Route checks

The generator uses 60 seeds per behavior and cycles through all 20 probe forms. The eight behaviors are coherent choices under a fixed preference, forced contradiction, indifference with abstention, frequent passes, habitual endorsement, random answers, changing preferences with stake, and early exit. The stake-dependent generator uses the common CHF 1,000 preference on the interview and a linearly scaled aversion at the larger validation stakes. This explicitly challenges transfer across stakes. An early exit contributes its partial answers and four unverified validation slots. Duplicate submissions are rejected on each route. An unresolved example ranking means comprehension failed, the bracket conflicts or lacks evidence, multiple examples are compatible, or omitting one answer changes the options.

For each card, the summary gives the number of generated routes selecting it. A separate deterministic witness generator tries to reach each of the 60 target IDs through the production router. Its counts are excluded from all performance metrics. The controlled presentation test permutes core order, option positions and which alternative the statement endorses, preserving the respondent's economic choices. It checks model invariance under equivalent encoding. A person may respond differently to a change of wording; the human phase measures that effect.

## Freeze before the first participant

Use the revisions in freeze.json for bank, router, predictions and [four validation scenarios](../../questions/pilot_holdout_v1.json). All monetary offers specify final balances in CHF after one year, stake and probabilities. Display the common prompt, both alternatives and an unsure option. The four items use unequal probabilities, three outcomes or new stakes. The live interview has no access to their responses.

Assign a random study pseudonym after consent and use the frozen hash partition in questionnaire_pilot.py, approximately one third development and two thirds evaluation. Keep all choices and repeat visits for a person in one group. Resolve wording issues in development. Any change to scoring, wording, selection or the primary outcome requires a new version and a fresh evaluation cohort. Record non-consent as aggregate counts only. Store consent and contact details separately from pseudonymous records.

Use a facilitated research session for the pilot. The standard app reveals the profile on completion; a pilot session must withhold that screen until all validation choices have been recorded. Before recruitment, rehearse the sequence with the blinded facilitator or a dedicated participant mode. Deliver practice feedback as usual and withhold the model ranking.

1. Record assignment, start time, device, questionnaire version, form and language comfort. Seal the core prediction on first completing the common items. If the participant stops early, freeze the available partial record for both arms.
2. Record each eligible and selected probe, answer, correction and timestamp. Seal the adaptive predictions at completion or withdrawal. A later correction can change only the adaptive comparison once the core record is sealed.
3. Give the four validation items once, before displaying results. Rotate item order by assigned form modulo four; alternate certain-first and gamble-first presentation by form plus item index. Archive offer order and semantic choice separately. Record unverified items explicitly. A strict inequality is required for a directional prediction from the entire compatible interval. Ties, conflicts, failed comprehension and ambiguous intervals yield abstention.
4. Record core minutes and additional minutes excluding logged interruptions. Count a funding correction only when the participant confirms a dated change to amount, settlement or reserve. Record it at core and at completion. A request to reconsider alone does not qualify.
5. Invite all starters to repeat the same frozen choices after 7–14 days, with a fresh display order. Report invited, returned, usable and paired counts. Document any change in circumstances and compare tolerance status, overlapping intervals and held-out choice repeatability. Debrief ambiguous wording by asking the participant to explain each alternative in their own words.

## Participant table and decisions

The collection template gives one row per assignment. The event ledger is linked by study pseudonym and visit. Record consent before individual data entry. Preserve scheduled but unverified outcomes as missing. No actual pilot records belong in the Git repository.

Compute the primary paired difference in verified hits per four assigned slots. Report alongside prediction coverage, verified coverage, conditional agreement, and accuracy on the common verified items. Average within person first. Strict additional constraints typically increase coverage while leaving pre-existing directional predictions unchanged. Zero change on the common items can therefore coexist with new correct predictions. Missing-outcome bounds treat every unverified slot as either a miss or a hit and are deliberately wide. Report uncertainty separately using a paired participant bootstrap (2,000 resamples, seed 2302). Report denominators for every metric, including zero-prediction participants, early exits, failed practice and unreturned retests. Preserve missing time as missing; never substitute estimated simulator time.

The project-defined useful gain is five percentage points in verified hits per assigned slot with at most two median extra minutes. Retain a funding probe with a documented consequential correction for separate review, even if its predictive gain is small. If uncertainty spans the target or timing is missing, keep the result inconclusive. Report median time and proportion within the original 5–10 minute design target. Revisions to thresholds and duration follow the independent observations.

For every common item, report pass rates and comprehension by wording version, device and declared language comfort. Report verified agreement with its coverage within each group. If groups have overlapping leave-one-item-out scores, both response outcomes and enough distinct participants to estimate coefficients, fit endorsement on that score, group and their interaction with participant-clustered uncertainty. Otherwise mark the comparison inconclusive. Record wording debriefs before attributing differences. Branch frequencies show which users reached a probe. The paired prediction comparison addresses incremental information on these routes; causal claims about offering a probe require randomized assignment among eligible participants.
