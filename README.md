# RiskMatch V2 — From client preferences to feasible portfolios

RiskMatch constructs and compares CHF portfolios for a US investment universe. The questionnaire records the client’s goals, loss capacity, tolerance and constraints. The allocation engine then estimates the highest net return it can achieve within the confirmed risk limits.

On 30 October 2026 the inventory contained **3,902 instruments**. The research model admitted **3,322**: 3,255 individual US stocks, 54 direct US Treasuries and 13 ETFs. Each admitted instrument can receive a weight, including zero. The separate account-access check admitted no instruments for an actual order. The 13-ETF benchmark is an earlier controlled experiment.

Start with the [main research notebook](RiskMatch_V2.ipynb). Use the notebook outline to jump to any of the 86 numbered checklist items (for example 3.1, 3.2, 3.3 and 3.4). Its progress table reads the checklist, its section 6 presents the multi-asset results, and its last section is 14. Section 8 compares five-factor sensitivities, observed crisis paths and portfolio stress in CHF. [Exposure and stress study](reports/08-chocs/README.md) · [Earlier factor estimates and exploratory variance forecasts](reports/econometrie/README.md).

Section 9 audits the individual-stock library and compares SPY with an allocation combining SPY and ten direct holdings. It records financial statement versions, sector changes and limits to the verified investment universe. [US equity study and figures](reports/09-stocks/README.md)

Section 10 gives a valuation and access status for each selected Treasury, compares bond and gold ETFs with their underlying exposures, and tests coupon, maturity and settlement cash flows. [Treasuries and gold](reports/10-treasuries-gold/README.md)

Section 11 tests a mandatory issuer exclusion through funds and a flexible intensity target on 55 measured share lines. Both comparisons report coverage, modelled risk, return and fees. [Environmental preferences and portfolio comparisons](reports/11-environment/README.md)

Section 12 tests dated macro, market, quantitative, geopolitical and policy-tone signals. The transfer audit covers all 3,902 inventory instruments. The five portfolio risk notices and the separate signal register are available on the Options page. [Forecast validation, figures and decision register](reports/12-forecasts/README.md)

Section 7 compares two dated CHF goals for clients with identical risk tolerance. The [funding report](reports/07-funding/README.md) shows required rates, cash shortfalls and the historical coverage available for paired simulations.

Section 13 connects the client interview, mandate, portfolio comparison, CHF ledger and revision in a local application. The public checkout includes a portable market simulation. [Launch guide, numerical results and screenshots](reports/13-application/README.md)

## Reproduce the verified release

The release guide provides the tested CPython 3.12 environment, both client paths, portfolio and FX freshness checks, and the list of open items. [Launch commands and acceptance report](reports/14-delivery/README.md) · [Sources and redistribution scope](reports/14-delivery/DATA.md)

## Working files and V2 status

| File | Role and status |
|---|---|
| [Checklist](CHECKLIST.md) | Implementation plan and validation criteria. The audit of Sections 1 to 6 specifies the evidence by box and the verifications that are still open. |
| [Notebook](RiskMatch_V2.ipynb) | Client profiles, asset library, efficient frontier and nine multi-asset comparisons, including replay, scoring and blends. |
| [Inventory of methods](LIBRARY_METHODS.md) | Reference for historical calculations, econometrics and forecasts. |
| [Journal](JOURNAL.md) | Decisions, evidence and benchmarks of results by stage. |
| [Results and graphs](reports/README.md) | Index of figures and reports, available locally and in the GitHub repository of the V2. |
| [Historical references](reports/01-4-references/README.md) | 60/40 annual, buy and hold and liquidity CHF, with fees and compatibility on theoretical warrants. |
| [Requirements matrix](reports/01-5-exigences/README.md) | Dependencies and evidence per request, from design to follow-up. |
| [Portfolio application](app/questionnaire.py) | Animated client studio, individual research sheets, full-universe matching and simulated account tracking. |
| [US Shares in 2026](reports/actions-2026/README.md) | 3,129 complete individual history until October 30 and inventory of exceptions. |

