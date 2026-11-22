# Local research data · import check of 22 November 2026

The new workspace contains raw exports, prepared tables and earlier research outputs. The [checklist](../CHECKLIST.md) defines study eligibility and the acceptance criteria. Start with the raw input and decision timestamp when adapting an older result. Preserve the import intact and give subsequent transformations a separate version.

## What the current check establishes

| Local input | Verified here | Decision and remaining work |
|---|---|---|
| Adjusted ETF prices and prepared returns | 13 series, 5,505 distinct ordered sessions from 2005-01-03 to 2026-11-18. All prices were finite and positive. All 5,504 daily return rows reconciled by date and ticker to the prepared Parquet panel from CSV prices without filling. | Ready for historical benchmark exploration, H01/H02 design and a first frontier fixture. Reconcile corporate actions, trading calendars, eligibility and executable quotes before a performance claim. These instruments do not define the client catalogue. |
| Macro and FX | All eight latest-vintage FRED CSVs matched the public-phase manifest. All 786 decompressed ALFRED snapshots matched their manifest for CPIAUCSL, INDPRO and UNRATE. Latest-vintage files include DEXSZUS (CHF per USD), Treasury/real yields, breakevens, broad USD, oil and copper. Additional FRED files include DTB3, VIX and credit/curve indicators. | Start the H03 dated panel. ALFRED is daily-resolution vintage evidence. Enforce availability before decision, preserve gaps and distinguish observations from carries. H04 still needs a dated valuation predictor if testing that variant. Identify a currency-matched CHF cash input or disclose a cash assumption. |
| WRDS and factors | All four raw WRDS exports matched the WRDS rows in the supplied manifest: daily and monthly CRSP, Compustat annual fundamentals and CCM link history. The prepared monthly panel's Parquet metadata reports 2,607,985 rows. Daily CRSP has bid/ask fields. Local factor archives include Fama–French five factors, momentum and other candidate factors. | H05 inputs are present. Check firm-month uniqueness, inactive securities, CIZ return conventions, link validity, reporting dates and restatements. The annual fundamentals header includes fiscal dates; actual filing availability needs separate evidence. Validate bid/ask quality before estimating costs. The row count is a structural check, not a replication of the panel. |
| Course sentiment, GICS and FOMC | The lab CSV matched its pilot fingerprint. Course pickle files and the GICS archive are present. In the imported sector table, 3,689 of 30,082 firm-days carry an effective match and zero carry a populated publication-verified sector field. FOMC statements and baseline files are present. | Reproduce the LN7 event study separately. Company-derived sector views remain gated on dated links and coverage. The imported collection audit reports 86 FOMC documents; verify original publication timestamps before prediction. |
| Execution and net performance | Processed holdings, monthly costs, signals, leg and net-return tables are present under additional_data/clean. The ETF event files and historical CHF walkthrough are dated local artifacts. | Rebuild entries from drifted units, currency, fees and next eligible fills. Actual client fees, fill history, private-data display rights and a production closing feed are unverified. |
| Profile | The inherited pilot manifest references two unavailable files: questions/bank.json and questions/transfer_validation.json. The design specification exists in this workspace. | Author and version the new bank and held-out choices. Do not use old questionnaire hashes to certify new items. Human pilot and retest evidence remain outstanding. |

## Inputs for the robust-frontier comparison

Start with a registered subset of the reconciled ETF panel, such as SPY, IEF and GLD. Join dated DEXSZUS observations for a CHF mandate with a documented missing-quote rule. Estimate return covariance and the sampling covariance of mean estimates separately on each training window. Both allocation arms use the same information cutoff, asset set, risk caps, funding, cost assumptions and eligible execution dates. For the reverse stress record the due amount, accessible CHF reserve, saleable assets and settlement date. Historical net results and shock probabilities require further validation.

## Reproduce the receipt check

From the repository root in a Python 3.12 environment, run:

```sh
python -m pip install -r requirements-data.txt
python research/verify_import.py
```

The command reads local files and prints a JSON summary. It checks SHA-256 fingerprints for the pilot data entries, FRED exports, decompressed ALFRED files and four WRDS extracts. It reconciles raw ETF returns with the prepared panel, reads the WRDS panel footer, and counts fields in the imported sector table. All eleven data entries of the thirteen-entry pilot manifest matched at receipt. The other two entries identify historical questionnaire versions. The verifier reports these names separately and leaves validation of newly authored cards to the profile tests. No data fingerprint mismatch was found in the tested scope. Reruns may hydrate cloud-backed files and must read the large WRDS CSVs. The main notebook remains usable without this private pack. Neither this script nor the notebook recreates every legacy derived dataset.

## Interpretation and sharing

- The earlier data notes report 48,506 accounting availability dates later than the decision session, including 11,983 investable rows, and 122,861 same-date rows without a timestamp. They also report 28 missing FX pairs in a 1,510-pair pilot. These are historical findings to reproduce on explicitly defined study windows.
- `data/demo/market_bundle.json` is labeled synthetic. `data/demo/chf_walkthrough.json` uses historical inputs and stays local. Keep WRDS, laboratory data, course materials and derived historical outputs outside the future public Git tree pending rights review.
- The first data release should retain query, vintage, schema, units, hashes, calendar, chronology tests, attrition by date and asset, and provider display rights. Freeze the analytical sample only after those checks. Imported backtests and ready-made net returns belong to development history.
