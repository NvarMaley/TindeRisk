import importlib.util
import json
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

import pytest


def test_discovery_session_and_score_http():
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location("riskmatch_discovery_server",root/"apps/api/server.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with module.ThreadingHTTPServer(("127.0.0.1",0),module.Handler) as server:
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        opener=build_opener(ProxyHandler({}));base=f"http://127.0.0.1:{server.server_port}"
        def post(path,payload):
            req=Request(base+path,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
            with opener.open(req,timeout=5) as response:return json.load(response)
        try:
            s=post("/api/discovery/session",{"seed":42,"currency":"CHF"})
            assert len(s["cards"])==30 and s["cards"]==post("/api/discovery/session",{"seed":43,"currency":"CHF"})["cards"]
            answers={c["id"]:c["prudent_response"] for c in s["cards"] if c["scored"]}
            result=post("/api/discovery/score",{"seed":42,"currency":"CHF","answers":answers,"confidence":3,"locales":{k:"fr" for k in answers}})
            assert result["score"]==30 and result["confidence"]==3
            with pytest.raises(HTTPError) as exc:post("/api/discovery/score",{"seed":42,"currency":"CHF","answers":{"bad":"like"}})
            assert exc.value.code==400
        finally:
            server.shutdown();thread.join(timeout=5)
