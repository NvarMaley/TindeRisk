"""Reproduce section 7 from the frozen multi-asset and econometric snapshots."""

import json
from dataclasses import replace
from datetime import date
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

from .archive_labels import read_snapshot
from .funding import block_draws, funding_paths, required_return, sale_values, years
from .interview import CARDS, Interview, route
from .risk_review import request
from .universe.desk import load_model
from .universe.model import affordable, broad_frontier
from .universe.treasury import terms

OUT = Path("reports/07-funding")


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    content = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content)
    tmp.replace(path)


def confirm_client(cfg, plan, *, mode="cap", low=0, high=0.12, overrides=None):
    fixture = read("reports/02-questionnaire/cas.json")
    answers = fixture["common"] | fixture["cases"][0]["answers"]
    answers.update(
        F02={"date": cfg["protection_end"]},
        F03=[answers["F03"][0] | {"date": plan["expense"]}],
        F04={"low": 20_000, "high": 25_000},
        F05={
            "low": plan["goal_chf"],
            "high": plan["goal_chf"],
            "date": plan["end"],
            "currency": "CHF",
        },
        P02=answers["P02"] | {"mode": mode},
    )
    opts = {}
    if mode == "cap":
        answers["P03"] = {"max": high * 100}
        opts["ceiling_pct"] = high * 100
    elif mode == "target_band":
        answers["P04"] = {"low": low * 100, "high": high * 100}
        opts = {"low_pct": low * 100, "high_pct": high * 100}
    answers.update(overrides or {})
    iv = Interview(date.fromisoformat(cfg["decision"]))
    for card in CARDS:
        if card in route(iv.answers):
            iv.record(card, answers.get(card, "skip"))
    iv.confirm()
    snap = iv.save_risk(
        request(mode, "investment sleeve", **opts),
        accept=True,
        bills="yes",
        comfort="yes",
    )
    return snap


def summarized(paths, dates):
    counts = lambda key: {
        dates[int(m) - 1]: int(v)
        for m, v in paths[key].value_counts().sort_index().items()
        if m
    }
    missed = paths.first_missed_month > 0
    return {
        "paths": len(paths),
        "all_goals_met": int(paths.all_goals_met.sum()),
        "missed": int(missed.sum()),
        "terminal_goal_met": int((paths.terminal_gap_chf <= 1e-7).sum()),
        "mean_terminal_gap_chf": float(paths.terminal_gap_chf.mean()),
        "median_terminal_gap_chf": float(paths.terminal_gap_chf.median()),
        "terminal_chf_quantiles": paths.terminal_chf.quantile(
            [0.05, 0.50, 0.95]
        ).to_dict(),
        "mean_first_gap_if_missed_chf": float(paths.loc[missed, "first_gap_chf"].mean())
        if missed.any()
        else None,
        "first_missed_dates": counts("first_missed_month"),
        "first_recovery_dates": counts("first_recovery_month"),
        "missed_without_recovery": int(
            (missed & paths.first_recovery_month.eq(0)).sum()
        ),
    }


def plan_variants(plan):
    end = pd.Timestamp(plan["end"])
    return {
        "base": (end, plan["goal_chf"], 0),
        "contribution": (end, plan["goal_chf"], 5_000),
        "higher_goal": (end, plan["goal_chf"] + 10_000, 0),
        "later_goal": (end + pd.offsets.MonthEnd(12), plan["goal_chf"], 0),
    }


