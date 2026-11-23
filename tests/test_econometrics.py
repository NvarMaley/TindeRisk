from importlib.util import find_spec
from unittest import TestCase, skipUnless


@skipUnless(
    all(find_spec(x) for x in ("numpy", "pandas", "duckdb", "scipy")),
    "research dependencies",
)
class EconomicsTest(TestCase):
    def test_hac_matches_explicit_session_kernel(self):
        import numpy as np
        from scipy.stats import t

        from riskmatch_v2.econometrics import hac

        rng = np.random.default_rng(17)
        x = np.column_stack((np.ones(95), rng.normal(size=95)))
        y = x @ np.array([0.03, -0.7]) + rng.normal(0, 0.1, len(x))
        y[11:14] = np.nan
        b, half, n = hac(x, y, 80, 5)
        ok = np.isfinite(y)
        z = x[ok]
        days = np.flatnonzero(ok)
        bread = np.linalg.inv(z.T @ z)
        actual = bread @ z.T @ y[ok]
        scores = z * (y[ok] - z @ actual)[:, None]
        kernel = np.maximum(0, 1 - np.abs(days[:, None] - days) / 6)
        v = bread @ scores.T @ kernel @ scores @ bread * n / (n - 2)
        np.testing.assert_allclose(b, actual)
        np.testing.assert_allclose(half, t.ppf(0.975, n - 2) * np.sqrt(np.diag(v)))
        self.assertIsNone(hac(x, y, 93, 5))

    def test_first_forecast_uses_only_predecision_data(self):
        import numpy as np
        import pandas as pd

        from riskmatch_v2.econometrics import forecasts

        dates = pd.bdate_range("2024-01-01", periods=84).astype(str)
        x = np.r_[np.full(42, 0.005), np.full(21, 0.01), np.full(21, 0.02)]
        row = forecasts(
            pd.DataFrame({"A": x}, index=dates), [True], dates[63], 0.94
        ).iloc[0]
        hist = np.mean(x[:63] ** 2)
        ew = np.average(x[:63] ** 2, weights=0.94 ** np.arange(62, -1, -1))
        self.assertEqual(row.windows, 1)
        self.assertAlmostEqual(
            row.qlike_gain, np.log(hist / ew) + 0.02**2 * (1 / hist - 1 / ew)
        )
