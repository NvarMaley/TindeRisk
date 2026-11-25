# Chapter 27 — Integration and validation

## Local paper workflow

Mandate → Discovery → Explore → My Matches → Confirm paper allocation → Dynamic management → Choose a policy → Export paper simulation ZIP.

The server reconstructs the Chapter 25 allocation and the Chapter 26 ledger from its frozen local inputs for every export. The selected policy must be computed over all expected dates. The validator checks capital continuity, cash flows, fees, P&L, funded weights, positions, transaction fees, return calculations and modeled stress limits. Infeasible or incomplete simulations do not produce an export. The result is deterministic for identical inputs and research versions.

| File | Meaning |
|---|---|
| weights.csv | Executed sleeve weights for each period |
| positions.csv | Ending sleeve-account notionals in USD |
| trades.csv | Actual simulated signed sleeve transfers in USD |
| nav.csv | Opening value, external flows, fees, profit/loss, end value, time-weighted return and turnover |
| metrics.json | Policy performance and costs |
| exposures.csv | Chapter 25 selected basket look-through weights before dynamic overlay |
| scenarios.csv | Chapter 25 selected basket stress returns before dynamic overlay |
| assumptions.json | Configuration, model and archive versions, scope and units |
| ledger.json | Full period-level simulation ledger |
| audit.json | Reconciliation status and SHA-256 digest of each ledger row |
| sensitivity.json | Cost and frequency comparisons |
| manifest.json | Stable run identity and content hashes for every other file |

All results are local research exports. Sleeve notionals are abstract funded accounts. Individual purchase quantities, broker execution, settlement and live orders are unavailable. Downloads contain derived information about the fictional mandate's capital and flows. Keep them private.

## Save backups and recovery

The Saves screen offers a JSON backup of local encrypted entries and a restore option while locked. Imports merge by stable save ID and preserve existing entries. The original PIN or legacy passphrase is required to unlock an imported entry. The backup contains encrypted snapshots along with plaintext save names, IDs and encryption metadata. Four-digit PINs have a small search space and are suitable only for fictional local profiles. The project does not provide multi-user authentication or server-side account recovery.

## Validation protocol

Run the unit suite, browser interaction tests, notebook schema and checklist checks, dependency graph check and Git path exclusion check. CI replays the entire notebook in its portable mode; historical calculations are enabled explicitly for local replay. Chapter 25 and 26 historical examples require privately held data and run locally. Chapter 27 has a deterministic synthetic export example for CI. Local API handler tests can verify route responses and JSON contracts without opening sockets.

The project remains an academic paper-simulation prototype. Actual host browser rendering, production authorization, independent financial and behavioral review, legal/privacy assessment, data distribution rights and full mandate/universe coverage remain formal acceptance items. No order execution endpoint is provided.

## Local evidence (2026-11-25)

The 45-month historical 60/40 Mean Reversion / Black-Litterman MPC export returned HTTP-handler status 200 with a reconciled twelve-file ZIP. The unit suite passed 171 tests plus five subtests before the additional route test, which passed in the three-test export suite. All 33 browser interaction tests pass, and all 27 approved synthetic notebook cells execute directly in a Python namespace. Schema, checklist, DAG and tracked-path audits pass. The environment denied local port binding during the three HTTP integration tests and Jupyter kernel launch; those end-to-end transport tests still require host execution.
