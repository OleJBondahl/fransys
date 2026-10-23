"""SW8 row P7.7 at solve level (el-0012): the cross-link instances, no facade, no markers.

The generic builder carries the family: a loop is a cross-link of stage 1, which the core brings
together (stage 3) and routes. The study's counts are the `expected result` cells of design
section 4.10. Of its rows one, the drawn supply, misses today's engine in the core: a strict
xfail that holds for the named core X only.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest
from conventions_fixtures import house
from cross_link_cases import (
    channels_model,
    drawn_supply_model,
    named,
    pilot_model,
    seal_in_model,
    solved,
    two_units_model,
)
from fransys_el import build, options, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout


@pytest.fixture(scope="module")
def seal_in() -> CoreLayout:
    return solved(seal_in_model())


@pytest.fixture(scope="module")
def pilot() -> CoreLayout:
    return solved(pilot_model())


@pytest.fixture(scope="module")
def units() -> CoreLayout:
    return solved(two_units_model())


def score_of(layout: CoreLayout) -> Any:
    """The layout's score, which `solve` always sets."""
    assert layout.score is not None
    return layout.score


def counts(layout: CoreLayout) -> str:
    """The measured numbers, printed into a failure message."""
    s = score_of(layout)
    return f"X={s.X} R={dict(s.R)} P={dict(s.P)} pages={s.pages} refs={len(layout.references)}"


def test_the_seal_in_circuit_is_one_column_with_no_crossing_and_no_reference(
    seal_in: CoreLayout,
) -> None:
    assert (score_of(seal_in).X, score_of(seal_in).R, score_of(seal_in).pages) == (0, (), 1), (
        counts(seal_in)
    )
    assert seal_in.references == (), counts(seal_in)
    contact_pins = {pin.pin for pin, _ in seal_in.wired}
    assert {"com", "no"} <= contact_pins, "the parallel contact is wired in the loop"


def test_the_pilot_beside_its_coil_has_no_crossing(pilot: CoreLayout) -> None:
    assert score_of(pilot).X == 0, counts(pilot)
    assert score_of(pilot).R == (), counts(pilot)


def test_a_crossing_rung_planted_in_the_pilot_shows_in_x() -> None:
    """Planted: a third coil wired across the pilot's rungs gives X above 0, so X can fail."""
    assert score_of(solved(pilot_model(crossed=True))).X > 0


def test_loads_in_two_units_end_in_stubs_only(units: CoreLayout) -> None:
    classes = dict(score_of(units).R)
    assert classes.get("stub", 0) > 0, counts(units)
    assert set(classes) == {"stub"}, counts(units)
    assert score_of(units).X == 0, counts(units)


def test_without_crosses_unit_the_stubs_are_gone() -> None:
    """Planted: the family fact off gives no stub, so the stub count above can fail."""
    model = two_units_model()
    problem, _ = build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)
    plain = replace(problem, nets=tuple(replace(n, crosses_unit=False) for n in problem.nets))
    assert "stub" not in dict(score_of(solve(plain, options(house(), LIBRARY))).R)


def test_a_drawn_supply_closing_the_circuit_has_no_crossing() -> None:
    x = score_of(solved(drawn_supply_model())).X
    named(x, 1, f"X={x}")
    assert x == 0


def test_coils_returned_to_channels_have_no_crossing_and_no_reference() -> None:
    layout = solved(channels_model(2))
    assert (score_of(layout).X, score_of(layout).R) == (0, ()), counts(layout)
