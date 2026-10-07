"""HA-D1: the harness-line layout records (decision model-0173, spec HL9)."""

import dataclasses
from typing import Any

import pytest
from layout_examples import (
    PRODUCED_BY,
    drawing_set,
    drawn_function,
    group_node,
    page,
    sheet_format,
)

from fransys_model.kernel import Draft, Id, Model, Origin, SchemaError, dumps, freeze, loads
from fransys_model.layout import (
    DERIVED_KINDS,
    BoxCell,
    BoxText,
    ConnectorBox,
    FanLeg,
    HarnessFanOut,
    HarnessLine,
    RoutePoint,
    layout_of,
)
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import ConductorKind, PortRole

_ORIGIN = Origin(file="test_harness_results.py", line=1, note="fixture")
_PORT_A: Id[Any] = Id(kind="port", value="1" * 32)
_PORT_B: Id[Any] = Id(kind="port", value="2" * 32)
_CONDUCTOR_A: Id[Any] = Id(kind="conductor", value="3" * 32)
_CONDUCTOR_B: Id[Any] = Id(kind="conductor", value="4" * 32)
_KEY = ("layout", "harness-engine", "harness")
_POINTS = (RoutePoint(index=0, x=4, y=12), RoutePoint(index=1, x=4, y=30))
_TEXTS = (BoxText(index=0, x=2, y=2), BoxText(index=1, x=2, y=5))
_CELLS = (
    BoxCell(index=0, port=_PORT_A, x=0, y=8, width=10, height=3),
    BoxCell(index=1, port=_PORT_B, x=0, y=11, width=10, height=3),
)
_LEGS = (
    FanLeg(index=0, conductor=_CONDUCTOR_A, points=_POINTS),
    FanLeg(index=1, conductor=_CONDUCTOR_B, points=_POINTS),
)


def _plant() -> tuple[Any, ...]:
    item, function = drawn_function()
    ports = tuple(
        Port(
            id=port,
            key=("plant", "port", name),
            function=function.id,
            template=None,
            name=name,
            role=PortRole.GENERIC,
        )
        for name, port in (("1", _PORT_A), ("2", _PORT_B))
    )
    conductors = tuple(
        Conductor(
            id=cid,
            key=("plant", "wire", name),
            a=_PORT_A,
            b=_PORT_B,
            kind=ConductorKind.WIRE,
            carrier=None,
        )
        for name, cid in (("a", _CONDUCTOR_A), ("b", _CONDUCTOR_B))
    )
    return group_node(), item, function, *ports, *conductors, drawing_set(), sheet_format(), page()


def _line(points: tuple[RoutePoint, ...] = _POINTS) -> HarnessLine:
    return HarnessLine(
        id=Id(kind="layout.harness_line", value="a" * 32),
        key=(*_KEY, "line"),
        page=page().id,
        harness=drawn_function()[0].id,
        branch=1,
        points=points,
        text_x=4,
        text_y=9,
        produced_by=PRODUCED_BY,
    )


def _box(texts: tuple[BoxText, ...] = _TEXTS, cells: tuple[BoxCell, ...] = _CELLS) -> ConnectorBox:
    return ConnectorBox(
        id=Id(kind="layout.connector_box", value="b" * 32),
        key=(*_KEY, "box"),
        page=page().id,
        function=drawn_function()[1].id,
        x=10,
        y=20,
        width=30,
        height=16,
        texts=texts,
        cells=cells,
        produced_by=PRODUCED_BY,
    )


def _fan(legs: tuple[FanLeg, ...] = _LEGS) -> HarnessFanOut:
    return HarnessFanOut(
        id=Id(kind="layout.harness_fan_out", value="c" * 32),
        key=(*_KEY, "fan"),
        page=page().id,
        harness=drawn_function()[0].id,
        branch=2,
        x=4,
        y=30,
        legs=legs,
        produced_by=PRODUCED_BY,
    )


def _freeze(*records: Any) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_harness_records_freeze_and_round_trip() -> None:
    """All three kinds freeze, read back through `layout_of` and survive dumps and loads."""
    model = _freeze(*_plant(), _line(), _box(), _fan())
    assert loads(dumps(model)) == model
    assert layout_of(model, HarnessLine)[_line().id].points == _POINTS
    assert layout_of(model, ConnectorBox)[_box().id].cells == _CELLS
    assert layout_of(model, HarnessFanOut)[_fan().id].legs == _LEGS


def test_line_points_are_stored_in_index_order() -> None:
    """`HarnessLine.points` is sorted by `index`, whatever order it was built in."""
    assert _line(tuple(reversed(_POINTS))).points == _POINTS


def test_box_texts_and_cells_are_stored_in_index_order() -> None:
    """`ConnectorBox.texts` and `.cells` are each sorted by `index`."""
    box = _box(tuple(reversed(_TEXTS)), tuple(reversed(_CELLS)))
    assert box.texts == _TEXTS
    assert box.cells == _CELLS


def test_fan_legs_and_their_points_are_stored_in_index_order() -> None:
    """`HarnessFanOut.legs` and each leg's `points` are sorted by `index`."""
    backwards = tuple(dataclasses.replace(leg, points=_POINTS[::-1]) for leg in _LEGS[::-1])
    assert _fan(backwards).legs == _LEGS


def test_a_repeated_index_is_refused_in_every_kind() -> None:
    """Two entries with one `index` have no order, in each place a record is ordered."""
    twin = RoutePoint(index=0, x=1, y=1)
    with pytest.raises(SchemaError):
        _line((_POINTS[0], twin))
    with pytest.raises(SchemaError):
        _box(texts=(_TEXTS[0], dataclasses.replace(_TEXTS[1], index=0)))
    with pytest.raises(SchemaError):
        _box(cells=(_CELLS[0], dataclasses.replace(_CELLS[1], index=0)))
    with pytest.raises(SchemaError):
        _fan((_LEGS[0], dataclasses.replace(_LEGS[1], index=0)))
    with pytest.raises(SchemaError):
        _fan((dataclasses.replace(_LEGS[0], points=(_POINTS[0], twin)),))


def test_the_harness_kinds_are_derived_kinds() -> None:
    """They are page-bound results, so passes remove and the tests count them as derived."""
    assert {HarnessLine, ConnectorBox, HarnessFanOut} <= set(DERIVED_KINDS)
