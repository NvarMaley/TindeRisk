# How the studio constructs a match

The studio solves a new allocation after calibration. It uses the approved band, investable CHF after the household reserve, goal date, desired annual return, affordable loss in CHF, direct ticker exclusions and any supported issuer restrictions. The model also handles funded revisions. A change in cash, holdings or date changes the inputs to the next solve.

## Universe and estimates

The **30 October 2026** closing model contains 3,322 eligible US instruments. These comprise 3,255 individual stocks, 54 direct US Treasuries, 10 equity ETFs, two Treasury ETFs and one gold ETF. The catalogue contains additional reviewed securities that missed the dated allocation gate. A large universe gives the optimiser more opportunities to select historical winners by chance. Individual estimates and optimised portfolio returns can be especially sensitive to the estimation window.

Historical CHF means use 504 or 756 sessions, cross-sectional 1st/99th percentile clipping and 50% or 75% shrinkage to the cross-sectional median. The covariance model contains exposure to three common factors (US equities, Treasuries and gold) plus security-specific variance. The variance of a blend comes from its combined holdings, including cross-correlations. The three modeled return estimates form a sensitivity range. That range has no statistical confidence level. The dated model bundle identifier is `e9d9400b2b65a9fd`.

## What each card optimises

| Card | Objective |
| --- | --- |
| Return seeker | Maximise the baseline historical return estimate after trading cost. |
| All-weather | Maximise the weakest return estimate across the three specifications and test both covariance specifications against the ceiling. |
| Spread the risk | Penalise concentration of invested positions and reward deployment, return and progress toward the annual aspiration. |
| Shock shelter | Minimise the worst modeled loss among the 2008 and conditional macro shocks, balanced against return, the goal and concentration. A small loss across these selected shocks can coexist with a much larger loss in a different crisis. |
| Carbon lens | When requested, apply a lower-intensity objective to corporate holdings with full instrument-level measured coverage. Only 55 model lines representing 54 issuers meet that instrument-level gate. The unit is US direct point-source tonnes of CO₂ equivalent per USD million of 2023 revenue. |
| The classic | Compare a 60/40 mix of SPY and IEF. Scale participation to fit the upper risk limit and maximum invested share. |
| Cash reserve | Retain the sleeve in CHF when the calibration mandates minimum exposure. |

The rate aspiration is the greater of the desired return and the return required for the stated goal. A target can be infeasible. The goal estimate compounds the post-fee sleeve with the historical model rate to the specified date and adds the remaining protected amount and applicable cash flows. The rate shown on a card includes the entry or revision cost amortised over the horizon. These conventions allow the one-time cost to enter the terminal projection once.

The solver uses the complete eligible vector, long-only positions, a 60% per-line cap and a 90% total invested cap. At least 10% remains as cash within the sleeve, separately from the protected household reserve. The solver leaves small margins for whole-unit rounding. It checks the final integer holdings against the estimated volatility floor and ceiling, whole-position limits, settled funding, selected restrictions and CHF loss budget. Where required, a supporting-plane branch searches for a portfolio above the risk floor. Failure to produce a card describes this strategy and search procedure. It cannot establish that every possible portfolio is infeasible.

Direct ticker exclusions remove those instruments. The strict Chevron screen also excludes unknown and indirect issuer exposure under the environmental study's look-through rules. The measured emissions metric covers the published subset of portfolio value. It is an operational point-source intensity with limited coverage. It cannot establish an all-sector footprint, fund-wide sustainability rating or full Scope 1–3 inventory. Environmental evidence was reviewed **23 November 2026**, including holdings disclosures after the market snapshot. The combined exercise is a retrospective demonstration.

## Stress, score and signals

The 2008 test applies observed CHF returns where a complete series exists. For other names it uses a factor projection. The five additional conditional scenarios cover oil up, oil down, USD/CHF appreciation, a USD interest rate increase and the joint market/rates/oil/FX shock. The interest rate move shifts the ten-year rate by 50 bp and the 10y–2y slope by 25 bp. Direct Treasuries use full cash-flow repricing for this move. Scenario profits and losses are denominated in CHF. The largest tested loss, including transition cost, is compared with the household's loss capacity. No scenario assigns an event probability or bounds the true maximum loss.

The comparison score reuses the historical study's four observable criteria. Goal alignment contributes 35 points, stress 15, diversification 15 and transaction cost 10. Their weighted result is rescaled from 75 available points to 100. Higher goal scores favour modeled returns relative to the household aspiration. Concentration includes both cash and securities. Lower modeled stress loss and lower turnover improve the other two scores. No points are assigned to unvalidated household-level forecast or sustainability claims.

Five signal families keep separate readings. These are momentum, yield curve, VIX, news tone and geopolitical risk. Section 12 measures the indicators on 30 October and issues its validation review on 23 November. Its 21-session entries concern SPY variance in CHF. Their transfer to custom portfolios has no validated forecast weight. Cards provide the portfolio's own rates scenario or SPY correlation where relevant.

## Execution, blending and follow-up

- Whole-unit execution assumes the project's synthetic USD closing prices and synthetic USD/CHF translation. One direct Treasury lot represents USD 100 face. The convention uses five dated closes from 30 October through 5 November. No field is a real-time market quote.
- The transaction charge is 10 basis points on absolute CHF traded. A funded revision charges only the difference between target units and the existing book. The household reserve stays outside the investable account.
- A manual blend takes nonnegative shares summing to 100%. A suggested blend searches positive shares at 10-percentage-point increments, then selects the highest annual net-return/volatility ratio among combinations that pass the full integer-holdings checks. Each candidate is rounded only after combining the holdings. The assumed CHF cash rate for this ratio is zero.
- The downstream ledger confirms holdings, costs and cash. It applies the dated simulated close to mark changes and records cash flows separately from portfolio performance.

## Reproducible example

For a CHF 35,000 sleeve plus a CHF 5,000 protected reserve, an estimated 6–12% band, a CHF 48,000 household goal on 30 October 2031 and a 5% desired annual return, the five ordinary strategies pass the integer checks. The comparator holds two instruments with 11.38% annualised modeled volatility. Spread the risk holds 207 instruments with 11.97%. Imposing a CHF 2,000 tested-loss ceiling removes the classic mix because its largest tested loss is about CHF 4,988. Four optimised alternatives pass in this example. The baseline model produces an annual return estimate above 40% for some selected mixes. It is an in-sample result selected from thousands of names. There is no evidence here that a client will earn it.

Run the portable regression suite from the repository root.

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_studio_allocation.py -v
```

The app uses the checked-in [derived model](model.json). To rebuild it with the local section 6, 8 and 11 archives installed, run `PYTHONPATH=src .venv/bin/python -m riskmatch_v2.build_studio_model`. [Section 6 universe and models](../univers-complet/resultats.json) · [Stress study](../08-chocs/results.json) · [Environmental review](../11-environment/results.json) · [Signal registry](../12-forecasts/registry.json).
