import importlib.util
import json
from pathlib import Path
from threading import Thread
from urllib.request import Request, build_opener, ProxyHandler

from riskmatch.market_data.security_master import universe_report


def test_universe_api_uses_coverage_without_approving_allocations(tmp_path):
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location("riskmatch_universe_server",root/"apps/api/server.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.universe_report=lambda as_of: universe_report(as_of,price_path=root/"configs/universe-coverage-example.csv",
                                                        rate_path=tmp_path/"missing.csv",records_dir=tmp_path)
    with module.ThreadingHTTPServer(("127.0.0.1",0),module.Handler) as server:
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        opener=build_opener(ProxyHandler({}))
        request=Request(f"http://127.0.0.1:{server.server_port}/api/universe",data=json.dumps({"as_of":"2018-06-20"}).encode(),headers={"Content-Type":"application/json"})
        try:
            with opener.open(request,timeout=5) as response:result=json.load(response)
            assert len(result["rows"])==27 and result["eligible_count"]==0
            xlc=next(r for r in result["rows"] if r["ticker"]=="XLC")
            assert xlc["coverage"]["prelaunch_rejected"]==2 and "market_data_not_validated" in xlc["reasons"]
        finally:
            server.shutdown();thread.join(timeout=5)
