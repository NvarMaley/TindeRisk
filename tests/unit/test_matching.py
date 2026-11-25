import unittest

from riskmatch.matching import allocate
from riskmatch.prototype import ClientProfile


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.profile = ClientProfile(100000, 10, .3)

    def test_consolidation_and_risk(self):
        result = allocate(self.profile, ['Cash', 'Conservative'], [.6, .4])
        self.assertAlmostEqual(result['weights']['USD cash'], .76)
        self.assertAlmostEqual(sum(result['weights'].values()), 1)
        self.assertAlmostEqual(sum(result['risk_contributions'].values()), result['metrics']['vol'])

    def test_optimized(self):
        result = allocate(self.profile, ['Cash', 'Conservative'], optimize=True)
        self.assertAlmostEqual(sum(result['budgets'].values()), 1)
        self.assertTrue(all(w >= 0 for w in result['budgets'].values()))

    def test_single(self):
        result = allocate(self.profile, ['Cash'], optimize=True)
        self.assertEqual(result['budgets'], {'Cash': 1.0})

    def test_invalid(self):
        for names, budgets in [([], []), (['Cash', 'Cash'], [.5, .5]),
                               (['Cash'], [.5]), (['Cash'], [float('nan')]),
                               (['Cash', 'Conservative'], [-.1, 1.1])]:
            with self.subTest(names=names, budgets=budgets), self.assertRaises(ValueError):
                allocate(self.profile, names, budgets)
        with self.assertRaises(ValueError):
            allocate(ClientProfile(100, 1, 0), ['Growth'], [1])
        with self.assertRaises(ValueError):
            allocate(self.profile, ['Cash'], [1], version='stale')
