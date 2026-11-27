import unittest
from datetime import date
from unittest.mock import patch
import numpy as np

from riskmatch import historical_matches as hm
from riskmatch.prototype import ClientProfile


class HistoricalMatchesTests(unittest.TestCase):
    def setUp(self):
        a=np.array([.01,-.01,.02,-.02,.035,-.02,.015,-.01])
        b=np.array([-.01,.02,-.02,.01,-.015,.01,-.03,.02])
        rows={'one':({'SPY':.5,'IEF':.5},{'crash':-.14,'rates':-.02},a),
              'two':({'SPY':.2,'IEF':.8},{'crash':-.04,'rates':-.12},b)}
        dates = [date(2024, month, 1) for month in range(1, 10)]
        self.mock=patch.object(hm,'_cached_catalog',return_value=(rows,4,a,np.full_like(a,.002),list(zip(dates,dates[1:]))))
        self.mock.start()
        self.addCleanup(self.mock.stop)
        self.profile=ClientProfile(1e5,10,.15)

    def test_shared_exposure_and_scenario(self):
        r=hm.blend('.',self.profile,['one','two'],[.6,.4],False)
        self.assertAlmostEqual(r['weights']['SPY'],.38)
        self.assertAlmostEqual(r['stress_loss'],.1)
        self.assertAlmostEqual(sum(r['risk_contributions'].values()),r['metrics']['vol'])

    def test_single_optimized_and_ineligible(self):
        self.assertEqual(hm.blend('.',self.profile,['one'],None,True)['budgets'],{'one':1})
        self.assertEqual(hm.cards('.',ClientProfile(1e5,10,.1)),[])
        with self.assertRaises(ValueError):
            hm.blend('.',self.profile,['two','one'],[.8,.4],False)
        with self.assertRaises(ValueError):
            hm.blend('.',self.profile,['two','unknown'],None,True)

    def test_constant_sleeve_has_no_defined_correlation(self):
        variable = np.array([.01,.02,-.01,.03,.02,-.02])
        rows = {"cash":({"USD cash":1.,"SPY":0.},{"stress":0.},np.full(6,.004)),
                "stock":({"USD cash":0.,"SPY":1.},{"stress":-.1},variable)}
        report = hm.blend_rows(self.profile,["cash","stock"],[.5,.5],False,rows,3,variable,
                               "test","test period","test costs")
        self.assertEqual(report["correlations"], [[None,None],[None,1.]])

    def test_card_sharpe_uses_held_out_cash_reference(self):
        card = next(row for row in hm.cards('.', self.profile) if row['name'] == 'one')
        excess = np.array([.035, -.02, .015, -.01]) - .002
        self.assertAlmostEqual(card['metrics']['sharpe'], excess.mean() / excess.std(ddof=1) * np.sqrt(12))
        self.assertEqual(card['backtest']['test']['months'], 4)
        self.assertIsNone(card['backtest']['worst_12_months'])
