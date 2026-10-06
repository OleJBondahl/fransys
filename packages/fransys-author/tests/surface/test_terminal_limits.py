"""TL1: `Terminal.limits` gives `Fn.limits`'s refusals and writes the same boundary call."""

from decimal import Decimal

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.vocab import Boundary, BoundaryValuesFacet, Rating

from ..equivalence.series_parts import series_library  # noqa: TID252 -- same suite's stub parts

_RATING = Rating(voltage_ac_v=Decimal(250))


def _in_unit(strip_of):
    d = design(series_library())
    root = d._engine
    d._engine = root.unit("io", revision=1, interface="1")  # ty: ignore[invalid-assignment] -- test-only seam until EA-UNITS-RUNS
    return root, strip_of(d)


def test_limits_writes_one_boundary_with_its_rating_and_returns_the_terminal() -> None:
    root, terminal = _in_unit(lambda d: d.terminal_strip("X1", "TEST-TERM", 2)[1])
    assert terminal.limits(rating=_RATING) is terminal
    (boundary,) = [r for r in root.draft().records() if isinstance(r, Boundary)]
    (facet,) = [r for r in root.draft().records() if isinstance(r, BoundaryValuesFacet)]
    assert facet.subject == boundary.id
    assert facet.rating == _RATING


def test_a_run_terminal_writes_too() -> None:
    root, terminal = _in_unit(lambda d: d.terminal_strip("X1", "TEST-TERM").run("IO", 2)[2])
    terminal.limits(rating=_RATING)
    assert [r for r in root.draft().records() if isinstance(r, BoundaryValuesFacet)]


def test_limits_without_a_value_raises_and_writes_nothing() -> None:
    root, terminal = _in_unit(lambda d: d.terminal_strip("X1", "TEST-TERM", 2)[1])
    with pytest.raises(AuthorError, match=r"use interface=True on the device"):
        terminal.limits()
    assert not [r for r in root.draft().records() if isinstance(r, Boundary)]


def test_limits_outside_a_unit_raises_the_engine_error() -> None:
    terminal = design(series_library()).terminal_strip("X1", "TEST-TERM", 2)[1]
    with pytest.raises(AuthorError, match="needs a unit"):
        terminal.limits(rating=_RATING)
