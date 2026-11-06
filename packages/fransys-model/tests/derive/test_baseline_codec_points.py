"""The listing codec writes a boundary row's rating and operating in the kernel's canonical form and reads them back."""

import pytest

from fransys_model.derive.baseline_codec import dumps, loads
from fransys_model.derive.rows_baseline import BaselineBoundary, BaselineUnit, Listing
from fransys_model.elecdef import At, Current, Range, Rating, Role, Unit
from fransys_model.kernel import SchemaVersionError
from fransys_model.vocab.operating import Operating


def _listing(rating: Rating | None, operating: Operating | None) -> Listing:
    unit = BaselineUnit(name="u", version=1, revision=1, interface="i")
    row = BaselineBoundary(designation="X1", ports=("1",), rating=rating, operating=operating)
    return Listing(unit=unit, items=(), units=(), boundary=(row,), conductors=(), mates=(), nets=())


def test_a_rating_and_an_operating_round_trip() -> None:
    rating = Rating(voltage=(Range(Role.RATED, nom=Unit.V(250), at=At(Current.AC)),))
    operating = Operating(fault_current=(Range(Role.RATED, max=Unit.A(800), at=At(Current.DC)),), fault_time_constant=Unit.MS(5))
    listing = _listing(rating, operating)
    text = dumps(listing)
    assert '"listing_version":7' in text
    assert loads(text) == listing
    assert dumps(loads(text)) == text


def test_a_stored_version_2_listing_is_refused_with_the_fix() -> None:
    text = dumps(_listing(None, None)).replace('"listing_version":7', '"listing_version":2')
    with pytest.raises(SchemaVersionError, match=r"fr\.rebaseline"):
        loads(text)
