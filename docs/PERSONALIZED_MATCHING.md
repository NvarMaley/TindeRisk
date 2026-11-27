# Personalized Match construction — research implementation

See the [French guide to portfolio data and the 47 candidate strategies](UNIVERS_DONNEES_STRATEGIES.md)
for the simulated mandate date, archive cutoff, cleaning and use of asset-level research.

## Methodology

The investment policy statement precedes portfolio construction. Separate
capacity to bear losses from willingness to take risk. The mandate establishes
the admissible universe, funded budget and measurable constraints; preferences
and dated objectives influence ranking and the research utility parameter.
This follows the CFA Institute's portfolio planning and suitability framework.
Constrained mean-variance, downside-risk and hierarchical allocation methods
also follow the general construction architecture of PyPortfolioOpt.

References:

- CFA Institute, [Basics of Portfolio Planning and Construction](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/basics-of-portfolio-planning-and-construction).
- CFA Institute, [Standard III(C) Suitability](https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-iii-c).
- Ledoit and Wolf (2004), [Honey, I Shrunk the Sample Covariance Matrix](https://ledoit.net/honey_abstract.htm).
- PyPortfolioOpt, [General Efficient Frontier](https://pyportfolioopt.readthedocs.io/en/latest/GeneralEfficientFrontier.html).

## Reusable inputs versus individual calculations

The client Universe tab lists the instruments eligible at the fixed USD
valuation date, 31 December 2025. Each security needs 60 valid, consecutive
monthly total returns on the shared SPY calendar. Stocks must belong to the
dated top 1,000 at the decision close. Equity and US Treasury ETFs come from
the project registry and use the CRSP total-return series. USD cash accrues
the Fama–French monthly risk-free rate. The mandate groups US stocks and
equity ETFs under one permission.

Missing or misaligned returns disqualify the security at that decision.
Values above 100% and complete losses can be genuine observations and stay in
the history. Known publication dates after the decision close disqualify the
observation. Original publication dates are unavailable for many rows in the
archive. Other data and individual forecasts remain available for research.
The published strategy cards use the same frozen return archive and dated
factor, membership, capitalization and macro inputs.

Every supported full mandate now generates its own weights:

1. Validate structural feasibility and measurable hard constraints.
2. Screen the common panel by allowed asset class and dated stock membership.
   Apply 5% research caps to stocks, 65% to listed products, and the tighter
   user-specified asset cap, including cash when that cap is explicit.
3. Translate the willingness score, horizon and objective priorities into a
   transparent research risk preference and utility parameter. This mapping
   is a heuristic, pending empirical behavioral calibration.
4. Run every funded strategy in the shared registry. Full-universe rules
   evaluate the entire eligible set. Matrix-heavy optimizers retain eligible
   ETFs and up to the 64-asset market-cap-ranked working set. This controls
   numerical cost; it is not an exhaustive search of all subsets.
5. Fit regularized trailing means on the common 60-month estimation window. The common estimate weights the observed annualized mean and the median of the asset’s class equally.
   The portfolio risk controller and cards use shrinkage on standardized
   returns with the original volatilities restored, including cash. Some
   strategies deliberately use shorter signals, factor data, macro data or
   their own risk model.
6. Apply funded budget, bounds, hard stress and volatility checks. The
   directly constrained utility candidate solves a quadratic objective with
   scenario inequalities. Other strategy targets may be blended with a
   feasible defensive reference to respect modeled limits. The overlay is a
   feasible adjustment, rather than a globally optimal constrained solution
   for every individual strategy.
7. Refit historical targets quarterly using the same 60-month admission rule
   and the stocks listed at each decision, including names absent at the
   current cutoff. Development covers January 2021 through November 2023
   and historical test results cover December 2023 through December 2025. Use a one-month execution delay, rebalance monthly, charge 10 bp on traded securities, and carry holdings across the development/holdout boundary. Unpriced held instruments or an infeasible dated target disqualify the historical path. Coverage therefore also depends on data quality.
8. Assess each candidate on 256 common six-month block-bootstrap scenarios
   from development returns, with two additional half-window sensitivity estimates, using actual dated goals and contribution
   schedules. Rank using estimated return, funding shortfall and stress fit.
   Objective-specific simulated scores cover preservation, withdrawal coverage
   (when modeled), conservative, balanced, growth, inflation, excess return
   and funding objectives. Missing distribution and liability-rate exposures
   remain explicit limitations.
   Soft volatility and asset-weight limits penalize the score when exceeded;
   unsupported soft limits are disclosed.
   Present up to six leading candidates with at least 5% of capital reallocated
   between any two displayed targets. An aligned comparison provides every
   compatible card, the SPY market benchmark and an availability explanation.
   The historical test CAGR does not determine the featured rank.
9. Version the deck by input archive, mandate and aversion. Reconstruct and
   revalidate it before allocation, goal assessment, dynamic simulation or
   export. Changed inputs invalidate previously selected weights.

For weights w, annualized estimated covariance Sigma and adjusted returns mu,
the directly constrained utility objective is

    maximize mu' w - lambda / 2 * w' Sigma w
    subject to sum(w) = 1, 0 <= w <= u, scenario_j' w >= -L

The volatility limit is independently checked. A weighted combination of
validated funded portfolios retains the linear limits. Its covariance-based
volatility, stress and actual sleeve transfer costs are recomputed.

## Boundaries

- The replay uses dated stock membership and a retrospective ETF registry.
  Missing original publication dates, historical fund holdings and the
  available return coverage limit point-in-time verification. Current targets use the
  December 2025 cutoff, displayed on each card.
- The historical test measures the replayed rules on common dates. The final
  ranking also uses estimates calibrated at the December 2025 cutoff, so
  the historical comparison does not independently validate that ranking.
- USD only for personalized Match; the aligned CHF cohort has 47 continuous
  months, insufficient for this 60-month minimum evaluation protocol. CHF
  research remains separate. Individual Treasury securities, standalone REIT
  ETFs, commodity ETPs, crypto, futures and short/leveraged trading sit outside
  the personalized portfolio universe. Legacy mandates with excluded classes
  can be opened and must be reviewed before rerunning the personalized deck.
- The 47 funded candidates are built from the four supported instrument
  types. The standalone SPY benchmark and the Sortino and Omega research
  methods are outside candidate scoring. The equal-weight duplicate was merged. The all-weather proxy uses SPY, IEF, TIP and SHY. The tail hedge is a
  defensive equity/Treasury allocation, while global macro uses economic data
  as signals for its equity/Treasury allocation. Actual card availability still
  depends on asset permissions, feasibility, historical coverage and de-duplication.
- Issuer/sector look-through, actual liquidity and transaction-cost limits,
  turnover from actual existing holdings, after-tax treatment and currency
  hedging lack sufficient inputs. These hard constraints block generation.
- Financial goal projection is conditional, with limited history and modeled
  cash returns. The confirmed allocation gets a 1,000-path projection using joint six-month blocks from 60 months of consolidated holdings. The model keeps target weights fixed, includes monthly rebalancing fees, and applies the mandate cash flows. The replay of the strategy sleeves and its separate test metrics remain available.
  Dynamic overlays require cash permission and cannot certify a hard asset
  cap or a hard volatility cap. Dated liability flows are handled by the
  goal projection rather than the dynamic overlay.
- Research only. Formal acceptance, data redistribution rights, investment
  suitability, actual instrument availability and execution remain separate.

## Verification

Use the Chapter 25 historical notebook cells to compare different risk
scores and mandate restrictions. The routes preserve the previous response
contract and use the same deck version for all subsequent calculations.
Run the normal unit suite and web tests, then the full historical notebook.
The prior fixed five-ETF deck is retained for legacy research and compatibility.

The [per-strategy audit and portfolio walkthrough](AUDIT_STRATEGIES_ET_PORTEFEUILLE.md) records the two mandate tests, the four allocation modes and the projection convention.
