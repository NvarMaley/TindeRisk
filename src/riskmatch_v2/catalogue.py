"""Load dated CHF total returns and distinguish tradable assets from factors."""

import csv
from dataclasses import dataclass
from datetime import date
from importlib.resources import files
from math import isfinite, prod, sqrt
from pathlib import Path
from statistics import mean, stdev


@dataclass(frozen=True)
class Observation:
    date: date
    asset_id: str
    asset_class: str
    role: str
    return_chf: float
    source: str


COLUMNS = {"date", "asset_id", "asset_class", "role", "return_chf", "source"}


def load_catalogue(path: Path | None = None) -> tuple[Observation, ...]:
    source_file = path if path is not None else files(__package__).joinpath("demo/returns.csv")
    observations = []
    keys = set()
    metadata = {}
    with source_file.open(encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream)
        if set(rows.fieldnames or ()) != COLUMNS:
            raise ValueError("Invalid catalogue columns")
        for row in rows:
            if not all(row.values()) or None in row:
                raise ValueError(f"Incomplete catalogue row {rows.line_num}")
            asset_id = row["asset_id"]
            role = row["role"]
            value = float(row["return_chf"])
            day = date.fromisoformat(row["date"])
            key = (asset_id, day)
            classification = (row["asset_class"], role)
            if (
                not isfinite(value)
                or value < -1
                or key in keys
                or role not in {"instrument", "factor"}
                or metadata.setdefault(asset_id, classification) != classification
            ):
                raise ValueError(f"Invalid catalog row {rows.line_num}")
            keys.add(key)
            observations.append(
                Observation(day, asset_id, *classification, value, row["source"])
            )
    if not observations:
        raise ValueError("Empty catalogue")
    return tuple(sorted(observations, key=lambda row: (row.asset_id, row.date)))


def instrument_panel(
    observations: tuple[Observation, ...], as_of: date
) -> dict[str, dict[date, float]]:
    panel = {}
    for row in observations:
        if row.role == "instrument" and row.date <= as_of:
            panel.setdefault(row.asset_id, {})[row.date] = row.return_chf
    return panel


def describe(returns: list[float], periods_per_year: int = 12) -> dict:
    return {
        "observations": len(returns),
        "cumulative_return": prod(1 + value for value in returns) - 1,
        "annualized_arithmetic_return": mean(returns) * periods_per_year,
        "annualized_volatility": stdev(returns) * sqrt(periods_per_year)
        if len(returns) >= 2
        else None,
    }


def equal_weight_reference(panel: dict[str, dict[date, float]]) -> dict[date, float]:
    """Return the gross rebalanced equal-weight series on common dates."""
    if not panel:
        raise ValueError("No instruments available")
    shared = set.intersection(*(set(returns) for returns in panel.values()))
    if not shared:
        raise ValueError("No common observation dates")
    return {day: mean(returns[day] for returns in panel.values()) for day in sorted(shared)}
