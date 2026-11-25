import base64
import copy
import hashlib
import io
import json
import unittest
import zipfile
import runpy
from pathlib import Path
from unittest.mock import patch
import numpy as np

from riskmatch.dynamic.policies import simulate
from riskmatch.integration import export_simulation


class ExportTests(unittest.TestCase):
    def fixture(self):
        dates=[str(i) for i in range(24)]
        run=simulate(np.tile([.01,.002],(24,1)),np.full(24,.001),dates,13,100000,
                     "static",[.6,.4],.2,.15,contribution=100)
        return {"status":"experimental","version":"dynamic-fixture","match_version":"fixture",
                "reference_run":"fixture","names":["A","B"],"dates":dates[13:],
                "policies":{"static":run},"settings":{"capital":100000,"stress_limit":.2},
                "selection":{"weights":{"A":.6,"B":.4},"scenarios":{"crash":-.15}},
                "assumptions":"Synthetic","sensitivity":{}}

    def test_zip_reproducibility_and_hashes(self):
        r=self.fixture()
        a=export_simulation(r,"static")
        b=export_simulation(r,"static")
        self.assertTrue(a["paper_only"])
        self.assertEqual(a["run_id"],b["run_id"])
        self.assertEqual(a["archive"],b["archive"])
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(a["archive"]))) as z:
            manifest=json.loads(z.read("manifest.json"))
            self.assertEqual(set(manifest["files"])|{"manifest.json"},set(z.namelist()))
            for name,digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),digest)
            self.assertIn("signed_notional_usd",z.read("trades.csv").decode())
            self.assertEqual(len(json.loads(z.read("audit.json"))),11)

    def test_reject_bad_ledger(self):
        r=self.fixture()
        for field,value in [("ending",0),("stress_estimate",.3),("fee",-1)]:
            bad=copy.deepcopy(r);bad["policies"]["static"]["ledger"][0][field]=value
            with self.assertRaises(ValueError):
                export_simulation(bad,"static")
        with self.assertRaises(ValueError):
            export_simulation(r,"unknown")
        r["policies"]["static"]["status"]="shortfall"
        with self.assertRaises(ValueError):
            export_simulation(r,"static")

    def test_export_route_without_socket(self):
        handler_type=runpy.run_path(str(Path(__file__).resolve().parents[2]/"apps/api/server.py"))["Handler"]
        request=object.__new__(handler_type)
        payload=json.dumps({"policy":"static"}).encode()
        request.path="/api/paper/export"
        request.headers={"Content-Length":str(len(payload))}
        request.rfile=io.BytesIO(payload)
        request.respond=lambda value,status=200:(status,value)
        with patch("riskmatch.dynamic.report.report",return_value=self.fixture()):
            status,response=request.do_POST()
        self.assertEqual(status,200)
        self.assertEqual(response["status"],"reconciled")
