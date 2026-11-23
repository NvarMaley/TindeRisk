"""Produce the published section 6 experiment from the frozen section 4 catalogue."""

from dataclasses import replace
from functools import lru_cache
from hashlib import sha256, file_digest
from importlib.metadata import version
from tempfile import TemporaryDirectory
from pathlib import Path
import json

import numpy as np
import pandas as pd
from ..benchmark import write_json
from ..library.controls import exposure
from ..library.sources import checked
from ..feasibility.orders import orders
from .compare import LABELS, combine, distinct, metrics, mix_search, models, weights
from .replay import replay, tape
from .scoring import rank
from .scenarios import scoring_controls
from .scoring import FAMILIES

REPORT = Path("reports/06-options")
CONFIG = Path("config/options-6.json")


def context():
    cfg = json.loads(CONFIG.read_bytes())
    params = json.loads(Path("config/faisabilite-5.json").read_bytes())
    cat = Path("data/local/4") / cfg["catalogue"]
    prices = pd.read_parquet(cat / "prices.parquet")
    events = pd.read_parquet(cat / "events.parquet")
    prices["symbol"] = prices.id.str.rsplit("-", n=1).str[-1]
    daily = prices.pivot(
        index="day", columns="symbol", values="return_chf"
    ).sort_index()
    levels = prices.assign(level=prices.adjusted * prices.fx).pivot(
        index="day", columns="symbol", values="level"
    )
    a, b = cfg["stress"]
    shock = (levels.loc[b] / levels.loc[a] - 1).to_numpy()
    assert np.isfinite(shock).all() and b < cfg["start"]
    t = tape(prices, events, cfg["start"], cfg["end"])
    return cfg, params, cat, daily, shock, t


def round_option(m, w, t, cfg, low=0.0, high=None, existing=None):
    p = m[0]
    high = cfg["risk_cap"] if high is None else high
    units = np.zeros(len(w)) if existing is None else existing
    order = orders(
        p,
        w,
        cfg["pocket"],
        t.usd[-1],
        np.full(len(w), t.fx[-1]),
        np.ones(len(w)),
        units,
        low=low,
        high=high,
        max_trials=400,
    )
    return order


def dated_concentration(w, names, holdings, instant):
    risky = float(sum(w))
    if risky <= 1e-8:
        return dict(largest=0.0, unknown_weight=0.0, issuer=None)
    fractions = {k: float(v / risky) for k, v in zip(names, w) if v > 0}
    view = exposure(fractions, holdings, {}, instant)
    ass = view["issuers"]
    largest = max(ass, key=ass.get) if ass else None
    return dict(
        largest=risky * ass.get(largest, 0),
        issuer=largest,
        unknown_weight=risky * view["unknown_gross"],
    )


def aggregate_card(m, w, shock, result, cfg):
    card = metrics(
        m, w, shock, cfg.get("risk_low", 0.0), cfg["risk_cap"], cfg["rf_chf"]
    )
    card.update(
        cagr=result["cagr"],
        drawdown=result["drawdown"],
        tradable=False,
        goal_margin=card["net"] - cfg["goal"],
        goal_gap_chf=(card["net"] - cfg["goal"]) * cfg["pocket"],
    )
    return card


def mixed_plan(plans, names, shares):
    dates = sorted(plans[names[0]])
    if any(sorted(plans[name]) != dates for name in names):
        raise ValueError("Incompatibility of decision time frames")
    return {day: combine([plans[name][day] for name in names], shares) for day in dates}


def cashflows():
    return {"2022-03-31": -1000.0}


def blended_card(m, components, names, shares, plans, t, shock, cfg):
    for name in names:
        if not m[0].evaluate(
            components[name], cfg.get("risk_low", 0.0), cfg["risk_cap"]
        )["valid"]:
            raise ValueError("Non-mandate component: " + name)
    w = combine([components[n] for n in names], shares)
    instructions = mixed_plan(plans, names, shares)
    hist = replay(
        t,
        instructions,
        cfg["pocket"],
        cfg["reserve"],
        flows=cashflows(),
        risk_cap=cfg["risk_cap"],
    )[0]
    c = aggregate_card(m, w, shock, hist, cfg)
    rounded = (
        round_option(m, w, t, cfg, low=cfg.get("risk_low", 0.0)) if c["valid"] else None
    )
    if rounded and rounded["order"]:
        rounded["indicators"] = metrics(
            m,
            np.array(rounded["order"]["candidate"]["weights"]),
            shock,
            cfg.get("risk_low", 0.0),
            cfg["risk_cap"],
            cfg["rf_chf"],
        )
        whole_history = replay(
            t,
            instructions,
            cfg["pocket"],
            cfg["reserve"],
            flows=cashflows(),
            whole=True,
            risk_cap=cfg["risk_cap"],
        )[0]
        rounded["indicators"].update(
            cagr=whole_history["cagr"], drawdown=whole_history["drawdown"]
        )
        rounded["scores"] = {
            profile: rank({"mix": rounded["indicators"]}, criteria, cfg, research=True)[
                "rows"
            ]["mix"]["total"]
            for profile, criteria in cfg["profiles"].items()
        }
    nearest = (
        None
        if c["valid"]
        else min(names, key=lambda n: float(np.linalg.norm(components[n] - w)))
    )
    return dict(
        parts=dict(zip(names, map(float, shares))),
        card=c,
        historical=hist,
        rounding=rounded,
        alternative=nearest,
    )