## Closing a step

Work from the root of RiskMatch V2. After checking, check the checklist box, add the result and links to the notebook, and then record the result, its source and limitations in the log. Write PNG-published figures in `reports/<étape>/` with a legend, units and period, and add their link in the index. The tables can accompany the figures in the same folder.

Then create the commit and push the branch towards the [GitHub private repository RiskMatch V2](https://github.com/NvarMaley/RiskMatch-V2). Local files received, client data, secrets and licensed entries remain outside the publication. Figures from restricted data follow the same conditions for dissemination.

## Start the standalone project

Since this case, with Python 3.12:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
riskmatch-v2
python -m unittest discover -s tests
```

The base loads a game **illustrative** delivered in the package. He calculates monthly statistics in CHF for a share, obligation, ETF, vehicle on gold and cash, then a gross equi-weighted reference on common dates. The fictitious oil series serves as an example of a factor. Customization calculations, market data and tracking are detailed in the checklist.

To run the notebook from this folder, install `python -m pip install -e '.[notebook]'`, then run `jupyter execute RiskMatch_V2.ipynb`, or open with the core of this environment.

To load a previously standardized monthly data file, use `riskmatch-v2 --catalogue data/local/returns.csv --as-of 2025-06-30`. The CSV is waiting `date,asset_id,asset_class,role,return_chf,source`. The dates follow the ISO format, the total returns in CHF are decimals and the role is `instrument` or `factor`. The diagnosis rejects the title-date duplicates and declares the data provided by the user. See [game delivered](src/riskmatch_v2/demo/returns.csv) for the format. Integration of actual data will add controls on liquidity, freshness, availability and costs.

## Open the portfolio application

With Python 3.12, run the following in the V2 folder.

```sh
python -m pip install -e '.[catalogue,faisabilite,questionnaire]'
python -m riskmatch_v2.studio --port 8766
```

Open [RiskMatch locally](http://127.0.0.1:8766/). Start at the lagoon, enter the financial brief, then swipe the behavioural cards. The profile explains the inferred volatility band. Explore individual asset sheets, calculate and compare personalised portfolios, then confirm a single or blended match. Monitoring displays the account and the provenance of its marks. [Studio guide and screenshots](reports/studio/README.md) · [Allocation method](reports/studio/ALLOCATION.md)

Streamlit also serves the studio with `python -m streamlit run app/questionnaire.py`. To reproduce the earlier five-screen study, append `?view=research` to its URL. [Historical application study](reports/13-application/README.md)

## Optional historical audit of V1

| Question | What the V1 can do | Work V2 |
|---|---|---|
| What does this client want and can handle? | Input of flows, reserve, required return if data are sufficient, theoretical maintenance, aversion interval. | Confirm a **Acceptable exposure area**, its horizon and base, record separately wishes and firm constraints, then link the responses to the customer's allocations. |
| Does the project have only three strategies? | Eight methods are present on the border: cash, equiweighting, mix 60/40, two variants of minimum variance, risk parity, classic and robust optimizations. Three methods were the subject of the detailed backtest. The custom form offers classic and robust lenses. | Select comparators on a common basis and display two or three distinct alternatives per mandate where data permit. |
| What does "average" mean? | In the implementation table, 2.96%, 2.32% and 2.43% are the arithmetic averages of **seven net annual household returns**, for fixed mix, classic and robust 13 ETF. Every year the same capital goes back. In the border, the expected average of a portfolio is the sum of the estimated weighted returns, with the costs modelled. | Label any number with strategy, currency, estimation date, horizon, home/investment sleeve base and definition. Separately present compound growth achieved, historical arithmetic mean, future estimate and scenario result. |
| Is it already dynamic? | The search page recalculates weights on request with an earlier snapshot, mandate liquidity, excluded tickers and a maximum of 0, 4, 8, 12 or 16%. The persistent demo uses fictional prices and a typical home. | Allow for a free seizure of demand, manage the impossibility, compare several objectives on the same mandate and value the positions actually selected. |

The client assessment includes a written mandate, financial ability to bear losses, willingness to take risks, objectives, liquidity and constraints. An objective solution is compatible with this approach. These references inform the design of the prices prototype. [CFA Institute, customer suitability](https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-iii-c) · [CFA Institute, allocation by objectives](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/principles-asset-allocation) · [Operation of V1](https://github.com/NvarMaley/TindeRisk/tree/c3a1fdb/research/universe)

## 1. Transforming the interview into an explainable portrait

**Card route.** Show a statement or a choice by card. Sliding to the right or touching "Yes/J" accepts" records an agreement. Sliding to the left or touching "No / I refuse" records a refusal. "I don't know/pass" remains a separate answer. The same choices are available on the keyboard. The client can review and correct a response. Amounts and dates are entered in dedicated fields. The local questionnaire supports these gestures, editing and correction.

Bank V1 contains **60 cards**, including 15 communes, one catching up, 20 probes and 24 revivals. The prices includes no more than 25 active responses. The seven families cover the **understanding**, **comfort declared**, **arbitrage between certainty and risk**, **sensitivity to loss around a reference point**, **reaction to a decline**, **project flexibility** and **desired follow-up**. A proposed sale after a fall may indicate an imminent bill, discomfort or expectation of further decline. The function of the revivals is precisely to distinguish them. [The 60 questions and their interpretation](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/questions/GUIDE_DES_CARDS.md)

**Inferring risk aversion.** A client considers a fair gamble paying CHF 900 or CHF 1,200 on CHF 1,000. Its mean return is 5% and its variance is 0.0225. Under the one-year model U = μ − φσ²/2, preferring a certain CHF 1,020 (2%) gives φ ≥ 2 × (0.05 − 0.02) / 0.0225 ≈ 2.67. Preferring the same gamble to a certain CHF 1,000 (0%) gives φ ≤ 4.44. Together the choices imply 2.67 ≤ φ ≤ 4.44 for this stake and horizon. Other stakes or inconsistent answers can change the inference. [Questionnaire and card rules](reports/02-questionnaire/CARDS.md)

| Field of the portrait | Origin | Use |
|---|---|---|
| Return **desired** | Amount, range or preference expressed | Compare wait to market opportunities. |
| Return **necessary** | Nominal or real objective, inflation, date, contributions and withdrawals | Calculate the compound rate that finances the flows. Show also the shortfall in CHF and the editable parameters. |
| Will / aversion | Understood trade-offs, the φ interval and sensitivity to individual answers | Evaluate which compromises remain preferable to both. If the ranking changes or the estimates are too close, keep several options. |
| Loss capacity | Funds available, reserve, stability of contributions, compulsory expenditure and settlement | Protect the cash that's due before you allocate the rest. Measure the deficit if the maturity progresses or prices fall. |
| Exposure **Acceptable** | Confirmed choice after presentation of loss scenarios in CHF | Record investment sleeve or focus, currency, horizon, maximum or approximate target, range and uncertainty. |
| Performance and volatility **estimated** | Portfolio weight, expected returns, covariance, fees | Describe each proposal with its assumptions, appropriate range and funding risks. |

**Section 3 dialogue bands.** The annual volatility of the CHF investment sleeve is said to be very conservative from 0 to less than 4%, conservative from 4 to less than 8%, moderate from 8 to less than 12%, dynamic from 12 to less than 20% and very dynamic from 20% onwards. The client can also confirm a minimum risk, a ceiling, a free slice or remain undecided. The amounts of the portrait determine the examples in CHF. The customer can review his decision and the reasons for clarification before export. [Case, figure, limits and calculations](reports/03-portrait/README.md)

**Design questions for the portrait and confirmation of the slice.** "Is this figure a ceiling, a level you are looking to achieve, or do you want to compare losses in francs first?" "On what part of your assets?" "After this decrease, could you pay on the expected date? If the invoice is already covered, would you like to keep the position?""Do your job, other investments or expenses expose you to a sector, business, country or currency?""What concentration do you want to prohibit, and for what diversification would you accept a lower expected cost or return?""What environmental criterion does it matter to you, and what if data is missing?"Provide an unknown answer and a correction option for each.

## 2. Find portfolios corresponding to the mandate

1. **Protecting deadlines.** Build a calendar by objective and currency. Separate money available that day, market value and proceeds from a pending sale. An eight-year target with a bill next year requires at least two horizons.
2. **Calculate the eligible boundary.** Apply verifiable exclusions, issuer and sector ceilings, budget including fees and leverage rule. For a ceiling s, maximize the estimated net return under (wW) ≤ s. The robust method removes a penalty for poorly estimated averages. The market portfolio in the financial sense is weighted by capitalisation; the library of feasible combinations is called here **eligible package**, and its best envelope **efficient border**.
3. **Respond to exact demand.** A ceiling of 40% allows a solution of 18%. A target of 40% ± 2 points requires checking this range. With the V1 model on 30 October 2026, the 13 ETFs, at most 60% per instrument, 90% invested and the rest in CHF, the exploratory audit finds a maximum of about **21.16% on the investment sleeve**either **14.81 per cent on the household** when CHF 35,000 out of 50,000 are invested. The notebook prepares the repetition of the calculation with the 170 eligible summits. This boundary depends on data and constraints and does not limit the future volatility achieved. If the wish is inaccessible, show the level reached, deviation and solutions on date, target or input. Systematicly looking for the upper edge of risk could pose an unnecessary risk.
4. **Propose options that change the decision.** A: maximum estimated net return at the confirmed ceiling. B: Robust choice with an uncertainty penalty. C: a solution that is better distributed or less exposed to a chosen scenario, with comparable return/risk in a reported margin. Show next to an eligible fixed comparator (60/40 reduced if necessary) or eligible cash. If A and B are almost identical, merge them. An environmental option requires agreed metrics, sufficient coverage and compromises. Sharpe's ratio can inform choice, as well as concentration, cost and risk of falling under the need.
5. **Compare in francs on the right basis.** Example: CHF 50,000 of which 15,000 is reserved, so a investment sleeve of CHF 35,000 to 8% represents 5.6% volatility on the home if the reserve remains stable. A customer with the same aversion and a closer expense can have a much smaller investment sleeve. An annual arithmetic forecast and the necessary compound return over eight years require a comparison by dated trajectories and after fees.
6. **Save the decision.** For each option, keep instant, mandate version, units, costs, risk assumptions and client response. An alert may open a review. Present and modify on the same prices and flows, with the cost of coverage and the risk that it will not cover the intended danger. Obtain confirmation prior to any change.

**Compare client-side options.** Eligible allocations are matched with sub-scores for the objective, risk, diversification, validated forecasts and fees. The grid displays weights, raw results and cases where ranking is uncertain. The screen presents, among other things, the ring diagram composition, the return-volatility graph, historical curves, scenarios and differences between the current portfolio and a revision. See [checklist](CHECKLIST.md) in steps 6.6–6.7 and 13.7–13.8.

**Choose, combine and follow.** The client browses portfolio cards, opens their graphics, then chooses an option or assembles multiple allocations. It can enter their own weights or ask the engine for a combination according to its criterion, such as the Sharpe after costs or the estimated return in its slice. The V2 recalculates the positions, risk and expense on the complete mixture. The prototype adopts a Miami nocturnal pink, electric blue and purple identity, with an original 3D cherry. After simulated confirmation, a heart animation marks the match and gives access to the follow-up of the chosen composition. The route provides for reduced animations according to the user's preferences. See steps 6.8–6.9 and 13.9–13.11 of the [checklist](CHECKLIST.md).

## 3. Asset library and data to be obtained

**Access to data.** The V2 uses as a priority files provided locally and complete with verifiable public sources. The local history CRSP and Compustat can be analysed according to their usage conditions. No WRDS subscription is required.

**American investment universe.** The enlargement covers US equities and bonds, US exposure funds and U.S.-listed commodity vehicles. Cash flow and targets remain in CHF. The returns of the instruments in USD are converted into CHF to measure the risk and performance of the customer.

| Priority | Data or source | What they allow / condition of passage |
|---|---|---|
| Immediately | The 13 ETFs, change USD/CHF, WTI, copper, VIX, macro data and local vintages | Reproducible historical records, correlations, scenarios and benchmarks. Nine sectoral ETFs cover a portion of SPY. Count funds overestimate diversification if exposures repeat. |
| From the first calculation | US CRSP stocks already present until the end of 2025 | Accept all securities whose data and trading conditions pass the dated criteria. Compare over a common period and prepare the update for more recent proposals. Follow stock classes, radiation, spreads, liquidity and concentration at the issuer level. |
| Update 2026 without subscription | Local files provided, listing lists dated, public history or prices supplied, volume and total return | Control identity and securities transactions, test a period of overlap and exclude from the proposal securities whose recent data or marketability are not verifiable. [Nasdaq Trader Directory](https://www.nasdaqtrader.com/Trader.aspx?id=symbollookup) |
| If we rank on the quality of enterprises | Compustat and CCM links already provided locally, supplemented by the ESA EDGAR deposits dated | Base tests on figures available at the date of decision. Report variables whose publication and revisions are not traceable. [Official EDGAR API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) |
| Individual bonds | Local files, Treasury issues and public data FINRA according to coverage and entitlements | Check prices or transactions, coupons, deadlines, lots and settlement. The auction data identify the issues. For a proposal to date, verifiable pricing and negotiability are also required. Use eligible bond funds when direct securities lack data. [Treasury Fiscal Data](https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/) · [FINRA TRACE](https://syndication.finra.org/content/what-trace-and-how-can-it-help-me) |
| Environmental constraints and overlaps | Published historical positions, availability dates, issuer identifiers, activity and comparable emissions. US N-PORT if vehicle is covered | Display coverage by weight. A firm exclusion with unknown coverage suspends the proposal concerned. A "greener" classification requires an explicit criterion, unit, scope, year and source. [SEC N-PORT](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets) |
| Accessible sources without expensive terminal | EIA for Energy, FRED/ALFRED for publications and revisions, Cboe for VIX, GPR for geopolitical news | Check quotas, availability time, revisions, coverage and display rights per series. Academic, private and public rights are to be verified separately. For directly held gold or oil, specify the vehicle, storage or bearing and costs. [EIA](https://www.eia.gov/opendata/) · [ALFRED](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) · [Cboe](https://www.cboe.com/tradable_products/vix/vix_historical_data) · [GPR and vintages](https://www.matteoiacoviello.com/gpr.htm) |

**Perimeter of the first personalized calculation.** Invent all classes from the start and submit to the engine all eligible assets on the date of the mandate. The register shall give for each instrument its status, the missing data and the conditions for negotiation. The reference will be a fixed allocation defined in V2, assessed on the same schedule and with the same cost assumptions. The already known ETFs may enter the catalogue if the necessary data are available. For CRSP, test first at the last validated common date. For a more recent decision, check prices and change them on the new date. Keep data licensed in private storage and create a public demonstration that is fictitious or explicitly authorized.

## 4. Econometrics, scenarios and forecasting

The [directory of library methods](LIBRARY_METHODS.md) connects each tool to prices, application and expected control.

**Minimum historical record.** In CHF, publish average return per session, annualized return arithmetic, compound return, variance/volatility, maximum loss from a peak, recovery time (or "still below the top"), extreme losses and actual losses. Provide windows of 1, 3, 5 and 10 years according to availability and measurements made on the horizons of the client. Compare assets and warrants after exchange and fees to common dates. For a portfolio, calculate w′的w, rolling correlations, risk contributions, weight per issuer/sector/currency and overlap. Distinguish weights fixed before the episode and current weight projection on an old crisis. Avoid multiplying a daily average by the number of days to describe the final richness.

**Oil exposure.** Section 8 compares increases and decreases in the WTI spot price separately across prior volatility regimes. On the latest 248 common sessions, XLE's CHF return has a Pearson correlation of 0.535 with the daily change in WTI. Holding market, dollar and rate moves fixed, the estimated response to a USD 10/barrel rise is +1.85%, with a 95% coefficient interval of +1.16% to +2.54%. Each of the five portfolio-level moving-block intervals includes zero. [Results, uncertainty and constituent coverage](reports/08-chocs/README.md)

**For tomorrow.** Separate the scenario ("oil +10 USD", "rate +100 bp", "dollar -5%"), conditional change in portfolio, accuracy of estimate and probability of occurrence. Encrypt an impact with dated regression or reclamation of flows, test interactions and crisis samples. Do not add three related alerts as three independent events. Use consistent joint scenarios. Publish a probability only for a defined event and a precise timeline, with chronological calibration and sufficient achievements. A rare war or a "bubble" can remain a documented stress or alert. An extreme recovery indicator uses a dated percentile, lever measure or momentum dependence; its past frequency does not give a turnaround date. The GPR index measures an intensity of new geopolitics. [Original GPR search](https://pubs.aeaweb.org/doi/10.1257/aer.20191823)

**Role of the ML.** The allowance solver responds to the mandate on the basis of available estimates. Supervised learning is possible upstream to predict a defined variance or surplus return. Compare historical mean, stabilized covariance and exponential volatility to regularized regression, then eventually to a boosted tree. Train and select exclusively on the past, purge overlapping targets, freeze the model before evaluation, compare after cost with a simple reference. Control return error, loss of variance forecast, interval coverage and economic value. V1 has already found monthly intervals targeting 80% that cover only 65.9% (bonds) and 70.7% (shares) of their references. A sentiment indicator can remain descriptive if its gain disappears over another period. Black–Litterman will have an opinion only if its horizon, uncertainty and validation are justified. [Evaluation of forecasts V1](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/research/experiments/README.md) · [Signals and limits](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/research/robustness/README.md)

## 5. Feasibility and order of implementation

| Lot | Difficulty/dependence | Verifiable |
|---|---|---|
| Portrait, feasibility CHF, all eligible assets and fixed/personalized comparison | Local data are used to prepare the calculation. The actual usable coverage will be measured during the inventory. | Two clients with the same answers but with different deadlines get appropriate amounts. An impossible target produces an explicit gap and alternatives. |
| Asset cards, portfolio risks and multi-year objectives | Feasible offline, with conventions, dates and gaps management. | Sheets by asset and portfolio, oil exposure with staff, financing and cost by date, crisis recovery documented. |
| Individual securities from inventory | Check CRSP returns, rates, coupons and bond trading rules, and then search for a public source or qualify a complementary local file. | Eligible shares and bonds included in the calculation on validation, with class-verifiable coverage and exclusions. |
| Signs, blankets and durable preferences | Conditional search. A conclusive comparison is never presumed. | Show multiple eligible options, including maintenance, and remove a tag or signal if coverage or validation fails. |
| Tracking | A closing update is the first realistic service. The intraday requires an authorized, synchronised flow and exchange, a query budget and a management of interruptions. | Value, non-contribution performance, freshness, estimated cost of change, new version of mandate and consent. If the change is expired, suspend the proposal. |
| Promises to be ruled out | Universally perfect portfolio, reliable forecasting of every crisis, validated behavioral profile without observations, complete ESG rating without positions and metrics, guaranteed free universal real time. | Instead: possibilities under assumptions, intervals, "unknown/unrealizable" states, last reliable prices and customer choice. |

**Anchoring in class.** QARM2 LN3 for timing uncertainty, LN4 for Black–Litterman opinions, LN5–LN6 for risk contribution and diversification. Local methodological guides 04, 07, 16, 21 and 34 cover portfolio constraints, production data, customer arbitrations, confirmed review and household capacity respectively. The first V2 version to target is a **CHF end-of-day comparison service** with several dated goals and portfolios actually different per customer. The remaining decisions and tests are included in the [checklist execution](CHECKLIST.md).
