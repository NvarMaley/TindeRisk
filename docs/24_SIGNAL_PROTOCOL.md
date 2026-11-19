# Step 4.5 — Signal protocol v1

Frozen on 2026-11-19 for development and exploratory validation. This record
preserves the recipes, comparisons and eligibility rules below. The project
final-test boundary remains unset. The legacy notebook contains comparisons
using future returns across the original sample, so this freeze cannot make
those periods untouched. See the [experiment log](06_EXPERIMENT_LOG.md) and
[holdout audit](13_EXPECTED_RETURNS.md#choice-and-scope).

## Fixed definitions

| Signal | Definition and timing | Status at the freeze |
|---|---|---|
| LN7 company event signal | Use the instructor's aligned data. Fit the return, polarity and message-volume market models and compare reconstructed events and CAR/CAP with the lab. See the [LN7 lab protocol](../data/README_data.md#ln7-lab-reproduction). | The SPY reference matched 5/5. The original Moodle files are pending. |
| Company-derived sector polarity | Require effective and available historical GICS classifications on message dates. Pool bullish and bearish counts across matched companies, then compute their difference divided by their sum. Group by next-session availability month. The monthly signal becomes usable in the first NYSE session of the following month. See the [sector definition](../data/README_data.md#company-derived-sector-sentiment). | Research candidate. Historical mapping and the sector test are pending. |
| Direct ETF tags | Use explicit ETF tags, the same pooled count formula and the same availability-month rule. Keep results labelled as direct ETF evidence. | Exploratory validation on 2016–2017 gave lower MAE for 4/9 ETFs and 0/8 Holm-adjusted rank comparisons below 5%. No view approved. |
| Black–Litterman | A validated sector score picks the strongest and weakest eligible sectors on the same dated snapshot, with +1/−1 exposures. Calibrate Q on completed months before the decision and final-test boundary. Require consistent positive direction and lower validation MAE than the zero-spread benchmark. Estimate Ω from frozen-training forecast validation MSE with the prior-variance floor. See [P, Q and Ω](03_METHODOLOGY.md#71-relative-view-matrix). | Zero active views. The no-view specification uses the ERC equilibrium prior. |
| FOMC tone | For each dated statement, divide hawkish minus dovish sentences by total sentences, including neutral. Use the next NYSE session for availability. The pinned FOMC-RoBERTa checkpoint is the planned classifier. See [FOMC data](../data/README_data.md#fomc-statement-tone). | The offline TF–IDF baseline is descriptive. Official classification and market validation are pending. |
| Macro HMM | Use the six lagged FRED features at completed NYSE month-ends. Four diagonal Gaussian states won the exploratory BIC comparison. Refit the scaler and HMM on the expanding prefix, filter through the current observation, and use the probability vector from the next NYSE session. See the [macro methodology](03_METHODOLOGY.md#86-regimes). | Exploratory latest-vintage fit. Historical vintages and the static/GMM comparison are pending. |

Missing and undefined scores remain missing. The asset calendar is independent
of signal coverage.

## Next StockTwits comparison

The [E014 entry](06_EXPERIMENT_LOG.md) preregisters the company-derived
**raw polarity** test. Align eligible sector ETF returns with the first close
through the last close of the following month. Choose the unique highest and
lowest available sector polarity before that holding window, with at least
two covered sectors. The primary outcome is the mean monthly spread of the
high-polarity ETF over the low-polarity ETF, against zero. Report eligible
months, coverage, and the direction separately in training and later
validation. Apply the existing 4.3b stability checks before proceeding to
view calibration. An abnormal-polarity sector candidate needs its own
preregistered definition and evidence before it can supply production views.

## Release conditions

Before the final comparison, record the 0.11 data split, exact input hashes
and the chosen protocol revision in the experiment log. Classify a run as
exploratory when the legacy analysis has already exposed its outcomes.
Report historical coverage limits and the no-view periods on the same market
calendar. Any method changed after viewing outcomes gets a new log entry
and keeps its exploratory status.
