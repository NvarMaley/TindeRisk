# RiskMatch

RiskMatch maps the portfolios a client can consider for a particular goal. The client states their target return, horizon, withdrawals and constraints. The application is designed to estimate risk tolerance, calculate a return–risk frontier after modeled costs in the client’s currency, and show which allocations fit the mandate. Historical returns, dated forecasts and the return needed to fund the goal are separate outputs.

1. **Client profile.** Four short intake screens precede a bank of 60 cards. Fifteen form the common core. Earlier answers determine which follow-up cards appear. The pilot targets roughly 20–25 cards and measures the time people actually take. Financial capacity, estimated risk aversion and monitoring preferences are recorded separately. [Client profile specification](CLIENT_PROFILE.md)
2. **Research and portfolio choice.** Replicate published studies and course labs, then test adaptations on ETFs and WRDS equities. Compare macroeconomic exposures, historical losses, forecasts and uncertainty across allocations in the same risk band. Out-of-sample evidence, implementation costs and data coverage determine which models enter the catalogue. [Research protocol](RESEARCH.md)
3. **Monitoring.** After selection, track portfolio value, cash flows, losses and the risk band. Explain the reason for a proposed rebalance and its cost. Start with dated closing prices. Live monitoring depends on the available feed.

## Team setup

The [Step 0 handoff](SETUP.md) covers the shared Python 3.12 environment, lab reproduction commands, research registry, review rules and outstanding team decisions.

## Current work

The English card bank is ready for piloting. The notebook contains portfolio checks, a descriptive StockTwits study and a common interest-rate shock applied to five allocations. The human pilot, full out-of-sample comparisons and catalogue validation remain open. [Card bank](questions/bank.json) · [Project checklist](CHECKLIST.md)

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

The available QARM brief is dated 2024. It calls for course-based portfolio optimization, GitHub code, a Streamlit application and a 15-minute client pitch. The archived November 17 instructor reply confirms the 2024 guidelines. Original teaching and data files retain their supplied filenames and contents. [Local course brief](<Theory/Quant_Project/Project_Brief/QARM_2_Slides___Projects.pdf>)
