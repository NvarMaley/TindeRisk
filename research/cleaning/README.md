# Historical data preparation v1

The [prepared release](../../data/prepared_v1/) freezes the data and eligibility rules for studies H01–H07. Use the [monthly sample manifest](../../data/prepared_v1/samples.parquet) before fitting a model. It retains months with missing inputs and distinguishes information available at the decision from coverage measured after the holding month. No broker executions or investment performance are reported here.

## Sessions, prices and currency

The market table has one row per asset, venue session and adjustment snapshot. The historical chart identifies NASDAQ for IEF and TLT and NYSE Arca for the other funds. The pinned calendar library maps their regular US equity sessions to the same schedule. The code uses the schedule’s UTC open and close, including holidays, early closes and daylight-saving changes. The 13 adjusted prices dated 18 November 2026 came from a file retrieved at 16:07 UTC, before the 21:00 UTC close. They remain visible as raw values and are excluded from close-based returns. The dated chart archive serves as a later cross-check.

USD returns use adjacent sessions. CHF returns multiply the USD gross return by the change in CHF per USD. Both exchange-rate observations must be present. A reverse quote must be inverted first. For a 5% USD gain and a move from CHF 0.90 to CHF 0.882 per dollar the CHF gain is 2.9%. The 13 series contain 71,539 USD returns and 70,161 CHF returns. There are 5,397 complete CHF daily returns for SPY, IEF and GLD. Asset/year records expose missing marks, flat runs, duplicates and flags. An unchanged close can be genuine. The [FX sensitivity](../../data/prepared_v1/fx_alignment.csv) compares simultaneous and shifted returns on identical dates, then measures what carrying a missing fixing would change on the larger grid. A shift or a carry is used only in that diagnostic.

Returns more than eight scaled median absolute deviations from the asset/year median are flagged retrospectively. The exception table records original values, the retained or excluded value, recorded cash events and an independent calculation from chart closes plus distributions. There are 29 statistical flags. Two differences exceeding 10 bp also require source review, both on distribution dates (XLF on 19 September 2008 and XLE on 23 March 2020). The imported adjusted return is preserved with its discrepancy. Neither fund is in the registered three-ETF sleeve. The calculations use two extracts from the same vendor.

## Corporate actions, cash and exits

