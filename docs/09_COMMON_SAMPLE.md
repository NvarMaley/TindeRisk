# Common comparison sample — Step 1.11

Generate with `python -m src.build_common_sample` after the market and asset
sentiment builders. This step fixes comparable **input calendars**, not
portfolio results, a final holdout split or validated predictive signals.

## Prepared periods

The periods come from `validation.periods` in the shared configuration; dates
are not selected by inspecting performance. All configured core strategies
use the same market dates. On the 2026-11-18 build:

| Period | First session | Last completed session | Sessions |
|---|---|---|---|
| Main | 2010-01-04 | 2020-03-31 | 2,578 |
| Extended | 2009-01-02 | 2026-11-17 | 4,497 |

The extended end is deliberately rolling, not frozen. A session is included
only once its scheduled NYSE close has passed at build time. This removes
the current provisional session but is not independent vendor finality
certification. Version and freeze the actual files for presentation/final
evaluation; `validation.final_test_start` remains unset (Step 0.11).

## Estimation history

Every selected session has at least 756 strictly preceding daily returns
(three years × 252 sessions). The first main session has separate warm-up
returns from 2007-01-03 through 2009-12-31. The extended sample warm-up is
2005-12-30 through 2008-12-31. At later dates, obtain the trailing window from
past warm-up and sample returns only; never include the decision-day return
in a decision made before that return is earned. Backtest decision/execution
timing remains to implement in Steps 6.1, 6.7 and 6.10.

## Sentiment arrivals and missing views

Counts are summed by **availability session and asset**, then polarity is
recomputed from the summed bullish/bearish counts. Friday/weekend/holiday
messages can arrive together. Averaging daily polarities would give unequal
message counts inappropriate equal weights.

The builder exports separate matrices for polarity, total messages, observed
arrivals, and nonmissing polarity. Missing arrival is not neutral sentiment;
messages with no bullish/bearish labels have undefined polarity. Neither is
forward-filled. No market session is dropped because sentiment is absent:
otherwise sentiment coverage could alter the comparison calendar in hindsight.

The last message date in the current source is 2020-03-23; those messages become
usable on 2020-03-24. Five main-period sessions have no labelled sentiment on
any asset. Coverage varies by asset (IEF: 1,697 sessions with labelled arrivals
in the main sample). This is availability, **not proof of sufficient volume,
predictiveness or view eligibility**. Missing observations do not prove that
there were no messages in the original universe.

Before **4.3c/4.6**, choose and validate confidence/volume thresholds, signal
history and any permitted signal age. Before **5.3/6.1**, implement the
no-view ERC anchor or validated view subset explicitly; this builder does not
execute that fallback. Step 4.9 limits historical sentiment to 31 March
2020, inclusive, on both message and availability dates. The extended
sample retains all later market sessions with missing sentiment. A monthly
score first usable in April falls outside coverage.
[Coverage decision](05_DECISIONS.md#dr-06--stocktwits-coverage).

Company-derived sentiment remains deferred behind
[1.4b/4.1c](../CHECKLIST.md#gics-dependency). Rebuild this sample and reconsider
signal coverage when that input changes. Market-only baselines can proceed.
The [cash-rate timing and accrual gate](08_DATA_CONVENTIONS.md#risk-free-proxy-explicit-approximation)
also remains necessary before final backtesting.

## Local artifacts and reproducibility

- `common_main_*.parquet` and `common_extended_*.parquet`: common-date prices,
  returns, log returns, excess returns, risk-free rate and macro values;
  separate warm-up returns and sentiment matrices.
- `series_coverage.csv`: first/last valid observation and count for each
  original market artifact/series.
- `common_sample_manifest.json`: requested and actual periods, per-asset
  sentiment source starts/ends and available dates, observed signal coverage,
  input/output SHA-256 hashes and remaining dependencies.

Generated files stay ignored by Git; the builder, tests and this specification
are versioned. To reproduce, regenerate the source bundle or use the exact
source artifacts identified by the manifest hashes. A fresh download may be
revised by the provider; hashes make such changes visible.
