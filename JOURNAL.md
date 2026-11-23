# Journal RiskMatch V2

## 23 November 2026 — State of departure

| Decision | Justification and evidence |
|---|---|
| Self-contained base V2 | Installation and testing of the catalogue on isolated copy. The notebook performs the diagnostics of the fictitious catalogue and exports a figure. V1 data are optional. |
| US market and CHF base | The universe of proposals must be negotiable at its decision date. The actual catalogue and eligibility checks are to be constructed. |
| Prototype web | Demonstration cards, fictitious score, choice and mix, animated match and consultation of composition. The visual identity resumes pink, electric blue and 3D cherry. Cognitive banking, the financial engine and their integration remain to be developed. |
| Work folder | The checklist details the controls, the notebook has a section per site and the directory documents the methods. Private repository [NvarMaley/RiskMatch-V2](https://github.com/NvarMaley/RiskMatch-V2) is dedicated to this file. |

## Access to data — 23 November 2026

The user provides local files and does not have WRDS subscription. Priority is given to local inventory, complementary public sources and dated universes whose coverage is demonstrable. For 2026 prices and direct bonds, keep a distinction between historical, listing, price and real access to trading. The missing data remain visible and no additional market imports are validated at this stage.

## Organisation of results — 23 November 2026

Deliverables for a verified step are linked in the checklist, log and notebook. The graphs and their legends are stored in the [directory of results](reports/README.md). The [first graph](reports/01-socle/README.md) checks the trajectory of an equal-weight portfolio and the volatility of fictitious data instruments. This check is based on the embedded catalogue and the notebook. It does not validate any market data.

## Step-by-step monitoring

For each verified step, enter the date, box number, decision or result, order and version of entries, links to evidence, limits and open actions. Update the [checklist](CHECKLIST.md) and [Notebook](RiskMatch_V2.ipynb) with the same condition.

## 23 November 2026 — 1.3 · Market import

The first V2 research catalogue brings together 3,341 monthly returns in CHF for 13 ETFs. The exchange rule on the same day retains 257 of the 261 candidate months. Four months are discarded and November 2026 is incomplete. Each series is dated and sealed by checksum. The commodities and the catalogue remain in `data/local/1.3/`. Transaction prices and hours of first availability remain to be qualified.

The vintage `2026-11-23.1` reproduces with `python -m riskmatch_v2.market_import`. The audit focuses on the same recovery, conversion to CHF, refusal of a revised file, missing months, reconciliation with the second local export and execution of the notebook. Next open box, 1.4, fixed weight comparison over explicit periods and fees. [Report and timetable](reports/01-3-import-marche/README.md) · [Notebook](RiskMatch_V2.ipynb)

## 23 November 2026 — 1.4 · Historical references in CHF

The 60/40 SPY–IEF is compared in annual storage and rebalancing, with a nominal reserve CHF at 0%. The four months of missing exchange lead to three independent periods of 70, 130 and 57 months. The scenario at 10 bps per amount processed is framed by the sensitivities 0 and 25 bps. Over the last period, annualized net compound returns reached 4.69% in annual management and 5.41% in conservation. The statutes and reasons are calculated for four theoretical terms.

The market vintage is `2026-11-23.1`, the parameters are versioned in `config/references-1.4.json`. The command `python -m riskmatch_v2.benchmark` reconstruct the aggregates and 771 lines of the private register. Controls of fees, net capital, periods and warrants by test and notebook. return remains historical and fees are an assumption. [Report and graph](reports/01-4-references/README.md) · [Notebook](RiskMatch_V2.ipynb)

## 23 November 2026 — 1.5 · Traceability and closure of Section 1

The matrix combines each of the 86 checklist items with an existing or expected demand, type of work, dependencies and evidence. Four paths specify the results to be checked for incomplete response, unrealizable target, radiation and revision after selection. The notebook automatically compares the matrix identifiers to those of the checklist. Check result: 86 out of 86, without duplicates, and five sub-steps of the checked base. [Matrix and route](reports/01-5-exigences/README.md) · [Notebook](RiskMatch_V2.ipynb)

The closing check replayed import 1.3, the calculation of references and the notebook from V2 with private data. A second execution installed the package on a copy of the only shared files in a 3.12 Python environment, with already available notebook dependencies. The 11 tests, the CLI and the notebook pass there without private data. The published aggregates are used to reread the graph on this copy. Recalculation from the prices requires the local entries of the vintage. The next box is 2.1, the card bank and the rules of interpretation.

## 23 November 2026 — 2.1 to 2.8 · Questionnaire and mandate

| Item | Decision and audited result |
|---|---|
| 2.1 | Bank 2.0.0 of 41 cards with stable identifier. The guide links each formulation and response to the construct, the other possible explanation, the relaunch and the authorized decision. |
| 2.2 | Seizure of capital, dated flows and their certainty, bearable loss and objective. The limits of the cumulative deficit determine the reserve. The case of 50,000 / 15,000 gives 35,000 CHF invested. |
| 2.3 | Desired return, type of risk, base, exposures, diversification, exclusions, sustainability, coverage and combination. Unknown firm rules remain to be checked. |
| 2.4 | Three comparable gambles can bound φ if the respondent understands them. Manual control gives 2.67 and 4.44. The removal of each numerical response is replayed. A contradiction opens up a clarification. |
| 2.5 | The exports in Figure 1 keep the vintage, dated responses, assumptions, provenance and open fields. The correction of the expenditure to CHF 22,000 gives a investment sleeve of CHF 28,000 in the new version. |
| 2.6 | A Streamlit card component shares the same validation between buttons, keyboard and swipe. Chrome has replayed the prices on computer and tactile gestures on emulated mobile, including a short gesture, cancellation and double click. |
| 2.7 | Seven fictitious cases dated November 23, 2026 verify the expected statements. The road tests cover the 41 cards and the removal of a branch which has become inactive after correction. |
| 2.8 | The seven families each have a common card and precision questions. The reasons for sale, the double inversion of scoping and the mismatch between declaration and bets have distinct effects. |

The notebook replays the seven cases, revision and graph with the application engine. Verifications by `python -m unittest discover -s tests -v`, `jupyter execute RiskMatch_V2.ipynb` and `python tests/parcours_navigateur.py` against local service. The answers remain in the session and individual exports on the customer's machine. The assessment is based on theoretical scenarios and an emulated motive. The next step, 3.1, sets the volatility band conventions. [Report and graph](reports/02-questionnaire/README.md) · [Guide by card](reports/02-questionnaire/CARDS.md) · [Notebook](RiskMatch_V2.ipynb)

## 23 November 2026 — 3.1 to 3.4 · Confirm the risk request

| Item | Decision and evidence |
|---|---|
| 3.1 | The thresholds of the checklist (4, 8, 12 and 20%) replace the ADRME preliminary agreement. Named classes include the low bound. The two bounds of a free slice are included. Configuration 3.0-2026-11-23. |
| 3.2 | After the questionnaire, the customer sees the scenarios, chooses the plate, confirms, modifies or differs his request. Figure 2 adds the dated decision and keeps the version of the portrait. The versions of diagram 1 remain legible. |
| 3.3 | The reasons cite the relevant responses and flows. An adversarial request remains in clarification and retains its declared value. In a synthetic case, the assumed 18% maximum limit is 38-42%. The limit of 40% remains to be tested. |
| 3.4 | 50 CHF 1,000 in capital and CHF 15,000 protected give a hypothetical loss of CHF 3,500 for -10% on the investment sleeve, i.e. -7% of the household. Cases of uncertain spending, date unknown and zero investment sleeve are replayed. |

The notebook reconstructs the 11-case record and the figure since the fictitious responses of November 23, 2026, with the same code as the application. The assumptions of -10 per cent to one month and -20 per cent to twelve months are used for dialogue. The market feasibility and allocation classification remain to be established in Sections 5 and 6. Check later on tests, the notebook and Chrome prices including modification, export and indecision. Next open box, 4.1. [Report, results and graph](reports/03-portrait/README.md) · [Notebook](RiskMatch_V2.ipynb)

## 23 November 2026 — 4.1 to 4.9 · American and historical catalogue in CHF

| Item | Outcome and scope |
|---|---|
| 4.1 | 27,507 versioned entries. The identity of a CRSP title follows the PERMNO and the classification valid for the month under review. The inventory also includes 65 Treasury issues, factors and references. |
| 4.2 | Reconcilable calendars and distributions. 70,161 daily ETF returns in CHF exploitable on 71,565 bottom-level pairs. Two of the 1,389 dividends exceed 10 bps of the reconstruction gap. Reasons and values are retained. |
| 4.3 | 60,684 action cards and 52 fund sheets over 1/3/5/10 years. Empirical control matrix over 3,404 series and 36 common months. |
| 4.4 | The criteria for the 4.0-2026-11-23 vintage give zero candidate verified for the account. The prices, the FX and the conditions for ordering must be updated. |
| 4.5 | Two separate views for December 2025 and November 2026. The last 60/40 over 57 months reproduces the final values of 124.32 and 128.41 CHF for 100 starting CHF. |
| 4.6 | Matrix by class, units, metrics obtained and missing entries. The reported duration covers the Treasury lines identified in IEF and TLT. |
| 4.7 | Manual cases and test files for change, closing, events, write-off, expired price, short history, duplicate and revision. |
| 4.8 | prices times and distinguished availabilities. Two macro frozen views, with ALFRED versions and conservative availability of prices extractions. |
| 4.9 | 1,055 lines of positions for 12 funds. The 20% of Apple live becomes 29.68% after taking SPY and XLK into account. GLD maintains an unallocated detailed exposure. |

Individual sources and tables remain in the local V2 folder. The notebook rereads the aggregate statement and regenerates the shareable figure. The application allows you to find an individual file by ID. Next open box, 5.1, preparation of Feasibility Engine inputs. [Report and figure](reports/04-catalogue/README.md) · [Methods matrix](reports/04-catalogue/METHODS.md) · [Notebook](RiskMatch_V2.ipynb)

Closing audits of Section 4. The 36 tests go through. The notebook regenerates the chart, including a copy of the only Git files. The second run of the catalogue checks the checksums. The local Chrome route finds SPY by symbol and Apple by PERMNO 14593.

## 23 November 2026 — 5.1 to 5.8 · Test the feasibility of an application

| Item | Decision and outcome |
|---|---|
| 5.1 | Windows of 504 and 756 sessions CHF, reduced averages, Ledoit–Wolf, empirical covariance and three factors. Three blocks of 63 sessions assess the volatility of the equal-weight investment sleeve on later dates. |
| 5.2 | Calculation function with reserve, positions, exposures, costs, financing control, minimum search and ceiling maximization. At 12%, the estimated return is 11.40 per cent in the historical case of funds. |
| 5.3 | Under a 40% ceiling, the optimum uses 20.50% risk. For the 38-42% band, the exact peak on 170 peaks is 22.18%. The statutes distinguish candidate, verified optimumity, impossibility and uncertainty. |
| 5.4 | The analytical case and independent grid on SPY–IEF corroborate the calculation. Exclusion controls, cash alone, empty universe, sales financing, bands and applications at 35/40/100%. |
| 5.5 | The local daily CRSP extraction reaches the population of December 2025. Of the 3,837 series envisaged, 3,676 are modelable. The current registry of 27,507 entries gives zero eligible instruments. Repeated measurements on several sizes and separate cache for data and mandate. |
| 5.6 | The 12% ceiling allocation varies with the window and blocks drawn. A conservative variant is tested on the sixteen models. The comparative ranking changes six times. |
| 5.7 | A test interrupts the search after the first candidate before certification. The active limits, weights, deviations and constraints are kept for rereading. |
| 5.8 | The rounded quantities are reverified. A minimum purchase of 900 CHF is unfeasible on the fictitious 500 CHF investment sleeve. A investment sleeve of CHF 1,000 keeps CHF 139.64 after purchases and expenses. |

The notebook reproduces the evidence in sections 1 to 4 and develops each of the eight checklist items in section 5. Outputs are saved in the shared file to allow direct reading of tables and figures. [Report](reports/05-faisabilite/README.md) · [Notebook](RiskMatch_V2.ipynb) · [Engine and testing](tests/test_feasibility.py)

Final check. The notebook contains 25 calculation cells with saved outputs and eight embedded graphics. The Git copy alone executes the notebook. Chrome replicates the 12% cap and the impossible 38-42% band.

## 23 November 2026 · Section 6, compare and combine options

Illustrative mandate in CHF, 35,000 investments and 15,000 reserves. Assumptions, scenario outputs and graphs are published together. [Report](reports/06-options/README.md) · [Notebook](RiskMatch_V2.ipynb) · [Versioned grid](config/options-6.json)

| Item | Decision and audited result |
|---|---|
| 6.1 | Four distinct variants under a 12 per cent ceiling. The 60/40 fixed reference is out of mandate. The environmental measure depends on step 11. |
| 6.2 | The table separates realized performance, annual estimate, model range and 2008 shock. Risk contributions return to the volatility of the investment sleeve. The exposures known by issuer shall bear a date of publication. |
| 6.3 | Nine annual decisions, implementation from the next session. Central cost of 10 bps on trade. Value in CHF and dividends credited to the day ex-dividend by agreement. |
| 6.4 | Daily check of available cash, regulations and positions. Tests include missed execution, partial sale, dividend, title division and withdrawal. |
| 6.5 | 35 regames compare costs, deadlines, first basket missed and rounded. The four variants serve the withdrawal of CHF 1,000. The reference serves CHF 272.86 in the central case. |
| 6.6 | Two illustrative profiles. Robust and Performance are in the same score band for the Objective profile. No options listed for the current account. |
| 6.7 | Historical grid common to 90% coverage. No feeling, complete assumptions on fictitious case, exclusion and inversion of rank below the margin of two points. |
| 6.8 | The manual mix 60% return, 40% Diversification achieves an estimated volatility of 11.68% after aggregation of positions. Whole quantities, risk, score and fees are reverified. |
| 6.9 | Eleven reference combinations. The Sharpe's search for three options has about 92.8% Performance and 7.2% Coverage. Controls also cover minimum risk, return and a minimum share per option. |

The local application allows to change the band, exclusions, priority and shares. The repository contains the published aggregates and the three figures. Detailed market records remain in the versioned local catalogue. [Implementation](app/pages/4_Options.py) · [Results](reports/06-options/resultats.json)

Closing check. The 49 tests pass. The notebook is re-executed on a copy of the Git files only and produces 34 calculation cells and 11 embedded figures, including nine cells and three figures for this section. The application also recalculated a Sharpe mixture and displayed its score after rounding.

## 23 November 2026 · Extension of individual stocks

The 3,824 actions active in December 2025 were sought without a WRDS subscription. **3,129** have a prices path and full volumes until 30 October 2026. **3,113** also pass the threshold of 252 returns CHF out of 504 sessions on common dates with factors. The monthly and daily tables bring together old and new observations, keeping their origin. The inventory lists the exceptions and documented outputs. The Catalogue tab and the notebook show the results. The IPO of 2026 and the reconstruction of the exits remain open in 9.1–9.2. [Report, graph and sources](reports/actions-2026/README.md)

## 23 November 2026 · Resumption of sections 1 to 6 on the selected universe

As of October 30, 2026, the multi-asset study submitted 3,322 securities, including 3,255 individual stocks, 54 direct Treasuries and 13 ETFs. Previous comparisons of 13 ETFs are used as a control. Composition and exclusion files are available by security and date. The application opens the entire universe by default. We can filter the volatility range, exclude identifiers and combine options.

- 75,822 FedInvest price, 65 programs identified and exact coupon documented from auctions. 64 titles existed on October 30.
- Nasdaq review of the 695 action files in difficulty and 289 IPO operations archived separately. Retrospective risk rating differs from account control.
- Four variants, 60/40 reference, nine replayed decisions, seven enforcement agreements, Euler contributions, three models and eight resamples.
- First joint rupture of valuation on 2017-12-22. Indicative values are reported, unestablished scores suspended and checklist items 6.3 to 6.5 reopened for missing evidence. The digital controls of the register pass. The game follows daily rates after the release of the monthly list and processes fully cash buybacks identified by a CRSP terminal event.
- 57 Automated tests passed. The Catalogue, Feasibility and Options screens were exercised on an action, obligation and mixture. The notebook executes 40 code cells and produces 15 figures in a copy containing only the shared files.

[Audit of assets, results and graphs](reports/univers-complet/README.md) · [Correspondence of 43 cells](reports/univers-complet/AUDIT.md) · [Notebook](RiskMatch_V2.ipynb)

## 23 November 2026 · Econometrics by security

Thirty-three exchange rate sessions supplemented by ECB observations of the same day. The corrected records give 2,844 complete monthly historical records over five years and 1,989 over ten years. The oil/rate/FX/market estimate reaches 3,338 instruments with the threshold of 200 observations out of 252. The coefficients cover all positions in the four options and the reference portfolio. Three historical episodes, two variance references and a descriptive alert are available in the Catalogue. Forecasts remain experimental. [Results and figure](reports/econometrie/README.md) · [Notebook](RiskMatch_V2.ipynb)

Delivery check on 59 automated tests and 42 code cells in the notebook. The Apple, GLD and Treaty Direct screens display the new analyses.

## 23 November 2026 · Alignment of point 6 of the notebook

The nine numbered subsections displayed the benchmark on 13 ETFs, while the multi-asset calculation appeared in a supplement after 6.9. Cells 6.1 to 6.9 now present the results of the universe used by default in the application. Local control recalculates the weights on archived models, the sum of contributions to risk, the daily reconciliation and the first weights of the manual mixture. The oil scenario comes from the econometric ratio linked to the same version of portfolios. The nine-year score remains suspended for incomplete trajectories. The 12-month retrospective diagnosis and Annex ETF each have separate wording. [Notebook](RiskMatch_V2.ipynb) · [Reference report](reports/univers-complet/README.md)

## 23 November 2026 · English edition and notebook scope audit

Reviewed all fourteen workstreams against the numbered checklist and requirements matrix. The main notebook derives its progress table from the checklist. Sections 1–5 have evidence for their checked items. The section 6 replay checks in 6.3–6.5 remain open. Sections 8–10 and 12 contain partial research results, and section 13 contains a working prototype. The point-in-time account gate continues to block actual orders. No acceptance box changed solely because its description was translated.

Section 6 now presents the selected multi-asset universe. Its 3,322 modelled instruments include 3,255 US stocks, 54 direct US Treasuries and 13 ETFs. Moved the nine code cells for the initial ETF experiment into a [separate benchmark notebook](reports/06-options/ETF_Benchmark.ipynb). The [main notebook](RiskMatch_V2.ipynb) ends with section 14.

Translated the research documentation, the 41 cards, their interpretation guide, the interfaces and the published figures. Versioned provider data, archive fingerprints, stable identifiers and client-entered text retain their original values. English display labels can be read from historical research snapshots. Closed-choice answers from older French exports can be validated without altering a client’s free text.

The notebooks contain 39 and nine executable cells, with 13 and three embedded figures respectively. The public JSON reports retain the same numerical values as the previous edition. Reproduction and browser checks cover the questionnaire, correction and export paths, the risk decision and mobile gestures. [Checklist](CHECKLIST.md) · [Reports and figures](reports/README.md)

## 23 November 2026 · Item-by-item research notebook

Reorganized the main notebook so all 86 numbered items, from 0 through 14.4, appear in checklist order. Each item has its own checkbox, method, tools, evidence and result or open measurement. Section 3 now gives separate worked cells for volatility bands, client confirmation, contradictory requests and the reserve’s effect on losses. Section 4 separates data schemas, cleaning, history, eligibility, point-in-time records, methods, data-quality tests, release timing and holdings attribution. The 13-ETF benchmark remains a separate study.

The notebook contains 82 executable cells and 13 embedded research figures. Item 1.5 checks heading coverage, section placement, order and checkbox status against the checklist. Open points retain their original status. The funding examples in section 7 illustrate the method without implying a completed client simulation. [Main notebook](RiskMatch_V2.ipynb) · [Checklist](CHECKLIST.md)

## 23 November 2026 · Section 7, dated goals and CHF funding gaps

Completed research items 7.1–7.4 for two synthetic mandates on the frozen 30 October market snapshot. Both clients desire 3–5% annually and confirm the same 12% sleeve volatility cap. Moving from a near-term bill and a three-year goal to a later bill and an eight-year goal changes the reserve from CHF 15,000 to zero. The annual net funding requirements are 12.61% for A and 8.62% for B. Moving only A’s bill to March 2028 lowers A’s required rate to 10.56%. At a constant illustrative 5% net rate, additional upfront savings of about CHF 8,185 and CHF 13,453 would fund the respective original goals under the dated-rate calculation.

The two affordable section 6 research allocations contain 137 and 141 positions. Seven overlapping six-month blocks support a paired scenario exercise, one twelve-month path can be repeated, and there are no complete paired twenty-four-month blocks. Reported counts describe the historical scenario construction. The longer fixed-benchmark series and deterministic price shocks show why an apparent success rate cannot certify either client goal. The separate account-access gate still admits zero orders.

Published the two client records, input configuration, control cases, coverage chart and path summaries. Individual lot counts and per-path first shortfalls, recoveries and terminal deficits remain in the reproducible local archive. The notebook now reports results separately under 7.1, 7.2, 7.3 and 7.4. [Funding study and figure](reports/07-funding/README.md) · [Checklist](CHECKLIST.md) · [Research notebook](RiskMatch_V2.ipynb)

## 23 November 2026 · Repair of the first multi-asset replay gap

Verified PFBX’s change of venue and reconnected observed OTC closes without changing the frozen plans or recording any new order. The common comparison now spans 51 sessions through 12 January 2018. The next unresolved observation is BHAC on 16 January. The central nine-year cash, fees, traded amounts and NAV reconcile across 11,310 option-days. Items 6.3–6.5 remain open for full-period economic validation. [Evidence and remaining data request](reports/univers-complet/README.md)

## 23 November 2026 · 8.1–8.4 · Exposures, crisis recovery and CHF stress attribution

Added the US two-year rate to the frozen 30 October snapshot, measured yield-curve and oil shocks, and aligned prior volatility regimes across 3,039 sessions. The central five-factor fits cover 3,373 of 3,902 instruments. Matching dates and weights reconcile direct portfolio fits for the benchmark and all four custom portfolios. In the complete recent robustness comparison, 2,253 of 3,247 oil exposures change sign. All five portfolio moving-block oil intervals include zero.

Each instrument has a dated status in each of three historical crises, including missing event paths and censored recoveries. Backcasts of the October 2026 weights have incomplete historical coverage. The observable Return subset during COVID-19 lost 20.27% in CHF, against a conditional model estimate of −14.82%, with 60.71% of capital invested. For the separate joint shock as at the decision date, all 147 Return holdings have coverage. The estimated loss on CHF 35,000 is CHF 652, including the local/FX interaction. Direct coupon repricing covers 64 Treasury issues.

The main notebook contains one executed analysis per checklist item, including an editable local security lookup. The Git repository carries aggregate evidence, figures and reproduction code. Detailed records are in the versioned local archive named in the summary. [Report and chart index](reports/08-chocs/README.md) · [Machine-readable results](reports/08-chocs/results.json)

## 23 November 2026 · 9.1–9.4 · Individual US stocks

Completed the CIZ extract audit, dated balance-sheet study and historical coverage audit. Compared daily and monthly total returns on 46,320 complete 2025 security-months. Verified Apple's ex-dividend return, the Facebook/Meta ticker change and the Pandion USD 60 cash consideration. An independent listing snapshot published before the October 2026 decision is now attached to the research record.

Applied the CHF 1,575 stock ticket and 1% turnover cap on ten decision dates. In October 2026, 2,959 of the 3,824 cohort securities pass. The mixed book beat the ETF-only book in six of nine complete, identically costed 21-session comparisons. A later SPY disclosure shows 60.61% exposure to the same ten issuers across the direct and ETF positions. A point-in-time financial statement view covers 2,506 October cohort names, including 2,070 passing the ticket screen. Verified the original and amended Veritone filings against EDGAR. Financial statement coverage ends with the September 2026 source quarter. Its allocation weight remains zero.

Items 9.1, 9.3 and 9.4 are checked. Item 9.2 retains an open acceptance criterion for market-wide identity and exit reconciliation. The dated screens, returns, listing candidates, observed endpoints and reasons for exclusion are published separately from that limitation. [Study and figures](reports/09-stocks/README.md) · [Per-date results](reports/09-stocks/results.json) · [Research notebook](RiskMatch_V2.ipynb)

The notebook also executes from tracked files alone. A repeat audit exposed a rounding difference below 0.000000001 basis points from parallel multiplication of daily returns. Monthly compounding now runs in chronological order within each security-month.

## 23 November 2026 · 10.1–10.4 · Treasuries and gold

Published sheets for all 65 selected nominal Treasury issues. The 30 October cutoff supports 64 full valuations and 54 issues meet the model's history rule. The June 2023 reopening of 91282CHC8 reproduces the Treasury price of 96.583639 per USD 100. Full repricing, modified duration, DV01, convexity, the +25 bp hypothetical spread and CHF translation are available by issue. Tenor-specific exposures remain in section 8. The separate maturity control uses an already redeemed issue because the selected holdings mature from 2033 onward.

Compared the ETF and direct cohorts on common endpoints, documented accepted Treasury buybacks for 45 selected issues, exercised a stale price, a nonconforming lot and a late cash deposit, and replayed an eligible illustrative auction purchase. All four numbered research checks are complete. Actual brokerage access, executable secondary size and personal settlement terms are unverified. No client order passed.

GLD's 0.40% annual expense and physical gold mechanism are recorded. A retrospective comparison to the World Bank's monthly average gold series covers 262 common months. The study separates monthly-average tracking, actual endpoint holding returns, the change of gold benchmark source and WTI's explanatory role. Downloaded source workbooks stay private. [Study and figures](reports/10-treasuries-gold/README.md) · [Issue sheets](reports/10-treasuries-gold/issues.json) · [Notebook](RiskMatch_V2.ipynb)

## 23 November 2026 · 11.1–11.2 · Environmental preferences

Reviewed all 3,322 instruments in the October market model with the issuer information available on 23 November. The XLE holdings disclose 18.75% Chevron, compared with wholly unknown exposure at the earlier October cutoff. A strict exclusion admitting only verifiable holdings leaves 1,461 eligible instruments. Unresolved issuer exposure falls from 62.23% of capital to zero.

Joined reconciled EPA point-source facility ownership to 2023 consolidated SEC revenue for 54 issuers. On 55 measured share lines, the two portfolios invest the same CHF 21,000 under a 12% volatility ceiling. A 20% reduction in the measured intensity costs 0.059 percentage point of estimated annual net return. Coverage is 60% of capital and 100% of the stock allocation in both. The study supports a conditional comparison on this historical measure. Group-wide exclusions and global corporate emissions require additional data. [Report and charts](reports/11-environment/README.md) · [Issuer calculations](reports/11-environment/issuers.json) · [Research notebook](RiskMatch_V2.ipynb)

## 23 November 2026 · 12.1–12.9 · Forecasts and signals

Committed the chronological protocol before running this study. Compared 52 specifications for SPY in CHF, including rolling and exponential variance comparators, GARCH, single-signal and incremental Ridge and a separate Black–Litterman diagnostic. Archived 176 dated FOMC statements, 60 GPR editions, publication controls, paired forecasts and funded replays. Momentum improved 63-session variance accuracy but breached the 12% risk ceiling in three of 22 final periods against two under rolling history. Fed policy tone lost its validation advantage. Each candidate has zero recommendation weight.

Published source and timing controls, separate 21- and 63-session notices for all five October portfolios, monthly overheating replays, event calibration and return interval coverage. The four observed final loss events do not support a client probability. The Options page and notebook expose the results. The scoring engine now checks the dated registry before accepting an annual forecast. [Methods and figures](reports/12-forecasts/README.md) · [Register](reports/12-forecasts/registry.json) · [Notebook](RiskMatch_V2.ipynb)

The follow-up coverage audit applied eight incremental signal specifications to all 3,902 October inventory instruments for three target/horizon pairs. At least one signal yields eight matched final outcomes for 3,572 instruments on 21-session return, 3,568 on 21-session variance and 2,402 on 63-session variance. The local ledger retains all 93,648 combinations, including missing histories. [Transfer audit](reports/12-forecasts/cross-asset.json)

## 23 November 2026 · 13.1–13.11 · Portfolio matching, monitoring and revision

Connected the 41-card interview and confirmed risk request to a five-screen Streamlit application. It compares five research portfolios and user-selected blends from the 3,322-instrument model. The 329 distinct instruments in the source portfolios enter the lot-level calculations. Declared loss capacity, funded capital, reserve, risk band and verified constraints gate each selection. A revised answer reopens consent. Tested typed weights, sliders, cancellation, suggested blends, match confirmation and review on desktop and in a mobile Chrome emulator.

The archived first-close example commits CHF 26.36 in fees to enter a 60% Return / 40% Diversification blend with 195 holdings, CHF 8,610.10 cash and 10.56% estimated volatility. After one simulated close and a CHF 1,000 contribution, a revision cuts absolute oil-shock exposure from CHF 30.36 to CHF 14.94 for a CHF 16.34 switching fee. A separate public replay uses synthetic fill prices. Both use the same derived parameters and simulated subsequent closes. Forecast signals carry zero decision weight.

Reconciled three daily account valuations and a 5.1385% cumulative flow-neutral return against a hand calculation. Tested two simultaneous confirmations, rollback, cancellation, cash settlement, changed inputs, stale prices, account isolation, export and deletion. The research notebook contains an executed cell for each section 13 item. The report indexes ten screenshots and the portable replay. [Application report and captures](reports/13-application/README.md) · [Notebook](RiskMatch_V2.ipynb) · [Ledger checks](reports/13-application/ledger-replay.json)

## 23 November 2026 · 14.1–14.4 · Release verification and delivery

Cloned the GitHub project, installed two isolated CPython 3.12 environments, captured the complete macOS ARM64 dependency lock and checked both public and private execution paths. The public demo uses synthetic fill prices. The second checkout supplied the archived first-close tape and saved model inputs. The audit reran the solver and compared eligible identifiers with actual input identifiers. Both sets contain exactly 3,322 instruments. The return optimum holds 147 positions above the research threshold; the five source portfolios together hold 329 distinct instruments.

Replayed the A and B dossiers from card answers through a booked match, deposit, oil review and confirmed revision. Required annual funding growth is 12.61% for A and 8.62% for B. Local first-close entry fees are CHF 26.36 and CHF 38.95 respectively. Whole-unit counts on the public fill tape differ as expected. The delivery register links client figures to numerical results and distinguishes distributed research evidence from private data and saved dossiers.

Measured a public IBM sample during the US session. The newest bar was 66.32 hours old at receipt. A separate historical session returned all 78 regular five-minute intervals. Portfolio monitoring displays the dated price and FX marks and the source check separately. A live CHF portfolio feed and display entitlement remain unverified. Checklist items 14.1, 14.2 and 14.4 are closed. Items 6.3–6.5, 9.2 and 14.3 remain open. [Release report and reproduction commands](reports/14-delivery/README.md) · [Data register](reports/14-delivery/DATA.md) · [Intraday observation](reports/14-delivery/intraday.json)

Both isolated checkouts completed 105 unit tests without skips. Fresh kernels executed all 97 code cells and produced 25 embedded figures. The tracked file inventory covers 268 files, and all seven numerical input fingerprints matched. [Verification receipts](reports/14-delivery/verification.json)

## 23 November 2026 — Client studio redesign

The client enters one financial brief, then calibrates willingness by swiping first-person propositions. The factual brief sets the protected and investable amounts, goal, horizon and mandatory constraints. A profile derives willingness and its volatility band from the active responses. The theoretical thresholds and conditions for an undetermined result appear alongside the profile.

The browser now exposes 3,902 dated research sheets. Each solve starts from 3,322 eligible securities before household restrictions. A shortlist supports manual and suggested blends, with separate review and confirmation in the fictional ledger. The portfolio chart uses five available simulated closes. Live display requires an operator-authorised feed covering every held position and USD/CHF.

The desktop and mobile replays reached a 44/100 Moderate profile after 22 answers, inspected GLD, compared and mixed two strategies, booked a match, advanced the close, recorded a deposit and resumed the profile. [Client studio and visual evidence](reports/studio/README.md) · [Allocation methodology](reports/studio/ALLOCATION.md)

### Client studio follow-up · Intake scroll and original soundtrack

Streamlit's fixed-height component disabled document scrolling. The studio now owns the vertical scroll area, and navigation returns it to the top. The entrance adds an original retro-jazz loop, water foley and two synchronised title impacts. The same speaker control follows the client through the application. [Interaction checks](reports/studio/interaction-check.json)

### Client studio follow-up · Cherry swipe

Both decks use the same transition for left and right votes. The outgoing card stays mounted until the cherry finishes its bounce. A still logo serves reduced-motion sessions. The browser replay checks the direction on each behavioural card and the transition on both shortlisted portfolios. [Animated capture](reports/studio/cherry-swipe.webp) · [Browser replay](reports/studio/browser-check.json)

### Client studio follow-up · Music on arrival

The lagoon now requests audible jazz as it opens. When autoplay is blocked, normal page interaction retries playback. The speaker control retains the user’s mute preference. Start retains the splash and both title cues. Right swipes add an ascending chime and left swipes add a short clap on an independent audio bus. The app keeps the jazz loop running during either effect and across tab visibility changes. [Interaction replay](reports/studio/interaction-check.json)

### Client studio follow-up · Simpler investment brief

Five required fields cover the starting budget, cash set aside, affordable loss, target amount and date. Each field has a help bubble. Optional preferences include planned spending, a yearly return aim, environmental preference and direct company exclusions. The dedicated Chevron screen came from the environmental look-through study and remains available to edit or remove from saved mandates that used it. [Interaction replay](reports/studio/interaction-check.json)

### Client studio follow-up · CHF reserve and final split

The financial brief keeps a five-field default. An optional annual CHF savings rate projects the reserve, accounting for withdrawals on their dates, and the terminal goal uses this value separately from the portfolio. The match preview shows each strategy's share and CHF equivalent. [Reserve and allocation method](reports/studio/README.md#chf-reserve-and-strategy-split)

### Client studio follow-up · Lagoon and navy glass

The lagoon artwork continues behind the studio at desktop and mobile aspect ratios. Translucent navy panels carry the brief, portfolio controls and asset library. [Desktop](reports/studio/glass-desktop.jpg) · [Mobile](reports/studio/glass-mobile.jpg)

### Client studio follow-up · Named test saves

The selector opens after the title sequence. A new save requires a name and matching four-digit PIN entries. Separate saves restore their own brief, completed card answers and portfolios after unlocking. A tester can explicitly lock a save, and the browser requires the PIN after reloading. Left votes remain available by text button or gesture. [Local test workflow](reports/studio/README.md#named-local-saves)

### Client studio follow-up · Goal comparison

The contenders screen now compares the desired return, the required return and the highest historical-model estimate among compatible cards. The separate goal scenario estimates how much volatility and stress loss the goal would require. Its continuous solve is checked after fees and whole-position rounding. It is an illustration only. [Method](reports/studio/ALLOCATION.md#goal-comparison)

### Client studio follow-up · Optional rates

New briefs omit planned spending. Existing briefs with a planned amount can edit or clear it. The help bubbles distinguish savings interest on reserved CHF from the desired yearly return on invested money.

### Client studio follow-up · Questionnaire study

The French study documents all 26 behavioural cards, the eight common prompts, the conditional route and the effect of each answer. It traces the three-domain score and volatility bands to the current implementation. [French study](reports/studio/ETUDE_QUESTIONNAIRE_FR.md)

### Client studio follow-up · Jazz suite and stable swipes

The studio plays six original jazz pieces as one looping mix. Match screens and the confirmation animation lower the music before the normal level returns on the portfolio page. The title now holds five seconds longer. The header reuses the opening lettering, and card transitions retain the current header and position. [Studio guide](reports/studio/README.md#sound-and-navigation)

### Client studio research · Questionnaire calibration

An 18-card candidate bank includes eight common statements and targeted follow-ups. The executable pilot reports eight category scores, response coverage and conflicts. The first-pass route count is 56,629,125 with three answer options. The deployed studio continues to use its current questionnaire. [French audit and candidate bank](reports/studio/CALIBRATION_QUESTIONNAIRE_FR.md)

### Client studio research · Adaptive deck size

The proposed adaptive questionnaire keeps eight common cards and caps the first pass at 40 cards per person. The candidate bank can grow beyond 100 items. Block-level stopping rules prioritise clarifications that could change profile interpretation. [French specification](reports/studio/CALIBRATION_QUESTIONNAIRE_FR.md#spécification-de-la-prochaine-banque-adaptative)

### Client studio research · Behavioural dimensions

The French calibration study now distinguishes portfolio risk and return choices, sensitivity to prospective losses, reactions after a decline, risk perception and ambiguity. It places framing, financial constraints and monitoring in their respective roles. [Research and proposed blocks](reports/studio/CALIBRATION_QUESTIONNAIRE_FR.md#blocs-recommandés-daprès-la-littérature)

### Client studio research · Extended French card bank

The extended bank contains the 18 pilot anchors and 108 conditional prompts. Research routing chooses portfolio, drawdown and mixed-outcome thresholds within their blocks. A synthetic replay covers all 126 prompts across 1,800 histories. The router keeps anchor scores and records added observations separately. [French catalogue](reports/studio/BANQUE_ADAPTATIVE_FR.md)

### Client studio follow-up · Explicit decision options

The studio uses named options for the guaranteed-versus-risky choices and the 15% decline. A plan review records its own answer and opens a goal-check follow-up, independent of the holding score. The research bank also accepts named portfolio choices, mixed outcomes, and drawdown responses. [Questionnaire study](reports/studio/ETUDE_QUESTIONNAIRE_FR.md#choix-explicites-en-service)

### Client studio follow-up · Portfolio cross-check

Two portfolio choices run after the scored cards. The score remains descriptive. New searches use a conservative ceiling and no volatility floor, show divergence or uncertainty, and retain the separate CHF loss constraint. [Method and examples](reports/studio/ETUDE_QUESTIONNAIRE_FR.md#vérification-sur-des-choix-de-portefeuille)


## 23 November 2026 — Volatility estimated from portfolio choices

Studio-3 keeps the willingness score and its components. Two CHF comparisons and a conditional third set bounds on the model's risk aversion parameter. Checked whole-position solutions at representative values produce the volatility zone. The upper estimate guides the match search alongside the existing financial constraints. The studio flags extrapolation beyond the cards and permits a cash option for unresolved choices. The method is reproducible with the dated release and fictional answers. Empirical validation of preferences and market assumptions remains open. [French questionnaire study](reports/studio/ETUDE_QUESTIONNAIRE_FR.md#vérification-sur-des-choix-de-portefeuille) · [Browser replay](reports/studio/volatility-browser-check.json) · [Notebook](RiskMatch_V2.ipynb)
