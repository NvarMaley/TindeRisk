from datetime import date
import pytest

from riskmatch.analytics.forecast_fallback import bond_yield


def test_conditional_yield_to_maturity():
    assert bond_yield(date(2025,1,31),date(2027,1,31),.04,100,"treasury_note")==pytest.approx(.04)
    assert bond_yield(date(2025,1,1),date(2026,1,1),0,95,"treasury_bill")==pytest.approx(100/95-1)
    with pytest.raises(ValueError):
        bond_yield(date(2026,1,1),date(2025,1,1),.04,100,"treasury_note")
