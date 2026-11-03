import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_config_declares_reproducible_core():
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

    assert config["python_version"] == "3.12"
    assert config["seed"] == 42
    assert config["validation"]["method"] == "walk_forward"
    assert config["portfolio"]["long_only"] is True
    assert config["portfolio"]["leverage_limit"] <= 1.0
    assert {"classic", "erc", "black_litterman", "benchmark_60_40"} <= set(
        config["scope"]["core_strategies"]
    )

    assert list(config["risk_bands"]) == [
        "conservative",
        "balanced",
        "growth",
        "aggressive",
    ]
    assert config["target_volatility_grid"] == [0.05, 0.08, 0.10, 0.14]
    assert config["client_display"]["comparison_period"] == "common"
    assert config["client_display"]["show_net_of_costs_first"] is True


def test_question_bank_contract_is_explicit():
    bank = json.loads((ROOT / "questions" / "bank.json").read_text(encoding="utf-8"))

    assert bank["status"] == "draft"
    assert sum(block["target_count"] for block in bank["blocks"].values()) == 60
    assert set(bank["blocks"]) == {"A", "B", "C", "D"}


def test_local_course_material_is_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "/cours  copie/" in gitignore
    assert "/Quant projet /" in gitignore