def holdings(models, prices, fx, weights, sleeve):
    model = models[0]
    result = {}
    for name, w in weights.items():
        if name == "Fixed 60/40":
            # Fund entry fees from the sleeve before flooring both benchmark legs.
            units = np.floor((sleeve / (1 + w @ model.fees)) * w / (prices * fx))
        else:
            rounded = affordable(model, w, prices, fx, None, sleeve)
            if "units" not in rounded:
                raise ValueError("Could not verify research lots for this client")
            units = rounded["units"]
        mask = units > 0
        cost = units[mask] * prices[mask] * fx
        fees = model.fees[mask]
        full = np.zeros(len(w))
        full[mask] = cost / sleeve
        estimate = model.evaluate(full)
        entry_fee = float(cost @ fees)
        risk_ok = bool(model.evaluate(full, 0, 0.12)["valid"])
        ids = np.asarray(model.names)[mask].tolist()
        result[name] = (
            ids,
            cost,
            fees,
            {
                "positions": len(ids),
                "entry_fee_chf": entry_fee,
                "entry_cash_chf": sleeve - float(cost.sum()) - entry_fee,
                "volatility": estimate["risk"],
                "estimated_net": estimate["net"],
                "model_range": [
                    min(m.evaluate(full)["net"] for m in models),
                    max(m.evaluate(full)["net"] for m in models),
                ],
                "within_research_mandate": risk_ok,
                "direct_treasuries": sum(i.startswith("UST:") for i in ids),
            },
        )
    return result


def simulate_client(cfg, plan, portrait, positions, monthly, archive):
    start = cfg["decision"]
    first_month = (pd.Period(start, freq="M") + 1).to_timestamp("M")
    dates = pd.date_range(
        first_month, pd.Timestamp(plan["end"]) + pd.offsets.MonthEnd(12), freq="ME"
    )
    # October 30 was the final trading session; the first scenario month is November.
    month_ids = dates.strftime("%Y-%m-%d").tolist()
    expense = portrait["facts"]["flows"][0]
    cost = expense["high"]
    bill = month_ids.index(expense["date"])
    deposit = month_ids.index("2027-10-31")
    capital = portrait["facts"]["capital_chf"]["low"]
    reserve = portrait["liquidity"]["reserve_chf"]["high"]
    ids = list(dict.fromkeys(i for names, *_ in positions.values() for i in names))
    shared = monthly[ids]
    results = {}
    path_tables = []
    for length in cfg["block_months"]:
        starts, draws = block_draws(
            shared, length, len(dates), cfg["paths"], cfg["seed"] + length
        )
        record = {
            "joint_holdings": len(ids),
            "source_blocks": len(starts),
            "starts": [str(shared.index[s]) for s in starts],
            "variants": {},
        }
        results[str(length)] = record
        if draws is None:
            continue
        for label, (names, notionals, fees, details) in positions.items():
            values = sale_values(monthly[names].to_numpy(), draws, notionals, fees)
            scenarios = {}
            for variant, (end, target, addition) in plan_variants(plan).items():
                months = month_ids.index(str(end.date())) + 1
                outs, ins = np.zeros(months), np.zeros(months)
                outs[bill], ins[deposit] = cost, addition
                paths = funding_paths(
                    values[:, :months],
                    reserve + details["entry_cash_chf"],
                    outs,
                    ins,
                    target,
                )
                scenarios[variant] = summarized(paths, month_ids)
                path_tables.append(
                    paths.assign(
                        block_months=length,
                        portfolio=label,
                        variant=variant,
                        path_id=np.arange(len(paths)),
                    )
                )
            record["variants"][label] = scenarios
    requirements = {}
    for variant, (end, target, addition) in plan_variants(plan).items():
        flows = [(expense["date"], -cost)]
        if addition:
            flows.append((month_ids[deposit], addition))
        requirements[variant] = required_return(
            start, str(end.date()), capital, reserve, flows, target
        )
    if path_tables:
        pd.concat(path_tables, ignore_index=True).to_parquet(
            archive / "paths.parquet", index=False
        )
    stresses = {}
    months = month_ids.index(plan["end"]) + 1
    outflows, inflows = np.zeros(months), np.zeros(months)
    outflows[bill] = cost
    for label, (_, notionals, fees, details) in positions.items():
        liquid = float(notionals @ (1 - fees))
        alternatives = {}
        for scenario, multiplier, growth in [
            ("flat_market", 1.0, 0.0),
            ("immediate_30pct_loss", 0.7, 0.0),
            ("constant_5pct_asset_growth", 1.0, 0.05),
        ]:
            proceeds = (
                liquid * multiplier * (1 + growth) ** (np.arange(1, months + 1) / 12)
            )
            simulated = funding_paths(
                proceeds[None, :],
                reserve + details["entry_cash_chf"],
                outflows,
                inflows,
                plan["goal_chf"],
            )
            alternatives[scenario] = summarized(simulated, month_ids)
        stresses[label] = alternatives
    # A longer benchmark-only window diagnoses the information lost in the paired comparison.
    names, notionals, fees, details = positions["Fixed 60/40"]
    benchmark_only = {}
    for length in cfg["block_months"]:
        starts, draws = block_draws(
            monthly[names], length, months, cfg["paths"], cfg["seed"] + length
        )
        record = {"source_blocks": len(starts)}
        if draws is not None:
            proceeds = sale_values(monthly[names].to_numpy(), draws, notionals, fees)
            record["base"] = summarized(
                funding_paths(
                    proceeds,
                    reserve + details["entry_cash_chf"],
                    outflows,
                    inflows,
                    plan["goal_chf"],
                ),
                month_ids,
            )
        benchmark_only[str(length)] = record
    return requirements, results, stresses, benchmark_only


