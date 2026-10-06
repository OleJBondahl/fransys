"""`function_operatings` and `states_current` (decision model-0088).

One function `f` of item `k1` (a template of a part), and four units that each take it as a
boundary. Each test adds only the facets it needs to a model built from `Plant`.
"""

from decimal import Decimal
from typing import Any

import pytest
from plant import Plant

from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab import (
    BoundaryValuesFacet,
    Operating,
    OperatingFacet,
    PartRatingFacet,
    Rating,
    RatingFacet,
    boundary_operating,
)
from fransys_model.vocab.core import Function, Unit
from fransys_model.vocab.rating_readers import (
    FunctionOperating,
    function_operatings,
    function_ratings,
    states_current,
)
from fransys_model.vocab.units import Boundary

_TEN = Decimal(10)
_B1, _B2, _B3, _B4 = (make_id(Boundary, (key,)) for key in ("b1", "b2", "b3", "b4"))
_U1, _U2, _U3 = (make_id(Unit, (key,)) for key in ("u1", "u2", "u3"))
_NOWHERE = make_id(Function, ("nowhere",))
_RATING_CURRENTS = {"current_ac_a", "current_dc_a"}


class _World:
    """The plant and the ids of its function, part and template."""

    def __init__(self) -> None:
        self.plant = Plant()
        part, template, _, _ = self.plant.relay_part()
        self.part, self.template = part.id, template.id
        item = self.plant.item("k1", part=self.part)
        self.function: Id[Function] = self.plant.function(item, "f", template=self.template)
        for unit, boundary in (("u1", "b1"), ("u2", "b2"), ("u3", "b3"), ("u4", "b4")):
            self.plant.boundary(self.plant.unit(unit, name=unit), self.function, key=boundary)

    def add(self, cls: type, subject: Any, **value: Any) -> None:
        key = ("current", cls.__name__, *(str(subject.value),))
        self.plant.add(cls(id=make_id(cls, key), key=key, subject=subject, **value))

    def model(self) -> Model:
        return self.plant.model()


# ---- function_operatings ----------------------------------------------------------------------


def test_function_operatings_lists_the_template_first_then_each_boundary_in_id_order() -> None:
    """The boundaries are made b1, b2, b3 (units u1, u2, u3) but their ids sort b3, b2, b1."""
    assert sorted([_B1, _B2, _B3]) == [_B3, _B2, _B1]
    world = _World()
    template_env = Operating(nominal_voltage_v=Decimal(864), max_current_dc_a=Decimal(186))
    b1_env = Operating(max_current_dc_a=Decimal(100))
    b2_env = Operating(max_current_ac_a=Decimal(63))
    b3_env = Operating(max_current_dc_a=Decimal(7))
    world.add(OperatingFacet, world.template, operating=template_env)
    world.add(BoundaryValuesFacet, _B1, operating=b1_env)
    world.add(BoundaryValuesFacet, _B2, operating=b2_env)
    world.add(BoundaryValuesFacet, _B3, operating=b3_env)
    # b4 states a rating only: no operating, so no entry
    world.add(BoundaryValuesFacet, _B4, rating=Rating(voltage_dc_v=Decimal(5)))

    found = function_operatings(world.model(), world.function)

    assert list(found) == [
        FunctionOperating(template_env, None),
        FunctionOperating(b3_env, _U3),
        FunctionOperating(b2_env, _U2),
        FunctionOperating(b1_env, _U1),
    ]


def test_function_operatings_has_no_template_entry_without_a_template_facet() -> None:
    world = _World()
    env = Operating(max_current_dc_a=Decimal(7))
    world.add(BoundaryValuesFacet, _B2, operating=env)
    assert function_operatings(world.model(), world.function) == (FunctionOperating(env, _U2),)


def test_function_operatings_reads_each_source_on_its_own_with_no_fallback() -> None:
    """A boundary with no facet adds nothing: the template's envelope is not repeated on it."""
    world = _World()
    env = Operating(max_current_dc_a=_TEN)
    world.add(OperatingFacet, world.template, operating=env)
    model = world.model()
    assert function_operatings(model, world.function) == (FunctionOperating(env, None),)
    assert boundary_operating(model, _B1) is None


