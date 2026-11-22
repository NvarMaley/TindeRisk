"""Construct unsigned catalogue content and paired annual client-value diagnostics."""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE.parent


def build():
    records = []
    sources = {}

    def read(path):
        data = (R / path).read_bytes()
        sources[path] = hashlib.sha256(data).hexdigest()
        return pd.read_csv(R / path)

    def add(study, version, name, gain, lo, hi, minimum, count, detail):
        def finite(x):
            return float(x) if pd.notna(x) else None

        records.append(
            dict(
                id=f"{study}/{version}/{name}",
                study=study,
                version=version,
                method=name,
                gain=finite(gain),
                lower=finite(lo),
                upper=finite(hi),
                minimum=finite(minimum),
                observations=int(count),
                disposition="descriptive only"
                if not count or study == "H05"
                else "inconclusive"
                if not np.isfinite(hi) or not np.isfinite(minimum) or hi >= minimum
                else "reject for material gain",
                reason=detail,
                approved=False,
                independent=0,
                permission="historical research",
                currency="study-specific",
                fallback="registered reference",
                mandate="research",
                as_of="2026-11-23",
                expires="2026-11-23",
            )
        )

    v = read("experiments/results/decisions.csv").set_index("study")
    for r in (
        read("experiments/results/paired_comparisons.csv")
        .query("phase=='historical replay' and block==3")
        .itertuples()
    ):
        add(
            r.study,
            "v1",
            r.arm,
            r.gain,
            r.low,
            r.high,
            v.at[r.study, "minimum_gain"],
            r.paired,
            "retrospective paired months; " + v.at[r.study, "decision"],
        )
    for r in (
        read("robustness/results/scorecard.csv")
        .query("phase=='historical replay' and block==3 and sample=='with fallback'")
        .itertuples()
    ):
        add(
            r.study,
            "v2",
            r.candidate,
            r.gain,
            r.low,
            r.high,
            r.minimum,
            r.scored,
            "exploratory historical extension; no independent months",
        )
    for r in (
        read("sentiment_followup/results/comparison.csv")
        .query(
            "phase=='historical replay' and block_months==3 and (cost_bp==10 or endpoint=='risk')"
        )
        .itertuples()
    ):
        add(
            "H06",
            "follow-up",
            r.endpoint,
            r.mean_gain,
            r.low,
            r.high,
            r.minimum,
            r.scored_months,
            "retrospective signal; live timestamps unverified",
        )
    x = read("execution/results/cohorts.csv")
    rows = []
    for (case, policy), g in x.groupby(["case", "policy"]):
        panel = g.pivot(
            index="cohort", columns="arm", values="net_household_return"
        ).dropna()
        n = len(panel)
        rng = np.random.default_rng(7201)
        starts = rng.integers(n - 1, size=(3999, (n + 1) // 2))
        idx = (starts[:, :, None] + np.arange(2)).reshape(3999, -1)[:, :n]
        for arm in ["classical", "robust"]:
            for phi in [8 / 3, 40 / 9]:

                def score(values, axis):
                    return (
                        values.mean(axis=axis) - phi * values.var(axis=axis, ddof=1) / 2
                    )

                a = panel[arm].to_numpy()
                b = panel["60/40"].to_numpy()
                gain = score(a, None) - score(b, None)
                boot = score(a[idx], 1) - score(b[idx], 1)
                lo, hi = np.quantile(boot, [0.025, 0.975])
                rows.append(
                    dict(
                        case=case,
                        policy=policy,
                        arm=arm,
                        phi=phi,
                        years=n,
                        gain=gain,
                        low=lo,
                        high=hi,
                        minimum=0.005,
                    )
                )
                if case == "primary" and policy == "hold":
                    add(
                        "allocation",
                        "v1",
                        f"{arm} phi {phi:.3f}",
                        gain,
                        lo,
                        hi,
                        0.005,
                        n,
                        "seven previously inspected annual household outcomes",
                    )
    pd.DataFrame(rows).to_csv(HERE / "client_value.csv", index=False)
    records.append(
        dict(
            id="demo/manual/v1",
            study="fictional monitoring",
            version="v1",
            method="client-confirmed example",
            approved=True,
            disposition="retain demo only",
            permission="synthetic local demonstration",
            currency="CHF",
            mandate="illustrative CHF 50000",
            cost_bp=10,
            fallback="hold CHF cash and protect bill",
            as_of="2026-11-23",
            expires="2027-11-23",
            independent=0,
        )
    )
    obj = {
        "schema": 1,
        "release": "2026-11-23.1",
        "sources": sources,
        "records": records,
    }
    (HERE / "catalogue.json").write_text(
        json.dumps(obj, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    build()