def coupon_comparison(asof, expense, fx):
    # Illustrative held-to-maturity Treasury per USD 100 face, separate from the actual portfolio.
    table = terms()
    valid = table[
        (table.issue_date <= asof)
        & (table.maturity_date > asof)
        & table.int_rate.notna()
    ]
    issue = (
        valid.assign(
            distance=(pd.to_datetime(valid.maturity_date) - pd.Timestamp(expense)).abs()
        )
        .sort_values(["distance", "maturity_date"])
        .iloc[0]
    )
    maturity = pd.Timestamp(issue.maturity_date)
    coupon_dates = []
    for k in range(80):
        day = maturity - pd.DateOffset(months=6 * k)
        if maturity.is_month_end:
            day = day + pd.offsets.MonthEnd(0)
        if day <= pd.Timestamp(asof):
            break
        if day <= pd.Timestamp(expense):
            coupon_dates.append(str(day.date()))
    principal = 100.0 if maturity <= pd.Timestamp(expense) else 0.0
    coupons = len(coupon_dates) * float(issue.int_rate) / 2
    return {
        "cusip": str(issue.name),
        "maturity": str(maturity.date()),
        "annual_coupon_pct": float(issue.int_rate),
        "coupons_due_by_bill": sorted(coupon_dates),
        "principal_usd": principal,
        "coupon_usd": coupons,
        "illustrative_chf_by_bill": (coupons + principal) * fx,
    }