def main():
    cfg, params, cat, daily, shock, t = context()
    manifest = json.loads((cat / "manifest.json").read_bytes())
    for file in [
        "prices.parquet",
        "events.parquet",
        "holdings.parquet",
        "decision.parquet",
    ]:
        checked(cat / file, manifest["products"][file])
    here = Path(__file__).parent
    dependencies = [
        here.parent / "feasibility" / (n + ".py")
        for n in ("study", "orders", "inputs", "engine")
    ]
    dependencies.append(here.parent / "library/controls.py")
    environment = {
        n: version(n)
        for n in (
            "numpy",
            "pandas",
            "scipy",
            "cvxpy",
            "clarabel",
            "scikit-learn",
            "pyarrow",
        )
    }
    source = sha256(
        json.dumps(environment, sort_keys=True).encode()
        + b"".join(p.read_bytes() for p in dependencies)
        + CONFIG.read_bytes()
        + Path("config/faisabilite-5.json").read_bytes()
        + (cat / "manifest.json").read_bytes()
        + b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))
    ).hexdigest()[:16]
    target = Path("data/local/6") / cfg["version"] / source

    def publish():
        manifest = json.loads((target / "manifest.json").read_bytes())
        for name, digest in manifest.items():
            checked(target / name, digest)
        write_json(
            REPORT / "resultats.json",
            json.loads((target / "summary.json").read_bytes()),
        )

    if target.is_dir():
        publish()
        print("Section 6 Archive verified", target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as temp:
        folder = Path(temp) / "archive"
        folder.mkdir()
        build(cfg, params, cat, daily, shock, t, source, folder)
        hashes = {}
        for path in folder.iterdir():
            with path.open("rb") as stream:
                hashes[path.name] = file_digest(stream, "sha256").hexdigest()
        write_json(folder / "manifest.json", hashes)
        try:
            folder.rename(target)
        except OSError:
            if not target.is_dir():
                raise
    publish()
    print("Section 6 published", target)


def build(cfg, params, cat, daily, shock, t, source, folder):
    cdate = cfg["market"]

    @lru_cache
    def dated(day):
        return models(daily.loc[:day], params)

    m = dated(cdate)
    opt = weights(m, shock, cfg["risk_cap"], cfg["return_concession"])
    calc, aliases = distinct(opt, cfg["duplicate_half_l1"])
    dates = pd.to_datetime(t.dates)
    octobers = dates[dates.month == 10].to_series()
    signals = [
        str(d.date())
        for d in octobers.groupby(octobers.dt.year).max()
        if str(d.date()) < cdate
    ]
    flows = cashflows()
    ledger_summaries = {}
    plans = {}
    cards = {}
    coverage = {}
    holdings = pd.read_parquet(cat / "holdings.parquet")
    monthly = {}
    full_orders = []
    full_nav = []
    full_units = []
    missed_variants = []
    for name, w in opt.items():

        def decide(day, current):
            ms = [replace(model, current=current) for model in dated(day)]
            variants = weights(ms, shock, cfg["risk_cap"], cfg["return_concession"])
            if name not in variants:
                missed_variants.append({"variant": name, "date": day})
                return current
            return variants[name]

        decisions = {
            day: (lambda current, d=day: decide(d, current)) for day in signals
        }
        ledger_summaries[name] = {}
        for scenario, settings in cfg["scenarios"].items():
            central = scenario == "central"
            outcome, nav, book, units, plan = replay(
                t,
                decisions if central else plans[name],
                cfg["pocket"],
                cfg["reserve"],
                flows=flows,
                capture=central,
                risk_cap=cfg["risk_cap"],
                **settings,
            )
            ledger_summaries[name][scenario] = outcome
            if central:
                monthly[name] = (
                    nav.groupby(nav.index.str[:7]).nav.last().round(2).to_dict()
                )
                plans[name] = plan
                cards[name] = aggregate_card(m, w, shock, outcome, cfg)
                coverage[name] = dated_concentration(
                    w, m[0].names, holdings, "2026-11-23T14:00:00Z"
                )
                full_units.append(units.assign(strategy=name))
            full_nav.append(nav.assign(strategy=name, scenario=scenario))
            full_orders.append(book.assign(strategy=name, scenario=scenario))
    pd.concat(full_nav).to_parquet(folder / "daily_nav.parquet")
    pd.concat(full_orders, ignore_index=True).to_parquet(
        folder / "orders.parquet", index=False
    )
    pd.concat(full_units).to_parquet(folder / "positions.parquet")
    write_json(folder / "annual_targets.json", plans)
    scored = {name: c for name, c in cards.items() if name in calc}
    profiles = {
        client: rank(scored, criteria, cfg, research=True)
        for client, criteria in cfg["profiles"].items()
    }
    sensitivity = {}
    for client, criteria in cfg["profiles"].items():
        experiments = {}
        for label, i in [("low bound", 0), ("high bound", 1)]:
            changed = {n: c | dict(net=c["interval"][i]) for n, c in scored.items()}
            experiments[label] = rank(changed, criteria, cfg, research=True)
        altered = criteria.copy()
        altered["goal"] -= 5
        altered["spread"] += 5
        experiments["diversification priority +5"] = rank(
            scored, altered, cfg, research=True
        )
        sensitivity[client] = {
            k: {
                n: {"score": v["total"], "groupe": v["group"]}
                for n, v in s["rows"].items()
            }
            for k, s in experiments.items()
        }
    eligible = [n for n in calc if cards[n]["valid"]]
    mix_names = [n for n in (LABELS[0], LABELS[2], LABELS[3]) if n in eligible]
    if len(mix_names) < 2:
        raise ValueError("Research mix insufficiently diverse")
    mixes = {}
    even = np.full(len(mix_names), 1 / len(mix_names))
    manual = np.r_[0.6, 0.4, np.zeros(len(mix_names) - 2)]
    proposals = {"Manual 60/40": manual, "Equal weight": even}
    for n, name in enumerate(mix_names):
        proposals["Alone " + name] = np.eye(len(mix_names))[n]
    searches = {}
    components = [opt[n] for n in mix_names]
    for criterion in ("Return", "Sharpe", "Minimum risk"):
        for floor in (0.0, 0.10):
            key = criterion + (" · minimum 10 %" if floor else " · free")
            solved = mix_search(
                m,
                components,
                criterion=criterion,
                low=0,
                high=cfg["risk_cap"],
                minimum=floor,
                rf=cfg["rf_chf"],
            )
            searches[key] = solved
            if "parts" in solved:
                proposals[key] = solved["parts"]
    for label, parts in proposals.items():
        mix = blended_card(m, opt, mix_names, parts, plans, t, shock, cfg)
        mix["issuer"] = dated_concentration(
            np.array(list(mix["card"]["weights"].values())),
            m[0].names,
            holdings,
            "2026-11-23T14:00:00Z",
        )
        if mix["rounding"] and mix["rounding"]["order"]:
            actual = np.array(mix["rounding"]["order"]["candidate"]["weights"])
            mix["rounding"]["issuer"] = dated_concentration(
                actual, m[0].names, holdings, "2026-11-23T14:00:00Z"
            )
        mixes[label] = mix
    for client, criteria in cfg["profiles"].items():
        grid = rank(
            {k: v["card"] for k, v in mixes.items()}, criteria, cfg, research=True
        )
        for label, row in grid["rows"].items():
            mixes[label].setdefault("scores", {})[client] = row["total"]
    real = pd.read_parquet(cat / "decision.parquet")
    admission = dict(
        screened=len(real), eligible=int(real.eligible.sum()), date=real.date.iloc[0]
    )
    write_json(
        folder / "summary.json",
        dict(
            version=cfg["version"],
            snapshot=source,
            market=cdate,
            signals=signals,
            aliases=aliases,
            absent=missed_variants,
            admission=admission,
            cards=cards,
            issuer=coverage,
            runs=ledger_summaries,
            profiles=profiles,
            sensitivity=sensitivity,
            mix_names=mix_names,
            mixes=mixes,
            monthly_chf=monthly,
            signal_status=dict.fromkeys(FAMILIES, "not validated for the 12-month target"),
            controls=scoring_controls(cfg),
            searches=searches,
            account_scores=rank(scored, cfg["profiles"]["Goal"], cfg)["rows"],
            environmental="Metrics and coverage to be validated in section 11",
            forecasts="Validation by target and horizon in section 12",
        ),
    )


if __name__ == "__main__":
    main()
