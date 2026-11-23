# RiskMatch V2 implementation checklist

- [x] **0. Define the project scope.** Perimeter V2 and execution plan defined.
  - **Procedure and tools.** List the perimeter decisions leading the project and link each requirement to a part of the checklist. Maintain the separation between the fictitious base and market studies.
  - **Evidence to retain.** README, checklist and directory of concordant methods on autonomy, American perimeter and CHF.
  - **Checks and fallback.** The design agreement does not validate any actual data or customer calculations.

**Reading the checklist.** A checked item has the evidence specified for that item. An open item may already have a working prototype or a published intermediate result. The notebook derives its progress table from the boxes below. Every numbered item has a dedicated heading in the [research notebook](RiskMatch_V2.ipynb), with its checkbox, method, tools, results or outstanding evidence. The coverage test in 1.5 checks their order and status. Sections 8–10, 12 and 13 already contain partial work.

**Work order.** Check the stand-alone base and V2 sources (1). Develop the mandate (2–3) and, in parallel, inventory all sources and build the catalogue (4, 9–10). Enter each eligible instrument in the first calculation per client (5–7). Measure exposures and shocks (8), apply environmental preferences (11), and then test forecasts (12). Provide follow-up and revision (13–14). Compare the multi-asset library to a fixed allocation defined in V2, with comparable dates, mandate and costs. Local sources go first in the calendar. The identified deficiencies trigger a search for targeted public sources or review of the local files already provided. The V2 workflow works without a WRDS subscription.

**Planned organization.** Python 3.12, locked environment, Parquet for series, JSON or YAML for parameters, local web prototype to validate the visual path, Streamlit for integrated demo, Git for decisions. Planned `src/riskmatch_v2/` for reusable code, `tests/` for testing, `config/` for assumptions and `reports/<étape>/` for the results. The notebook calls the same functions as the site. The base uses an embedded demo catalogue and accepts an explicit local file. The first market import and historical references in CHF are validated in 1.3–1.4. For each step, keep the command, dated parameters, input versions and checksums, results report and past controls. After each step checked, check the sub-step, complete the notebook with reproducible results and record in the [V2 journal](JOURNAL.md) the decision, rationale, data used and limitations. For each step that produces visual results, save the figures and a short comment in `reports/<étape>/`, and then connect them from the [directory of results](reports/README.md), the notebook and the journal. After validation, create the commit and push shareable changes to the V2-specific GitHub repository. Keep private or licensed entries in `data/local/` and exclude results for which dissemination is not permitted. If data is missing, record the absence, test the withdrawal and keep visible what remains to be done. The following thresholds are an initial project protocol. Action, stimulus, risk measures and data controls remain verifiable on fictitious cases before the market replay. To find the dependencies, follow the order of work. The numbering identifies the workstreams and their evidence.

**Reading the checklist items.** The design, calculation, control and delivery tasks each have their own proof. Some can move in parallel. The final validation checklist items are based on the outputs of previous tasks.

**Transversal control of 23 November 2026.** As of October 30, 2026, the multi-asset study submitted 3,322 securities, including 3,255 individual stocks, 54 direct Treasuries and 13 ETFs. Previous comparisons of 13 ETFs are used as a control. The evidence by sub-step is in the [review of the 43 checklist items](reports/univers-complet/AUDIT.md). checklist items 6.3 to 6.5 remain open for full certification of extended trajectories. The previous ETF comparison remains searchable. [Audit of assets, results and graphs](reports/univers-complet/README.md)

## 1. Project foundation and historical benchmarks

- [x] **1.1 Create a standalone project.** Installing from `pyproject.toml`. Check the command `riskmatch-v2` and tests of the catalog on isolated copy.
  - **Procedure and tools.** In an isolated copy, create a Python 3.12 environment, install the package with `python -m pip install .`, then run `riskmatch-v2` and `python -m unittest discover -s tests`.
  - **Evidence to retain.** The command uses embedded data and tests pass from the copy alone.
  - **Checks and fallback.** A reading in the parent repository or an import dependent on the current directory blocks standalone delivery.
- [x] **1.2 Prepare the V2 research notebook.** Load on-board demonstration data, trace sources and compare instrument returns on a common basis. Check cells from the stand-alone project.
  - **Procedure and tools.** Install Notebook option and run `jupyter execute RiskMatch_V2.ipynb` with the core of the environment. Compare the result to the CLI diagnosis on an equal date.
  - **Evidence to retain.** Run in an isolated copy, displayed fictitious sources and common results between entries.
  - **Checks and fallback.** Any state hidden between cells or external file required must be eliminated before the next validation.
- [x] **1.3 Import market data for the first mandates.** Record the source, licence, date of observation and availability, unit, cover and checksum of each import. An import of existing data is possible if its use is allowed. The V2 catalogue remains responsible for its validation.
  - **Procedure and tools.** Inventory files and endpoints by provider. Keep the brutes intact. Write a manifest with query parameters, version, time stamping, SHA-256, lines, cover, currency and private/public rights. Record secrets outside the repository.
  - **Evidence to retain.** A reproducible import from an authorized file, accompanied by an array of missing sources, with a public source to be checked, a local file to be qualified or an explicitly blocked state.
  - **Checks and fallback.** Isolate a file whose fingerprint or schema changes. Document a review and recheck before using its new vintage.
  - **Audited result on November 23, 2026.** 13 ETF, 257 months available in CHF and 4 months excluded. [Report, graph, manifest and sources to be qualified](reports/01-3-import-marche/README.md)
- [x] **1.4 Define the V2 benchmarks.** Define one or more internal strategies with fixed weights, with schedule, rebalancing and explicit fees. Check and display their compatibility with each mandate. Publish results by period and distinguish arithmetic mean and compound return.
  - **Procedure and tools.** Version weights, actives, calendar, weight gain and scale. Replay buy and hold and simple rebalancing on the same dates as custom options.
  - **Evidence to retain.** Series of returns and costs reconciled, status of compatibility with the mandate and reference available even on simple cases.
  - **Checks and fallback.** A non-mandate reference remains as a comparison. An incomplete history leads to an explicit reduction of the common period.
  - **Audited result on November 23, 2026.** 257 three independent periods, two variants of 60/40 and CHF cash, fee register and four illustrative mandates. [Graph, results and controls](reports/01-4-references/README.md)

- [x] **1.5 Map requirements to deliverables.**
  - **Procedure and tools.** Create a column or table of correspondence between client request, section, dependencies, proof and file. Distinguish delivery obligations, studies to be tested and conditional extensions to data.
  - **Evidence to retain.** Delivery covers incomplete questionnaire cases, out-of-scope target, non-negotiable assets and post-selection review. The known dependencies are visible before starting the work.
  - **Checks and fallback.** An experimental result can remain open with a pattern. An essential criterion without evidence prevents the full V2 from being declared.

  - **Audited result on November 23, 2026.** [Matrix of requests, dependencies, evidence and four paths to verify](reports/01-5-exigences/README.md). The notebook checks the correspondence with all the checklist items.

**Deliverable and evidence.** Installable base, demonstration set, local import test and market inventory verified at the time of integration. [Notebook](RiskMatch_V2.ipynb)

## 2. Questionnaire and client mandate

- [x] **2.1 Build the complete V2 questionnaire specification.** For each project question, provide ID, exact text, category, answers, scale or rule, possible deduction, clarification and consequence. Create a versioned local bank and create independent theoretical cases. Historical cards are available for their examples. Keep the correspondence between ID and version.
  - **Procedure and tools.** Build a JSON bank with stable identifier, version, text, situation, measured built, answers, scale, relaunch and effect on the mandate. Make each choice read economically and establish the road graph.
  - **Evidence to retain.** One line per card with theoretical justification. Check valid identifiers, branch destinations and responses by data testing.
  - **Checks and fallback.** An ambiguous interpretation has a neutral revival and an unknown state. The fictitious scenarios test the declared logic.
  - **Evidence of November 23, 2026.** [guide to 41 cards and branches](reports/02-questionnaire/CARDS.md).
- [x] **2.2 Write the questions about financial circumstances.** "How much can you mobilize today?", "When and in what currency will you have to withdraw money?", "What contributions are certain enough to count?", "What loss would put your project in trouble?", "What amount do you want to achieve and when?" Enter amounts, dates, intervals and unknowns. The schedule calculates the amount to be protected and the investable balance. Separate the financially absorbable loss from the feeling in the face of a decline.
  - **Procedure and tools.** Create fields for amounts, currencies, dates and ranges. Horodater contributions and expenses, specify their certainty and calculate the reserve based on confirmed flows.
  - **Evidence to retain.** Manual case CHF 50,000 with CHF 15,000 to protect. Verify uncertain inputs, withdrawal before/after the horizon and missing date.
  - **Checks and fallback.** An unknown amount remains unknown. If several sizes are plausible, test the feasibility on the bounds before confirming the investment sleeve.
  - **Evidence of November 23, 2026.** [proof of reserve calculation and flows](reports/02-questionnaire/README.md).
- [x] **2.3 Write the preference questions.** "What return would you like?", "Do you want a ceiling, a target band or the lowest risk?", "What exposures do you already have, for example via your employer?", "Do you want to limit a sector, country, currency or issuer?", "What environmental exclusions or preferences do you intend to apply?". For each preference, record the perimeter, priority, imperative character and desired response if data is missing.
  - **Procedure and tools.** Write the desired target cards, type of risk, diversification, exclusions and sustainability. For each preference, collect perimeter, intensity and imperative character.
  - **Evidence to retain.** Two mandates with the same tolerance and distinct preferences trigger the expected differences. Test a mandatory exclusion and a flexible preference.
  - **Checks and fallback.** Indecision leaves the preference open. A firm exclusion cannot become a flexible penalty at the time of calculation.
  - **Evidence of November 23, 2026.** [Mandates with imperative and flexible preferences](reports/02-questionnaire/cas.json).
