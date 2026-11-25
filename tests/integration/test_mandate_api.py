"""Exercise actual local HTTP contracts with a synthetic profile only."""

import importlib.util
import json
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_mandate_api_preview_and_candidate_gate():
    spec = importlib.util.spec_from_file_location("riskmatch_local_server", ROOT / "apps/api/server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with module.ThreadingHTTPServer(("127.0.0.1", 0), module.Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        opener = build_opener(ProxyHandler({}))

        def post(path, data):
            request = Request(url+path, data=json.dumps(data).encode(), headers={"Content-Type":"application/json"})
            return json.load(opener.open(request, timeout=5))

        try:
            fixture = json.loads((ROOT / "configs/mandate-example.json").read_text())
            result = post("/api/mandate/preview", fixture)
            assert result["status"] == "structurally_valid"
            assert post("/api/candidates", fixture)
            fixture["constraints"]["max_cost"]["value"] = .01
            assert not post("/api/mandate/preview", fixture)["demo_eligible"]
            with pytest.raises(HTTPError) as exc:
                post("/api/candidates", fixture)
            assert exc.value.code == 400
            fixture["consent"] = False
            with pytest.raises(HTTPError) as exc:
                post("/api/mandate/preview", fixture)
            assert exc.value.code == 400
        finally:
            server.shutdown()
            thread.join(timeout=5)
