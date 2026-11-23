"""Rebuild section 10 from frozen V2 catalogues and dated external source slices."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import requests

from ..archive_labels import read_snapshot
from ..econometrics import ecb_series
from ..equity_extension.fetch import CAT
from ..library.sources import checked
from ..universe.treasury import BASE, RAW, terms
from .access import marks, replay
from .gold import compare
from .pricing import risk, schedule

LOCAL = Path("data/local/10")
REPORT = Path("reports/10-treasuries-gold")


def records(frame):
    return json.loads(
        frame.to_json(orient="records", date_format="iso", double_precision=12)
    )


def get_inputs(cfg):
    raw = LOCAL / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for filename, src in cfg["sources"].items():
        path = raw / filename
        if not path.exists():
            response = requests.get(src["url"], timeout=60)
            response.raise_for_status()
            temp = path.with_suffix(".download")
            temp.write_bytes(response.content)
            if filename not in cfg["bounded_gold_hashes"]:
                checked(temp, src["sha256"])
            temp.replace(path)
        if filename not in cfg["bounded_gold_hashes"]:
            checked(path, src["sha256"])
    return raw


def gate(day, issue, last, firm_size=None, face=1000, account=False):
    if day < issue:
        return "Not issued"
    if last is None or last != day:
        return "Missing or stale valuation"
    if firm_size is None or firm_size < face:
        return "No verified executable size"
    if not account:
        return "Unverified account"
    return "Price and size checks passed"


def run():
    cfgfile = Path("config/treasury-gold-10.json")
    cfg = json.loads(cfgfile.read_text())
    raw = get_inputs(cfg)
    cutoff = cfg["as_of"]
    cash_file = raw / (cfg["matured_control"] + ".json")
    bondfile = BASE / "bonds.parquet"
    checked(bondfile, json.loads((BASE / "bonds.json").read_text())["file"])
    history = pd.read_parquet(bondfile)
    prices = pd.read_parquet(CAT / "prices.parquet")
    fx = (
        pd.read_parquet(CAT / "fx.parquet")
        .set_index("day")
        .value.combine_first(
            ecb_series(json.loads(Path("config/econometrie.json").read_text()))
        )
    )
    universe = BASE / cfg["universe"]
    inventory = read_snapshot(
        universe / "membership.parquet", filters=[("day", "=", cutoff)]
    ).set_index("id")
    daily = marks(cutoff)
    auction_files = sorted(RAW.glob("auctions-*.json"))
    auctions = pd.concat(
        [pd.DataFrame(json.loads(p.read_bytes())["data"]) for p in auction_files]
    )
    terms_table = terms()
    cfg["example"]
    assert set(inventory.index[inventory["class"].eq("Direct Treasury")]) == {
        "UST:" + k for k in terms_table.index
    }
    sponsor = pd.read_parquet(CAT / "holdings.parquet")
    held = (
        sponsor[sponsor.security.isin(terms_table.index)]
        .groupby("security")
        .fund.agg(lambda v: ", ".join(sorted(set(v))))
    )
    rows, shocks, flows, returns = [], [], [], []
    # Common annual endpoints and issue paths include coupon reinvestment at observed marks.
    start = "2025-10-31"
    label = prices.id.str.rsplit("-", n=1).str[-1]
    endpoints = prices.assign(symbol=label).pivot(
        index="day", columns="symbol", values="adjusted"
    )
    fx_ratio = fx[cutoff] / fx[start]
    fund_return = (
        (endpoints.loc[cutoff, ["IEF", "TLT"]] / endpoints.loc[start, ["IEF", "TLT"]])
        * fx_ratio
        - 1
    ).to_dict()
    # A Treasury session is observable if the FedInvest archive supplies any selected mark.
    bond_calendar = sorted(
        history.loc[history.day.between(start, cutoff), "day"].unique()
    )
    for key, t in terms_table.iterrows():
        name = "UST:" + key
        stream = history[history.name == name].sort_values("day").set_index("day")
        hist = stream.loc[:cutoff]
        flow = schedule(t.dated_date, t.maturity_date, t.int_rate)
        flows.append(flow.assign(cusip=key))
        age = (
            None
            if hist.empty
            else (pd.Timestamp(cutoff) - pd.Timestamp(hist.index[-1])).days
        )
        if key == cfg["auction_notice_override"]["cusip"]:
            original = cfg["auction_notice_override"]
            assert t.pdf_filenm_announcemt == original["file"]
            minimum, increment = original["minimum"], original["increment"]
            announced = t.announcemt_date
        elif pd.isna(t.min_bid_amt):
            fallback = json.loads((RAW / f"security-{key}.json").read_bytes())[0]
            minimum, increment = (
                int(fallback["minimumToBidAmount"]),
                int(fallback["multipleToBidAmount"]),
            )
            announced = fallback["announcementDate"][:10]
        else:
            minimum, increment = int(t.min_bid_amt), int(t.multiples_to_bid)
            announced = t.announcemt_date
        row = {
            "cusip": key,
            "type": t.security_type,
            "currency": "USD",
            "fund": held.get(key),
            "announced": announced,
            "issue": t.issue_date,
            "maturity": t.maturity_date,
            "coupon_pct": float(t.int_rate),
            "auction_min_face": minimum,
            "auction_increment": increment,
            "marks": len(hist),
            "last_mark": None if hist.empty else hist.index[-1],
            "age_days": age,
            "model": bool(inventory.at[name, "included"]),
            "gate": gate(cutoff, t.issue_date, None if hist.empty else hist.index[-1]),
            "secondary_size_usd": None,
            "last_client_trade": None,
            "executable": False,
        }
        if age == 0:
            m = daily.loc[key]
            clean = m.EODPrice
            assert abs(float(t.int_rate) / 100 - m.Rate) < 1e-8 and pd.Timestamp(
                t.maturity_date
            ) == pd.Timestamp(m.MaturityDate)
            central, cases = risk(flow, cutoff, clean, cfg)
            assert abs(central["dirty"] - hist.close.iloc[-1]) < 1e-8
            row.update(central)
            for scen, c in cases.items():
                shocks.append(dict(cusip=key, scenario=scen, **c))
            row["program_gap_per100"] = (
                abs(m.BuyPrice - m.SellPrice)
                if min(m.BuyPrice, m.SellPrice) > 0
                else None
            )
            row["dv01_chf_on_face"] = (
                central["dv01_per_100"] * cfg["face_usd"] / 100 * fx[cutoff]
            )
        rows.append(row)
        block = stream.reindex(bond_calendar)
        ok = (
            len(block) > 1
            and bond_calendar[0] == start
            and bond_calendar[-1] == cutoff
            and block.close.notna().all()
            and block.usd.iloc[1:].notna().all()
            and list(block.previous.iloc[1:]) == bond_calendar[:-1]
        )
        returns.append(
            {
                "cusip": key,
                "fund": held.get(key),
                "complete": ok,
                "direct_chf": (1 + block.usd.iloc[1:]).prod() * fx_ratio - 1
                if ok
                else None,
            }
        )
    sheets = pd.DataFrame(rows)
    # Auction-style Treasury buybacks supply dated, aggregated executed amounts
    # by issue. They never constitute a standing retail order or executable depth.
    buybacks = pd.DataFrame(
        json.loads((raw / "buybacks_security_details.json").read_bytes())["data"]
    )
    operations = pd.DataFrame(
        json.loads((raw / "buybacks_operations.json").read_bytes())["data"]
    )
    buybacks = buybacks[buybacks.cusip_nbr.isin(sheets.cusip)].merge(
        operations,
        on=["operation_date", "operation_start_time_est"],
        validate="many_to_one",
    )
    buybacks["accepted_usd"] = pd.to_numeric(buybacks.par_amt_accepted)
    traded = buybacks[buybacks.accepted_usd.gt(0)].copy()
    traded["weighted_price"] = pd.to_numeric(
        traded.weighted_avg_accepted_price, errors="raise"
    )
    traded["name"] = "UST:" + traded.cusip_nbr
    traded = traded.merge(
        history[["name", "day", "clean"]],
        left_on=["name", "operation_date"],
        right_on=["name", "day"],
        how="left",
        validate="many_to_one",
    )
    traded["price_gap_per100"] = traded.weighted_price - traded.clean
    latest = traded.sort_values(
        ["operation_date", "operation_start_time_est"]
    ).drop_duplicates("cusip_nbr", keep="last")
    sheets = sheets.merge(
        latest[
            ["cusip_nbr", "operation_date", "settlement_date", "accepted_usd"]
        ].rename(
            columns={"cusip_nbr": "cusip", "accepted_usd": "last_buyback_accepted_usd"}
        ),
        on="cusip",
        how="left",
        validate="one_to_one",
    )
    cases = pd.DataFrame(shocks)
    paths = pd.DataFrame(returns)
    example = cfg["example"]
    funded = replay(
        cfg, auctions, terms_table, history, json.loads(cash_file.read_bytes())
    )
    prior = history[
        (history.name == "UST:" + example) & (history.day <= cfg["stale_check_date"])
    ].day.max()
    stale = gate(cfg["stale_check_date"], terms_table.loc[example, "issue_date"], prior)
    assert (
        stale == "Missing or stale valuation"
        and example not in marks(cfg["stale_check_date"]).index
    )
    # The programme's two posted levels are not a trade tape. Do not infer order capacity.
    client_access = json.loads(Path("reports/04-catalogue/resultats.json").read_text())[
        "eligibility"
    ]["by_class"]
    assert (
        client_access["fonds_tresor"]["sum"] == 0
        and client_access["obligation_directe"]["sum"] == 0
    )
    gold, monthly = compare(raw, prices, fx, cfg)
    if gold["bounded_hashes"] != cfg["bounded_gold_hashes"]:
        raise ValueError("Gold observations changed inside the frozen time window")
    wti = Path("data/local/4/raw/DCOILWTICO.csv")
    checked(
        wti, json.loads(Path("config/sources-4.json").read_text())[wti.name]["sha256"]
    )
    factor = (
        pd.read_csv(wti, index_col="observation_date")
        .iloc[:, 0]
        .loc[cfg["gold_start"] : cutoff]
        .dropna()
    )
    response = json.loads(Path("reports/08-chocs/results.json").read_text())
    gold["wti"] = {
        "observations": len(factor),
        "negative_days": int((factor < 0).sum()),
        "unit": "USD/barrel",
        "sensitivity": next(
            v for v in response["example_oil_plus10_pct"] if v["name"] == "GLD"
        ),
    }
    byfund = []
    for fund in fund_return:
        pair = paths[paths.fund.str.contains(fund, na=False)]
        byfund.append(
            {
                "fund": fund,
                "issues": len(pair),
                "complete": int(pair.complete.sum()),
                "median_direct_chf": pair.direct_chf.median(),
                "fund_chf": fund_return[fund],
            }
        )
    summary = {
        "as_of": cutoff,
        "fx": fx[cutoff],
        "issues": len(sheets),
        "types": sheets.type.value_counts().to_dict(),
        "mark_count": int(sheets.marks.sum()),
        "valued": int(sheets.dirty.count()),
        "modelled": int(sheets.model.sum()),
        "gates": sheets.gate.value_counts().to_dict(),
        "live_orders": int(sheets.executable.sum()),
        "fallbacks": [
            {
                "mandate": "Exact dated USD principal",
                "research": "Selected direct issue with matching maturity",
                "access": "No executable secondary terms or account",
            },
            {
                "mandate": "Treasury duration exposure",
                "research": "Compare IEF or TLT with matched duration and CHF risk",
                "access": "No verified fund order on the account",
            },
            {
                "mandate": "Near-term CHF payment",
                "research": "Keep already settled CHF available for the dated bill",
                "access": "Conditional on actual cash balance; no trade assumed",
            },
        ],
        "buybacks": {
            "window_start": "2024-01-01",
            "accepted_issue_operations": len(traded),
            "issues_with_accepted": traded.cusip_nbr.nunique(),
            "zero_acceptance_rows": int(buybacks.accepted_usd.eq(0).sum()),
            "compared_marks": int(traded.clean.count()),
            "median_abs_gap_per100": traded.price_gap_per100.abs().median(),
            "recent_example": records(
                latest.sort_values(["operation_date", "cusip_nbr"]).tail(1)[
                    [
                        "cusip_nbr",
                        "operation_date",
                        "settlement_date",
                        "accepted_usd",
                        "weighted_price",
                        "clean",
                        "price_gap_per100",
                    ]
                ]
            )[0],
        },
        "programme_dispersion": {
            "available": int(sheets.program_gap_per100.count()),
            "median_per100": sheets.program_gap_per100.median(),
            "max_per100": sheets.program_gap_per100.max(),
        },
        "stale_case": {
            "cusip": example,
            "check": cfg["stale_check_date"],
            "last_mark": prior,
            "decision": stale,
        },
        "auction_replay": funded,
        "example_risk": records(sheets[sheets.cusip.eq(example)])[0],
        "example_shocks": records(cases[cases.cusip.eq(example)]),
        "risk_ranges": records(
            sheets.groupby("type")
            .agg(
                issues=("cusip", "size"),
                measured=("dirty", "count"),
                min_duration=("duration", "min"),
                max_duration=("duration", "max"),
                median_convexity=("convexity", "median"),
                max_approx_error_bp=("max_approx_error_bp", "max"),
            )
            .reset_index()
        ),
        "approx_exceeds": int(sheets.exceeds_tolerance.eq(True).sum()),
        "comparison": {
            "start": start,
            "end": cutoff,
            "required_marks": len(bond_calendar),
            "by_fund": byfund,
        },
        "gold": gold,
    }
    files = [
        cfgfile,
        *sorted(Path(__file__).parent.glob("*.py")),
        BASE / "bonds.json",
        universe / "manifest.json",
        CAT / "manifest.json",
        *auction_files,
        *sorted(RAW.glob("security-*.json")),
        RAW / (cutoff + ".xml.gz"),
        RAW / (cfg["stale_check_date"] + ".xml.gz"),
        RAW / (funded["matured_control"]["last_mark_day"] + ".xml.gz"),
        RAW / (funded["matured_control"]["pay"] + ".xml.gz"),
        Path("config/econometrie.json"),
        Path("reports/08-chocs/results.json"),
        Path("reports/04-catalogue/resultats.json"),
    ]
    hashes = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    stamp = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16]
    summary["archive"] = stamp
    dest = LOCAL / stamp
    if not dest.exists():
        with TemporaryDirectory(dir=LOCAL) as temp:
            stage = Path(temp) / "records"
            stage.mkdir()
            for label, df in {
                "issues": sheets,
                "scenario": cases,
                "cashflows": pd.concat(flows),
                "matched_etfs": paths,
                "buyback_operations": traded,
                "gold_months": monthly,
            }.items():
                df.to_parquet(stage / (label + ".parquet"))
            (stage / "sources.json").write_text(json.dumps(hashes, indent=2))
            stage.rename(dest)
    REPORT.mkdir(parents=True, exist_ok=True)
    disclosure = sheets.merge(
        cases.pivot(index="cusip", columns="scenario", values="chf").add_suffix(
            " CHF return"
        ),
        on="cusip",
        how="left",
        validate="one_to_one",
    )
    (REPORT / "issues.json").write_text(
        json.dumps(records(disclosure), indent=2, allow_nan=False) + "\n"
    )
    (REPORT / "results.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n"
    )
    print("Section 10 archive", stamp)


if __name__ == "__main__":
    run()