- **Split.** XLK split two-for-one on 5 December 2025. Both archived chart closes are already expressed on the same split basis. USD 146.6000 divided by USD 145.5350 gives a gain of about 0.732%. Applying another factor of two would double count the split. [Issuer split notice](https://www.ssga.com/us/en/institutional/library-content/products/fund-docs/etfs/us/information-schedules/select-sector-spdr-fund-share-splits-faq.pdf)
- **Distribution.** On 18 March 2005 SPY went from USD 119.36 to USD 118.54 and paid USD 0.467. The reconstructed total return is approximately −0.296%. The archived adjusted series gives −0.297%. Fund expenses already reflected in the fund return receive no second charge.
- **Delisting.** CRSP CIZ monthly total returns incorporate delisting returns where appropriate. Five daily returns for PERMNO 11300 in January 1998 compound to −6.63554%, within 0.00004 percentage points of the reported monthly return. The terminal table retains the vendor flag, end-month diagnostic and reported return. All 16,683 candidate terminal rows have a monthly return. A nonmissing monthly return alone does not prove receipt of the full exit proceeds. On 5,367 uncertain candidates (missing return, or flags N/M/P in the terminal set), additional shocks of −30% and −100% apply to remaining wealth in separate stress columns. No stress replaces an observed return. [CRSP CIZ guide](https://www.crsp.org/wp-content/uploads/guides/CRSP_US_Stock_%26_Indexes_Database_Guide_Flat_File_Format_2.0.pdf)
- **USD cash.** Price a hypothetical 91-day bill at 1 − discount × 91/360, then spread its maturity gross return over the actual calendar-day gap using the previous decision’s available rate. This proxy omits market repricing and rollover costs. The largest daily difference from simple discount-rate accrual is about 0.0443 bp. Observed CHF cash and client fee schedules are still missing. [US Treasury pricing convention](https://www.treasurydirect.gov/marketable-securities/understanding-pricing/)

## Which information was knowable?

All 786 ALFRED vintages retain their observation dates, vintage dates and assumed next-session availability. CPI and industrial production growth use two observations from the same vintage. Unemployment uses its level. The decision join chooses the latest eligible record strictly before the cutoff. Unknown publication times stay null. The latest-vintage daily spreads, DTB3, exchange-rate levels and adjusted ETF histories support retrospective research. A timing proxy does not reconstruct the first version a historical investor received. An absolute-price filter or share count needs a quote version for the exact asset/session that was already received. The latest adjustment snapshot supplies no such verified historical closing level in this panel.

The tests insert a later macro revision, an after-close release and a future price correction representing a split adjustment. They check the earlier feature, illustrative weight, absolute-price filter and unit count. The July 2024 early close, next eligible session after the holiday, winter UTC opening hour, reversed FX quote and deferred fill are also checked.

The security universe has 2,607,985 distinct PERMNO/months before research screens. Duplicate distribution/header rows in the raw extract are collapsed on the projected security facts. Where versions differ, the effective metadata interval and its latest start determine precedence. A remaining tie makes the row unresolved. CCM candidates must be valid on the observation date, have LC or LU type and P or C primacy. Prefer P to C, then LC to LU. Equally ranked distinct GVKEYs are excluded. All original months remain in the denominator, including companies that subsequently leave.

The imported accounts panel contains 48,506 rows with assumed availability later than the trading session and 122,861 with only a same-day date. The raw annual accounts contain fiscal dates but no verified public filing time or as-reported version. All accounting-based H05 forecasts are withheld. For the 30,082 tagged company-days, exact ticker/session CRSP matching and dated CCM/GICS produce 3,676 effective sector matches, 22,570 missing sectors and 3,836 missing security identifiers. No publication-verified sector or equal-priority ambiguous match was found. The earlier import counted 3,689 effective matches under its mapping. The new release restricts the first join to an actual security observation on the tagged day. [Coverage by year and sector](../../data/prepared_v1/sector_coverage.csv) includes available returns, observed prior capitalisations and their subgroup summaries. Missing sizes remain unknown.

## Monthly eligibility and interpretation

The [coverage table](../../data/prepared_v1/sample_coverage.csv) includes every scheduled holding month in the registered historical windows, including warm-up and failures. Each row of the underlying manifest stores the preceding decision close, earliest scheduled execution, any first eligible proxy session and an empty actual execution timestamp. A missing asset quote or CHF fixing keeps the current feasible holdings until all required proxy quotes are available. Even a matched historical opening bar and same-session FX fixing cannot establish the FX price available at the open. Issuer terms, actual charges and fills remain prerequisites for a client performance claim.

| Study | Frozen data rule | Historical comparison with complete outcomes |
|---|---|---|
| H01 | Require 719 observed one-session CHF returns in a trailing window of 756 venue sessions for both covariance methods. Never bridge a gap with a multiday return. | 65 of 82 months for the common sleeve. |
| H02 | Rolling and EWMA require 60 observed returns in 63 sessions. Missing days supply no return. GARCH requires 756 consecutive valid observations. Keep the registered rolling fallback when available. | EWMA versus rolling has 53 of 82 months. GARCH has zero eligible months under the consecutive-session rule. |
| H03/H04 | Before each origin require current inputs and 36 earlier complete feature/label months for that specification. Outcomes are ETF USD returns and the documented USD cash proxy. | 82 of 82 months for both studies as retrospective inputs. Daily spreads and rates lack historic release vintages. |
| H05 | Count dated, linked US common-stock candidates with positive capitalisation and no recorded current delisting flag. Measure next-month return coverage on that original set. Enforce as-reported filing evidence before ranking. | Zero of 84 verified accounting-based comparisons. |
| H06 | Use the historical price supplement in 2010, then the course return file. Compare both series on overlap. Use at least 126 paired daily returns in the trailing 252 sessions for the anchor, then the latest classified AAPL event available during the decision month. A neutral or absent event uses the anchor. | 20 of 26 complete retrospective months for the Black–Litterman comparison. |
| H07 | Use the fixed target basket and dated valuations for all three policies. Preserve missing outcomes and hold on a missing quote. Model 0, 10 or 25 bp per traded notional. | 65 of 82 months with paired inputs and full daily coverage. Net results depend on execution and the mandate. |

The thresholds are data-preparation choices for v1. These counts describe input and outcome coverage. They do not report fitted forecasts, model convergence, an independent test or realized trades. The monthly factor table reconstructs the research library’s FF5 and momentum observations from their archived percentage files and converts to decimals once. The cost panel records assumptions at each decision.

## Reproduce

With Python 3.12.6 and the reconstructed large source files, run from the repository root.

```sh
python -m pip install -r requirements-data.txt
python research/prepare_panels.py
python tests/test_cleaning.py
```

The builder checks the consumed raw files against the 3.1 manifest, records the hashes of the three auxiliary imports, then stages all outputs together. Running against an existing release compares files and refuses replacement on a difference. Use `--output NEW_DIRECTORY` to inspect a separate build. [Output hashes](../../data/prepared_v1/manifest.json) · [Audit totals](../../data/prepared_v1/audit.json)
