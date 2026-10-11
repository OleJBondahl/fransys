"""The listing codec writes a rating's RATINGS-3 fields only when set (R1), and reads them back."""

from decimal import Decimal

from fransys_model.derive.baseline_codec import dumps, loads
from fransys_model.derive.rows import BaselineBoundary, BaselineUnit, Listing
from fransys_model.vocab import BreakingPoint, Operating, Rating


def _listing(rating: Rating, operating: Operating) -> Listing:
    unit = BaselineUnit(name="u", version=1, revision=1, interface="i")
    row = BaselineBoundary(designation="X1", ports=("1",), rating=rating, operating=operating)
    return Listing(unit=unit, items=(), units=(), boundary=(row,), conductors=(), mates=(), nets=())


def test_points_and_a_fault_current_round_trip() -> None:
    rating = Rating(
        breaking_ac=(BreakingPoint(voltage_v=Decimal(400), current_a=Decimal(10000)),),
        breaking_dc=(
            BreakingPoint(
                voltage_v=Decimal(250), current_a=Decimal(5000), time_constant_ms=Decimal(15)
            ),
        ),
    )
    operating = Operating(fault_current_dc_a=Decimal(800), fault_time_constant_ms=Decimal(5))
    listing = _listing(rating, operating)
    text = dumps(listing)
    assert "breaking_dc" in text
    assert loads(text) == listing
    assert dumps(loads(text)) == text
