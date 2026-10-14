"""layout-0217: one function says where a stub stands; both callers read it."""

import dataclasses
from types import SimpleNamespace
from typing import TYPE_CHECKING

from samples import connection, function_spec, hid

from fransys_layout.engines.schematic import _stub_seats
from fransys_layout.stages.black_box import stub_places
from fransys_layout.stages.references import off_stubs
from fransys_layout.stages.references.types import BlackBoxReads, LinkWorld
from fransys_layout.stages.types import Cell, Column, Home, Role, StubText

if TYPE_CHECKING:
    import pytest

inner, outer = hid("unit", 1), hid("unit", 2)


def test_a_stub_stands_at_its_black_boxes_else_at_home() -> None:
    assert stub_places([1], [2]) == [1]
    assert stub_places([], [2]) == [2]


def test_off_stub_ends_take_the_black_box_page_over_the_home_page() -> None:
    near, far = hid("function", 1), hid("function", 2)
    text = StubText(cable="-W1", far="-K2", port="13")
    world = LinkWorld(
        where={
            near: {(1, 1): ("invented", "a"), (2, 1): ("invented", "b")},
            far: {(1, 1): ("invented", "a")},
        },
        drawn_of={},
    )
    ends = off_stubs._stub_ends(
        (connection(1, 1, 2),),
        world,
        {hid("port", 12): [text]},
        frozenset(),
        {near: frozenset({2})},
    )
    assert [end.page for _, end, _ in ends] == [(2, 1)]


def test_stub_seats_take_the_black_box_column_over_the_home_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = dataclasses.replace(function_spec(1), unit=inner)
    reads = BlackBoxReads(nested=frozenset({inner}), edges=frozenset(), top=lambda _u: None)
    monkeypatch.setattr(
        _stub_seats, "unit_nesting", lambda *_: SimpleNamespace(nested=reads.nested)
    )
    monkeypatch.setattr(_stub_seats, "black_box_reads", lambda *_: reads)

    def column(unit):
        return Column(
            key=("invented", str(unit)),
            cells=(Cell(function=spec.function, index=0, home=Home.HERE),),
            group=None,
            role=Role.CONTROL,
            location=None,
            unit=unit,
        )

    columns = (column(inner), column(outer))  # home first, black box (parent's set) second
    seats = _stub_seats.stub_seats(
        None,  # ty: ignore[invalid-argument-type] -- the reads are patched; no model is read
        SimpleNamespace(functions=(spec,)),  # ty: ignore[invalid-argument-type] -- only functions are read
        columns,
        frozenset({spec.function}),
    )
    assert seats == {(spec.function, 1)}
