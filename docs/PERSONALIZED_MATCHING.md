# Personalized Match construction — research implementation

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

The frozen common USD monthly total-return panel has 575 instruments (549
stocks and 26 ETFs/ETPs) and 100 continuous months ending December 2025.
The broad catalogue has 1,474 records, including instruments with incompatible
or insufficient common history. The model consumes the common forecast
vector, dated factor scores, membership, market caps, historical returns
and macro data. The server caches these common inputs in memory. No raw
dataset is duplicated in Git or fetched during a client session.

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
5. Fit shrinkage covariance and a regularized expected-return vector. Current
   regularized utility and Black–Litterman targets may use the dated common
   forecast vector, combined with historical means; historical segments use
   only earlier returns. Other methods keep their own estimators and signals.
6. Apply funded budget, bounds, hard stress and volatility checks. The
   directly constrained utility candidate solves a quadratic objective with
   scenario inequalities. Other strategy targets may be blended with a
   feasible defensive reference to respect modeled limits. The overlay is a
   feasible adjustment, rather than a globally optimal constrained solution
   for every individual strategy.
7. Fit historical targets separately at the development and holdout origins.
   Simulate monthly fixed-target rebalancing with 10 bp modeled costs and
   chronological separation. Current weights are constructed at the archive
   end; the card's holdout performance represents the earlier fitted rule,
   not a replay of the current weights over past data.
8. Assess each candidate on 256 common six-month block-bootstrap scenarios
   from development returns, using actual dated goals and contribution
   schedules. Rank using estimated return, funding shortfall and stress fit.
   Objective-specific simulated scores cover preservation, withdrawal coverage
   (when modeled), conservative, balanced, growth, inflation, excess return
   and funding objectives. Missing distribution and liability-rate exposures
   remain explicit limitations.
   Soft volatility and asset-weight limits penalize the score when exceeded;
   unsupported soft limits are disclosed.
   Select a diverse initial set by portfolio distance, with all remaining
   viable methods available. Some strategies have overlapping exposures.
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

- Common-panel composition is retrospective and not a fully verified
  point-in-time universe. Monthly source release dates and historical fund
  holdings still require independent validation. Current targets use the
  December 2025 cutoff, displayed on each card.
- USD only for personalized Match; the aligned CHF cohort has 47 continuous
  months, insufficient for this 60-month minimum evaluation protocol. CHF
  research remains separate. Individual
  Treasury bonds, crypto, futures and short/leveraged trading are unavailable
  in the common funded portfolio engine. Commodity ETPs are opt-in; futures-backed
  commodity products require explicit derivative permission.
- Issuer/sector look-through, actual liquidity and transaction-cost limits,
  turnover from actual existing holdings, after-tax treatment and currency
  hedging lack sufficient inputs. These hard constraints block generation.
- Financial goal projection is conditional, with limited history and modeled
  cash returns. The final allocation gets the existing 1,000-path assessment.
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
