"""Build the studio's dated, portable library from the research archives.

Only identifiers already used for public display and derived statistics leave
the local directory. The portable output contains no vendor tape, monthly return
series, private stock identifiers, orders or client dossiers.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .archive_labels import read_snapshot

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "web/data"
YEARS = [1, 3, 5, 10]
FACTORS = ["market", "fx", "oil", "ten_year_bp", "slope_bp"]
SHOCKS = [0.01, 0.01, 10, 50, 25]
PERIODS = ["rolling_0", "rolling_252", "history"]
PEERS = ["SPY", "IEF", "GLD"]
SIGNALS = [
    "vix",
    "curve",
    "unemployment",
    "gpr",
    "tone",
    "realized",
    "momentum",
    "liquidity",
]
TARGETS = [("return", 21), ("variance", 21), ("variance", 63)]
BATCH = 256
FUND_NAMES = {
    "SPY": "SPDR S&P 500 ETF Trust",
    "GLD": "SPDR Gold Shares",
    "IEF": "iShares 7–10 Year Treasury Bond ETF",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    **{
        f"XL{k}": f"{v} Select Sector SPDR Fund"
        for k, v in {
            "B": "Materials",
            "E": "Energy",
            "F": "Financial",
            "I": "Industrial",
            "K": "Technology",
            "P": "Consumer Staples",
            "U": "Utilities",
            "V": "Health Care",
            "Y": "Consumer Discretionary",
        }.items()
    },
}


def read_json(path):
    return json.loads((ROOT / path).read_text())


def number(value, digits=4):
    return (
        round(float(value), digits) if pd.notna(value) and np.isfinite(value) else None
    )


def pct(value):
    return number(100 * value, 3)


def save_json(filename, value):
    (DEST / filename).write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        + "\n"
    )


def build():
    u = read_json("reports/univers-complet/resultats.json")
    e = read_json("reports/econometrie/results.json")
    stress = read_json("reports/08-chocs/results.json")
    assert (
        u["snapshot"] == e["source_snapshot"] and u["date"] == e["end"] == stress["end"]
    )
    universe = ROOT / "data/local/univers" / u["snapshot"]
    eco = ROOT / "data/local/econometrics" / e["snapshot"]
    stress_dir = ROOT / "data/local/8" / stress["archive"]
    inventory = read_snapshot(
        universe / "membership.parquet", filters=[("day", "=", u["date"])]
    ).set_index("id")
    assert inventory.index.is_unique
    episodes = read_json("config/econometrie.json")["events"]
    bonds = {
        row["cusip"]: row for row in read_json("reports/10-treasuries-gold/issues.json")
    }
    env = pd.read_parquet(ROOT / "data/local/11/allocations.parquet")
    env_date = read_json("reports/11-environment/results.json")["review"]
    details = {
        asset: {
            "h": [None] * 4,
            "f": [[None] * 5 for _ in PERIODS],
            "p": [None] * 3,
            "c": [None] * len(episodes),
            "s": [[None] * 8 for _ in TARGETS],
        }
        for asset in inventory.index
    }

    for x in read_snapshot(eco / "sheets.parquet").itertuples():
        details[x.id]["h"][YEARS.index(x.years)] = [
            int(x.observations),
            pct(x.annual_mean) if x.observations >= 2 else None,
            pct(x.volatility),
            pct(x.cagr) if x.full_sample else None,
            pct(x.max_drawdown) if x.full_sample else None,
            pct(x.cumulative) if x.full_sample else None,
        ]

    ex = pd.read_parquet(
        stress_dir / "exposures.parquet", filters=[("variant", "in", PERIODS)]
    )
    ex = ex[ex.id.isin(inventory.index)]
    for x in ex.itertuples():
        i = FACTORS.index(x.factor)
        details[x.id]["f"][PERIODS.index(x.variant)][i] = [
            pct(x.beta * SHOCKS[i]),
            pct(x.low * SHOCKS[i]),
            pct(x.high * SHOCKS[i]),
            number(x.pearson),
            number(x.spearman),
            int(x.n),
        ]
    # Correlations are pairwise on identical months, with the missing months
    # removed before ranking each side for Spearman.
    frame = pd.read_parquet(eco / "monthly_all_chf.parquet").sort_index().tail(36)
    for i, peer in enumerate(PEERS):
        paired = frame.loc[frame[peer].notna()]
        n = paired.count()
        candidates = n[n >= 18].index
        for asset in candidates:
            s = paired[asset].dropna()
            ref = paired.loc[s.index, peer]
            if s.nunique() < 2 or ref.nunique() < 2:
                continue
            details[asset]["p"][i] = [
                number(s.corr(ref)),
                number(s.rank().corr(ref.rank())),
                len(s),
            ]
    for x in read_snapshot(stress_dir / "historical_crises.parquet").itertuples():
        details[x.id]["c"][list(episodes).index(x.episode)] = [
            pct(x.return_chf),
            pct(x.drawdown),
            number(x.recovery_sessions, 0),
            x.status,
        ]
    for x in pd.read_parquet(eco / "forecasts.parquet").itertuples():
        slots = details[x.id].setdefault("v", [None, None])
        slots[(21, 63).index(x.horizon)] = [
            pct(x.hist_vol),
            pct(x.ewma_vol),
            int(x.windows),
            number(x.qlike_gain),
        ]
    for x in pd.read_parquet(eco / "momentum.parquet").itertuples():
        details[x.Index]["z"] = number(x.momentum_z)
    for x in pd.read_parquet(stress_dir / "security_index.parquet").itertuples():
        details[x.Index]["oil"] = x.oil_interpretation
    tails = pd.read_parquet(
        stress_dir / "oil_tails.parquet", filters=[("rule", "=", "Fixed USD")]
    )
    for x in tails[tails.id.isin(inventory.index)].itertuples():
        slots = details[x.id].setdefault("tails", [None] * 4)
        pos = ("Normal", "High").index(x.regime) * 2 + ("Down", "Up").index(x.side)
        slots[pos] = [int(x.n), pct(x.mean_chf)]
    rows = pd.read_parquet(ROOT / "data/local/12/cross-asset.parquet")
    assert (
        set(rows.instrument) == set(inventory.index)
        and not rows.duplicated(["instrument", "target", "horizon", "signal"]).any()
    )
    for x in rows.itertuples():
        details[x.instrument]["s"][TARGETS.index((x.target, x.horizon))][
            SIGNALS.index(x.signal)
        ] = [
            int(x.n),
            number(x.gain, 9) if x.comparable else None,
        ]

    classes = [
        "Individual stock",
        "Equity ETF",
        "Treasury ETF",
        "Gold (GLD)",
        "Direct Treasury",
    ]
    listing, batch = [], []
    for asset in sorted(inventory.index, key=lambda a: (inventory.at[a, "symbol"], a)):
        x = inventory.loc[asset]
        row = details[asset]
        symbol = x.symbol.removeprefix("UST:")
        name = FUND_NAMES.get(symbol, x.issuer)
        if symbol in bonds:
            b = bonds[symbol]
            name = f"US Treasury {b['type']} · {b['maturity']}"
            row["bond"] = {
                k: b[k]
                for k in (
                    "coupon_pct",
                    "maturity",
                    "duration",
                    "dv01_per_100",
                    "next_coupon",
                )
            }
        if asset in env.index:
            z = env.loc[asset]
            row["env"] = {
                "measured": pct(z.covered),
                "unknownIssuer": pct(z.unknown_gross),
                "intensity": number(z.numerator / z.covered) if z.covered > 0 else None,
            }
        row["reason"] = x.reason
        one = row["h"][0]
        listing.append(
            [symbol, name, classes.index(x["class"]), bool(x.included), one[1], one[2]]
        )
        batch.append(row)
        if len(batch) == BATCH or len(listing) == len(inventory):
            save_json(f"library-{(len(listing) - 1) // BATCH:02}.json", batch)
            batch = []
    manifest = {
        "date": u["date"],
        "model": u["snapshot"],
        "environmentDate": env_date[:10],
        "batch": BATCH,
        "years": YEARS,
        "classes": classes,
        "factors": FACTORS,
        "shocks": SHOCKS,
        "periods": PERIODS,
        "peers": PEERS,
        "signals": SIGNALS,
        "targets": TARGETS,
        "episodes": episodes,
        "assets": listing,
    }
    save_json("library.json", manifest)
    assert len(listing) == 3902 and sum(int(item[3]) for item in listing) == 3322
    coverage = {
        "market_close": u["date"],
        "model_snapshot": u["snapshot"],
        "econometrics_snapshot": e["snapshot"],
        "stress_snapshot": stress["archive"],
        "environment_review": env_date[:10],
        "instruments": len(listing),
        "model_eligible": sum(item[3] for item in listing),
        "classes": {
            label: sum(item[2] == i for item in listing)
            for i, label in enumerate(classes)
        },
        "complete_monthly_windows": {
            f"{year}Y": sum(d["h"][i][3] is not None for d in details.values())
            for i, year in enumerate(YEARS)
        },
        "with_at_least_one_three_year_reference_correlation": sum(
            any(ref is not None for ref in d["p"]) for d in details.values()
        ),
        "with_at_least_one_historical_crisis_return": sum(
            any(crisis is not None and crisis[0] is not None for crisis in d["c"])
            for d in details.values()
        ),
        "macro_estimation_rows": len(ex),
        "individual_signal_tests": len(rows),
        "source_register": "reports/14-delivery/DATA.md",
        "scope": "Dated research output. Broker availability, executable quotes and live marks are unverified.",
    }
    report = ROOT / "reports/studio/library-coverage.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(coverage, indent=2) + "\n")
    print(
        f"{len(listing)} instruments; {len(ex)} factor rows; {len(rows)} signal tests."
    )


if __name__ == "__main__":
    DEST.mkdir(parents=True, exist_ok=True)
    build()
