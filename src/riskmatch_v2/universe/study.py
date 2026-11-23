"""Re-run completed quantitative tasks on the nominated universe, with dated evidence."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

import numpy as np
import pandas as pd
from scipy import sparse

from ..library.controls import exposure
from ..library.sources import checked
from ..options.compare import combine, distinct
from ..options.scoring import rank
from .data import BR, CAT, END, EQ, Panel, cash_exits, historical
from .model import (
    affordable,
    blend_search,
    broad_frontier,
    fit,
    moments,
    options,
    risk_metrics,
)
from .replay import run
from .sheets import sheets
from .sources import PUBLIC, fetch_extra, listing_log, review
from .treasury import BASE, RAW, fetch, latest_marks

REPORT = Path("reports/univers-complet")
CFG = Path("config/faisabilite-5.json")
POLICY = Path("config/options-6.json")
REF = "60/40 benchmark"


def write(path, x):
    path.write_text(
        json.dumps(
            x,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
            default=lambda a: a.item() if isinstance(a, np.generic) else str(a),
        )
    )


def group_weights(card, inv):
    return pd.Series(card["weights"], dtype=float).groupby(inv["class"]).sum().to_dict()


def tidy(c, inv):
    weights = c.pop("weights")
    g = inv.loc[list(weights), ["symbol", "class"]].copy()
    g["weight"] = pd.Series(weights, dtype=float)
    c["top"] = (
        g.nlargest(10, "weight").rename_axis("id").reset_index().to_dict("records")
    )
    c["by_class"] = g.groupby("class").weight.sum().to_dict()
    c.pop("euler")
    return c


def align(plans, shares, names):
    output = {}
    for day in plans[names[0]]:
        result = {}
        for n, a in zip(names, shares):
            if not a:
                continue
            for key, w in plans[n][day].items():
                result[key] = result.get(key, 0) + w * a
        output[day] = result
    return output


def simulation():
    fetch()
    fetch_extra()
    historical()
    panel = Panel()
    panel.exits = cash_exits(panel)
    params = json.loads(CFG.read_bytes())
    policy = json.loads(POLICY.read_bytes())
    digest = hashlib.sha256()
    input_hashes = {}
    for file in sorted(
        [
            *(RAW.glob("*")),
            *(PUBLIC.glob("*")),
            EQ,
            BR / "manifest.json",
            CAT / "manifest.json",
            CFG,
            POLICY,
            *Path(__file__).parent.glob("*.py"),
        ]
    ):
        d = hashlib.file_digest(file.open("rb"), "sha256").hexdigest()
        input_hashes[str(file)] = d
        digest.update(str(file).encode() + d.encode())
    stamp = digest.hexdigest()[:16]
    dest = BASE / stamp
    REPORT.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        for k, v in json.loads((dest / "manifest.json").read_bytes()).items():
            checked(dest / k, v)
        (REPORT / "resultats.json").write_bytes((dest / "resultats.json").read_bytes())
        return
    with TemporaryDirectory(dir=BASE) as tmp:
        path = Path(tmp) / "result"
        path.mkdir()
        result = build(panel, path, params, policy, stamp)
        write(path / "sources.json", input_hashes)
        write(path / "resultats.json", result)
        write(
            path / "manifest.json",
            {
                f.name: hashlib.file_digest(f.open("rb"), "sha256").hexdigest()
                for f in path.iterdir()
            },
        )
        path.rename(dest)
        (REPORT / "resultats.json").write_bytes((dest / "resultats.json").read_bytes())


def build(panel, path, params, policy, stamp):
    ipos = listing_log()
    ipos.to_parquet(path / "ipos.parquet", index=False)
    exchange_checks = review()
    exchange_checks.to_parquet(path / "secondary_checks.parquet", index=False)
    out_of_sample = []
    annual = []
    targets = {}
    inventories = []
    sparse_weights = []
    present = {}
    for day in panel.year_days:
        tick = monotonic()
        models, shock, inv = fit(panel, day, params)
        weights = options(models, shock)
        main = models[0]
        ref = np.zeros(len(main.names))
        ref[main.names.index("SPY")] = 0.6
        ref[main.names.index("IEF")] = 0.4
        weights[REF] = ref
        annual.append(
            dict(
                day=day,
                fit_solve_seconds=round(monotonic() - tick, 3),
                classes=inv.groupby("class")
                .included.agg(["size", "sum"])
                .to_dict("index"),
            )
        )
        inventories.append(inv.assign(day=day).reset_index())
        for name, w in weights.items():
            a = {s: float(x) for s, x in zip(main.names, w) if x}
            sparse_weights.extend((day, name, k, v) for k, v in a.items())
            if day != END:
                last = panel.days[panel.dindex.get_loc(day) + 63]
                test, frame, _ = run(panel, {day: a}, {**policy, "market": last})
                out_of_sample.append(
                    dict(
                        decision=day,
                        end=str(last),
                        option=name,
                        predicted_vol=main.evaluate(w)["risk"],
                        realized_vol=test["realized_vol"]
                        if test["first_problem"] is None
                        else None,
                        net_return=float((1 + frame.ret).prod() - 1)
                        if test["first_problem"] is None
                        else None,
                        first_problem=test["first_problem"],
                    )
                )
                targets.setdefault(name, {})[day] = a
            else:
                present[name] = w
        print(day, len(main.names), flush=True)
    pd.concat(inventories, ignore_index=True).to_parquet(
        path / "membership.parquet", index=False
    )
    pd.DataFrame(sparse_weights, columns=["day", "option", "id", "weight"]).to_parquet(
        path / "weights.parquet", index=False
    )
    write(path / "historical_plans.json", targets)
    raw_prices = panel.close[-1, panel.names.get_indexer(main.names)].astype(float)
    fx = panel.fx[-1]
    for k, m in enumerate(models):
        sparse.save_npz(path / f"risk_{k}.npz", m.root)
    np.savez_compressed(
        path / "models.npz",
        names=np.array(main.names),
        mu=np.array([m.mu for m in models]),
        prices=raw_prices,
        fx=fx,
        shock=shock,
    )
    holdings = pd.read_parquet(CAT / "holdings.parquet")
    direct = {
        key: (
            "US-TREASURY"
            if key.startswith("UST:")
            else "CUSIP6:" + str(panel.register.loc[int(key[7:]), "cusip_2025"])[:6]
        )
        for key in main.names
        if key.startswith(("UST:", "PERMNO:"))
    }

    def exposure_attribution(w):
        total = w.sum()
        if total < 1e-8:
            return dict(issuer=None, largest=0, unknown=0)
        x = exposure(
            {k: a / total for k, a in zip(main.names, w) if a > 0},
            holdings,
            direct,
            "2026-11-23T18:00:00Z",
        )
        known = x["issuers"]
        top = max(known, key=known.get) if known else None
        return dict(
            issuer=top,
            largest=total * known.get(top, 0),
            unknown=total * x["unknown_gross"],
        )

    summary, monthly_chf = sheets(panel, inv)
    monthly_chf.to_parquet(path / "monthly_all_chf.parquet")
    summary.to_parquet(path / "sheets.parquet", index=False)
    fixed_check = summarize_sheets(summary, inv)
    cards = {}
    runs = {}
    navs = {}
    ledger = []
    daily = []
    rounding = {}
    euler = []
    for n, w in present.items():
        outcomes = {}
        stats = None
        for label, spec in policy["scenarios"].items():
            r, frame, orders = run(
                panel, targets[n], policy, capture=label == "central", **spec
            )
            outcomes[label] = r
            if label == "central":
                stats = r
                navs[n] = frame
                ledger.append(orders.assign(option=n))
                daily.append(frame.reset_index().assign(option=n))
        runs[n] = outcomes
        c = risk_metrics(models, shock, w)
        c.update(
            cagr=stats["cagr"],
            drawdown=stats["drawdown"],
            tradable=False,
            issuers=exposure_attribution(w),
            stress_observed_weight=float(
                w[np.isin(main.names, list(panel.observed_shocks))].sum()
            ),
        )
        euler.extend((n, k, v) for k, v in c["euler"].items())
        cards[n] = tidy(c, inv)
        if n != REF:
            lot = affordable(main, w, raw_prices, fx, None, policy["pocket"])
            rounding[n] = {
                k: v for k, v in lot.items() if k not in ("weights", "units")
            }
    pd.concat(ledger).to_parquet(path / "orders.parquet", index=False)
    pd.concat(daily).to_parquet(path / "nav.parquet", index=False)
    pd.DataFrame(euler, columns=["option", "id", "contribution"]).to_parquet(
        path / "euler.parquet", index=False
    )
    distinct_w, aliases = distinct(present, policy["duplicate_half_l1"])
    score_input = {n: c for n, c in cards.items() if n in distinct_w}
    profiles = {
        k: rank(score_input, p, policy, research=True)
        for k, p in policy["profiles"].items()
    }
    # Alternative diagnostic on the current weights, keeping the walk-forward score separate.
    fitted_cards = {}
    for name, w in present.items():
        positive = w > 0
        hist = monthly_chf.loc[:, np.array(main.names)[positive]].tail(12)
        weights = w[positive]
        if hist.isna().any().any():
            continue
        current = np.zeros_like(weights)
        growth = [1.0]
        for row in hist.to_numpy():
            fee = 0.001 * np.abs(weights - current).sum()
            factor = 1 - fee + float(row @ weights)
            growth.append(growth[-1] * factor)
            current = weights * (1 + row) / factor
        growth = np.array(growth)
        fitted_cards[name] = dict(
            **{k: v for k, v in cards[name].items() if k not in ("cagr", "drawdown")},
            cagr=float(growth[-1] - 1),
            drawdown=float(np.min(growth / np.maximum.accumulate(growth) - 1)),
        )
    backcast = {
        k: rank(
            {n: c for n, c in fitted_cards.items() if n in distinct_w},
            p,
            policy,
            research=True,
        )
        for k, p in policy["profiles"].items()
    }
    candidates = [n for n in distinct_w if n != REF]
    components = [present[n] for n in candidates]
    combinations = {}
    for label, parts in [
        (
            "Manual 60/40",
            np.array(
                [
                    0.6 if k == 0 else 0.4 if k == len(candidates) - 1 else 0
                    for k in range(len(candidates))
                ]
            )
            if len(candidates) > 1
            else np.ones(1),
        ),
        ("Equal weight", np.ones(len(candidates)) / len(candidates)),
    ]:
        combinations[label] = dict(parts=parts, status="selected shares")
    for criterion in ("Return", "Minimum risk", "Sharpe"):
        for floor in (0, 0.1):
            combinations[f"{criterion} · floor {floor:.0%}"] = blend_search(
                models,
                components,
                criterion=criterion,
                low=0.0,
                high=0.12,
                minimum=floor,
            )
    mix_report = {}
    for label, d in combinations.items():
        if "parts" not in d:
            mix_report[label] = d
            continue
        z = d["parts"]
        w = combine(components, z)
        r, frame, _ = run(panel, align(targets, z, candidates), policy)
        c = risk_metrics(models, shock, w)
        c.update(cagr=r["cagr"], drawdown=r["drawdown"])
        lot = affordable(main, w, raw_prices, fx, None, policy["pocket"])
        mix_report[label] = dict(
            parts=dict(zip(candidates, list(z))),
            status=d["status"],
            **tidy(c, inv),
            lots=lot["status"],
            quality=r["first_problem"],
            scores={
                k: rank({"mix": c}, p, policy, research=True)["rows"]
                .get("mix", {})
                .get("total")
                for k, p in policy["profiles"].items()
            },
        )
    bounds = {}
    for low, high in [
        (0, 0.12),
        (0, 0.20),
        (0, 0.30),
        (0, 0.4),
        (0.18, 0.22),
        (0.28, 0.32),
        (0.38, 0.42),
        (0.99, 1.01),
    ]:
        answer = broad_frontier(main, low, high)
        c = answer["candidate"] or {}
        bounds[f"{low:.0%}–{high:.0%}"] = dict(
            status=answer["status"],
            reason=answer["proof"],
            upper_return=answer["upper_net"],
            gap=answer["gap"],
            risk_upper_bound=answer["max_risk_bound"],
            vol=c.get("risk"),
            net=c.get("net"),
        )
    subsets = {}
    cls = inv.loc[list(main.names), "class"]
    for label, mask in {
        "ETFs only": cls.isin(["Equity ETF", "Treasury ETF", "Gold (GLD)"]),
        "Individual stocks only": cls == "Individual stock",
        "Direct Treasuries only": cls == "Direct Treasury",
        "Full universe": cls.notna(),
    }.items():
        ix = np.flatnonzero(mask)
        sub = replace(
            main,
            names=tuple(main.names[j] for j in ix),
            mu=main.mu[ix],
            root=main.root[:, ix],
            lo=main.lo[ix],
            hi=main.hi[ix],
            current=main.current[ix],
            fees=main.fees[ix],
            groups={k: (v[ix], cap) for k, (v, cap) in main.groups.items()},
        )
        a = broad_frontier(sub)
        c = a["candidate"] or {}
        subsets[label] = dict(
            offered=len(ix),
            held=sum(v > 1e-7 for v in c.get("weights", [])),
            net=c.get("net"),
            vol=c.get("risk"),
            status=a["status"],
        )
    monthly = pd.DataFrame({n: f.nav for n, f in navs.items()})
    monthly.index = pd.to_datetime(monthly.index)
    monthly = monthly.resample("ME").last()
    monthly.index = monthly.index.strftime("%Y-%m-%d")
    # A common prefix stops before the first unknown mark in any alternative.
    first = min(
        [
            s["central"]["first_problem"]
            for s in runs.values()
            if s["central"]["first_problem"]
        ]
        or [END]
    )
    common = {}
    for name, f in navs.items():
        ret = f.loc[f.index < first, "ret"]
        common[name] = dict(
            sessions=len(ret),
            end=ret.index[-1] if len(ret) else None,
            cumulative=float((1 + ret).prod() - 1),
        )
    stability = []
    for ix, alternative in enumerate(models):
        sol = broad_frontier(alternative)
        if not sol["candidate"]:
            continue
        v = np.array(sol["candidate"]["weights"])
        stability.append(
            dict(
                model=ix + 1,
                net=sol["candidate"]["net"],
                vol=sol["candidate"]["risk"],
                distance=float(np.abs(v - present["Return"]).sum() / 2),
                base_net=main.evaluate(v)["net"],
                base_vol=main.evaluate(v)["risk"],
                gap=sol["gap"],
            )
        )
    # Resample contiguous blocks of 21 sessions without reselecting the asset universe.
    cols = panel.names.get_indexer(main.names)
    raw = panel.history(END, 504)[:, cols]
    fidx = [main.names.index(k) for k in ("SPY", "IEF", "GLD")]
    rng = np.random.default_rng(5026)
    boot = []
    for i in range(8):
        starts = rng.integers(0, len(raw) - 21 + 1, size=24)
        sample = raw[np.concatenate([np.arange(j, j + 21) for j in starts])]
        means, root, _ = moments(sample, sample[:, fidx], minimum=50)
        lo, hi = np.quantile(means, [0.01, 0.99])
        bm = replace(
            main, mu=(np.clip(means, lo, hi) + np.median(means)) / 2, root=root
        )
        sol = broad_frontier(bm)
        if sol["candidate"]:
            w = np.array(sol["candidate"]["weights"])
            boot.append(
                dict(
                    draw=i + 1,
                    net=sol["candidate"]["net"],
                    risk_under_base=main.evaluate(w)["risk"],
                    distance=float(np.abs(w - present["Return"]).sum() / 2),
                )
            )
    last_inv = inv.assign(reason=inv.reason.replace("candidate", "submitted"))
    flags = (
        last_inv.groupby(["class", "reason"])
        .size()
        .unstack(fill_value=0)
        .to_dict("index")
    )
    live = pd.read_parquet(CAT / "decision.parquet")
    # The new archive supplies research evidence retrieved after the original decision timestamp.
    # Keep that original decision immutable; re-evaluate what facts remain missing after collection.
    newer = live.copy()
    marks = latest_marks()
    obs36 = summary[summary.years.eq(3)].set_index("id").observations
    for ix, r in newer.iterrows():
        k = (
            r.id.rsplit("-", 1)[-1]
            if r.id.startswith("ETF-")
            else "UST:" + r.id[7:-1]
            if r.id.startswith("ISIN:US")
            else r.id
        )
        if k not in inv.index:
            continue
        reasons = set(r.reasons.split("|")) - {""}
        if k.startswith("UST:") and k[4:] in marks:
            newer.at[ix, "price_day"] = "2026-11-20"
            reasons.discard("PRIX_NON_FRAIS")
        if k.startswith("PERMNO:") and (
            panel.register.loc[int(k[7:]), "status"] == "complete"
            or int(k[7:]) in panel.recovered
        ):
            newer.at[ix, "price_day"] = END
        newer.at[ix, "history_months"] = obs36[k]
        if obs36[k] >= 36:
            reasons.discard("HISTORIQUE_RISQUE")
        newer.at[ix, "reasons"] = "|".join(sorted(reasons))
        newer.at[ix, "eligible"] = not reasons
    newer.to_parquet(path / "post_collection_review.parquet", index=False)
    new_admissible = int(newer.eligible.sum())
    return dict(
        backcast=backcast,
        bootstrap=boot,
        validation=out_of_sample,
        stability=stability,
        ipo_deals=len(ipos),
        secondary_recovered=len(panel.recovered),
        secondary_checked=len(exchange_checks),
        secondary_quoted=int(exchange_checks.quote_symbol.notna().sum()),
        date=END,
        snapshot=stamp,
        annual=annual,
        reasons=flags,
        sheets=fixed_check,
        cards=cards,
        profiles=profiles,
        aliases=aliases,
        runs=runs,
        common=common,
        rounding=rounding,
        mixes=mix_report,
        frontier=bounds,
        subsets=subsets,
        monthly=monthly.to_dict(),
        live={
            "examined": len(live),
            "eligible": int(live.eligible.sum()),
            "after_collection": new_admissible,
            "bond_marks_nov20": len(set(panel.bonds.index) & marks),
        },
        bond_marks=len(pd.read_parquet(BASE / "bonds.parquet")),
        simulations=len(runs) * len(policy["scenarios"]),
    )


def summarize_sheets(table, inventory):
    return (
        table.join(inventory["class"], on="id")
        .groupby(["class", "years"])
        .agg(fiches=("id", "size"), completes=("full_sample", "sum"))
        .reset_index()
        .to_dict("records")
    )


if __name__ == "__main__":
    simulation()
