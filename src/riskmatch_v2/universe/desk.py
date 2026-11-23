"""Interactive research portfolios using the same archived factor models as the notebook."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy import sparse

from ..feasibility.study import market
from ..options.compare import combine, distinct
from .model import affordable, blend_search, broad_frontier, options, risk_metrics


def load_model(bundle):
    b = Path(bundle)
    params = json.loads(Path("config/faisabilite-5.json").read_text())
    with np.load(b / "models.npz", allow_pickle=False) as data:
        names = data["names"].tolist()
        return (
            [
                market(names, mu, sparse.load_npz(b / f"risk_{i}.npz"), params)
                for i, mu in enumerate(data["mu"])
            ],
            data["shock"],
            data["prices"],
            float(data["fx"]),
        )


def customize(models, shock, low, high, excluded):
    if not 0 <= low <= high:
        raise ValueError("Invalid volatility range")
    hi = models[0].hi.copy()
    for k in excluded:
        hi[models[0].names.index(k)] = 0.0
    models = [replace(m, hi=hi) for m in models]
    bound = broad_frontier(models[0], low, high)
    if not bound["candidate"]:
        return models, {}, bound["status"] + " · " + bound["proof"]
    main = models[0]
    witness = np.array(bound["candidate"]["weights"])
    raw = {"Return": witness}
    for name, w in options(models, shock, high).items():
        if name == "Return":
            continue
        if main.evaluate(w)["risk"] < low:
            left, right = 0.0, 1.0
            for _ in range(48):
                mid = (left + right) / 2
                if np.linalg.norm(main.root @ (w + mid * (witness - w))) < low:
                    left = mid
                else:
                    right = mid
            w = w + right * (witness - w)
        if not main.evaluate(w, low, high)["valid"]:
            continue
        if name == "Robust" and any(
            not m.evaluate(w, high=high)["valid"] for m in models
        ):
            continue
        if (
            name != "Robust"
            and main.evaluate(w)["net"] < bound["candidate"]["net"] - 0.025 - 1e-6
        ):
            continue
        raw[name] = w
    ref = np.zeros(len(witness))
    ref[main.names.index("SPY")] = 0.6
    ref[main.names.index("IEF")] = 0.4
    raw["60/40 benchmark"] = ref
    return models, distinct(raw, 0.005)[0], bound["status"]


def mix(models, shock, prices, fx, candidates, parts, criterion, minimum, low, high):
    if criterion != "Manual":
        result = blend_search(
            models, candidates, criterion=criterion, low=low, high=high, minimum=minimum
        )
        if "parts" not in result:
            return {"status": result["status"]}
        parts = result["parts"]
    w = combine(candidates, parts)
    c = risk_metrics(models, shock, w)
    c["valid"] = models[0].evaluate(w, low, high)["valid"]
    if not c["valid"]:
        return dict(status="mixture out of slice", vol=c["vol"])
    c.update(
        status="candidate verified",
        parts=parts,
        rounding=affordable(models[0], w, prices, fx, None, 35000, high, low)["status"],
    )
    return c
