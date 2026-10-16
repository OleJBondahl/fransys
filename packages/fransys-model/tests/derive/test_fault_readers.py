"""The RATINGS-3 per-function readers: breaking points, fault current, draw, conductive ports."""

from decimal import Decimal

from current_plant import fuse, rate
from plant import Plant

from fransys_model.derive.facts.fault.readers import (
    breaking_points,
)
from fransys_model.kernel import make_id
from fransys_model.vocab import (
    BreakingPoint,
    PartRatingFacet,
    Rating,
    RatingFacet,
)
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Current
from fransys_model.vocab.templates import FunctionTemplate

_HOLDER = make_id(Item, ("F",))
_F = Plant.function_id("F", "f")
_TEMPLATE = make_id(FunctionTemplate, ("F", "f"))
_HOLDER_POINT = BreakingPoint(voltage_v=Decimal(250), current_a=Decimal(10000))
_LINK_POINT = BreakingPoint(
    voltage_v=Decimal(1000), current_a=Decimal(5000), time_constant_ms=Decimal(10)
)


def _holder(*, points: tuple[BreakingPoint, ...] = (), link: Rating | None = None) -> Plant:
    """A protection holder `F` whose template states `points` DC, with a link of rating `link`."""
    plant = Plant()
    fuse(plant, "F", None)
    rating = Rating(breaking_dc=points, breaking_ac=points)
    plant.add(
        RatingFacet(id=make_id(RatingFacet, ("F",)), key=("F",), subject=_TEMPLATE, rating=rating)
    )
    if link is not None:
        part = rate(plant, "L", None)
        plant.add(
            PartRatingFacet(
                id=make_id(PartRatingFacet, ("L",)), key=("L",), subject=part, rating=link
            )
        )
        plant.item("L", part=part, parent=_HOLDER)
    return plant


def test_a_fitted_link_with_no_points_gives_none_even_when_the_holder_states_some() -> None:
    model = _holder(points=(_HOLDER_POINT,), link=Rating(current_dc_a=Decimal(4))).model()
    assert breaking_points(model, _F, Current.DC) == ()
