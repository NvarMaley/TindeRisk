"""Public checks that also run in a clone without course or market files."""

from datetime import date
from pathlib import Path
import json

import yaml

from riskmatch.profile import choice_threshold

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_calendar_and_costs():
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    benchmark = config["benchmark"]
    dates = [
        date.fromisoformat(d)
        for split in ("development", "retrospective_validation", "prospective")
        for d in benchmark[split]
    ]
    assert all(a < b for a, b in zip(dates, dates[1:]))
    assert date.fromisoformat(config["specified_on"]) < dates[-2]
    assert set(benchmark["assets"]) <= set(config["archived_etf_panel"])
    assert benchmark["reference_fee_bps"] in benchmark["fee_bps"]


def test_portable_course_tradeoffs():
    bank = json.loads((ROOT / "questions/bank.json").read_text())
    cards = [c for c in bank["cards"] if c["id"].startswith("A")]
    assert len(cards) == 20
    for item in cards:
        value = choice_threshold(
            item["stake"], item["certain"], item["outcomes"], item["probabilities"]
        )
        assert abs(value - item["phi_threshold"]) < 1e-8