- [x] **2.4 Implement the interpretation rules for each card.** For a bet included and comparable to the certain placement, calculate the bound on φ via the average difference and the variance of the bet. In the reference bet card, a certain choice of CHF 1,020 against the gamble paying CHF 900/1,200 equal chances gives a low bound of around 2.67 and the choice of bet a high bound. Intersect compatible bounds. A passage, incomprehension and an answer on the emotional reaction do not add any numerical bounds. Replay the calculation by removing each decisive card. In case of conflict, ask for clarification and then keep uncertainty if it persists.
  - **Procedure and tools.** Use decimal returns on the bet displayed. For a strictly positive variance, calculate the threshold by twice the mean return difference on the variance. Add only the bound due to an included choice and re-enact the intersection by removing each key card.
  - **Evidence to retain.** Recalculate the example CHF 1,020 by hand. Test agreement, refusal, passage, incomprehension, contradiction and sensitivity to the deletion of a response.
  - **Checks and fallback.** An empty interval triggers clarification. Maintain open boundaries, contradiction or insufficient evidence as separate states.
  - **Evidence of November 23, 2026.** [limits, contradictions and card removal](reports/02-questionnaire/README.md).
- [x] **2.5 Save a versioned client mandate.** In typical Python structures, keep answers, corrections, facts, assumptions, objectives, flows, exclusions, confirmed choices and outstanding questions. Allow correction in Streamlit. Scenarios remain theoretical. Test their consistency on fictitious cases, without presenting them as validation with participants.
  - **Procedure and tools.** Define Python structures typed for facts, answers, objectives, constraints and preferences. Version the mandate to confirm and trace the link between each derived field and its entries.
  - **Evidence to retain.** A change in expenditure recalculates the reserve. A change in risk choice recalculates its own fields. Each export indicates the version and unknowns.
  - **Checks and fallback.** A correction invalidates the previous proposal. An older version must remain legible in the follow-up with the appropriate schema.
  - **Evidence of November 23, 2026.** [export versioned, corrected and rereaded](reports/02-questionnaire/README.md).

- [x] **2.6 Specify the cards and supported gestures.** Show one statement or preference at a time. Right and button "Yes / I accept" give the same answer. Left and "No / I refuse" button give the same answer. "I don't know / pass" is recorded separately and doesn't give any risk aversion points. Provide arrows on the keyboard and a correction history. For an A/B choice, specify on the card what each gesture selects. Enter amounts and dates in dedicated fields.
  - **Procedure and tools.** Implement an active card. Mapper swipe, button and keyboard to the same answer. Define a threshold of gesture, a state of cancellation and a return to the previous answer.
  - **Evidence to retain.** Test on mobile and computer right, left, pass, incomplete gesture, keyboard and correction. Each response produces the same branch regardless of the input mode.
  - **Checks and fallback.** An incomplete gesture or double interaction does not validate any additional response. A passage retains a separate condition.
  - **Evidence of November 23, 2026.** [buttons, keyboards, touch gestures and cancellation](reports/02-questionnaire/README.md).

- [x] **2.7 Test the adaptive route independently of the interface.**
  - **Procedure and tools.** Build predefined fictitious paths for agreement, refusal, passage, adversarial response and correction. List branches' destinations, test inaccessible cards and recalculate from the answers retained after correction.
  - **Evidence to retain.** Each prices produces the expected state of the grid, score and mandate. A recovery card for incomprehension does not count as a new preference.
  - **Checks and fallback.** A missing branch can be used to repeat or clarify. Correcting a response removes its consequences that have become invalid.
  - **Evidence of November 23, 2026.** [seven routes and control of all cards](reports/02-questionnaire/cas.json).

- [x] **2.8 Adapt the behavioural and cognitive questions to V2.**
  - **Procedure and tools.** Build a common core covering seven families documented in V1. Understanding of probabilities, declared tolerance, arbitrations certain/uncertain, sensitivity to the passage under the start, reaction to a decline, flexibility of the objective and preference for follow-up. For each family, specify the number of cards of the kernel, the re-launches, the bias or behaviour studied, the other possible explanations and the permitted consequence. Adapt the stimulus to V2 choices, including diversification, coverage and combination. Use coverage or tracking responses as preferences, with score criteria distinct from numerical arbitrations.
  - **Evidence to retain.** Bank V2 and matrix « family → card → answer → other explanation → restart → decision ». Compare a route with declared and contradictory bets, a repeated reversal around the initial bet and three distinct sales patterns after decline. Verify that only a confirmed change in expenditures changes the reserve.
  - **Checks and fallback.** After persistent incomprehension, keep the aversion undetermined. A response to scoping or emotional reaction produces an observation to discuss. Hypothetical choices and hypothetical cases do not allow an individual psychological diagnosis to be attributed.
  - **Evidence of November 23, 2026.** [matrix of the seven families and three sales reasons](reports/02-questionnaire/CARDS.md).

**Deliverable and evidence.** Mandate grid and diagram, with case "decline by 15% → need for money", "decline by 15% → preference for stability" and "decline by 15% → anticipation of a further decline". These three responses produce three different suites. [Design V1](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/questions/QUESTIONNAIRE_DESIGN.md) · [card Guide](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/questions/GUIDE_DES_CARDS.md) · Local theory, guides 14, 16, 21 and 34.

## 3. Risk confirmation and loss capacity

