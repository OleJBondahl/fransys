"""The RATINGS-3 per-function readers: breaking points, fault current, draw, conductive ports."""

from current_plant import fuse, rate
from plant import Plant
from rating_plant import point, rated, states_block

from fransys_model.derive.facts.current.bounds import LimitRole, _limits_of
from fransys_model.derive.facts.fault.readers import (
    breaking_points,
)
from fransys_model.elecdef import Current, Fuse, Range, Rating, Role, Unit
from fransys_model.kernel import make_id
from fransys_model.vocab import PartRatingFacet
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.templates import FunctionTemplate

_HOLDER = make_id(Item, ("F",))
_F = Plant.function_id("F", "f")
_TEMPLATE = make_id(FunctionTemplate, ("F", "f"))
_HOLDER_POINT = point("250", "10000")


def _holder(*, link: Rating | None = None, link_block: Fuse | None = None) -> Plant:
    """A protection holder `F` whose template states a DC point, with a link of rating `link`."""
    plant = Plant()
    fuse(plant, "F", None)
    states_block(plant, _TEMPLATE, Fuse(breaking_capacity=(_HOLDER_POINT,)))
    if link is not None:
        part = rate(plant, "L", None)
        plant.add(PartRatingFacet(id=make_id(PartRatingFacet, ("L",)), key=("L",), subject=part, rating=link))
        if link_block is not None:
            template = make_id(FunctionTemplate, ("L", "f"))
            plant.add(FunctionTemplate(id=template, key=("L", "f"), part=part, name="f", kind=FunctionKind.GENERIC))
            states_block(plant, template, link_block, key="L")
        plant.item("L", part=part, parent=_HOLDER)
    return plant


def test_a_fitted_link_with_no_points_gives_none_even_when_the_holder_states_some() -> None:
    assert breaking_points(_holder().model(), _F, Current.DC) == (_HOLDER_POINT,)
    assert breaking_points(_holder().model(), _F, Current.AC) == ()
    assert breaking_points(_holder(link=rated(amps_dc="4")).model(), _F, Current.DC) == ()


def test_a_fitted_links_block_gives_the_points() -> None:
    link_point = point("1000", "5000", "10")
    model = _holder(link=rated(amps_dc="4"), link_block=Fuse(breaking_capacity=(link_point,))).model()
    assert breaking_points(model, _F, Current.DC) == (link_point,)


def test_a_partial_range_link_hides_the_holders_protection_bound() -> None:
    full = _limits_of(_holder(link=rated(amps_dc="4")).model(), _F)
    partial = Fuse(breaking_capacity=(Range(Role.RATED, min=Unit.A(4000)),))
    hidden = _limits_of(_holder(link=rated(amps_dc="4"), link_block=partial).model(), _F)
    assert any(b.role is LimitRole.PROTECTION for b in full)
    assert not any(b.role is LimitRole.PROTECTION for b in hidden)
