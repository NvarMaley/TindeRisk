"""Reproducible local evidence using the same JSON contracts as the web app."""

import base64
import hashlib
import io
import json
import runpy
import zipfile
from collections import Counter
from html import escape
from pathlib import Path
from time import perf_counter

from IPython.display import HTML, SVG, display


class Evidence:
    def __init__(self, root):
        self.root = Path(root)
        self.handler = runpy.run_path(str(self.root / "apps/api/server.py"))["Handler"]
        self.date = {"as_of": "2026-11-25"}
        self.core = self.date | {"scope": "core", "currency": "USD"}
        self.cohort = self.core | {"scope": "cohort"}
        self.mandate = json.loads((self.root / "configs/mandate-example.json").read_text())
        self.mandate.update(self.date)
        self.results = []
        self.selection = None

    def call(self, chapter, route, payload, show=True):
        request = object.__new__(self.handler)
        body = json.dumps(payload).encode()
        request.path = "/api/" + route
        request.headers = {"Content-Length": str(len(body))}
        request.rfile = io.BytesIO(body)
        request.wfile = io.BytesIO()
        status = []
        request.send_response = status.append
        request.send_header = lambda *_: None
        request.end_headers = lambda: None
        start = perf_counter()
        request.do_POST()
        duration = perf_counter() - start
        result = json.loads(request.wfile.getvalue())
        assert status == [200], (chapter, route, status, result)
        state = result.get("status", "response received") if isinstance(result, dict) else f"{len(result)} records"
        self.results.append({"chapter": chapter, "route": route, "http": status[0],
                             "status": state, "seconds": round(duration, 3)})
        print(f"Chapter {chapter:02} | {route} | HTTP {status[0]} | {state} | {duration:.2f}s")
        if show:
            self.show(route, payload, result)
        return result

    @staticmethod
    def show(route, payload, result):
        # Retain the complete response, including failure reasons and diagnostics.
        # Nested sections keep extensive historical ledgers and universe tables navigable.
        def details(label, value):
            content = json.dumps(value, ensure_ascii=False, indent=2)
            size = len(value) if isinstance(value, (list, dict)) else ""
            return (f"<details><summary>{escape(str(label))} {size} </summary>"
                    f"<pre style='max-height:500px;overflow:auto'>{escape(content)}</pre></details>")
        parts = [f"<h4>{escape(route)}</h4>", details("Request", payload)]
        if isinstance(result, dict):
            top = {k: v for k, v in result.items() if not isinstance(v, (list, dict))}
            if top:
                parts.append("<table>" + "".join(
                    f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in top.items()
                ) + "</table>")
            parts.extend(details(k, v) for k, v in result.items() if isinstance(v, (list, dict)))
        else:
            parts.append(details("All records", result))
        display(HTML("".join(parts)))
        if isinstance(result, dict):
            import pandas as pd
            for group in ("models", "strategies", "policies", "benchmarks", "comparison"):
                records = result.get(group)
                if not isinstance(records, dict) or not all(isinstance(v, dict) for v in records.values()):
                    continue
                metrics = {}
                for key, row in records.items():
                    scalars = {k: v for k, v in row.items() if k in (
                        "status", "reason", "expected_return", "volatility", "sharpe", "cvar",
                        "annual_mean", "annual_volatility", "cagr", "drawdown", "ending",
                        "fees", "annual_turnover", "final_nav", "worst_shock", "objective_error")}
                    if isinstance(row.get("locked"), dict):
                        scalars.update({"holdout_" + k: v for k, v in row["locked"].items()
                                        if isinstance(v, (float, int))})
                    metrics[key] = scalars
                if any(metrics.values()):
                    display(HTML(f"<h5>{escape(group)} — metric comparison</h5>"))
                    display(pd.DataFrame.from_dict(metrics, orient="index"))

    @staticmethod
    def wealth_plot(title, paths):
        """Compare net wealth paths at base 100, without a plotting dependency."""
        import numpy as np
        paths = {name: 100 * np.asarray(values, float) / values[0]
                 for name, values in paths.items() if len(values) > 1 and values[0] > 0}
        if not paths:
            return
        low = min(v.min() for v in paths.values())
        high = max(v.max() for v in paths.values())
        span = max(high - low, 1.)
        palette = ("#146C82", "#B24B27", "#6554C0", "#397A45")
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="760" viewBox="0 0 760 275">',
                 f'<text x="58" y="22" font-size="15">{escape(title)}</text>']
        for tick in np.linspace(low, high, 5):
            y = 220 - 175 * (tick - low) / span
            parts.append(f'<path d="M58 {y:.2f}h680" stroke="#ccc"/><text x="4" y="{y+4:.2f}" font-size="11">{tick:.1f}</text>')
        for index, ((label, values), color) in enumerate(zip(paths.items(), palette)):
            points = " ".join(f"{58+680*i/(len(values)-1):.2f},{220-175*(v-low)/span:.2f}"
                              for i, v in enumerate(values))
            parts.append(f'<polyline points="{points}" stroke="{color}" stroke-width="2" fill="none"/>')
            parts.append(f'<text x="{58+175*index}" y="258" fill="{color}" font-size="12">{escape(label)}</text>')
        parts.append('<text x="58" y="238" font-size="11">Start (100)</text><text x="680" y="238" font-size="11">End</text></svg>')
        display(SVG("".join(parts)))

    def archive(self, name, report):
        """Check each asset record of the frozen universe, plus provenance."""
        filename = "results.jsonl" if name == "forecasts" else "assets.jsonl"
        path = self.root / "data/processed" / name / report["run_id"] / filename
        expected_hash = report["file_hash"] if name == "forecasts" else report["files"][filename]
        with path.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == expected_hash
        with path.open() as stream:
            rows = [json.loads(line) for line in stream]
        identities = {r["id"] for r in rows}
        states = Counter(r["status"] for r in rows)
        assert len(identities) == len(rows) == report["catalogue_count"]
        assert dict(states) == report["statuses"]
        index = [{k: r.get(k) for k in ("id", "ticker", "category", "status", "reason",
                                       "source", "frequency", "last", "missing_models")}
                 for r in rows]
        print(f"{name}: {len(rows)} asset records verified, SHA-256 matches, {dict(states)}")
        self.show(f"{name} — all archived asset statuses", {},
                  {"file": str(path.relative_to(self.root)), "sha256": expected_hash,
                   "status_counts": dict(states), "per_asset": index})
        return path

    def asset_record(self, name, asset_id):
        """Show the complete stored result for any catalogue ID in the current run."""
        folder = self.root / "data/processed" / name
        report = json.loads((folder / "report.json").read_text())
        path = folder / report["run_id"] / ("results.jsonl" if name == "forecasts" else "assets.jsonl")
        with path.open() as stream:
            for line in stream:
                row = json.loads(line)
                if row["id"] == asset_id:
                    self.show(f"{name} — {asset_id}", {}, row)
                    return row
        raise KeyError(asset_id)

    def chapter(self, n):
        call = lambda route, payload, **kwargs: self.call(n, route, payload, **kwargs)
        if n == 1:
            report = call("mandate/preview", self.mandate)
            assert report["personalized_eligible"]
        elif n == 2:
            session = call("discovery/session", {"seed": 42, "currency": "USD"})
            answers = {c["id"]: "dislike" for c in session["cards"]}
            report = call("discovery/score", {"seed": 42, "currency": "USD", "answers": answers})
            self.aversion = report["score"]
            assert self.aversion is not None
            assert len(session["cards"]) == 30 and report["total_scored"] == 20
            assert [row["loss"] for row in report["mixed_gain_thresholds"]] == [100, 500]
        elif n in (3, 4, 5, 6):
            call({3: "universe", 4: "sources", 5: "snapshot", 6: "returns"}[n], self.date)
            if n == 3:
                portfolio_universe = call("statistics/catalog", self.date | {"scope": "matching"})
                counts = Counter(row["category"] for row in portfolio_universe["items"])
                assert counts.keys() == {"stock", "equity_etf", "treasury_etf", "cash"}
                assert counts["cash"] == 1
                assert portfolio_universe["matching_months"] == 60
                assert portfolio_universe["matching_data_end"] == "2025-12-31"
                print("Matching universe at the frozen cutoff:", dict(sorted(counts.items())))
        elif n == 7:
            call("statistics", self.date)
            catalogue = call("statistics/catalog", self.date)
            item = next(i for i in catalogue["items"] if i["ticker"] == "SPY" and i["series"])
            self.asset = item["id"]
            second = next(i for i in catalogue["items"] if i["ticker"] == "IEF" and i["series"])
            first_series = next(s for s in item["series"]
                                if any(t["source"] == s["source"] for t in second["series"]))
            second_series = next(s for s in second["series"] if s["source"] == first_series["source"])
            self.series = [{"source": s["source"], "instrument": s["instrument"]}
                           for s in (first_series, second_series)]
            self.asset_query = self.date | {"id": self.asset}
            self.comparison = self.date | {"series": self.series, "currency": "USD",
                                           "kind": "total_return", "start": "2015-01-01",
                                           "end": self.date["as_of"]}
            call("statistics/compare", self.comparison)
        elif n in (8, 9, 10, 11):
            route = {8: "forecast/universe", 9: "risk/universe", 10: "factors/universe",
                     11: "tail/universe"}[n]
            report = call(route, self.date)
            self.archive({8: "forecasts", 9: "risk", 10: "factors", 11: "tail"}[n], report)
            call(route + "/asset", self.asset_query)
            if n == 8:
                call("sentiment", self.date)
            if n == 9:
                call("risk/matrix", self.comparison)
            if n == 11:
                call("tail/matrix", self.comparison)
        elif n == 12:
            call("objectives/evaluate", self.mandate)
            # Evaluate all eleven objective types in isolation on identical inputs.
            from riskmatch.analytics.objectives import SPECS
            for objective in SPECS:
                goal = self.mandate["goals"][0] | {"objective_id": objective,
                                                  "funding": objective in {"OBJ09", "OBJ10"}}
                if objective == "OBJ02":
                    goal["amount"] = 500
                example = self.mandate | {"goals": [goal]}
                if objective == "OBJ02":
                    example["withdrawal_monthly"] = 500
                call("objectives/evaluate", example)
        elif n == 13:
            call("baselines", self.core)
        elif n in range(14, 21):
            routes = ("mean-variance", "black-litterman", "hierarchical", "downside",
                      "advanced", "long-only", "alternative")
            call(routes[n - 14], self.core)
            call(routes[n - 14], self.cohort)
        elif n == 21:
            call("treasury", self.date)
        elif n == 22:
            call("futures", self.date)
        elif n == 23:
            report = call("walk-forward", self.core)
            self.wealth_plot("Walk-forward net wealth — base 100", {
                "60/40": report["benchmarks"]["sixty_forty"]["nav"],
                "Cash": report["benchmarks"]["cash"]["nav"],
                "Mean variance": report["strategies"]["mean_variance_utility"]["nav"]})
            call("walk-forward", self.cohort)
        elif n == 24:
            settings = {"months": 60, "paths": 1000, "contribution": 500.,
                        "target": 150000., "frequency": 3, "include_instrument_examples": True}
            call("stress-mc", self.core | settings)
            call("stress-mc", self.cohort | settings)
        elif n == 25:
            call("matching/research", {})
            call("matching/improvements", {})
            call("matching/prepare", {"mandate": self.mandate})
            cards = call("matching/cards", {"mandate": self.mandate, "aversion": self.aversion})
            assert len(cards) >= 2
            for card in cards:
                assert card["estimation_months"] == 60 and card["model_as_of"] == "2025-12-31"
                test = card["backtest"]["test"]
                assert (test["months"], test["start"], test["end"]) == (25, "2023-11-30", "2025-12-31")
                assert card["backtest"]["development"]["months"] == 35
            assert abs(cards[0]["risk_aversion_parameter"] - (1 + 13.3 * cards[0]["fit_risk_weight"] ** 2)) < 1e-10
            alternative_score = 1 if self.aversion > 15 else 30
            alternative = call("matching/cards", {"mandate": self.mandate, "aversion": alternative_score})
            first_utility = next(c for c in cards if "mean_variance_utility" in [c["name"], *c.get("equivalent_methods", [])])
            other_utility = next(c for c in alternative if "mean_variance_utility" in [c["name"], *c.get("equivalent_methods", [])])
            assert first_utility["version"] != other_utility["version"]
            assert first_utility["weights"] != other_utility["weights"]
            import copy
            restricted = copy.deepcopy(self.mandate)
            restricted["constraints"]["allowed_assets"] = ["treasury", "cash"]
            restricted["constraints"]["max_asset_weight"]["value"] = .25
            restricted["constraints"]["volatility"]["value"] = .07
            restricted["constraints"]["stress_loss"]["value"] = .08
            treasury = call("matching/cards", {"mandate": restricted, "aversion": 27})
            assert treasury
            for candidate in treasury:
                assert candidate["stress_loss"] <= .08 + 1e-8
                assert candidate["estimated_volatility"] <= .07 + 1e-7
                assert all(value <= .25 + 1e-8 for value in candidate["weights"].values())
                assert all(value <= 1e-8 for name, value in candidate["weights"].items()
                           if name not in {"BIL", "SHY", "IEF", "TLT", "TIP", "USD cash"})
            import pandas as pd
            display(pd.DataFrame({"Original risk score": {
                "score": self.aversion, "stress": first_utility["stress_loss"],
                "volatility": first_utility["estimated_volatility"], "cash": first_utility["weights"]["USD cash"]},
                "Alternative risk score": {
                "score": alternative_score, "stress": other_utility["stress_loss"],
                "volatility": other_utility["estimated_volatility"], "cash": other_utility["weights"]["USD cash"]}}))
            self.selection = {"mandate": self.mandate, "version": cards[0]["version"],
                              "names": [c["name"] for c in cards[:2]], "budgets": [.6, .4]}
            manual = call("match-allocations/evaluate", self.selection)
            optimized = call("match-allocations/optimize", self.selection)
            goal_mix = call("match-allocations/goal", self.selection)
            assert goal_mix["comparison"]["goal"]["score"] >= goal_mix["comparison"]["manual"]["score"]
            for result in (manual, optimized, goal_mix):
                assert abs(sum(result["weights"].values()) - 1) < 1e-7
                assert result["stress_loss"] <= .20 + 1e-8
            import pandas as pd
            display(pd.DataFrame({"Manual": manual["budgets"], "Optimized": optimized["budgets"]}))
            display(pd.DataFrame({"Manual": manual["weights"], "Optimized": optimized["weights"]}))
            self.wealth_plot("Matches — historical net wealth (holdout)", {
                "Manual 60/40 sleeves": manual["metrics"]["nav"],
                "Optimized sleeves": optimized["metrics"]["nav"]})
            call("matching/goals", self.selection)
        elif n == 26:
            self.dynamic = call("dynamic", self.selection)
            assert self.dynamic["policies"]["mpc"]["status"] == "computed"
            import pandas as pd
            display(pd.DataFrame.from_dict(
                {name: {k: result.get(k) for k in ("status", "cagr", "volatility", "drawdown",
                                                    "fees", "ending", "annual_turnover")}
                 for name, result in self.dynamic["policies"].items()}, orient="index"))
            self.wealth_plot("Dynamic management — historical net wealth (holdout)", {
                name: self.dynamic["policies"][name]["nav"]
                for name in ("static", "drift", "mpc", "robust_control")})
        elif n == 27:
            result = call("paper/export", self.selection | {"policy": "mpc"}, show=False)
            assert result["status"] == "reconciled"
            with zipfile.ZipFile(io.BytesIO(base64.b64decode(result["archive"]))) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                assert set(archive.namelist()) == set(manifest["files"]) | {"manifest.json"}
                for name, digest in manifest["files"].items():
                    assert hashlib.sha256(archive.read(name)).hexdigest() == digest
                self.show("paper/export — manifest and audit", self.selection,
                          {"run_id": result["run_id"], "manifest": manifest,
                           "audit": json.loads(archive.read("audit.json"))})
            import pandas as pd
            display(pd.DataFrame(self.results))
