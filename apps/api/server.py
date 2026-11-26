"""Loopback-only MVP HTTP service; no persistence or trading endpoints."""
import json
import sys
from datetime import date
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from riskmatch.prototype import ClientProfile, cards, score, candidates
from riskmatch.matching import allocate, research_report
from riskmatch import historical_matches
from riskmatch import personalized_matches
from riskmatch.profiling.mandate import validate_mandate, SCHEMA_VERSION
from riskmatch.behavioral.discovery import session as discovery_session, score as discovery_score
from riskmatch.market_data.security_master import universe_report
from riskmatch.market_data.source_catalog import source_report
from riskmatch.market_data.point_in_time import snapshot_report
from riskmatch.market_data.returns import returns_report
from riskmatch.analytics.descriptive_report import descriptive_report, assets as descriptive_assets, compare as descriptive_compare, compare_series, client_catalog
from riskmatch.analytics.forecast_report import asset_forecast
from riskmatch.analytics.forecast_batch import batch_report, batch_asset
from riskmatch.analytics.risk_report import risk_batch_report, risk_batch_asset, asset_risk, matrix_risk
from riskmatch.analytics.factor_report import factor_report, factor_asset
from riskmatch.analytics.tail_report import tail_report, tail_asset, tail_matrix
from riskmatch.analytics.objectives_report import objective_report
from riskmatch.backtesting.baseline_report import baseline_report
from riskmatch.optimization.mean_variance_report import cached_report as mean_variance_report
from riskmatch.optimization.black_litterman_report import cached_report as black_litterman_report
from riskmatch.analytics.sentiment_report import sentiment_report, sentiment_asset
from riskmatch.optimization.hierarchical_report import cached_report as hierarchical_report
from riskmatch.optimization.downside_report import cached_report as downside_report
from riskmatch.optimization.advanced_report import cached_report as advanced_report
from riskmatch.strategies.long_only_report import cached_report as long_only_report
from riskmatch.strategies.alternative_report import run_report as alternative_report
from riskmatch.analytics.treasury_report import run_report as treasury_report
from riskmatch.analytics.futures_report import report as futures_report
from riskmatch.backtesting.walk_report import cached_report as walk_report
from riskmatch.simulation.stress_report import cached_report as stress_report


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "apps/web"), **kwargs)

    def respond(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/cards":
            return self.respond(cards())
        if self.path == "/api/health":
            return self.respond({"status": "ok", "mode": "simulation", "client_flow": 30, "matching_engine": personalized_matches.VERSION})
        return super().do_GET()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length < 65536:
                raise ValueError("Invalid request size")
            data = json.loads(self.rfile.read(length))
            if self.path == "/api/paper/quotes":
                from riskmatch.market_data.paper_quotes import quotes
                return self.respond(quotes(ROOT, data["symbols"]))
            if self.path == "/api/matching/prepare":
                raw=data["mandate"]
                if not validate_mandate(raw)["personalized_eligible"] or raw["as_of"]<"2026-11-25":
                    raise ValueError("demoUnavailable")
                with personalized_matches.LOCK:
                    data=personalized_matches.market_data(ROOT.resolve())
                return self.respond({"status":"ready","count":len(personalized_matches.KEYS),
                                     "universe_size":len(data[0])})
            if self.path == "/api/match-allocations/goal":
                from riskmatch.selection.goals import compare_allocations
                return self.respond(compare_allocations(ROOT,data))
            if self.path == "/api/matching/goals":
                from riskmatch.selection.goals import assess
                return self.respond(assess(ROOT,data))
            if self.path == "/api/paper/export":
                from riskmatch.dynamic.report import report
                from riskmatch.integration import export_simulation
                return self.respond(export_simulation(report(ROOT,data),data["policy"]))
            if self.path == "/api/dynamic":
                from riskmatch.dynamic.report import report
                return self.respond(report(ROOT,data))
            if self.path == "/api/matching/improvements":
                from riskmatch.improvement import compare_variants
                return self.respond(compare_variants(ROOT))
            if self.path == "/api/matching/research":
                return self.respond(research_report(ROOT))
            if self.path in ("/api/matching/cards", "/api/match-allocations/evaluate", "/api/match-allocations/optimize"):
                raw = data['mandate']
                if raw.get('schema_version') == SCHEMA_VERSION:
                    if self.path == "/api/matching/cards":
                        return self.respond(personalized_matches.run(ROOT,raw,data.get("aversion"),data.get("style","000"))["cards"])
                    if personalized_matches.is_version(data.get("version")):
                        return self.respond(personalized_matches.blend(
                            ROOT,raw,data["version"],data["names"],data.get("budgets"),
                            self.path.endswith("/optimize")))
                if raw.get('schema_version') == SCHEMA_VERSION:
                    report = validate_mandate(raw)
                    if not report['demo_eligible']:
                        raise ValueError('demoUnavailable')
                    profile = ClientProfile(raw['capital'], report['horizon_years'], report['effective_stress_limit'])
                else:
                    profile = ClientProfile(**raw)
                if self.path == "/api/matching/cards" or data.get("version") == historical_matches.VERSION:
                    if raw.get("schema_version") == SCHEMA_VERSION and raw["as_of"] < "2026-11-25":
                        raise ValueError("Historical archive unavailable at mandate date")
                    if self.path == "/api/matching/cards":
                        return self.respond(historical_matches.cards(ROOT, profile,data.get("aversion"),raw.get("goals",[])))
                    return self.respond(historical_matches.blend(ROOT, profile, data["names"], data.get("budgets"),
                                                                self.path.endswith("/optimize")))
                return self.respond(allocate(profile, data['names'], data.get('budgets'),
                                             self.path.endswith('/optimize'), data['version']))
            if self.path == "/api/score":
                return self.respond(score(data))
            if self.path == "/api/discovery/session":
                return self.respond(discovery_session(data["seed"], data["currency"]))
            if self.path == "/api/discovery/score":
                return self.respond(discovery_score(data["seed"], data["currency"], data["answers"],
                                                     data.get("confidence"), data.get("locales")))
            if self.path == "/api/mandate/preview":
                return self.respond(validate_mandate(data))
            if self.path == "/api/objectives/evaluate":
                return self.respond(objective_report(ROOT,data))
            if self.path == "/api/baselines":
                return self.respond(baseline_report(ROOT,data))
            if self.path == "/api/mean-variance":
                return self.respond(mean_variance_report(ROOT,data))
            if self.path == "/api/black-litterman":
                return self.respond(black_litterman_report(ROOT,data))
            if self.path == "/api/hierarchical":
                return self.respond(hierarchical_report(ROOT,data))
            if self.path == "/api/downside":
                return self.respond(downside_report(ROOT,data))
            if self.path == "/api/advanced":
                return self.respond(advanced_report(ROOT,data))
            if self.path == "/api/long-only":
                return self.respond(long_only_report(ROOT,data))
            if self.path == "/api/alternative":
                return self.respond(alternative_report(ROOT,data))
            if self.path == "/api/treasury":
                return self.respond(treasury_report(ROOT,data))
            if self.path == "/api/futures":
                return self.respond(futures_report(ROOT,data))
            if self.path == "/api/walk-forward":
                return self.respond(walk_report(ROOT,data))
            if self.path == "/api/stress-mc":
                return self.respond(stress_report(ROOT,data))
            if self.path in ("/api/sentiment","/api/sentiment/asset"):
                as_of=date.fromisoformat(data['as_of'])
                if as_of>date.today() or as_of<date(1900,1,1):raise ValueError('invalid_universe_date')
                return self.respond(sentiment_asset(ROOT,as_of,data['id']) if self.path.endswith('/asset') else sentiment_report(ROOT,as_of))
            if self.path == "/api/universe":
                as_of = date.fromisoformat(data["as_of"])
                if as_of > date.today() or as_of < date(1900, 1, 1):
                    raise ValueError("invalid_universe_date")
                return self.respond(universe_report(as_of))
            if self.path == "/api/sources":
                as_of=date.fromisoformat(data["as_of"])
                if as_of>date.today() or as_of<date(1900,1,1):raise ValueError("invalid_universe_date")
                return self.respond(source_report(as_of))
            if self.path == "/api/snapshot":
                as_of = date.fromisoformat(data["as_of"])
                if as_of > date.today() or as_of < date(1900, 1, 1):
                    raise ValueError("invalid_universe_date")
                return self.respond(snapshot_report(ROOT, as_of))
            if self.path == "/api/returns":
                as_of = date.fromisoformat(data["as_of"])
                if as_of > date.today() or as_of < date(1900,1,1):
                    raise ValueError("invalid_universe_date")
                return self.respond(returns_report(ROOT, as_of))
            if self.path in ("/api/tail/universe","/api/tail/universe/asset","/api/tail/matrix"):
                as_of=date.fromisoformat(data['as_of'])
                if as_of>date.today() or as_of<date(1900,1,1):raise ValueError('invalid_universe_date')
                if self.path.endswith('/matrix'):return self.respond(tail_matrix(ROOT,as_of,data))
                return self.respond(tail_asset(ROOT,as_of,data['id']) if self.path.endswith('/asset') else tail_report(ROOT,as_of))
            if self.path in ("/api/factors/universe","/api/factors/universe/asset"):
                as_of=date.fromisoformat(data["as_of"])
                if as_of>date.today() or as_of<date(1900,1,1):
                    raise ValueError("invalid_universe_date")
                return self.respond(factor_asset(ROOT,as_of,data["id"]) if self.path.endswith("/asset") else factor_report(ROOT,as_of))
            if self.path in ("/api/risk/universe","/api/risk/universe/asset","/api/risk/asset","/api/risk/matrix"):
                as_of=date.fromisoformat(data["as_of"])
                if as_of>date.today() or as_of<date(1900,1,1):
                    raise ValueError("invalid_universe_date")
                if self.path=="/api/risk/universe":
                    return self.respond(risk_batch_report(ROOT,as_of))
                if self.path=="/api/risk/universe/asset":
                    return self.respond(risk_batch_asset(ROOT,as_of,data["id"]))
                start,end=date.fromisoformat(data["start"]),date.fromisoformat(data["end"])
                if self.path=="/api/risk/asset":
                    return self.respond(asset_risk(ROOT,data["source"],data["instrument"],start,end,data["currency"],data["kind"],as_of))
                return self.respond(matrix_risk(ROOT,data["series"],start,end,data["currency"],data["kind"],as_of))
            if self.path in ("/api/forecast/universe","/api/forecast/universe/asset"):
                as_of=date.fromisoformat(data["as_of"])
                if as_of>date.today() or as_of<date(1900,1,1):
                    raise ValueError("invalid_universe_date")
                if self.path.endswith("/asset"):
                    return self.respond(batch_asset(ROOT,as_of,data["id"]))
                return self.respond(batch_report(ROOT,as_of))
            if self.path == "/api/forecast":
                as_of=date.fromisoformat(data["as_of"])
                if as_of>date.today() or as_of<date(1900,1,1):
                    raise ValueError("invalid_universe_date")
                return self.respond(asset_forecast(ROOT,data["source"],data["instrument"],
                    date.fromisoformat(data["start"]),date.fromisoformat(data["end"]),
                    data["currency"],data["kind"],as_of,data.get("include_ml",False)))
            if self.path in ("/api/statistics","/api/statistics/assets","/api/statistics/compare","/api/statistics/catalog"):
                as_of = date.fromisoformat(data["as_of"])
                if as_of>date.today() or as_of<date(1900,1,1):
                    raise ValueError("invalid_universe_date")
                if self.path=="/api/statistics":
                    return self.respond(descriptive_report(ROOT,as_of))
                if self.path=="/api/statistics/catalog":
                    return self.respond(client_catalog(ROOT,as_of))
                if self.path=="/api/statistics/assets":
                    return self.respond(descriptive_assets(ROOT,data["source"],as_of))
                if "series" in data:
                    return self.respond(compare_series(ROOT,data["series"],date.fromisoformat(data["start"]),
                        date.fromisoformat(data["end"]),data["currency"],data["kind"],as_of))
                return self.respond(descriptive_compare(ROOT,data["source"],data["instruments"],
                    date.fromisoformat(data["start"]),date.fromisoformat(data["end"]),data["currency"],data["kind"],as_of))
            if self.path == "/api/candidates":
                if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION:
                    report = validate_mandate(data)
                    if not report["demo_eligible"]:
                        return self.respond({"error": "demoUnavailable"}, 400)
                    return self.respond(candidates(ClientProfile(data["capital"], report["horizon_years"],
                                                                 report["effective_stress_limit"])))
                return self.respond(candidates(ClientProfile(**data)))
            return self.respond({"error": "Not found"}, 404)
        except (ValueError, TypeError, KeyError) as exc:
            return self.respond({"error": str(exc)}, 400)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 3000), Handler).serve_forever()
