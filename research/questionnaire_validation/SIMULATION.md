# Checking the hypothetical questionnaire

The [behavioral rationale](../../questions/QUESTIONNAIRE_DESIGN.md#how-to-interpret-hypothetical-answers-in-the-report) gives the possible meanings of each question family. The [route table](synthetic_participants.csv) and [per-card counts](simulation_summary.json) describe generated answers only.

## Reproduce the checks

Run from the repository root with Python 3.12.6.

```sh
python research/simulate_interview.py --table /tmp/riskmatch-routes.csv > /tmp/riskmatch-summary.json
cmp /tmp/riskmatch-routes.csv research/questionnaire_validation/synthetic_participants.csv
cmp /tmp/riskmatch-summary.json research/questionnaire_validation/simulation_summary.json
python tests/test_questionnaire_pilot.py
```

The generator uses seed 2301, eight response rules, 60 routes per rule and 20 probe forms. Rules cover consistent trade-offs, contradictions, indifference, frequent passes, habitual endorsement, random answers, stake-dependent preferences and early exit. All 60 cards occur in the 480 routes. A separate targeted search supplies a witness route for each card and is excluded from the metrics. Presentation tests keep economic choices fixed while varying order, position and the alternative that “yes” endorses.

The [four external choices](../../questions/pilot_holdout_v1.json) use different stakes, probabilities or payoffs. Core and adaptive predictions are sealed before comparison with synthetic responses to these choices. The evaluation partition contains 333 generated routes. Coverage is the proportion of slots receiving a directional prediction, averaged by route. The summary also reports agreement among verifiable choices and missing-outcome bounds. These measures depend on the eight assumed rules and their assigned frequency. They cannot estimate how investors would respond or how long they would take.

The [version manifest](freeze.json) identifies the inputs, generator and scoring code used here. The notebook's three fictional sale decisions illustrate how the same action can lead to a cash review, a stability preference or a recorded market belief.