def mandate_controls(cfg, model, current_weights):
    plan = cfg["clients"]["A"]
    largest = int(np.argmax(current_weights))
    limits = {"priority": "high", "strength": "mandatory", "missing": "suspend"}
    cases = [
        ("minimum", "minimum", 0, 0, {}),
        ("cap_40", "cap", 0, 0.40, {}),
        ("target_35", "target_band", 0.33, 0.37, {}),
        ("target_40", "target_band", 0.38, 0.42, {}),
        ("target_100", "target_band", 0.99, 1.01, {}),
        (
            "direct_exclusion",
            "cap",
            0,
            0.12,
            {"P07": [limits | {"scope": model.names[largest]}]},
        ),
        (
            "position_diversification",
            "cap",
            0,
            0.12,
            {"P06": [limits | {"scope": "Maximum 2% per direct position"}]},
        ),
    ]
    results = {}
    for label, mode, low, high, rules in cases:
        snap = confirm_client(cfg, plan, mode=mode, low=low, high=high, overrides=rules)
        review = snap["risk_review"]
        row = {
            "request": review["choice"],
            "client_decision": review["state"],
            "rules": rules,
        }
        results[label] = row
        if review["state"] != "confirmed for study":
            row["status"] = "requires client clarification"
            continue
        cap = model.hi.copy()
        if "P07" in rules:
            cap[model.names.index(rules["P07"][0]["scope"])] = 0
        if "P06" in rules:
            cap = np.minimum(cap, 0.02)
        constrained = replace(model, hi=cap)
        if mode == "minimum":
            solution = constrained.evaluate(np.zeros(len(cap)))
            status = "minimum volatility attained with CHF cash"
        else:
            answer = broad_frontier(constrained, low, high)
            solution, status = answer["candidate"], answer["status"]
        row["status"] = status
        if solution is not None:
            w = np.asarray(solution["weights"])
            assert np.all(w <= cap + 1e-6)
            row.update(
                estimated_net=solution["net"],
                volatility=solution["risk"],
                maximum_position=float(w.max()),
                excluded_position=float(w[largest]) if "P07" in rules else None,
            )
    etf = read("reports/05-faisabilite/resultats.json")
    results["controlled_unreachable"] = {
        "universe": "13-ETF controlled experiment",
        "request": "38–42% target band",
        "status": etf["cases"]["band 0.38–0.42"]["status"],
        "maximum_volatility": etf["diagnostics"]["max_risk"],
        "alternative": "Review a lower band with the client; no automatic substitution.",
    }
    difficult = plan | {"end": "2027-10-31", "goal_chf": 200_000}
    snap = confirm_client(cfg, difficult)
    desired = required_return(
        cfg["decision"],
        difficult["end"],
        50_000,
        15_000,
        [(plan["expense"], -15_000)],
        difficult["goal_chf"],
    )
    ceiling = broad_frontier(model)["upper_net"]
    results["excessive_required_return"] = {
        "required": desired,
        "one_year_model_upper_net": ceiling,
        "state": snap["risk_review"]["state"],
        "exceeds_model_upper_bound": desired["rates"][0] > ceiling,
        "alternative": "Reduce the goal, extend the deadline or add savings and confirm the change.",
    }
    return results