- [x] **3.1 Define risk measurement conventions.** Use annual initial slices on the investment sleeve, in CHF. Proposal to be tested and documented before use: very conservative [0, 4[%, prudent [4, 8[%, moderate [8, 12[%, dynamic [12, 20[%, very dynamic [20, ∞[%. These are benchmarks for dialogue. Allow a custom volatility band and a free percentage. Make 4%, 8%, 12% and 20% unambiguous in the tests.
  - **Procedure and tools.** Put the steps in a dated configuration in annual CHF volatility of the investment sleeve. Describe their bounds and store the custom slice in decimal units.
  - **Evidence to retain.** Tests at 4%, 8%, 12% and 20%, just below and above. Check for 35%, 40% and 100% conversions.
  - **Checks and fallback.** Refuse reverse bounds, negative values and ambiguous units. Keep the free demand for the feasibility test.
  - **Evidence of November 23, 2026.** Dated conventions, controlled thresholds on both sides and tested units. [Section 3 Report](reports/03-portrait/README.md)
- [x] **3.2 Present the risk decision to the client.** Link responses to examples of losses in frances across multiple horizons. Present the proposed band with reasons, scenario losses and household effect. Request to confirm, modify or remain undecided. Keep separate `minimum`, `plafond`, `cible_tranche` and `inconnu`. A target of 40% with a tolerance of 2 points gives [38%, 42%].
  - **Procedure and tools.** Show the instalment recommendation, its reasons, loss of scenario in CHF and the two relevant denominators. Record the decision and type of mandate.
  - **Evidence to retain.** Four cases of seizure give the four expected statements. A 40% ±2 point target becomes 38-42%.
  - **Checks and fallback.** If the customer does not confirm its slice, keep the uncertainty and suspend its custom ranking.
  - **Evidence of November 23, 2026.** Four modes, target 40 ± 2 and export versioned after rereading. [Section 3 Report](reports/03-portrait/README.md)
- [x] **3.3 Resolve conflicting answers.** A high risk preference and a need to protect close spending trigger clarification and flow protection. A slice that has become impossible triggers a feasibility result. An uncertain preference leaves the custom ranking waiting.
  - **Procedure and tools.** Code rules for clarification between horizon, financial capacity and declared preference. For each conflict, display the flow or response involved.
  - **Evidence to retain.** Test a near expense, an uncertain need and a drop deemed intolerable despite a high target. Show the reasons for the final mandate.
  - **Checks and fallback.** Preserving the reserve. If conflict persists, maintain confirmed limits and present uncertainty.
  - **Evidence of November 23, 2026.** Reasons for clarification and target/ceiling comparison against a fictitious 18% mark. [Section 3 Report](reports/03-portrait/README.md)

- [x] **3.4 Test the effects of the reserve and the risk measurement basis.**
  - **Procedure and tools.** Apply the same scenarios to the investment sleeve and then to the assets covered by the mandate. Replay a certain nominal expense and an estimated expenditure only. Report available amounts on each date.
  - **Evidence to retain.** Of CHF 50,000 of which CHF 15,000 is protected, a 10% decrease in the investment sleeve alone represents CHF 3,500, before another scenario effect. Also check the case without investment capital.
  - **Checks and fallback.** Show denominator next to each measurement. An unconfirmed reserve triggers clarification before committing the amount concerned.
  - **Evidence of November 23, 2026.** Two denominators, dated cash and uncertain or full reserve cases. [Section 3 Report](reports/03-portrait/README.md)

**Deliverable and evidence.** Validation view with examples 6–10%, 35%, 40%, 100% and minimal risk. The same tolerance responses with different liquidity needs give different mandates. [ESMA, suitability elements](https://www.esma.europa.eu/sites/default/files/2023-04/ESMA35-43-3172_Guidelines_on_certain_aspects_of_the_MiFID_II_suitability_requirements.pdf) · Local theory, guides 16, 21 and 34.

## 4. Asset catalogue and dated eligibility

**Perimeter.** US market for shares, bonds and equity/bond funds. Raw materials vehicles listed in the United States. Cash and targets in CHF. Record the rating space and exposure area, then test eligibility on both fields for funds.

- [x] **4.1 Define the instrument-level data schema.** Stable identifier, type of asset, issuer, place, currency, calendar, date of entry and exit, source, right of use, date of observation and date of availability. Add price, total return, foreign exchange value, fees, liquidity and missing data per series. Inventory of available ETFs and CRSP securities, bond series, commodity instruments, foreign exchange and CHF cash. Record separately the role of each series in the catalogue, negotiable instrument, factor, benchmark or source to be completed. Add dated classifications and the underlying positions of ETFs when available.
  - **Procedure and tools.** Define Arrow schemes for instruments, historical identifiers, prices and distributions, FX, sources and fund positions. Use dated keys and role and class vocabularies.
  - **Evidence to retain.** Unique keys, verified roles and class coverage. Demonstrate that a reused ticker does not identify two issuers as one title.
  - **Checks and fallback.** Isolate observation without reliable identity or date. A spot factor remains excluded from the weight of a portfolio.
- [x] **4.2 Clean and align market data.** Use pandas and PyArrow. Deduce, verify securities events and the direction of change. Convert by `(1 + local return) × (1 + FX return into CHF) − 1`. Keep return in local currency and CHF. Mark each hole, do not create zero returns to fill it and use common dates for comparisons and empirical covariance control. Maintain a separate measurement of fees already embedded in the total return series.
  - **Procedure and tools.** Align calendars, hours and currencies. Treat splits, dividends and quotes duplicated before aggregations. Make past-oriented as-of joins for published data. Keep raw, corrected and pattern code.
  - **Evidence to retain.** Known games with split, dividend, closing, reverse FX, expired price and subsequent revision. Disturb the future and check that previous outputs do not change.
  - **Checks and fallback.** An extreme movement remains in the game unless corrected. Report coverage and loss of lines to each join.
- [x] **4.3 Build one-, three-, five- and ten-year instrument profiles.** With NumPy/pandas, publish effective, average and compound return, annualized variance and volatility according to frequency, maximum decrease and recovery time in days. Mark unfinished recoveries and incomplete windows. Produce correlations and concentrations by currency, sector, issuer and underlying on a comparable basis.
  - **Procedure and tools.** Calculate the records from the total returns and actual dates observed. Reconstitute the curves of wealth. Define the peak and recovery from the same recovery agreement.
  - **Evidence to retain.** Manual case with compound return, drawdown and recovery. Publish coverage, numbers, frequency and dates by window.
  - **Checks and fallback.** Mark incomplete windows and unobserved recoveries. Compare only assets using a consistent calendar base and currency.

- [x] **4.4 Determine eligibility at each decision date.** Version criteria by class before results. For any proposal in 2026, verify on its exact date the actual quotation or negotiability, access on behalf of the customer, freshness of price and exchange, minimum size, settlement, liquidity and fees. Also check the minimum history required for the risk model and the absence of double counting. For historical purposes, use the information available on the date studied and keep dividends, outflows and cashed product. Keep all instruments in the inventory and publish by class the numbers identified, eligible and excluded, with good reason and possible extraction to be requested. The criteria can produce a different universe depending on the date and mandate.
  - **Procedure and tools.** Apply by date and class the controls of negotiability, freshness, volume or batches, settlement and coverage of risk. Record additional access to the instrument for the account concerned.
  - **Evidence to retain.** Register with active, date, decision and reason code. Inventory of candidates, eligible and selected with differences explained by class.
  - **Checks and fallback.** A title of unknown or non-purchaseable status on the date of the mandate does not pass into a proposal. Keep it in the inventory for research.
- [x] **4.5 Build two point-in-time views.** For comparison, choose the last common usable period and compare V2 strategies on the same dates and fees. For the most recent proposal, apply eligibility checks on its own valuation date. A CRSP extract arrested in 2025 can enter a replay dated 2025. A valid prices on the decision date is required to be able to use a title in a more recent proposal. Test a written title after the historical period, an expired price in 2026 and a recent introduction with insufficient history.
  - **Procedure and tools.** Generate a frozen replay snapshot and a recent decision snapshot. Associate price date, calendar and version of the catalogue with each release.
  - **Evidence to retain.** Replay an action then rated in 2025, then show its status for a 2026 proposal. Test radiation, outdated prices and recent introduction.
  - **Checks and fallback.** A stopped historical series can remain exploitable in research. It does not replace a valid current price.

- [x] **4.6 Document applicable methods for each asset class.** Follow [directory of methods](LIBRARY_METHODS.md). To give priority to historical measurements and the diagnosis of the base. Add class-specific analyses and mark methods whose data do not yet allow calculation. Comparisons of forecasts and plans follow steps 8 and 12.
  - **Procedure and tools.** Build a matrix methods × classes. Link descriptive sheets, factor tests, bond metrics and fee measures to functions and inputs. Check the examples of the [method sheet](LIBRARY_METHODS.md).
  - **Evidence to retain.** For each class, see available calculations, their units and missing data. Document the method used for each value presented.
  - **Checks and fallback.** Mark "not estimable" with the missing condition instead of publishing a metric on an inadequate basis.

- [x] **4.7 Test the catalogue with defective data.**
  - **Procedure and tools.** Create a small independent reference game with missing price, reverse exchange, split, dividend, write-off, corrected price and late macro announcement. Use Python tests and hand-calculated expected results.
  - **Evidence to retain.** Check the date-by-date join, the number of lines excluded by reason and the recalculated reports. The modification of a future value does not change any previous result.
  - **Checks and fallback.** Any invalid data shall retain its motive and source. A correction published later does not rewrite any frozen decision snapshots.

- [x] **4.8 Verify when each source becomes available.**
  - **Procedure and tools.** Store separately economic date, publication, first possible use and market time stamping. Build a snapshot by analysis date with retrospective joins and dated versions.
  - **Evidence to retain.** Inject a post-closure deposit and a correction published later. The old recommendation is identical and the new one reads the correct version.
  - **Checks and fallback.** If the time is unknown, use a documented conservative delay or suspend the historic use of the signal.

- [x] **4.9 Reconstruct fund exposures as of the mandate date.**
  - **Procedure and tools.** Attach published positions, issuer identifiers and cover on the version available in each decision. Calculate the total holding of an issuer via funds and direct securities.
  - **Evidence to retain.** Hand-to-hand approach an asset held via two funds and live. Publish the unattributable share and effect of missing lines.
  - **Checks and fallback.** Uncertain exposure remains distinct from zero exposure. Apply the agreed rule if a mandatory exclusion depends on that data.

**Result of November 23, 2026.** 60,736 records, nine documented checks and zero eligible instruments for an order on that date. [Report, graph and reproduction](reports/04-catalogue/README.md) · [Class and exit methods](reports/04-catalogue/METHODS.md) · [Aggregates](reports/04-catalogue/resultats.json)

**Deliverable and evidence.** Catalogue Parquet, register of provenance, sheets and matrix. Reconcil a CHF return by hand, check a dividend and a market closure, and then test a series whose history does not cover ten years. [Inventory V1](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/data/README_data.md) · Local theory, guide 01 and QARM2 LN1–LN3.

## 5. Portfolio feasibility and allocation

- [x] **5.1 Prepare allocation inputs.** Investment investment sleeve, existing weights and positions, exclusions, limits by security/sector/currency, reserve, `mu` and covariance in CHF. First based on 504 sessions compared to 756 depending on coverage. Compare empirical covariance and Ledoit–Wolf. If the intersection of history reduces coverage excessively, test factor covariance with a small set of factors, asset sensitivities estimated on available dates and residual variances. Verify the semi-defined positivity, compare risk to common sub-universe estimates and measure out-of-sample deviations. If the risk of an asset remains unestimated, keep its record and explain its ineligibility. For expected returns, from a reduced historical average to an explicit reference, and compare with the equilibrium prior if a benchmark and justifiable weights are available.
  - **Procedure and tools.** Build CHF returns at the decision date and produce consistent moments in frequency. Compare windows, shrinking and factor model on common dates. Recalculate matrix after exclusions.
  - **Evidence to retain.** Archive of solver inputs, symmetry and positivity tests, coverage by security and predicted risk compared to the realized risk.
  - **Checks and fallback.** A poorly conditioned matrix triggers a documented coverage check or stabilized estimate. An estimated risk-free security remains uncalculated.
- [x] **5.2 Implement the efficient frontier.** Use CVXPY and CLARABEL, with SciPy HiGHS for linear control problems. First, check that a portfolio meets the constraints. Find the minimum volatility and then maximize the net expected return under several ceilings, with a standard constraint on volatility. Start long-only, without borrowing. Configure costs according to commissions, spread, change and turnover. Check separately that the cash flow finances each transaction.
  - **Procedure and tools.** Write constraints in CVXPY from the current mandate and positions. Resolve feasibility, minimum and ceiling grid. Bring back fresh and horizon to a comparable base and preserve the reserve.
  - **Evidence to retain.** Trace the border, active constraints, costs and final cash. Recalculate the budget and non-solver bounds.
  - **Checks and fallback.** An ambiguous numerical status or a breached constraint blocks the recommendation. Explain the constraint if it is identifiable.
- [x] **5.3 Handle lower volatility bounds and unreachable requests.** If the optimum also satisfies the bottom of the slice, hold it. Otherwise, the minimum volatility requirement in the band is non-convex. On the small universe, list the peaks when constraints and budget describe a listable polytope. The maximum variance is then reached at least one summit. For a target, use segments between eligible solutions to produce candidates and verify the recalculated risk. To ensure the best estimated return in the band, use separate and evaluated research as required. Divide the weight intervals, use ceiling relaxation to limit the net return of each region and remove regions with too low a certified maximum variance. Keep the best possible allocation and its deviation at the global boundary. For the prototype, publish no more than 1 pb of annualized return deviation for a solution declared optimal to this accuracy. In the enlarged universe, an upper limit of variance can certify the impossibility. A set of tested allocations can only describe what has been found. Send explicitly "inconclusive search" if no solution is found or proven impossibility.
  - **Procedure and tools.** First check if the ceiling optimum is already in the slice. Otherwise, find candidates, establish valid boundaries and keep the search log. Use a small listable case as oracle.
  - **Evidence to retain.** For each application, register candidate, valid bound, deviation, delay and status. Test an impossible target and a possible target whose low bound changes the optimum.
  - **Checks and fallback.** Only a valid bound makes it possible to conclude that it is impossible. At the end of the calculation, keep the verified candidates with their level of evidence.
- [x] **5.4 Test the optimizer.** Compare to an analytical case with two actives and then an independent reference on a small V2 universe. Recalculate weight, fresh, exposure and risk outside the solver. For the prototype, check sum of weights to `1e-6` and violations by weight at `1e-6` in decimal units. Play minimum, 35%, cap and target 40%, 100%, binding exclusion and empty universe. Report optimal result, verified candidate, impossible according to evidence or inconclusive search.
  - **Procedure and tools.** Write analytical cases with two assets and recalculate independently residues, volatility, costs and limits. Add cash tests alone, no eligible instruments and multiple exclusions.
  - **Evidence to retain.** Table of residues and expected results for minimum, ceilings and targets. Verify unit consistency on 40% and 100%.
  - **Checks and fallback.** Explain the error, ineligibility and optimum uncertified statements. An optimization score does not correct warrant violations.

- [x] **5.5 Measure computation across the full library.** Raise dimensions, calculation time, convergence and optimum deviation on the small reference set and all eligible titles. Cache intermediate data and results by date and version of catalogue. Verify that a change in the mandate only recalculates the results concerned. If a slice search reaches its time budget, show only the verified candidates and the remaining uncertainty on the optimum. Record performance and assets actually considered.
  - **Procedure and tools.** Measure time and memory over a series of snapshots of increasing size and then over any eligible universe. Index the cache by data, date and version of the computational dependencies.
  - **Evidence to retain.** Median and worst observed time, number of candidates, status and full list of assets submitted. A change of mandate invalidates the results concerned.
  - **Checks and fallback.** An excessive delay triggers the expected decline in research, without imposing a silent quota on assets.

- [x] **5.6 Measure allocation stability.**
  - **Procedure and tools.** Freeze variants of averages, windows, covariance and costs. Recalculate options by disrupting each input and then on resynchronized blocks. Compare on the same mandate and with the same universe.
  - **Evidence to retain.** Present weight dispersion, securities rotation, risk variation, expected return change and ranking changes. Verify that a small plausible variation can be explained in case of unstable option.
  - **Checks and fallback.** Mark a sensitive recommendation and display a robust variant if eligible. A ranking that easily reverses retains its level of uncertainty.

- [x] **5.7 Verify the solver’s optimality and feasibility certificates.**
  - **Procedure and tools.** Check on each output weight, residual cash, volatility, fresh and active constraints. Calculate a valid standstill separate from the candidates for those bands where a certificate is expected.
  - **Evidence to retain.** Test a workable slice where an optimum under ceiling falls below the low limit, an impossible case demonstrated and an interrupted calculation with eligible candidate.
  - **Checks and fallback.** Separately display eligible states, certified optimum, impossible and inconclusive search. Archive the tolerance and limits of the calculation.

- [x] **5.8 Convert continuous weights into executable orders.**
  - **Procedure and tools.** Convert weight to units with price, currency and lots. Recalculate fresh, concentration, exposure and reserve after rounding. If necessary solve or adjust again with the quantities actually purchaseable.
  - **Evidence to retain.** A small file and a minimum batch obligation illustrate the difference. The option presented as executable meets the constraints after rounding.
  - **Checks and fallback.** If no eligible lot meets the mandate, display the difference between the theoretical result and the feasible alternative.

**Result of November 23, 2026.** Research boundary on the 13 funds, maximum of 22.18% verified on 170 summits, load test on 3,676 series and control of all entries in the November registry. [Report and two figures](reports/05-faisabilite/README.md) · [Executed Notebook](RiskMatch_V2.ipynb) · [Results](reports/05-faisabilite/resultats.json)

**Deliverable and evidence.** Reusable calculation function, boundary and feasibility reasons. Test a target and a 40% cap on a V2 game where the target exceeds the achievable limit. [CVXPY, solvers](https://www.cvxpy.org/version/1.7/tutorial/solvers/index.html) · [Ledoit–Wolf](https://scikit-learn.org/stable/modules/generated/sklearn.covariance.LedoitWolf.html) · Local theory, guide 04 and QARM2 LN2–LN4.

## 6. Portfolio options, scores and blends

- [x] **6.1 Define the portfolio variants.** Calculate the highest net return in the mandate, the minimum or robust risk variant, and a priority preference variant that can be measured. For a coverage preference, minimize the loss under the relevant scenario. For diversification, e.g. reduce the aggregate concentration per issuer or a sector exposure requested, with a documented return threshold. When the client has requested and coverage allows, calculate also the environmental option of step 11. Display a fixed reference and compromises by option. Report variants that result in the same weights.
  - **Procedure and tools.** Set optimisation targets by variant. Reuse imperative constraints. For a coverage option, use the stress chosen. For a sustainable option, use the approved measure and its coverage.
  - **Evidence to retain.** Test that each variant meets its criteria and fulfils the same mandate. Distinguish substantial differences, compromises and identical allocations.
  - **Checks and fallback.** Show only the distinct and computable variants. Explicitly display a non-mandate reference.
- [x] **6.2 Measure trade-offs.** Produce weight, expected return and range, variance/volatility, fresh, Sharp in common currency and frequency, concentration and contributions of Euler to risk. Compare to a fixed strategy with the same dates, flows and cost assumptions. Display its possible incompatibility with the mandate. Distinguish net realized return, expected return and loss of scenario.
  - **Procedure and tools.** Compare on the same date, currency and fee assumption. Calculate Sharpe with consistent cash flow, risk contribution and crisis performance. Indicate the nature and coverage of the ranges.
  - **Evidence to retain.** Table by option with weight, fresh, historical, estimate, loss of scenario and effect on target. Verify an aggregated risk by independent calculation.
  - **Checks and fallback.** An unavailable metric keeps its pattern. A change of classification under plausible assumption must appear in the form.
- [ ] **6.3 Replay transactions.** Set annual rebalancing in study V2 and perform at the next session according to a documented agreement. Test an initial hypothesis of 10 bp and sensitivities at 0 and 25 bp. Test an expanded cost and rounded batches where the source permits. The costs of buying, selling and holding apply to allocations calculated with or without Black–Litterman.
  - **Procedure and tools.** Build a decision schedule and then execute from eligible currencies and prices. Replay orders on the first allowed date. Calculate costs on amounts actually exchanged after weight drift.
  - **Evidence to retain.** Net and gross results, turnover, date of execution and possible lack of cash. Check purchase, no transaction, sale and withdrawal on manual case.
  - **Checks and fallback.** An unexecuted, partial or delayed order retains its status and the former portfolio until effective settlement.

- [ ] **6.4 Reconcile each replay cash flow.**
  - **Procedure and tools.** Keep a record by date with order, execution, units, exchange, cash, fees, payments, withdrawals and any pending settlement. Separate decision, enforcement and settlement time stamping. Arrange returns on positions actually held.
  - **Evidence to retain.** Check with manual cases a purchase followed by price variation, partial sale, withdrawal, missed order and delayed settlement. Reconcil positions and cash with the daily net value.
  - **Checks and fallback.** An order on hold does not carry any performance before it is executed. The reserve and cash required for settlement remain verifiable.

- [ ] **6.5 Compare strategies under identical execution assumptions.**
  - **Procedure and tools.** Figer starting capital, calendar, returns, changes and implementing rules. Test with and without charge, then spread expanded, transaction missed and delay of a session.
  - **Evidence to retain.** Table of net wealth differences, turnovers, withdrawals paid and risk exceedances under the same basis. Identify the outcome that depends on a favourable hypothesis.
  - **Checks and fallback.** Indicate the effect of each cost and timing difference before interpreting a variance as a strategy gain.

- [x] **6.6 Define a mandate-fit score.**
  - **Procedure and tools.** Check imperative constraints and negotiability before classifying. For eligible allocations, calculate sub-scores of financial, historical and stress risk, diversification and concentration, validated forecasts, and fees. Link a historical sub-score to the observed net return and holding during crises, avoiding twice the same risk. Normalize on benchmarks set by mandate, horizon and currency. The final score in 100 is the weighted sum of the sub-scores. Version the grid. Propose explicit default weights and link them to the client's confirmed priorities.
  - **Evidence to retain.** Table with gross values, sub-scores, weights, contributions and recalcable total. Test two customers who differently weigh diversification and goal. Verify that an off-term option cannot win in the ranking.
  - **Checks and fallback.** The score is an index of adequacy. A probability or expected return remains displayed separately. The macro, market, quantitative and sentimental signals remain visible in their families. They contribute to the forecast sub-score via validated models for the right target and horizon.

- [x] **6.7 Test missing data and ranking stability.**
  - **Procedure and tools.** Apply a common grid of available criteria to all comparison options. Set the necessary data, level of coverage and withdrawal rules before testing. Test a historical grid without forecasts when the complete grid is unavailable for comparison. Reasonably vary weights and estimates. Define a margin of equality before producing the ranks.
  - **Evidence to retain.** Comparison with complete data, scenario without validated sentiment, scenario with missing essential data and similar cases, the order of which is inverse. Show the cover and version of the scale.
  - **Checks and fallback.** A private option of an indispensable data remains without an overall score. A partial score has its own wording and coverage. Close or unstable options are reported as comparable, with compromises to be agreed.

- [x] **6.8 Combine several portfolios at client-selected weights.**
  - **Procedure and tools.** Allow to choose two or more eligible options with one share per option. The shares are positive or zero and total 100% of the investment sleeve. The confirmed reserve remains separate. Convert shares by weight per instrument with the matrix of candidate portfolios. Group positions of the same security, including cash per currency, and calculate net orders from positions already held. Recalculate estimated return, covariance, costs, concentration, exposure to shocks and feasibility after rounding to the quantities that can be purchased. For the historical replay, simulate the actual planned rebalancing rules.
  - **Evidence to retain.** Recalculate by hand a 60/40 mixture with a common title. If it weighs 20% in A and 10% in B, check its final weight of 16%. Test 100% in one option, shares that do not total 100%, identical portfolios and off-site mix despite eligible components. Check the suitability score and graphs from the aggregated positions.
  - **Checks and fallback.** Recalculate the risk and score on the mixture. Any violation of the mandate shall be explained before confirmation. Display a workable adjustment when the calculation finds one. The reserve investment sleeve does not contribute to the budget of the combination.

- [x] **6.9 Optimize the blend of the selected options.**
  - **Procedure and tools.** Optimize the shares of the selected options, then check the aggregate portfolio with controls of 5.2–5.8. Propose the Sharpe estimated in CHF after costs on an explicit horizon and a consistent reference rate, the maximum estimated return in the confirmed band, or the minimum risk compatible with the mandate. Use common returns and covariance of underlying positions, or covariance of strategies obtained on a common game if they follow distinct dynamic rules. Check the minima per option if the client wants to keep more than one, and report cases where only one option is sufficient according to their criteria.
  - **Evidence to retain.** Compare free weighting, equiweighting, best option alone and optimized combination. Replay a simple analytical case and a set of strongly correlated strategies. Publish the criterion, fees, horizon, aggregate risk and level of evidence of research.
  - **Checks and fallback.** An almost zero variance or too fragile return estimate may render Sharp untapped. In this case, explain and propose feasible comparisons on the other criteria. When the solver does not certify the optimum, present the verified result as a candidate.

**Deliverable and evidence.** A comparison card per customer and a grid that justifies the differences in ranking. Replay the calculation with different costs and explain the changes. [Replay V1](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/research/execution/PROTOCOL.md) · Local theory, Guides 04 and 06, QARM2 LN5–LN6.

**Section 6 results on the multi-asset universe.** Cells 6.1 to 6.9 of the notebook use mandate results on 3,322 instruments. Four variants were calculated, two of which were grouped together, with a fixed benchmark outside the mandate. Eight mixtures were compared. Sections 6.3 to 6.5 remain open for validation of the nine-year replay. The separate ETF benchmark notebook retains its eleven blends and historical rankings. [Main report](reports/univers-complet/README.md) · [Notebook](RiskMatch_V2.ipynb) · [ETF benchmark](reports/06-options/ETF_Benchmark.ipynb)

**Multi-asset replay.** The PFBX continuation extends the comparable window from 37 to 51 sessions (12 January 2018) across all 35 scenarios. BHAC blocks the next session. The original 39,408 fills reconcile to the recorded ledger; independent prices and settlement evidence are still missing for the complete nine-year comparison. [Replay evidence](reports/univers-complet/replay-evidence.json) · [Method and outstanding data](reports/univers-complet/README.md)

## 7. Goals and cash-flow schedules

- [x] **7.1 Build the CHF cash-flow schedule.** Dates, contributions, withdrawals, reserve and explicit nominal or real objective. Calculate the constant rate required by flow projection and `scipy.optimize.brentq` when the series allows a single root. Detect absence or ambiguity. Test capital alone, opposing flows, already funded objective and insufficient reserves.
  - **Procedure and tools.** Build a schedule in CHF and separate real, nominal and protected flows objectives. Use `brentq` in a relevant interval after verifying the presence and, depending on the flow structure, the uniqueness of a solution.
  - **Evidence to retain.** Check a case without contributions by closed formula, then the payments dated by reprojecting of the final capital.
  - **Checks and fallback.** If no single rate solves the problem, explain the reason and present the differences in francs per scenario.
- [x] **7.2 Evaluate multiple investment horizons.** Simulate the post-cost trajectory by resampling monthly blocks synchronized between assets and currency. Start with blocks of 12 months and 2,000 paths, then compare to blocks of 6 and 24 months if historical allows. Fix the seed and publish the assumptions. Measure the dates payable, the terminal deficit and its sensitivity to contributions, amount and maturity. For bonds, also compare coupon and repayment deadlines to requirements.
  - **Procedure and tools.** Resampling common monthly blocks by maintaining the dependency between assets and exchange. Replay fees, payments, withdrawals, lots and coupons according to the data. Fix seeds and variants before comparison.
  - **Evidence to retain.** Simulated achievement rate, mean and median deficit, date of absence, quantiles and sensitivities block/date/amount/contributions.
  - **Checks and fallback.** If history is too short, publish the available scenarios and their coverage. The simulated frequency remains conditional on the model.
- [x] **7.3 Replay the complete client journey with the V2 catalogue.** A has a close expense. B has a long horizon. At the same tolerance, check the effect of their fluxes. Also replay minimum, 40% cap, target of 35 or 40%, 100% wish, too high required return, exclusions and diversification preferences. Compare the custom allowance to a fixed V2 allowance at the same time and on the same cost basis. Link each change to a flow change, preferably or d-universe. Use a controlled case to test an impossible target even if 40% becomes accessible with some individual securities.
  - **Procedure and tools.** Use two clients with the same tolerance and separate timelines, then change a single data. Repeat minimal risk cases, ceiling, reachable band, impossible target and required return too high.
  - **Evidence to retain.** Two files that link responses, reserves, assets, options, costs, desires, needs and achievable range. Show the expected change with each variation.
  - **Checks and fallback.** Any proposal that alters a firm constraint without confirmation is rejected. An alternative indicates precisely what objective it fulfils.

- [x] **7.4 Measure the first cash shortfall and the final funding gap.**
  - **Procedure and tools.** For each trajectory, record the first unfunded maturity, deficit at that date, terminal deficit and recovery conditions. Test the separate effect of a revised input, offset or target.
  - **Evidence to retain.** One case succeeds the final objective but lacks an intermediate expenditure. The results explicitly show both measures and amounts in CHF.
  - **Checks and fallback.** A trajectory that ends above the target does not erase a missed deadline. Simulated probabilities remain conditional on assumptions.

**Deliverable and evidence.** Two client files and a comparison of date/contribution/amount scenarios. Display side by side the desired return, the required return and the estimated achievable range in the confirmed risk band. Enact the deviations and the possible effect of an adjustment in the amount, date or payment. [Simulation V1](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/research/options/PROTOCOL.md) · Local theory, guides 21 and 34.

**Section 7 research evidence.** The dated CHF solver, two theoretical client dossiers, paired block scenarios, lot-based costs and missed-payment reconciliation are available in the [funding report](reports/07-funding/README.md). The common history supports seven six-month starts, one twelve-month start and no twenty-four-month start. The longer benchmark-only sensitivity is reported separately. No client success probability or live order is certified.

## 8. Exposures, correlations and shocks

- [x] Calculate individual WTI sensitivities, 10-year rates, market and exchange with HAC intervals, compare two years and aggregate the WTI scenario on published positions. Three historical crises have one register per instrument. The five-factor extension below adds curve slope, signed oil shocks, regimes, observed recoveries and direct cash-flow repricing. [Calculations and coverage](reports/econometrie/README.md)

- [x] **8.1 Build the factor time series.** Market, CHF exchange, rate and slope, WTI in USD/bar, volatility regimes. Align closing hours and observation dates. Load factors from their documented sources, including EIA for WTI. Study positive and negative shocks separately, with initial thresholds of ±5 USD/barrel and quantile variants fixed before analysis.
  - **Procedure and tools.** Build dated factors: base point rates, WTI in USD per barrel, exchange and market in returns, then volatility regimes. Archive calendars and availability.
  - **Evidence to retain.** Source table, distribution of shocks and non-missing measurements. Check one threshold plus and minus and one holiday.
  - **Checks and fallback.** Do not collate comments from different sessions without explicit rules. Test sensitivity to fences and thresholds.
- [x] **8.2 Estimate exposures for individual instruments and portfolios.** With SciPy/statsmodels, produce Pearson and Spearman correlations, multifactor regressions and mobile sensitivities. First test a 252 session window, at least 200 common observations, one session delay and HAC errors. Calculate effects and intervals, varying the windows and the set of factors. Test if a sign is robust at times, currency and withdrawal of extreme episodes.
  - **Procedure and tools.** Create OLS/HAC regressions with statsmodels, then moving windows. Recalculate over comparable periods, with several factors and sensitivity to extremes.
  - **Evidence to retain.** Coefficients, units, intervals, numbers and signs by period. Check the weight aggregation on a portfolio with constant weight and sample.
  - **Checks and fallback.** An unstable correlation or insufficient sample gives a conservative or unestimated exposure. Publish contradictory cases.
- [x] **8.3 Build the historical crisis library.** Choose episodes and windows before testing, calculate returns around events, maximum loss and recovery, specify the number of episodes and process recoveries or their dependence. For uncertainty, use one bootstrap per block when the sample is sufficient. Link the scenario to the portfolio via exposures, then compare to a historical replay with explicit weight and calendar.
  - **Procedure and tools.** Freeze the list of episodes and windows, calculate abnormal returns if the reference allows and treat overlaps. Test isolated and joint shocks with common assumptions.
  - **Evidence to retain.** Crisis registry and recovery, WTI +10 USD and joint scenario. Show difference between observed episode and conditional estimate.
  - **Checks and fallback.** If there are not enough events, present the cases and uncertainty without extrapolated frequency.

- [x] **8.4 Attribute shock effects to holdings and currencies.**
  - **Procedure and tools.** Apply multifactor stress to positions and revalue instruments whose fluxes allow direct calculation. Compare stable portfolio change, contributions per asset and aggregate exposures.
  - **Evidence to retain.** Bring the WTI and USD/CHF shock closer to total in CHF. Check consistency with rate curve revalorisation for an obligation.
  - **Checks and fallback.** An important interaction calls for a costed joint scenario with its assumptions. Keep explicit the date, uncertainty and omitted factors.

**Verified in 8.1–8.4.** Five dated factors, signed shock distributions, 3,373 central fits among 3,902 securities, matched-weight checks on five portfolios, 11,706 crisis records and direct repricing for 64 Treasury issues. Incomplete paths and unstable exposures are identified separately. [Methods, charts and coverage](reports/08-chocs/README.md) · [Scenario results](reports/08-chocs/results.json) · [WTI source](https://www.eia.gov/dnav/pet/hist/rwtcD.htm)

## 9. Individual US stocks

- [x] **9.1 Audit the local CRSP extract.** Inventory tables, last observations and version-specific treatment of dividends and delistings. For 2026, attach a dated listing list and price and volume history from a usable public source or a new local file provided. Control identifying, date, price, total return, listing history, volume and output. Check if output is integrated with performance to avoid counting twice.
  - **Procedure and tools.** Inventory CRSP tables and versions with permanent keys. Compare daily and monthly coverage, performance agreements and availability in 2026. Describe missing data by field and date. Check an overlap period before extending a series with another source.
  - **Evidence to retain.** Manifest, actual, latest dates and distribution/output controls. The connection between sources is reproducible and its deviations are documented. [Nasdaq Trader Directory](https://www.nasdaqtrader.com/Trader.aspx?id=symbollookup)
  - **Checks and fallback.** An output already taken into account does not add up. Unverified 2026 data blocks current eligibility, while allowing for a historical replay dated.
  - **Verified.** 46,320 complete 2025 stock-month comparisons, three corporate-action controls and a pre-open October 2026 listing snapshot. [Extract and bridge evidence](reports/09-stocks/README.md)

- [ ] **9.2 Construct a point-in-time stock universe.** Accept all extraction actions that pass the criteria of 4.4 and publish the grounds for exclusion. Define the measurement period and a volume contribution limit adapted to the amount. Select with the values then available, re-examine the universe at rebalancing and track outputs to the actually cashed product. Measure overlap between direct and ETF titles.
  - **Procedure and tools.** Apply size, liquidity, access and historical rules to the entire extraction on each date. Reconstitute quotation periods and transaction effects.
  - **Evidence to retain.** Compare ETF and ETF + direct securities with a common base. Check dividend, change of drawer, quote exit and overlap of funds.
  - **Checks and fallback.** Do not rebuild the ancient universe from survivors alone. Exclusions retain reasons and dates.
  - **Measured scope and open evidence.** Ten dated screens, nine paired ETF comparisons and 2,959 passing stocks on 30 October 2026. Historical successor payments and permanent IDs outside the frozen cohort still require verification. [Research outcomes and exact limitations](reports/09-stocks/README.md)

- [x] **9.3 Add fundamentals after matching identifiers.** If available, Compustat and CRSP/Compustat link table with period of validity and date on which the report was known. EDGAR reply with CIK identifiers, filing date and deposit ID. Check a history with reprocessing. Report variable if date is not traceable.
  - **Procedure and tools.** Attach financial data and valid date identifiers. Use publication date and filing version with CCM or EDGAR. Test a post-closure deposit and reprocessing.
  - **Evidence to retain.** An observation obtained from its source and a subsequent revision that does not change an earlier classification.
  - **Checks and fallback.** In the absence of a demonstrable publication deadline, keep the variable out of the historical ranking.

- [x] **9.4 Audit historical coverage of US stocks.**
  - **Procedure and tools.** Publish staff by year, sector and reason for exclusion from registration and release dates. Compare the universe actually available each year to the universe that would survive until the end date.
  - **Evidence to retain.** Check an entry, exit and reclassification several years before the end. Explain the effect of filtering and missing data on the test universe.
  - **Checks and fallback.** When coverage is partial, qualify the subuniverse and conclusion. Non-observable titles remain identified if their existence is known.

**Deliverable and evidence.** ETF-only and ETF-plus-stock returns use identical dates, fees and cash. The publication-time control preserves Veritone's original balance sheet, and dated counts expose the effect of filtering historical membership. The local archive contains detailed securities, filings and terminal events. [Study, figures and sources](reports/09-stocks/README.md) · [Auditable summary](reports/09-stocks/results.json)

## 10. US Treasuries and commodities

- [x] **10.1 Identify the bond data needed for the selected issues.** The selected direct bonds are US Treasuries. Verify each issue’s identifier, coupon schedule, maturity, quoted price, accrued interest, settlement, lot size and trading access. Corporate bonds are outside the selected universe.
  - **Procedure and tools.** Sample sources first on simple emissions. Inventory ID, currency, price, date, interest accrued, coupon, maturity, settlement and customer access data.
  - **Evidence to retain.** For each category, field proof and list of measurable issues with liquidity limit. Document gaps in coverage and permitted use by source.
  - **Checks and fallback.** An issue without exploitable price or adapted model remains in inventory. Document the ETF fold or shadow example.
  - **Verified coverage.** All 65 issue sheets include terms, historical auction lots, mark and access status. The October cohort has 64 valuations, 54 model-eligible issues and zero verified customer orders. [Issue register](reports/10-treasuries-gold/issues.json)

- [x] **10.2 Calculate bond value and interest-rate risk.** Generate the schedule, reconcile clean price with full price, coupons, total return, modified duration and convexity on an verified example. Test sensitivity to ±100 bp, change and credit gap. In case of insufficient coverage, keep bond ETFs in the historical allocation and isolate the pedagogical example of direct obligation.
  - **Procedure and tools.** Generate flows according to dates and conventions, calculate own/full price then duration, DV01 and convexity. Separate stress rate, credit and FX then joint shocks.
  - **Evidence to retain.** Reconcil an obligation by hand, with coupon, accrued interest, repayment and revalorization ±100 bp.
  - **Checks and fallback.** Use full revalorisation if the duration/convexity approximation becomes too far away. Show the sensitivity of results to flows and prices.
- [x] **10.3 Validate the selected investable commodity exposure.** Validate GLD as the selected investable gold exposure, including costs and coverage. Use WTI spot in the factor and shock analysis. Any additional commodity vehicle would require a separate selection decision and a documented total-return series.
  - **Procedure and tools.** Identify rated vehicles, mechanism, rolling rules, total return history and fees. Load the spot price into the scenario factors.
  - **Evidence to retain.** A card compares vehicle performance and spot variation on common dates and explains the relevant difference.
  - **Checks and fallback.** An asset without marketable and historical prices produces a factor analysis alone.

- [x] **10.4 Test tradability for bonds with irregular quotes.**
  - **Procedure and tools.** Set separately the listing and transaction dates. Examine age, price dispersion and observed sizes. Test the batches and payment deadlines for the customer's portfolio.
  - **Evidence to retain.** An obligation with an old price or no suitable size shall be rejected on the exact date. Replay a valid batch purchase and payment before payment.
  - **Checks and fallback.** An indicative valuation does not allow a proposal that is presented as a purchaseable. Show the ETF or cash alternative if it meets the mandate.

**Verified in 10.1–10.4.** Reconciled a real auction to six decimals, repriced 64 nominal issues, reviewed 230 accepted issue-level buyback amounts, tested cash, coupon, maturity and rejection cases, and measured GLD versus gold over 262 common months. [Report and figures](reports/10-treasuries-gold/README.md) · [Reproducible results](reports/10-treasuries-gold/results.json)

## 11. Environmental preferences

- [x] **11.1 Choose measurable environmental criteria.** Explicit exclusion and, if sources permit, carbon intensity with units and coverage rates. Define aggregation for securities held directly and indirectly, date of measurement and processing of missing data.
  - **Procedure and tools.** Choose a dated metric, unit, perimeter and source. Calculate coverage by weight and check indirect positions with issuer identifiers.
  - **Evidence to retain.** Cover table with direct title case, funds and missing data. Check the exclusion of an indirectly held issuer.
  - **Checks and fallback.** A mandatory preference and an unknown underlying trigger the rule chosen in the mandate. A partially measured preference displays its coverage.
- [x] **11.2 Test decisions under environmental constraints.** Apply mandatory exclusions according to the mandate rule. For a flexible preference, create a variant with limit on the measure or compromise classification. Display measurable coverage and return/risk/fee spread against reference.
  - **Procedure and tools.** Compare the environmental option and other constraints with the same data, ceiling and cost assumptions. Test imperative and flexible preference.
  - **Evidence to retain.** File illustrating triggered exclusion, risk and fee differences, measure and share actually covered.
  - **Checks and fallback.** If the measure is missing or the allocations are identical, explain the result rather than artificially classify the options.

**Deliverable and evidence.** Replay a case with a prohibited title hidden in an ETF and a case where the information is missing. Compare variants on the same documented perimeter. Local Theory, Guide 15.

**Executed evidence.** The dated Chevron look-through replay and paired optimizations ran on the section 6 model. The conditional point-source measure covers 54 issuers. [Controls, comparisons and figures](reports/11-environment/README.md)

## 12. Forecasts and signal validation

- [x] Timely comparison of historical variance and exponential weighting by security at 21 and 63 sessions, then record a descriptive alert of acceleration. The nine tests below record the subsequent signal, probability and allocation decisions. [Test results](reports/econometrie/README.md)

- [x] **12.1 Freeze the forecast evaluation protocol.** For each signal define the target, date of publication, horizon and reference model before calculation. Define before the test the economic measurement according to the signal function. For a performance signal, compare the net return to equal cap. For a risk signal, compare the frequency of overruns and the extent of overruns under the same portfolio rules. For volatility, start with variance performed over the next 21 sessions and then test 63 sessions if data is sufficient. For return, start with the monthly excess return on CHF cash. For alerts, define an observable event and its delay. Retest on the same calendar by reference and candidate.
  - **Procedure and tools.** Write for each signal a structured sheet: target, decision date, horizon, usable information, comparison, metrics and pass threshold. Freeze before final block.
  - **Evidence to retain.** Reproducible card for variance 21 sessions, monthly performance and a defined alert. The dates and scores are aligned by reference and candidate.
  - **Checks and fallback.** Without a verifiable target and time stamp, keep the descriptive signal. The return prediction and the risk prediction keep their tests clean.
- [x] **12.2 Prepare the signals.** Macro: rate and economic situation, with ALFRED vintages if available and date of availability. Market: VIX and other price risk measures, with source and time stamp. Quantitative: realized volatility, delayed momentum and liquidity. Geopolitics: GPR index dated. Feeling: inventory the corpus and its rights, then date the observations, align the publications with the first usable moment, deduce and test a simple reference and then a NLP model if the coverage is sufficient. Archive text, score and date separately. No signal calculated during a session is used in a previous order.
  - **Procedure and tools.** Import by family. Horodate vintage macros, move publications after closing to the first possible decision, deduce messages and archive values, texts, licenses and scores separately.
  - **Evidence to retain.** Macro revision tests, new after closing, duplicate message and spindle change. The signals remain identifiable at their origin.
  - **Checks and fallback.** Late or missing data recorded with documented pattern and processing. No future score is attributed to a past decision.
- [x] **12.3 Compare forecast models.** Volatility: mobile history and EWMA as references, GARCH with `arch`, then regularized regression or gradient boosting if the observations allow. Note QLIKE and variance error. Performance: reduced average as reference, Ridge to test an additional signal. If a view brings an estimated gain and uncertainty, test Black–Litterman with prior, matrix of documented views and uncertainty, under the same constraints and costs. Keep the refused signals on the register.
  - **Procedure and tools.** Compare mobile references and EWMA to GARCH, then test Ridge and candidates on chronological subsamples. For Black–Litterman, document prior, horizon, view and matrix of uncertainty.
  - **Evidence to retain.** Archived forecasts, QLIKE, errors, coverage and proof that the confidence view tending to zero is regaining the prior.
  - **Checks and fallback.** An unstable model returns to the reference. The costs remain those of induced transactions and apply with the same agreements.
- [x] **12.4 Test market overheating indicators.** Start with simple indicators, e.g. price acceleration, valuation if available and volume. On fairly long series, evaluate SADF/GSADF on a limited basket, with appropriate critical values and false positive tests. Repeat on successive historical dates, recalculating without future data and adjusting multiplicity. Publish reported episodes, lack of data and delayed detection.
  - **Procedure and tools.** Archive a long series overheating protocol and fix windows and false positives accepted. Compare a simple indicator to SADF/GSADF tests if coverage allows.
  - **Evidence to retain.** Dates of detection, false positives, delay and effect of multiplicity control. Replay historical dates with the only information available.
  - **Checks and fallback.** An overheating alert describes the observed evidence and its instability. Probability requires its own validation.
- [x] **12.5 Define acceptance criteria for signals.** Chronological cutting with increasing window, adjustment on drive windows only, train/test separation by duration of overlapping targets and last block reserved. Test a signal alone, then its additional effect. Use a block bootstrap of score differences. To enter the recommendation, require a forecast gain of which the 95% interval excludes the lack of improvement and whose sign holds in the majority of blocks, then verify that the funded rule brings the expected economic improvement after costs on the final block. To display a probability, check Brier or log-loss against the reference frequency and check the calibration curves on the reserved data. Otherwise display an exposure or scenario alert.
  - **Procedure and tools.** Set drive, time validation and reserved test block. Purging overlapping targets. Calculate matched losses and block intervals, then replay net transactions on the frozen rule.
  - **Evidence to retain.** Decision by candidate and reason, sample size, statistical and economic gain, calibration curves and negative results retained.
  - **Checks and fallback.** Any unstable or insufficient gain leaves the reference active. A forecast without verified calibration does not produce a percentage of customer probability.

- [x] **12.6 Display each signal and combine evidence for each forecast target.** Maintain a record by signal with family, measure, date, target, horizon, meaning, intensity and quality of evidence. Display macro, market, quantitative and sentimental signals individually. Build a weighted opinion only between validated signals for the same target and horizon. Compare to a simple reference, measure the additional input and limit the weight of redundant signals. Fig the rule before the final test. Compare the combination to the best signal alone and the reference. Show meaning, intensity, effective weights, contributions, exclusions, missing data and disagreements. Keep the exploratory signals visible with zero weight. Test and calibrate separately any announced probability. Check a case with opposing signals and a case without sufficient evidence where only the reference notice is displayed. [Detailed rule](LIBRARY_METHODS.md#4-signal-interpretation-and-evidence-based-weighting)
  - **Procedure and tools.** Separately measure, direction, intensity and proof of each signal. Compare weight and weight based on validation for the same target and horizon. Test redundancy, then freeze.
  - **Evidence to retain.** Details of contributions, actual weight and coverage. Compare on the block reserved for reference and the best signal alone. Replay disagreement and missing data.
  - **Checks and fallback.** An exploratory signal keeps a zero weight. If the combination is not robust, display individual reviews and return to the reference model.

- [x] **12.7 Link risk assessments to verifiable actions.**
  - **Procedure and tools.** For each portfolio, the estimated risks are 21 and 63 sessions depending on coverage, oil/rate/exchange scenarios and maturity deficit risk. Attach to each notice its date, unit, horizon, signal weights and model. Compare reference allowance and allocation taking into account the signal at equal costs.
  - **Evidence to retain.** Replaying opposing signals, a positive opinion with fragile historical gain and a portfolio whose volatility increases without significant effect on the target. Explain when the client keeps his or her allowance, studies a cover or reviews his or her assumptions.
  - **Checks and fallback.** A directional score remains presented with its scale. Only calibrated events can display a probability. Coverage is also judged on its cost and effects on other risks.

- [x] **12.8 Prevent unvalidated signals from changing a proposal.**
  - **Procedure and tools.** Build a versioned registry by target and horizon. Connect the engine to the only eligible condition on the decision date and log back versions, withdrawals and references.
  - **Evidence to retain.** Inject a strong but rejected signal, an expired signal and a version change. The allowance follows only the eligible game and the explanation corresponds.
  - **Checks and fallback.** Information rejected or expired may appear to be descriptive with zero weight. The previous version remains reproducible.

- [x] **12.9 Test probabilities and prediction intervals separately from the score.**
  - **Procedure and tools.** Figer events, horizons and units. Compare probabilities to reference frequency and ranges to coverage frequencies on a reserved block. Publish the workforce and uncertainty intervals.
  - **Evidence to retain.** Calibration curves and scores, coverage and width of range. Test a series with few events then a change of diet.
  - **Checks and fallback.** Remove the percentage or range whose reliability does not pass the checks. Present the conditional impact or descriptive alert.

**Deliverable and evidence.** Record of experiments and decisions by signal, including references, scores, dates, fees, leak tests, accepted probabilities and negative results. [ALFRED](https://alfred.stlouisfed.org/) · [GPR Index](https://www.matteoiacoviello.com/gpr.htm) · [Time cut](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) · [Calibration](https://scikit-learn.org/stable/modules/calibration.html) · [Work on bubbles](https://www.cambridge.org/core/journals/econometric-theory/article/abs/financial-bubble-implosion-and-reverse-regression/E43AC1EFA8A36467BAF4C602950B6074) · Local theory, QARM2 LN3–LN4 and LN7, EMiF classes 9–10, guides 12, 17 and 19.

**Executed evidence.** The 3,902-instrument transfer audit, 52 admission experiments, held-out predictions, publication and withdrawal controls, two calibration diagnostics and five portfolio notices are archived. No signal passes both statistical and funded gates in validation and on the final block. [Report and figures](reports/12-forecasts/README.md)

## 13. Application, portfolio matching and monitoring

- [x] Verify the cherry transition on both card decks, including the like chime, the pass clap, uninterrupted jazz, touch input and reduced motion. [Recorded swipe](reports/studio/cherry-swipe.webp)
- [x] Verify the continuous six-piece soundtrack, the quieter match screens, the title timing and a stable header during swipes. [Sound and navigation](reports/studio/README.md#sound-and-navigation)
- [x] Compare the desired and required return with the goal scenario and the eligible matches. Exclude the illustrative allocation from booking. [Goal comparison method](reports/studio/ALLOCATION.md#goal-comparison)
- [x] Verify multiple named saves with four-digit PIN confirmation, failed-attempt delay, progress recovery and locking. [Save workflow](reports/studio/README.md#named-local-saves)
- [x] Check the lagoon background and navy glass panels on desktop and mobile. [Desktop](reports/studio/glass-desktop.jpg) · [Mobile](reports/studio/glass-mobile.jpg)
- [x] Project the CHF reserve at an optional savings rate and show strategy allocations as percentages and CHF before matching. [Method and test](reports/studio/README.md#chf-reserve-and-strategy-split)
- [x] Show five required fields and short help bubbles on the brief. Group preferences under a collapsed disclosure and preserve planned spending on existing mandates. Keep compatibility with saved mandates. [Interaction replay](reports/studio/interaction-check.json)
- [x] Verify the full brief is reachable by wheel and touch in standalone and Streamlit, together with pre-start music, automatic retry on normal interaction when autoplay is blocked, synchronised title audio and persistent mute. [Interaction replay](reports/studio/interaction-check.json)
- [x] Deliver the client-facing path from the lagoon entrance through the budget and goal brief, adaptive swipes, behavioural score and explanatory profile.
- [x] Review the studio questionnaire in both languages and make the fictional examples and their routing explicit. [Questionnaire review](reports/studio/ETUDE_QUESTIONNAIRE_FR.md#relecture-bilingue-du-studio)
- [x] Show the five behavioural blocks, their individual scores and answers, and a restart that preserves the brief and any portfolio. [Scoring and questions](reports/studio/ETUDE_QUESTIONNAIRE_FR.md#profil-en-cinq-blocs)
- [x] Choose English or French at startup and switch from the studio header without clearing the current form or questionnaire. [Studio language](reports/studio/README.md#studio-language)
- [x] Derive the studio's illustrative annual volatility zone from A/B portfolio choices and the constrained allocation engine. Preserve the behavioural scores and verify unresolved choices, cash and checked whole-unit matches. [Questionnaire method](reports/studio/ETUDE_QUESTIONNAIRE_FR.md#vérification-sur-des-choix-de-portefeuille) · [Desktop and mobile replay](reports/studio/volatility-browser-check.json)
  - **Open evidence.** Validation on held-out portfolio choices and out-of-sample market assumptions. The current test uses fictional decisions and the dated historical model.
- [x] Expose the complete research library and calculate whole-unit strategies from the dated eligible universe. Show risk, strengths, weaknesses, measured environmental coverage and separate signal readings.
- [x] Verify manual and suggested blends, independent confirmation, holdings, a simulated close, a deposit and resume on desktop and phone. [Studio methods, screenshots and test receipt](reports/studio/README.md)

The numbered points below also retain the earlier research walkthrough. Section 14.3 tracks live-data coverage.

- [x] **13.1 Integrate five Streamlit screens.** Questionnaire, mandate confirmed, results and comparison, portfolio monitored, request for review. Build the V2 interface separately from the Python engine. Test cards on mobile and computer. Verify that gesture, button and keyboard produce the same response and branch, that a correction recalculates the mandate and that an incomplete gesture does not validate any response. Rewrite an amended application and invalidate the old proposal with its version of mandate.
  - **Procedure and tools.** Link the five screens to common Python functions in the notebook. Follow drafts, confirmed mandate, recalculated options, simulated portfolio and revision. Test via browser on phone and computer.
  - **Evidence to retain.** Check gestures, buttons, keyboard, screen rotation, feedback and data modification. An old result becomes obsolete after validated change.
  - **Checks and fallback.** An incomplete status remains editable and confirmation is based on the latest version of the mandate.
- [x] **13.2 Monitor portfolios at the close.** Save fictitious transactions, positions, flows and portfolio versions to SQLite. Valorize with price and timed FX and display latest update, out-of-payments/debit performance to compare the strategy and value of the account including all streams. Reconcil the result with a small hand-calculated survey. Report an expired price and suspend the confirmation that depends on it.
  - **Procedure and tools.** Write a SQLite register of units, prices, FX, flows and fees. Set the order of operations for a day and calculate value and neutralized performance of flows. Horod the corrections and recalculate the affected periods.
  - **Evidence to retain.** Reconcil by hand a purchase, a prices review, a withdrawal and a positive cashflow. Show value, performance, drawdown, drift and last quote.
  - **Checks and fallback.** A withdrawal reduces the value and does not create a fictitious loss. Suspend proposals that depend on an outdated price.
- [x] **13.3 Test a targeted portfolio revision.** The client asks for oil protection after choosing his portfolio. Recalculate from current positions and mandate. Present status quo and alternative, decrease in exposure or loss under shock, transaction costs, impact on target and other displaced risks. Require a unique confirmation in the demo. Replay a double submission and change of mandate between proposal and confirmation. Repeat the calculation after changing the date, target, savings or band and show the difference with the portfolio actually held.
  - **Procedure and tools.** Build review triggers, including shock requested, drift or modified lens. Compare maintenance and revision on the same data, check possible sales and settlement cash, then request versioned confirmation.
  - **Evidence to retain.** Oil protection with estimated effect, costs, other risks and result on target. Replay refusal, double click, delayed settlement and modified mandate.
  - **Checks and fallback.** Repeated confirmation creates at most a simulated movement. An impossible sale or expired listing blocks the explained transition to the customer.

- [x] **13.4 Define how the demo handles client data.**
  - **Procedure and tools.** List the necessary data, location and read rights. Use only fictitious profiles in the published demo. Defining export and deletion of a folder by including its registered versions and proposals. Keep local and secret files out of deposit.
  - **Evidence to retain.** Create two fictitious accounts, check their separation, test export and deletion, and inspect distributed files and logs with a set of fictitious markers.
  - **Checks and fallback.** Any cross-access or identifiable distributed profile blocks public demo. Keep local state time to correct the broadcast.

- [x] **13.5 Trigger a review while leaving the decision to the client.**
  - **Procedure and tools.** Version the drift thresholds of weights, losses, risk, maturity and change of mandate. Compare the retention option to a change and explain the trigger.
  - **Evidence to retain.** Test for sub-threshold variation, significant drift, near expense and reported risk. The site distinguishes opinions, proposals and confirmation.
  - **Checks and fallback.** A notification or signal does not trigger any transaction. Retention remains available when it is compatible with the mandate.

- [x] **13.6 Safely record a simulated revision.**
  - **Procedure and tools.** Write in a single SQLite transaction confirmation, mandate version and portfolio movements. Use a unique identifier for confirmation and check the status just before writing.
  - **Evidence to retain.** Replay an interruption after validation, two simultaneous confirmations and a cancellation followed by a restart. The register returns to a consistent state and does not duplicate any movement.
  - **Checks and fallback.** If data or mandate changes, invalidate the proposal concerned. In case of write error, the transaction is cancelled and the last reliable state remains visible.

- [x] **13.7 Build the graphical portfolio comparison screen.**
  - **Procedure and tools.** With Streamlit and Plotly, show the score side by side, its sub-scores and three key compromises. Use a ring diagram for weights by class or sector, with details of titles and cash in a table. Add bars for concentration and risk contributions, as well as a card of correlations on request. On the return–volatility chart, indicate the proposed band, reference and allocations.
  - **Evidence to retain.** On phone and computer, check that graphs use the same dated data as the notebook and table. Weights total 100% based on the denominator displayed. The contribution bars are reconciled with the total of the measure represented.
  - **Checks and fallback.** Show units, date, currency and legends. The values remain accessible via an array and the classification remains legible without colour. An unknown or aggregated category is explicitly indicated. [Streamlit Graphs](https://docs.streamlit.io/develop/concepts/design/charts) · [Plotly diagrams](https://plotly.com/python/pie-charts/)

- [x] **13.8 Visualize history, scenarios and the revision decision.**
  - **Procedure and tools.** Show a curve of historical value and maximum decline at comparable dates, a frieze of payments and withdrawals, identified future scenario bands and shock loss bars in CHF. Add a short outline of the prices answers → mandate → allocations → choice. For a review, trace current portfolio and proposal with the fees and exposures that change, then display the signals and their contributions to the notice.
  - **Evidence to retain.** Replay an out-of-range risk target and oil cover. Verify on the charts common dates, threshold, feasible options and net effect of revision. Test the mobile display and a scenario without validated forecast.
  - **Checks and fallback.** Visually identify observed historical, modeled projection and conditional impact result. When a forecast is missing, leave the historical reading or scenario available with its own wording.

- [x] **13.9 Design and implement the visual identity.**
  - **Procedure and tools.** Build a mobile interface first, with airy cards and legible numbers. Take the local web prototype as a visual reference. Use a pink, electric blue and purple night palette, an original skyline and a 3D cherry. Apply the same system to cards, backgrounds, transitions, waiting states and match animation. Maintain an original lettering, with Archivo Black and DM Sans in the demo version. Keep color choices of graphs consistent between comparison and tracking. Use short transitions for navigation between cards and original icons for actions.
  - **Evidence to retain.** Captures of the questionnaire journeys, comparison, choice and follow-up on telephone and computer. Check contrast, keyboard focus, colorless readability and support for animation reduction.
  - **Checks and fallback.** The movements adapt to the preference of reducing animations. Legends, states and amounts are understandable without animation or dependence on a single color.

- [x] **13.10 Let clients browse, choose and confirm a portfolio match.**
  - **Procedure and tools.** Display options on cards with score, estimated return, risk and fees, then offer a detailed view with graphics and comparison. Give the actions "Choose this portfolio" and "Compose an allocation". For a combination, propose sliders coupled with percentage fields and engine weights. Show the aggregate composition and its controls, then ask for confirmation. Trigger the heart animation and "Confirmed Match" status only after recording the simulated selection. Then present the action "See my portfolio".
  - **Evidence to retain.** Test the simple choice, manual combination, proposed combination, cancellation and double click. Check that the animation is played once and that the follow-up opens the confirmed version. Check the same result in reduced motion mode.
  - **Checks and fallback.** The heart confirms a successful recording. In case of error or portfolio become inadmissible, keep the choice in draft and explain the cause. The customer can return to alternatives before confirmation.

- [x] **13.11 Monitor and revise a blended allocation.**
  - **Procedure and tools.** Record original options and their shares, final composition after rounding, market snapshot, mandate and simulated movements. Displays value, performance, allocation and risks of the aggregate portfolio. The initial shares remain searchable, and follow-up indicates whether the strategy plans to maintain these shares or allow composition to drift.
  - **Evidence to retain.** Replay a 60/40 match, market variation, flow and cover demand. Reconciling the follow-up with the aggregate position register, then comparing the costs and risks of a review with those of the portfolio held.
  - **Checks and fallback.** A revision starts again from the actual composition held and requires a new confirmation. Suggested weight changes remain proposals until this confirmation.

**Deliverable and evidence.** The five-screen simulator, dated CHF match, oil revision, privacy checks and desktop/mobile captures are available in the [section 13 report](reports/13-application/README.md). [Follow-up V1](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/research/monitor/README.md) · Local theory, guides 07, 21 and 22.

## 14. Final verification and delivery

The [release audit and launch guide](reports/14-delivery/README.md) records both clean-checkout replays. Intraday feasibility was assessed; a verified multi-asset price and USD/CHF feed remains open. [Measured source freshness](reports/14-delivery/intraday.json)

- [x] **14.1 Reproduce the release in a clean checkout.** Install the locked environment, run `python -m unittest discover -s tests` Since the future V2 repository, then the notebook with a new kernel, then remake both paths and revision without manual intervention in the data. Test also foreign currency, missing data, incomplete history and empty investment universe. Attach the class balance sheet of available, used and blocked instruments, proof that all eligible instruments have been offered to the engine and compare it with the fixed V2 strategy. Identify separately the eligible securities and those that the engine has actually retained in the allocations.
  - **Procedure and tools.** Start with a clean copy, install the package, run tests and notebook, then replay the tracks with and without private data. Include mobile integration and desktop checks.
  - **Evidence to retain.** Precise orders, versions, results of each case, catalogue comparison and traces of the route. Ensure that the stand-alone installation reproduces the base.
  - **Checks and fallback.** Any divergence is localized by version, source or hypothesis. Unreproduced evidence remains open in the checklist.
- [x] **14.2 Prepare the final evidence package.** Deliver launch guide, list of data and rights, assumptions, validation decisions and cases still open. The notebook maintains the results and methods of the study. The site presents the customer's decision and reasons. Examine separately the dissemination of the code and data.
  - **Procedure and tools.** Gather guide, sources, rights, model choice and journal. Summarize the path of a mandate and its alternatives, then link each digit to the notebook and corresponding dataset.
  - **Evidence to retain.** A person can restart the demo and check the numbers with the expected files. Inventory of fictitious and published data.
  - **Checks and fallback.** Remove private data or without confirmed rights from dissemination files. Document the demonstration fold.
- [ ] **14.3 Assess intraday monitoring.** If a source is accessible, check time stamping, deadlines observed, fees, calendar, currencies, quotas and withdrawal at closing. Replay a session and display the freshness of the enhancement. Follow-up remains at the close or with the observed time limit until a live source is verified.
  - **Procedure and tools.** Compare market time, reception and display during a session. Check for change, access, rights, and offending behaviour. Measure latency rather than infer the name of the flow.
  - **Evidence to retain.** Journal with time, latency, rights and results of outdated or missing data tests. Show clearly the recovery status to the customer.
  - **Checks and fallback.** Keep the last reliable price and the closing or delayed mode in case of unverified flows. Lintraday remains open if its source is missing.

- [x] **14.4 Verify the delivered scope before publication.**
  - **Procedure and tools.** Reread the 1.5 matrix and point out the proofs of the notebook, journal, tests and site on the same version. Control the public list of files after creating the demo version.
  - **Evidence to retain.** An independent prices covers cards, expenses, eligible U.S. universe, out-of-range slice, coverage search and simulated confirmation. Report the status of intraday and missing sources.
  - **Checks and fallback.** Any gap between demo, notebook and published data is corrected or declared open. V1 references remain optional for installation.

**Deliverable and evidence.** Reproduction report, demo, verifiable results and explicit statement of multi-asset coverage and intraday. Local theory, guides 06, 07 and 30.

## Course references

The methodological guides cited are optional readings. In the local course notes, they are in `Theory/Methodology/Chapter_Guides_00-34/`. The notes QARM2 and the classes EMiF 9–10 are in `Theory/Course_Notes/`. The CFA synthesis on sensitivities is in `Theory/CFA/`. V1 remains an optional historical document. The V2 project installs and runs with its files only.

[Return to V2 README](README.md)
