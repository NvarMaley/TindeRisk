# Chapter 09 — Volatility and covariance (research)

## Univariate volatility

Period returns must be finite and have continuous exact start/end intervals.
Annualization uses 252 exchange days, 365 crypto days, 52 weeks, or 12
months; irregular marks retain interval-only descriptive risk. Use a fixed
60/20/20 chronological split and center shocks on the training mean only.
Historical expanding mean squared shocks, 20-period rolling and EWMA
(decay 0.94, first observed squared shock initialization) predict one-step
variance using only earlier observations.

The pinned arch 8.0.0 package fits GARCH(1,1), asymmetric EGARCH(1,1,1) and
GJR-GARCH(1,1,1) on training shocks in percent units; minimum 100 periods
for conditional fits. Recurse parameters without refitting on validation
or test. For GARCH, h[t+1]=omega+alpha*e[t]^2+beta*h[t]; GJR adds
gamma*e[t]^2*I(e[t]<0). Require successful convergence and persistence
strictly below one (GJR alpha+beta+gamma/2, Gaussian reference).
EGARCH uses log variance, standardized shock magnitude and signed asymmetry.
A prespecified log variance numerical guard [-18,18] retains extreme
predictions for evaluation and records occurrences. A guarded training or
validation model cannot be selected. Test guard occurrences are warnings,
not grounds for changing the validation selection. Residual and squared
residual Ljung–Box p-values are research diagnostics. Return variance is
converted back to squared decimal units.

Evaluate QLIKE = log(h)+realized squared shock/h and MSE, on exactly the
same held-out periods. Select the minimum validation QLIKE, without looking
at test performance. Volatility forecasts are not guarantees; realized
absolute shocks are noisy proxies for conditional volatility.

## Multivariate covariance

Use complete exact common start/end intervals, identical frequency,
currency, target kind and annualization; no pairwise deletion matrix.
Fit sample covariance (n-1), EWMA covariance, Ledoit–Wolf and OAS
shrinkage on training observations. Statistical PCA factor covariance
uses training principal components and B Sigma_f B' plus diagonal or full
residual covariance; external economic factors await Chapter 10.
Compare fixed equal-weight realized squared portfolio shocks against
training covariance on validation/test, and choose by validation QLIKE.
An inverse-volatility weight change between training and validation is
a stability diagnostic only, not a proposed portfolio.

Check symmetry and eigenvalues using explicit relative/absolute tolerances;
reject materially indefinite inputs. Keep raw matrices and separately
floor small eigenvalues at max(1e-12, 1e-8*largest eigenvalue), recording
eigenvalue count, conditioning and Frobenius change. All per-period
covariances are squared decimal returns; multiplying by periods per year
gives annualized covariance.

DCC is a two-step Gaussian quasi-likelihood correlation fit: standardized
training GARCH shocks define a PSD target Q; estimate nonnegative a,b
with a+b<1, recursively update Q and normalize its diagonal to obtain R.
Conditional covariance is diag(sqrt(h))*R*diag(sqrt(h)). Restrict DCC to
2–8 assets with 100 aligned intervals and stationary converged marginal
GARCH fits. Evaluate held-out equal-weight conditional variance. Large or
short cohorts do not pretend to have a validated DCC fit.

## Local evidence, 2026-11-25

Run `.venv/bin/python scripts/build_risk_universe.py --as-of 2026-11-25 --workers 4`.
All 1,474 catalogue assets examined: 574 six-model profiles without
numerical guards, 441 partial/guarded profiles, 457 descriptive-only
profiles and two unavailable. The three baseline models cover 1,015,
GARCH 836, EGARCH 831 (205 with guards), GJR 849. No selected model has
a training/validation numerical guard; five selected models have a
later guard and remain experimental.

Six aligned covariance cohorts, including the exact 575-asset Chapter 8
monthly USD total-return vector at 2025-12-31, yield 36 model matrices.
All raw and numerically regularized matrices passed PSD checks; the
575-asset cohort has 99 common intervals and singular sample covariance,
so shrinkage is essential. Three small cohorts have fitted DCC conditional
covariance, all PSD. All result rows/matrices stay local in ignored
content-hashed files. The Sources view shows coverage; asset profiles and
comparison expose risk charts and diagnostics. G04 backtest validation,
G02/G07 data approval and CH10 economic-factor validation remain open.
