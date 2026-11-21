# RiskMatch

RiskMatch is an English-language web app for a person investing toward a specific goal. Its purpose is to show which combinations of net return and risk are feasible for that person, what could go wrong, and how a chosen allocation performs over time. The client profile is available now. Portfolio comparison and monitoring are in development.

1. **Establish the client profile.** Four short intake screens capture the goal, spending currency, horizon, contributions, withdrawals, desired return and constraints, including ethical exclusions. Then the client swipes on one statement at a time. The bank contains 60 scenarios, including a common core of 15. Follow-ups clarify uncertain choices or repeated behavior. The profile estimates a range of risk aversion (φ) and separately assesses the household’s capacity to absorb losses. The design target is 5–10 minutes for a typical visit, with roughly 20–25 scenarios. Duration and band calibration await participant testing. [Profile specification](CLIENT_PROFILE.md) · [Card and routing tables](questions/CARD_REVIEW.md)
2. **Research and compare feasible portfolios.** Replicate published studies and QARM labs, then test adaptations on study-specific assets. Historical analysis measures returns, volatility, drawdowns and dependence during shocks. Forecasts give dated ranges for a stated horizon and are checked against subsequent outcomes. Macro scenarios apply across allocations. Econometric and machine-learning candidates are evaluated against simple benchmarks using information available at the decision date. Sweep risk budgets to estimate the feasible frontier after modeled costs in the client’s currency. Compare allocations across the client’s plausible φ range after protecting withdrawals and applying constraints. Show the desired return, the return needed to fund the goal, and the evidence for each feasible option. A funding shortfall is a possible result. [Research protocol](RESEARCH.md)
3. **Monitor the selected allocation.** Show value, cash flows, net performance, drawdown and risk since selection in charts with dated observations. When circumstances or exposures change, explain the proposed reallocation, its expected costs and the effect on the goal. The client confirms the change. The first monitoring version is designed for closing prices. Intraday updates depend on an authorized timestamped feed.

## Run the client profile web app

From the repository root, run the following in a Python 3.12 environment. Open the local URL printed by Streamlit in a browser. Clients on a hosted instance would only need the URL. This version runs locally for review.

```sh
python -m pip install -r requirements-app.txt
python -m streamlit run streamlit_app.py
```

Choose **Use the CHF example** to try the four intake screens with a fictional goal, or enter a different mandate. Each card presents one statement. Swipe right for yes or left for no. On a computer, drag the card or use the arrow keys. A short gesture returns the card to its place. Pass if unsure. After the last card, review the tolerance range, reserve, available growth capital, constraints and monitoring preference. You can correct an answer, confirm the profile or download a local JSON file and restore it in a new browser session. The profile runs independently of the private market datasets.

The optional pilot adds four held-out choices before revealing the score. Instructions for the participant split, retest and outcome measures are in the [client profile specification](CLIENT_PROFILE.md#running-the-pilot). The web app currently ends at profile review. Portfolio selection and monitoring are subsequent product phases.

Portfolio methods are candidates for the research comparison. Macro scenarios apply across allocations. A strategy that changes risk budgets by market regime is an optional extension. The final catalogue depends on out-of-sample performance after costs and compatibility with the client’s mandate.

The archived market panel has 13 ETF price series including SPY. The three-ETF benchmark uses SPY, IEF and GLD. Each research study defines its own holdings, predictors and comparison dates; the client catalogue includes only allocations supported by those results and the client’s constraints. [Research and allocation checklist](CHECKLIST.md#phase-2--research-and-compare-feasible-allocations)

## Team setup

The [Step 0 handoff](SETUP.md) covers the shared Python 3.12 environment, lab reproduction commands, research registry, review rules and outstanding team decisions.

## Current work

The English profile web app and its 60-card bank are implemented and tested with simulated routes. The local research replays contain portfolio checks, a descriptive StockTwits study and a common interest-rate shock applied to five allocations. The human pilot, full out-of-sample comparisons and catalogue validation remain open. [Card bank](questions/bank.json) · [Project checklist](CHECKLIST.md)

The three ETF benchmarks have monthly development backtests and a prospective evaluation schedule. The historical notebook also replays a CHF withdrawal using historical USD/CHF quotes. The first reproducible scenario connects the profile to an equity, bond and gold comparison and a dated withdrawal need. Negative research results belong in the record. [Benchmark schedule](RESEARCH.md#etf-benchmark-schedule) · [Local historical replays](RiskMatch_research_replays.ipynb)

The allocation sensitivity pilot examines three risk-aversion values, two covariance estimators and four review policies. The local sensitivity experiments report weight intervals, simulated fees, volatility-cap breaches and capital left after withdrawal. The illustrative 12% cap applies to the investable sleeve in CHF. Project-level risk includes reserves and removes the effect of external cash flows. [Frontier sensitivity](RESEARCH.md#frontier-sensitivity)

## Reproduce the notebook

From the repository root, create a Python 3.12 environment, install the pinned dependencies, and run the notebook in cell order with that environment’s kernel. The full financial run requires the local market and course datasets listed in the data inventory. Course links resolve when those original files are present. A fresh clone includes the card bank and synthetic market bundle. The primary notebook runs from a fresh clone using the interview engine and synthetic prices. The separate research notebook requires authorized local data. To rebuild the historical CHF walkthrough with the authorized input files, run `python -m riskmatch.catalogue`. [Pilot requirements](requirements-pilot.txt) · [Execution notebook](RiskMatch_pipeline.ipynb)

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-pilot.txt
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 RiskMatch_pipeline.ipynb
```

The checklist identifies possible biases, how to measure their effects and what to do when a check fails. The data inventory covers raw inputs, vintages and attrition. The research protocol maps the 34 available numbered chapter guides to project decisions and the checklist covers the seven QARM II notes. [Data inventory](data/README_data.md) · [Research protocol](RESEARCH.md) · [Decision journal](DECISION_LOG.md)

The available QARM brief is dated 2024. It calls for course-based portfolio optimization, GitHub code, a Streamlit application and a 15-minute client pitch. The team’s archived summary of the professor’s November 17 reply confirms that the 2024 guidelines still apply. Original teaching and data files retain their supplied filenames and contents. [Local course brief](<Theory/Quant_Project/Project_Brief/QARM_2_Slides___Projects.pdf>)