def main():
    cfg = read("config/funding-7.json")
    broad = read("reports/univers-complet/resultats.json")
    eco = read("reports/econometrie/results.json")
    assert (
        broad["date"] == eco["end"] == cfg["decision"]
        and eco["source_snapshot"] == broad["snapshot"]
    )
    bundle = Path("data/local/univers") / broad["snapshot"]
    models, _, prices, fx = load_model(bundle)
    model = models[0]
    weights = read_snapshot(bundle / "weights.parquet")
    selected = (
        weights[(weights.day == broad["date"]) & (weights.option == "Return")]
        .set_index("id")
        .weight
    )
    custom = selected.reindex(model.names, fill_value=0).to_numpy()
    assert np.isclose(custom.sum(), selected.sum())
    fixed = np.zeros(len(custom))
    fixed[model.names.index("SPY")], fixed[model.names.index("IEF")] = 0.6, 0.4
    input_file = (
        Path("data/local/econometrics") / eco["snapshot"] / "monthly_all_chf.parquet"
    )
    relevant = np.asarray(model.names)[(custom > 0) | (fixed > 0)].tolist()
    monthly = (
        pd.read_parquet(input_file, columns=relevant)
        .sort_index()
        .loc[: cfg["decision"]]
    )
    OUT.mkdir(exist_ok=True)
    outputs = {}
    for name, plan in cfg["clients"].items():
        snap = confirm_client(cfg, plan)
        portrait = snap["portrait"]
        review = snap["risk_review"]
        assert (
            review["state"] == "confirmed for study"
            and not snap["allocation_authorized"]
        )
        sleeve = portrait["liquidity"]["investable_chf"]["low"]
        allocations = holdings(
            models, prices, fx, {"Custom": custom, "Fixed 60/40": fixed}, sleeve
        )
        archive = Path("data/local/7") / broad["snapshot"] / name
        archive.mkdir(parents=True, exist_ok=True)
        records = []
        for label, (names, notionals, fee_rates, _) in allocations.items():
            indices = pd.Index(model.names).get_indexer(names)
            records.append(
                pd.DataFrame(
                    {
                        "portfolio": label,
                        "id": names,
                        "initial_chf": notionals,
                        "lots": np.rint(notionals / (prices[indices] * fx)).astype(int),
                        "one_way_fee_rate": fee_rates,
                    }
                )
            )
        pd.concat(records, ignore_index=True).to_parquet(
            archive / "holdings.parquet", index=False
        )
        req, sims, stress, benchmark_only = simulate_client(
            cfg, plan, portrait, allocations, monthly, archive
        )
        desired_net = snap["answers"]["P01"]["high"] / 100
        remaining_bill = max(0, 15_000 - portrait["liquidity"]["reserve_chf"]["high"])
        horizon = years(cfg["decision"], plan["end"])
        goal_at_desired_cap = sleeve * (1 + desired_net) ** horizon - remaining_bill * (
            1 + desired_net
        ) ** years(plan["expense"], plan["end"])
        additional_now = (plan["goal_chf"] - goal_at_desired_cap) / (
            1 + desired_net
        ) ** horizon
        outputs[name] = {
            "funding_alternative": {
                "assumed_constant_net_rate": desired_net,
                "terminal_goal_chf": goal_at_desired_cap,
                "additional_initial_chf_for_original_goal": max(0.0, additional_now),
                "client_accepted": False,
            },
            "decision": cfg["decision"],
            "plan": plan,
            "universe": broad["snapshot"],
            "source_instruments": len(model.names),
            "answers": snap["answers"],
            "aversion": portrait["aversion"],
            "desired_annual_pct": snap["answers"]["P01"],
            "risk_request": review["choice"],
            "confirmation": review["state"],
            "liquidity": portrait["liquidity"],
            "funding_requirements": req,
            "simulations": sims,
            "deterministic_stress": stress,
            "benchmark_only": benchmark_only,
            "positions": {n: v[3] for n, v in allocations.items()},
            "executable": False,
            "treasury_example": coupon_comparison(cfg["decision"], plan["expense"], fx),
        }
    assert outputs["A"]["aversion"] == outputs["B"]["aversion"]
    delayed = cfg["clients"]["A"] | {"expense": "2028-03-31"}
    shifted = confirm_client(cfg, delayed)
    liquidity = shifted["portrait"]["liquidity"]
    expense_only = {
        "plan": delayed,
        "liquidity": liquidity,
        "same_aversion": shifted["portrait"]["aversion"] == outputs["A"]["aversion"],
        "required": required_return(
            cfg["decision"],
            delayed["end"],
            50_000,
            liquidity["reserve_chf"]["high"],
            [(delayed["expense"], -15_000)],
            delayed["goal_chf"],
        ),
    }
    detail = funding_paths(
        np.zeros((1, 3)), 2_000, [5_000, 0, 0], [0, 8_000, 0], 4_000
    ).iloc[0]
    summary = {
        "config": cfg,
        "universe": broad["snapshot"],
        "history": eco["snapshot"],
        "history_sha256": sha256(input_file.read_bytes()).hexdigest(),
        "history_first": str(monthly.index[0]),
        "history_last": str(monthly.index[-1]),
        "order_gate": broad["live"],
        "delay_only_for_A": expense_only,
        "controls": mandate_controls(cfg, model, custom),
        "missed_then_recovered": json.loads(detail.to_json()),
        "clients": list(outputs),
    }
    for name, data in outputs.items():
        write(OUT / f"client-{name}.json", data)
    write(OUT / "results.json", summary)


if __name__ == "__main__":
    main()