def test_function_operatings_of_a_function_with_none_or_an_unknown_id_is_empty() -> None:
    world = _World()
    model = world.model()
    assert function_operatings(model, world.function) == ()
    assert function_operatings(model, _NOWHERE) == ()


# ---- states_current ---------------------------------------------------------------------------


def _with_current(source: str, field: str) -> _World:
    """A world whose only current is `field` = 10, stated by `source`."""
    world = _World()
    value = {field: _TEN}
    rating, operating = (
        (Rating(**value), None) if field in _RATING_CURRENTS else (None, Operating(**value))
    )
    if source == "part":
        world.add(PartRatingFacet, world.part, rating=rating)
    elif source == "template" and rating is not None:
        world.add(RatingFacet, world.template, rating=rating)
    elif source == "template":
        world.add(OperatingFacet, world.template, operating=operating)
    else:
        world.add(BoundaryValuesFacet, _B2, rating=rating, operating=operating)
    return world


_CASES = [
    ("template", "current_ac_a"),
    ("template", "current_dc_a"),
    ("template", "max_current_ac_a"),
    ("template", "max_current_dc_a"),
    ("part", "current_ac_a"),
    ("part", "current_dc_a"),
    ("boundary", "current_ac_a"),
    ("boundary", "current_dc_a"),
    ("boundary", "max_current_ac_a"),
    ("boundary", "max_current_dc_a"),
]


@pytest.mark.parametrize(("source", "field"), _CASES, ids=[f"{s}-{f}" for s, f in _CASES])
def test_a_stated_current_makes_states_current_true(source: str, field: str) -> None:
    world = _with_current(source, field)
    assert states_current(world.model(), world.function) is True


def test_no_rating_states_no_current() -> None:
    world = _World()
    assert states_current(world.model(), world.function) is False


def test_a_part_rating_with_voltages_only_states_no_current() -> None:
    """The function has no template rating, so the part's rating is the one the reader sees."""
    world = _World()
    world.add(PartRatingFacet, world.part, rating=Rating(voltage_dc_v=Decimal(24)))
    assert function_ratings(world.model(), world.function) != ()
    assert states_current(world.model(), world.function) is False


def test_a_part_rating_with_a_current_states_a_current() -> None:
    """The twin of the voltages-only case: the same scenario plus `current_dc_a`."""
    world = _World()
    rating = Rating(voltage_dc_v=Decimal(24), current_dc_a=Decimal(2))
    world.add(PartRatingFacet, world.part, rating=rating)
    assert states_current(world.model(), world.function) is True


def test_an_operating_and_a_boundary_with_voltages_only_state_no_current() -> None:
    world = _World()
    voltages = Operating(nominal_voltage_v=Decimal(864), max_voltage_v=Decimal("985.5"))
    world.add(OperatingFacet, world.template, operating=voltages)
    world.add(BoundaryValuesFacet, _B1, operating=voltages)
    world.add(BoundaryValuesFacet, _B2, rating=Rating(voltage_ac_v=Decimal(230)))
    assert states_current(world.model(), world.function) is False


def test_a_min_breaking_current_alone_is_not_a_stated_current() -> None:
    """A partial-range fuse's minimum breaking current bounds no continuous current."""
    world = _World()
    rating = Rating(min_breaking_current_a=Decimal(4000))
    world.add(PartRatingFacet, world.part, rating=rating)
    assert states_current(world.model(), world.function) is False


def test_a_min_breaking_current_beside_a_current_states_a_current() -> None:
    """The twin of the case above: the same rating plus `current_dc_a`."""
    world = _World()
    rating = Rating(current_dc_a=Decimal(400), min_breaking_current_a=Decimal(4000))
    world.add(PartRatingFacet, world.part, rating=rating)
    assert states_current(world.model(), world.function) is True


def test_states_current_of_an_unknown_function_is_false() -> None:
    assert states_current(_with_current("template", "max_current_dc_a").model(), _NOWHERE) is False
