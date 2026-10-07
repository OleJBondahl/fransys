"""The RATINGS-3 per-function readers: breaking points, fault current, draw, conductive ports."""

from decimal import Decimal

from current_plant import fuse, rate
from plant import Plant

from fransys_model.kernel import make_id
from fransys_model.vocab import (
    BoundaryValuesFacet,
    BreakingPoint,
    Operating,
    OperatingFacet,
    PartRatingFacet,
    Rating,
    RatingFacet,
)
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import Current, PortRole
from fransys_model.vocab.fault_readers import (
    breaking_points,
    conductive_ports,
    draw,
    fault_current,
    fault_time_constant,
)
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


def test_a_holders_own_points_are_read_by_kind() -> None:
    model = _holder(points=(_HOLDER_POINT,)).model()
    assert breaking_points(model, _F, Current.DC) == (_HOLDER_POINT,)
    assert breaking_points(model, _F, Current.AC) == (_HOLDER_POINT,)


def test_a_fitted_links_points_replace_the_holders() -> None:
    link = Rating(breaking_dc=(_LINK_POINT,))
    model = _holder(points=(_HOLDER_POINT,), link=link).model()
    assert breaking_points(model, _F, Current.DC) == (_LINK_POINT,)
    assert breaking_points(model, _F, Current.AC) == ()


def test_a_fitted_link_with_no_points_gives_none_even_when_the_holder_states_some() -> None:
    model = _holder(points=(_HOLDER_POINT,), link=Rating(current_dc_a=Decimal(4))).model()
    assert breaking_points(model, _F, Current.DC) == ()


def test_a_boundary_rating_gives_no_points() -> None:
    plant = _holder()
    unit = plant.unit("u", name="u")
    boundary = plant.boundary(unit, _F)
    rating = Rating(breaking_dc=(_HOLDER_POINT,))
    facet = BoundaryValuesFacet(
        id=make_id(BoundaryValuesFacet, ("b",)), key=("b",), subject=boundary, rating=rating
    )
    plant.add(facet)
    assert breaking_points(plant.model(), _F, Current.DC) == ()


def _sources(*envelopes: Operating) -> Plant:
    """Function `F`, whose template states the first envelope and units' boundaries the rest."""
    plant = _holder()
    plant.add(
        OperatingFacet(
            id=make_id(OperatingFacet, ("F",)),
            key=("F",),
            subject=_TEMPLATE,
            operating=envelopes[0],
        )
    )
    for number, envelope in enumerate(envelopes[1:]):
        boundary = plant.boundary(plant.unit(f"u{number}", name="u"), _F, key=f"b{number}")
        key = (f"b{number}",)
        plant.add(
            BoundaryValuesFacet(
                id=make_id(BoundaryValuesFacet, key), key=key, subject=boundary, operating=envelope
            )
        )
    return plant


def test_fault_current_is_the_largest_of_the_kind_over_the_envelopes() -> None:
    plant = _sources(
        Operating(fault_current_dc_a=Decimal(900), fault_current_ac_a=Decimal(50)),
        Operating(fault_current_dc_a=Decimal(1200)),
        Operating(fault_current_dc_a=Decimal(700)),
    )
    model = plant.model()
    assert fault_current(model, _F, Current.DC) == Decimal(1200)
    assert fault_current(model, _F, Current.AC) == Decimal(50)


def test_fault_current_and_time_constant_are_none_when_none_states_them() -> None:
    model = _sources(Operating(nominal_current_a=Decimal(3))).model()
    assert fault_current(model, _F, Current.DC) is None
    assert fault_time_constant(model, _F) is None
    assert fault_time_constant(_holder().model(), _F) is None


def test_fault_time_constant_is_the_largest_over_the_envelopes() -> None:
    plant = _sources(
        Operating(fault_time_constant_ms=Decimal(5)), Operating(fault_time_constant_ms=Decimal(20))
    )
    assert fault_time_constant(plant.model(), _F) == Decimal(20)


def test_draw_is_the_largest_nominal_current_over_the_envelopes() -> None:
    plant = _sources(
        Operating(nominal_current_a=Decimal(2)), Operating(nominal_current_a=Decimal(6))
    )
    model = plant.model()
    assert draw(model, _F) == Decimal(6)
    assert draw(_holder().model(), _F) is None


def test_a_lamp_with_l_n_and_pe_ports_has_two_conductive_ports() -> None:
    plant = Plant()
    function = plant.function(plant.item("H"), "f")
    other = plant.function(plant.item("K"), "f")
    roles = {"L": PortRole.GENERIC, "N": PortRole.GENERIC, "PE": PortRole.PE}
    ids = {name: make_id(Port, ("H", "f", name)) for name in roles}
    for name, role in roles.items():
        plant.add(
            Port(
                id=ids[name],
                key=("H", "f", name),
                function=function,
                template=None,
                name=name,
                role=role,
            )
        )
    plant.port(other, "1")  # another function's port is never one of these
    assert conductive_ports(plant.model(), function) == tuple(sorted((ids["L"], ids["N"])))
