# RiskMatch

RiskMatch maps the portfolios a client can consider for a particular goal. The client states their target return, horizon, withdrawals and constraints. The application is designed to estimate risk tolerance, calculate a return–risk frontier after modeled costs in the client’s currency, and show which allocations fit the mandate. Historical returns, dated forecasts and the return needed to fund the goal are separate outputs.

1. **Client profile.** Four short intake screens precede a bank of 60 cards. Fifteen form the common core. Earlier answers determine which follow-up cards appear. The pilot targets roughly 20–25 cards and measures the time people actually take. Financial capacity, estimated risk aversion and monitoring preferences are recorded separately. [Client profile specification](CLIENT_PROFILE.md)
2. **Research and portfolio choice.** Replicate published studies and course labs, then test adaptations on ETFs and WRDS equities. Compare macroeconomic exposures, historical losses, forecasts and uncertainty across allocations in the same risk band. Out-of-sample evidence, implementation costs and data coverage determine which models enter the catalogue. [Research protocol](RESEARCH.md)
3. **Monitoring.** After selection, track portfolio value, cash flows, losses and the risk band. Explain the reason for a proposed rebalance and its cost. Start with dated closing prices. Live monitoring depends on the available feed.

## Run the client profile web app

From the repository root, run the following in a Python 3.12 environment. Open the local URL printed by Streamlit in a browser. Clients on a hosted instance would only need the URL. This version runs locally for review.

```sh
python -m pip install -r requirements-app.txt
python -m streamlit run streamlit_app.py
```

Choose **Use the CHF example** to try the four intake screens with a fictional goal, or enter a different mandate. Each card presents one statement. Swipe right for yes or left for no. On a computer, drag the card or use the arrow keys. A short gesture returns the card to its place. Pass if unsure. After the last card, review the tolerance range, reserve, available growth capital, constraints and monitoring preference. You can correct an answer, confirm the profile or download a local JSON file and restore it in a new browser session. The profile runs independently of the private market datasets.

The optional pilot adds four held-out choices before revealing the score. Instructions for the participant split, retest and outcome measures are in the [client profile specification](CLIENT_PROFILE.md#running-the-pilot). The web app currently ends at profile review. Portfolio selection and monitoring are subsequent product phases.

Portfolio methods are candidates for the research comparison. Macro scenarios apply across allocations. A strategy that changes risk budgets by market regime is an optional extension. The final catalogue depends on out-of-sample performance after costs and compatibility with the client’s mandate.

The archived market panel has 13 ETF price series including SPY. The three-ETF benchmark uses SPY, IEF and GLD. Each research study defines its own holdings, predictors and comparison dates; the client catalogue includes only allocations supported by those results and the client’s constraints. [Scope by step](CHECKLIST.md#scope-by-technical-step)

## Team setup

The [Step 0 handoff](SETUP.md) covers the shared Python 3.12 environment, lab reproduction commands, research registry, review rules and outstanding team decisions.

## Current work

The English profile web app and its 60-card bank are implemented and tested with simulated routes. The notebook contains portfolio checks, a descriptive StockTwits study and a common interest-rate shock applied to five allocations. The human pilot, full out-of-sample comparisons and catalogue validation remain open. [Card bank](questions/bank.json) · [Project checklist](CHECKLIST.md)

The three ETF benchmarks have monthly development backtests and a prospective evaluation schedule. The notebook also replays a CHF withdrawal using historical USD/CHF quotes. The first reproducible scenario connects the profile to an equity, bond and gold comparison and a dated withdrawal need. Negative research results belong in the record. [Benchmark schedule](RESEARCH.md#etf-benchmark-schedule) · [First reproducible walkthrough](CHECKLIST.md#first-reproducible-walkthrough)

The allocation sensitivity pilot examines three risk-aversion values, two covariance estimators and four review policies. Steps 6 and 7 report weight intervals, simulated fees, volatility-cap breaches and capital left after withdrawal. The illustrative 12% cap applies to the investable sleeve in CHF. Project-level risk includes reserves and removes the effect of external cash flows. [Frontier sensitivity](RESEARCH.md#frontier-sensitivity)

## Reproduce the notebook

From the repository root, create a Python 3.12 environment, install the pinned dependencies, and run the notebook in cell order with that environment’s kernel. The full financial run requires the local market and course datasets listed in the data inventory. Course links resolve when those original files are present. A fresh clone includes the card bank and synthetic market bundle. Step 3.1d can verify the bank independently. To rebuild the historical CHF walkthrough with the authorized input files, run `python -m riskmatch.catalogue`. [Pilot requirements](requirements-pilot.txt) · [Execution notebook](RiskMatch_pipeline.ipynb)

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-pilot.txt
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 RiskMatch_pipeline.ipynb
```

The checklist identifies possible biases, how to measure their effects and what to do when a check fails. The data inventory covers raw inputs, vintages and attrition. The research protocol maps the 34 available numbered chapter guides to project decisions and the checklist covers the seven QARM II notes. [Data inventory](data/README_data.md) · [Research protocol](RESEARCH.md) · [Decision journal](DECISION_LOG.md)

The available QARM brief is dated 2024. It calls for course-based portfolio optimization, GitHub code, a Streamlit application and a 15-minute client pitch. The team’s archived summary of the professor’s November 17 reply confirms that the 2024 guidelines still apply. Original teaching and data files retain their supplied filenames and contents. [Local course brief](<Theory/Quant_Project/Project_Brief/QARM_2_Slides___Projects.pdf>)
