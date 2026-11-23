import json
from dataclasses import replace
from importlib.util import find_spec
from pathlib import Path
from unittest import TestCase, skipUnless


@skipUnless(
    find_spec("cvxpy") and find_spec("sklearn"),
    "Catalogue options and feasibility required",
)
class OptionsTest(TestCase):
    def setUp(self):
        import numpy as np
        from riskmatch_v2.feasibility.engine import Problem

        self.cfg = json.loads(Path("config/options-6.json").read_bytes())
        self.p = Problem(
            ("SPY", "IEF"),
            np.array([0.08, 0.08]),
            np.diag([0.2, 0.1]),
            np.zeros(2),
            np.ones(2),
            np.zeros(2),
            np.zeros(2),
            {},
        )

    def test_manual_overlap_and_bounds(self):
        import numpy as np
        from riskmatch_v2.options.compare import combine, distinct, metrics

        W = np.array([[0.2, 0.7], [0.1, 0.2]])
        w = combine(W, [0.6, 0.4])
        self.assertAlmostEqual(w[0], 0.16)
        np.testing.assert_allclose(combine(W, [1, 0]), W[0])
        np.testing.assert_allclose(combine([W[0], W[0]], [0.3, 0.7]), W[0])
        for malformed in ([0.5, 0.4], [1.1, -0.1], [float("nan"), 1]):
            with self.assertRaises(ValueError):
                combine(W, malformed)
        kept, aliases = distinct({"A": W[0], "B": W[0].copy()}, 0.005)
        self.assertEqual(list(kept), ["A"])
        self.assertEqual(aliases, {"B": "A"})
        p = replace(self.p, root=np.array([[0.2, -0.2]]))
        self.assertTrue(all(p.evaluate(x, 0.18, 0.25)["valid"] for x in np.eye(2)))
        self.assertFalse(
            metrics(
                [p], combine(np.eye(2), [0.5, 0.5]), np.array([-0.3, -0.1]), 0.18, 0.25
            )["valid"]
        )
        p = replace(self.p, current=np.array([0.16, 0.50]), fees=np.full(2, 0.001))
        self.assertAlmostEqual(p.evaluate(w)["fee"], 0.0)
        self.assertLess(
            p.evaluate(w)["fee"],
            0.6 * p.evaluate(W[0])["fee"] + 0.4 * p.evaluate(W[1])["fee"],
        )

    def test_analytic_sharpe_min_and_correlated(self):
        import numpy as np
        from riskmatch_v2.options.compare import mix_search, metrics

        for criterion in ("Sharpe", "Minimum risk"):
            r = mix_search([self.p], np.eye(2), criterion=criterion, low=0, high=0.3)
            self.assertAlmostEqual(r["parts"][0], 0.2, places=4)
        r = mix_search(
            [self.p], np.eye(2), criterion="Sharpe", minimum=0.35, low=0, high=0.3
        )
        self.assertAlmostEqual(r["parts"][0], 0.35, places=5)
        correlated = replace(self.p, root=np.array([[0.15, 0.15]]))
        c = metrics([correlated], np.array([0.5, 0.5]), np.zeros(2), 0, 0.2)
        self.assertAlmostEqual(sum(c["euler"].values()), 0.15)
        self.assertAlmostEqual(c["vol"], 0.15)
        bad = mix_search(
            [self.p, replace(self.p, mu=np.array([-0.1, -0.1]))],
            np.eye(2),
            criterion="Sharpe",
            low=0,
            high=0.3,
        )
        self.assertEqual(bad["status"], "Inoperative Sharp")

    def test_scores_and_real_admission(self):
        from riskmatch_v2.options.scenarios import scoring_controls
        from riskmatch_v2.options.scoring import rank

        proofs = scoring_controls(self.cfg)
        for name, g in proofs.items():
            for r in g["rows"].values():
                self.assertAlmostEqual(r["total"], sum(r["contributions"].values()))
        base = dict(
            valid=True,
            tradable=False,
            net=0.06,
            cagr=0.05,
            drawdown=-0.2,
            loss=0.1,
            hhi=0.2,
            fee=0.001,
        )
        self.assertFalse(
            rank({"x": base}, self.cfg["profiles"]["Goal"], self.cfg)["rows"]
        )

    def test_trade_accounting_and_delay(self):
        import numpy as np
        from riskmatch_v2.options.replay import replay, Tape

        dates = [
            "2025-06-02",
            "2025-06-03",
            "2025-06-04",
            "2025-06-05",
            "2025-06-06",
            "2025-06-09",
        ]
        usd = np.array(
            [[9, 20], [10, 20], [11, 20], [11, 20], [11, 20], [11, 20]], float
        )
        t = Tape(
            dates,
            ["A", "B"],
            usd,
            np.ones(6),
            usd,
            np.ones_like(usd, bool),
            np.zeros_like(usd),
            np.ones_like(usd),
        )
        plan = {dates[0]: [0.8, 0], dates[2]: [0, 1]}
        result, d, book, positions, _ = replay(
            t, plan, 1000, 150, fee=0, flows={dates[2]: -100}, capture=True
        )
        self.assertEqual(positions.iloc[0].tolist(), [0, 0])
        self.assertEqual(positions.iloc[1].tolist(), [80, 0])
        self.assertEqual(positions.iloc[3].tolist(), [0, 5])
        self.assertEqual(positions.iloc[4].tolist(), [0, 49])
        self.assertEqual(result["paid"], 100)
        self.assertEqual(d.loc[dates[3], "pending"], 880)
        self.assertEqual(book[book.kind == "vente"].settlement.tolist(), [dates[4]])
        np.testing.assert_allclose(
            d.nav, d.bank_cash + d.pending - d.purchase_payable + d.positions
        )
        self.assertAlmostEqual(result["final"], 980)
        missed = replay(t, {dates[0]: [0.8, 0]}, 1000, 150, miss=True)[0]
        self.assertEqual(missed["final"], 1000)
        self.assertEqual(missed["missing"], 1)
        delayed = replay(t, plan, 1000, 150, fee=0, settle=2, capture=True)
        self.assertGreater(delayed[1].loc[dates[4], "pending"], 0)
        self.assertGreaterEqual(delayed[1].cash.min(), -1e-7)
        no_trade = replay(t, {dates[0]: [0, 0]}, 1000, 150, fee=0.001)[0]
        self.assertEqual(no_trade["fees"], 0)

    def test_partial_sale_split_and_missing_quote(self):
        import numpy as np
        from riskmatch_v2.options.replay import replay, Tape

        dates = [f"2025-04-{i:02}" for i in range(1, 7)]
        usd = np.array([[10], [10], [5], [5], [5], [5]], float)
        tradable = np.ones_like(usd, bool)
        tradable[1, 0] = False
        t = Tape(
            dates,
            ["A"],
            usd,
            np.ones(6),
            usd,
            tradable,
            np.zeros_like(usd),
            np.ones_like(usd),
        )
        a = replay(t, {dates[0]: [0.5], dates[3]: [0.25]}, 100, 0, fee=0, capture=True)
        self.assertEqual(a[3].iloc[1, 0], 0)
        self.assertEqual(a[3].iloc[2, 0], 10)
        self.assertEqual(a[3].iloc[4, 0], 5)
        t.trade[1, 0] = True
        t.splits[2, 0] = 2
        t.dividends[2, 0] = 0.5
        b = replay(t, {dates[0]: [0.5]}, 100, 0, fee=0, capture=True)
        self.assertEqual(b[3].iloc[2, 0], 10)
        self.assertEqual(b[0]["final"], 105)
        self.assertEqual(b[0]["max_residual"], 0)

    def test_variant_objectives(self):
        import numpy as np
        from riskmatch_v2.options.compare import weights, metrics, LABELS

        p = replace(self.p, mu=np.array([0.10, 0.04]))
        shock = np.array([-0.4, 0.10])
        options = weights([p], shock, 0.18, 0.025)
        cards = {n: metrics([p], w, shock, 0, 0.18) for n, w in options.items()}
        self.assertLessEqual(
            cards["Diversification"]["hhi"], cards["Return"]["hhi"] + 1e-6
        )
        self.assertLess(cards["Hedge"]["loss"], cards["Return"]["loss"])
        for n in LABELS[:4]:
            self.assertTrue(cards[n]["valid"])
        self.assertGreaterEqual(
            cards["Hedge"]["net"], cards["Return"]["net"] - 0.025001
        )
