import numpy as np
import pandas as pd

from src.adaptive_simulation import compare_designs, simulate_clients


def test_simulation_uses_paired_clients_and_measures_full_bank():
    truth, cap, observed = simulate_clients(12, seed=3)
    stressed_truth, stressed_cap, stressed = simulate_clients(12, seed=3, cutoff_shift=.55)
    np.testing.assert_array_equal(truth, stressed_truth)
    np.testing.assert_array_equal(cap, stressed_cap)
    assert len(observed) == 44
    assert any(not np.array_equal(observed[key], stressed[key]) for key in observed)
    comparison = compare_designs(12, seed=3)
    pd.testing.assert_frame_equal(comparison, compare_designs(12, seed=3))
    assert len(comparison) == 46
    assert comparison.loc[comparison.design.eq("whole bank"), "informative_cards"].item() == 44
    assert comparison.category_accuracy.between(0, 1).all()
    assert (comparison.rmse_log_phi > 0).all()
