# Chapter 25 — Research kickoff

Started 2026-11-25 in research mode. Formal acceptance is pending the Chapter 25 dependency gates. The reference below is fixed by simplicity and data coverage, without ranking candidates by their observed returns.

## Provisional frozen reference (CH25.15)

- Reference: 60% SPY / 40% IEF, rebalanced on the Chapter 23 schedule. SPY buy-and-hold, cash and equal weight remain secondary comparators.
- Core USD run: `099ceda3c1c651997a4ee6d186e8cfcf93a9985192eecfb0b9ef33ece165a105` (`walk-forward-v3`).
- Matrix hash: `37c5e9a589e25fd8dd770a862d3eb3f0cd0fc02ed2a3067a0f2b592f067f74cf`.
- Local artifact: `data/processed/walk_forward/<run_id>.json`. Reuse its exact dated folds, returns, configuration and benchmark. Reject mismatched dates, data versions or execution assumptions.
- Rolling training: 36 months; validation: 12; step: 12; embargo: 1; execution delay: 1 month; transaction cost: 10 basis points under the Chapter 23 ledger convention.
- Development: 128 months from July 2011; previously examined holdout: 45 months from March 2022 through December 2025. Use exact intervals and four locked folds from the artifact rather than reconstructing calendar dates.
- Secondary universe sensitivity: USD cohort run `a5b3d3c049f567d5b20fb59ce7c3a9823a365ebb89f485e59ffc9c76f9aaa4c5`, 30 development months and 20 holdout months. Compare within its own aligned timeline and do not pool it with the core results.

The core artifact contains 38 computed experimental strategies. The reference's reported holdout CAGR is 8.06%, annualized volatility 11.98% and maximum drawdown 16.32%. Its monthly ES95 is unavailable in the source. These are historical research outputs, subject to the existing ledger and data limitations.

## Evaluation order

1. Run paired changes to covariance, return estimates, concentration, turnover, factors and robustness on development folds, controlling all other inputs. Record unavailable inputs and infeasibility.
2. Compare net return, risk, turnover, stress, goal shortfall and uncertainty against the fixed reference; report each change separately before ensembles. Retain simpler specifications where evidence is insufficient.
3. Use the existing holdout for descriptive retrospective comparison only, since its results have already been examined. Independent confirmation requires a new untouched evaluation window or an independently documented prospective protocol.
4. Finalize eligible candidate registry only after the formal prerequisites and independent validation are satisfied. Then build matching and multi-Match allocation according to [PORTFOLIO_MATCHING.md](PORTFOLIO_MATCHING.md).

## Readiness

### Executed paired experiments

The frozen USD folds were replayed with the chapter 23 delayed transaction ledger. The reference model uses historical means, Ledoit–Wolf covariance, a 65% position cap and a variance penalty of three. The table gives annualized paired arithmetic return differences on the previously examined 45-month test period. Turnover uses the full out-of-sample ledger.

| Single change | Return change vs model | Test volatility | Annual turnover |
|---|---:|---:|---:|
| Reference model | 0.00 pp | 11.41% | 14.85% |
| Empirical covariance | −0.49 pp | 10.96% | 16.27% |
| EWMA expected return | −0.71 pp | 11.13% | 26.81% |
| 40% position cap | −2.56 pp | 9.17% | 16.19% |
| L1 penalty on target changes | +0.60 pp | 11.74% | 12.55% |
| Mean reduced by one estimated standard error | −4.23 pp | 7.26% | 32.45% |

The turnover penalty reduces trading in this replay and increases test volatility. Keep the reference model for subsequent comparisons. Promotion requires evidence covering additional periods and stress conditions. The API returns joint moving-block uncertainty estimates alongside these measurements.

CH25.15 still depends on CH08.11, CH12.10, CH15.09, CH20.16, CH24.12 and G07. Existing modules and experimental reports allow preparatory research, but unknown mandate constraints, historical investability, executable futures/bond data, dated rolling forecasts and independent acceptance remain limitations. No candidate is promoted to validated by this kickoff.
