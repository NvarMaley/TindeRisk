import unittest
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
        self.mock=patch.object(hm,'catalog',return_value=(rows,4,a))
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
