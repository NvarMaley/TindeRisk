import copy
import json
from pathlib import Path

import numpy as np

from riskmatch.personalized_matches import (
    adapt_target, bounds_for, defensive_reference, fingerprint, risk_preferences, valid_weights,
)
from riskmatch.profiling.mandate import validate_mandate


def test_mandate_conditioned_stress_overlay():
    upper = np.array([.65, .65, 1.])
    shocks = np.array([[-.4, -.1, 0.], [-.1, -.2, 0.]])
    covariance = np.diag([.09, .03, 0.])
    reference = defensive_reference(upper, shocks, covariance, .08, .10)
    target = np.array([.65, .35, 0.])
    cautious = adapt_target(target, reference, upper, shocks, .08, covariance, .10)
    permissive = adapt_target(target, reference, upper, shocks, .30, covariance, 1.)
    assert valid_weights(cautious, upper, shocks, .08, covariance, .10)
    assert valid_weights(permissive, upper, shocks, .30, covariance, 1.)
    assert cautious[0] < permissive[0]
    assert cautious[2] > permissive[2]
    assert defensive_reference(np.array([.1, .1, .1]), shocks, covariance, .08, .1) is None


def test_mandate_asset_filter_and_preference_version():
    root = Path(__file__).resolve().parents[2]
    mandate = json.loads((root / "configs/mandate-example.json").read_text())
    mandate["constraints"]["allowed_assets"] = ["treasury", "cash"]
    mandate["constraints"]["max_asset_weight"]["value"] = .25
    report = validate_mandate(mandate)
    assert report["personalized_eligible"] and not report["demo_eligible"]
    assets = [{"category": "stock", "instrument": "1", "ticker": "ABC"},
              {"category": "treasury_etf", "instrument": "2", "ticker": "SHY"}]
    upper, cash = bounds_for(assets, mandate, "date", {"date": {"1"}})
    assert np.allclose(upper, [0, .25])
    assert cash == .25
    assert risk_preferences(mandate, report, 30)[0] > risk_preferences(mandate, report, 1)[0]
    assert fingerprint(mandate, 1, "data") != fingerprint(mandate, 30, "data")
    amended = copy.deepcopy(mandate)
    amended["constraints"]["max_asset_weight"]["value"] = .3
    assert fingerprint(mandate, 1, "data") != fingerprint(amended, 1, "data")
    amended["constraints"]["max_issuer_weight"]["value"] = .2
    assert not validate_mandate(amended)["personalized_eligible"]
