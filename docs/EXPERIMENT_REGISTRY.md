# Experiment and Data Registry

Each research run uses a unique `run_id` (UTC date/time + ticket + short random identifier), schema version and model version. Record the Git commit, dependency lock digest, dataset version/hash and decision-time cutoff, seed, split boundaries, instrument IDs, return frequency, currency and units, assumptions, metrics and warnings. Keep records of failed and rejected experiments. Store only synthetic or redistribution-authorized results in Git; keep licensed data, derived proprietary outputs and client records local.

| Run ID | Ticket | Data | Evidence | Status |
|---|---|---|---|---|
| 20261124-infra01-local | INFRA.01 | Synthetic tests; environment only | Python 3.12; requirements.lock; 13 Python and 5 Node tests passed; 8 synthetic notebook cells executed | Local installation verified |
| 20261124-contracts-local | SYS.01–02 | Synthetic fixture | tests/unit/test_contracts.py; notebook g00-contract-demo | Contract and fail-closed registry checks passed; no model approved |
| 20261124-mandate-local | CH01.01–15 | configs/mandate-example.json (fictional) | notebook chapter 01; unit, loopback HTTP, Web confirmation tests | Deterministic mandate validated; no suitability or market feasibility claim |
| 20261124-discovery-local | CH02.01–15, CH02.21 | Synthetic card/response fixtures; seed 42 | notebook chapter 02; bank, quota, score, likelihood, HTTP and UI tests | Experimental implementation; human validation pending |
| 20261124-pilot-readiness | CH02.16–20 | Artificial complete anchor panel; not volunteers | pilot_analysis.py; draft protocol; synthetic test/retest and held-out logistic metrics | Synthetic dry run only; actual pilot pending |
| 20261124-universe-local | CH03.01–04, CH03.09–11 | Public issuer metadata; synthetic coverage fixture; local receipt summary only | `security_master.py`, catalog, unit/HTTP/UI tests, notebook chapter 03 | Candidate catalog and checks ready; raw price coverage, PIT holdings and actual liquidity pending |
| 20261124-source-coverage | CH03–04 | Local CRSP monthly/daily extracts; official Treasury/FRED and issuer snapshots | Acquisition/monitoring plans, local receipt hashes, provider contracts, synthetic tests | 22 ETF historical daily/monthly series; current issuer snapshots fail strict money-market rule; direct Treasury identity only; no allocation approved |

Use `data/raw/` for immutable authorized sources, `data/processed/` for versioned transformations and `data/features/` for derived features. Keep dataset license and provenance metadata local if identifying restricted contents. Shared tests must use synthetic fixtures or licensed redistributable examples, never require a WRDS account. Logical data versions are content hashes plus cutoff and transformation version. Never log passwords, tokens, client identities or raw client responses.
