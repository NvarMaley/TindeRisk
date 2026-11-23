from dataclasses import replace
from datetime import date
from importlib.util import find_spec
import json
from pathlib import Path
from unittest import TestCase, skipUnless


@skipUnless(find_spec("cvxpy") and find_spec("sklearn"),"Feasibility option required")
class FeasibilityTest(TestCase):
    def setUp(self):
        import numpy as np
        from riskmatch_v2.feasibility.engine import Problem
        self.p=Problem(("A","B"),np.array([.07,.04]),np.diag([.20,.10]),np.zeros(2),np.ones(2),
                       np.zeros(2),np.zeros(2),{},invested_min=1)
    def test_analytic_minimum_and_certified_cap(self):
        from riskmatch_v2.feasibility.engine import Frontier
        e=Frontier(self.p)
        result=e.solve(minimum=True)
        self.assertEqual(result["status"],"optimal")
        self.assertAlmostEqual(result["candidate"]["weights"][0],.2,places=4)
        self.assertAlmostEqual(result["candidate"]["risk"],.008**.5,places=6)
        self.assertEqual(e.solve(high=.05)["status"],"impossible")
        r=e.solve(high=.12)
        c=r["candidate"]
        self.assertTrue(c["valid"])
        self.assertLessEqual(c["residual"],1e-6)
        self.assertGreaterEqual(r["upper_net"]+1e-8,c["net"])
        self.assertLessEqual(r["gap"],.0001)
    def test_target_search_and_interrupt(self):
        from riskmatch_v2.feasibility.study import oracle_cases
        cases,_=oracle_cases()
        self.assertAlmostEqual(cases["binding lower volatility bound"]["risk"],.10,places=5)
        self.assertGreater(cases["interruption"]["gap"],.0001)
    def test_no_borrowing_sales_and_fees(self):
        import numpy as np
        from riskmatch_v2.feasibility.engine import Frontier
        p=replace(self.p,current=np.array([.9,0]),fees=np.full(2,.001),invested_min=0)
        self.assertTrue(p.evaluate([0,.90])["valid"])
        self.assertFalse(replace(p,prefund=True).evaluate([0,.90])["valid"])
        self.assertFalse(p.evaluate([0,1])["valid"])
        q=replace(p,hi=np.zeros(2))
        c=Frontier(q).solve(high=0)["candidate"]
        self.assertAlmostEqual(c["cash"],.9991)
        self.assertEqual(Frontier(replace(q,invested_min=.5)).solve()["status"],"impossible")
    def test_psd_factor_and_cache_limits(self):
        import numpy as np
        import pandas as pd
        from riskmatch_v2.feasibility.inputs import factors
        from riskmatch_v2.feasibility.study import cache_key
        rng=np.random.default_rng(1)
        d=pd.DataFrame(rng.normal(0,.01,(300,5)),columns=["SPY","IEF","GLD","action","courte"])
        d.loc[:89,"action"]=np.nan
        d.loc[:279,"courte"]=np.nan
        names,_,root,counts=factors(d,["SPY","IEF","GLD"],100)
        self.assertEqual(counts["action"],210)
        self.assertNotIn("courte",names)
        self.assertGreaterEqual(np.linalg.eigvalsh((root.T@root).toarray()).min(),-1e-10)
        self.assertNotEqual(cache_key(self.p,{},'v'),cache_key(replace(self.p,groups={"industrie":([1,0],.5)}),{},'v'))
    def test_lots_odd_holdings_and_restrictions(self):
        import numpy as np
        from riskmatch_v2.feasibility.orders import orders
        from riskmatch_v2.feasibility.study import examples_lots
        cases=examples_lots()
        self.assertEqual(cases["Bond lot"]["status"],"impossible in batches")
        self.assertGreaterEqual(cases["small investment sleeve"]["order"]["cash_chf"],0)
        p=replace(self.p,current=np.array([.15,0]),invested_min=0,hi=np.array([.10,1.]))
        r=orders(p,[.05,0],1000,[10,20],[1,1],[10,10],[15,0])
        self.assertEqual(r["order"]["units"][0],5)
    def test_mandate_confirmed_cash_and_household_basis(self):
        import pandas as pd
        from riskmatch_v2.interview import Interview,CARDS,route,SKIP
        from riskmatch_v2.risk_review import request
        from riskmatch_v2.feasibility.mandate import account_gate
        d=json.loads(Path("reports/02-questionnaire/cas.json").read_bytes())
        session=Interview(date.fromisoformat(d["as_of"]))
        ans=d["common"]|d["cases"][0]["answers"]
        for card in CARDS:
            if card in route(session.answers):
                session.record(card,ans.get(card,SKIP))
        session.confirm()
        instant=d["as_of"]+"T14:00:00Z"
        reg=pd.DataFrame([dict(id="A",eligible=False,date=instant)])
        self.assertEqual(account_gate(session.versions[-1],reg,instant)["status"],"request to be confirmed")
        session.save_risk(request("cap","household",ceiling_pct=14),accept=True,bills="yes",comfort="yes")
        r=account_gate(session.versions[-1],reg,instant)
        self.assertEqual(r["status"],"no eligible instrument")
        self.assertAlmostEqual(r["high"],.2)
        self.assertEqual(r["reserve_chf"],15000)

    def test_account_model_uses_verified_mandatory_exposure(self):
        from unittest.mock import patch
        import numpy as np
        from riskmatch_v2.feasibility.account import solve_account
        snapshot={"portrait":{"mandatory_checks":[{"card":"P07","scope":"prohibited sector"}]}}
        gate={"ids":["A","B"],"mode":"cap","low":0.,"high":.2}
        model=replace(self.p,invested_min=0)
        opts=dict(model=model,model_date="2026-11-23")
        key=("P07","prohibited sector")
        with patch("riskmatch_v2.feasibility.account.account_gate",return_value=gate):
            def run(limits=None):
                return solve_account(snapshot,None,"2026-11-23",exposure_limits=limits,**opts)
            self.assertIn("documented",run()["status"])
            self.assertIn("incomplete",run({key:({"A":1},0)})["status"])
            research=run({key:({"A":1,"B":0},0)})
            self.assertEqual(research["status"],"optimal")
            self.assertLessEqual(research["continuous"]["candidate"]["weights"][0],1e-6)
