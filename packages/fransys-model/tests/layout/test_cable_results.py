"""CT5-1C: the cable drawing's layout records (decision model-0158, spec CD2, Q3, Q5, Q9)."""

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

from fransys_model.kernel import (
    Draft,
    Id,
    Model,
    Origin,
    SchemaError,
    dumps,
    freeze,
    loads,
)
from fransys_model.layout import (
    CABLE_KINDS,
    BlockRow,
    BoxKind,
    CableBlock,
    CableBox,
    CoreWire,
    EndBox,
    EndStyle,
    PinCell,
    RoutePoint,
    derived_layout_ids,
    layout_of,
)
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import ConductorKind, PortRole

_ORIGIN = Origin(file="test_cable_results.py", line=1, note="fixture")
_PORT_A: Id[Any] = Id(kind="port", value="1" * 32)
_PORT_B: Id[Any] = Id(kind="port", value="2" * 32)
_CONDUCTOR: Id[Any] = Id(kind="conductor", value="3" * 32)
_KEY = ("layout", "cable-engine", "cable_block", "pump1")


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
    conductor = Conductor(
        id=_CONDUCTOR,
        key=("plant", "wire"),
        a=_PORT_A,
        b=_PORT_B,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    return item, function, *ports, conductor, sheet_format()


def _block(**changes: Any) -> CableBlock:
    fields: dict[str, Any] = {
        "id": Id(kind="layout.cable_block", value="a" * 32),
        "key": _KEY,
        "subject": drawn_function()[0].id,
        "unit": None,
        "width": 120,
        "height": 60,
        "pitch": 4,
        "sheet_format": sheet_format().id,
        "produced_by": PRODUCED_BY,
    }
    return CableBlock(**{**fields, **changes})


def _box() -> CableBox:
    return CableBox(
        id=Id(kind="layout.cable_box", value="b" * 32),
        key=(*_KEY, "cable"),
        block=_block().id,
        item=drawn_function()[0].id,
        kind=BoxKind.CABLE,
        external=False,
        x=8,
        y=20,
        width=100,
        height=20,
        produced_by=PRODUCED_BY,
    )


def _end(pins: tuple[PinCell, ...] = ()) -> EndBox:
    return EndBox(
        id=Id(kind="layout.end_box", value="c" * 32),
        key=(*_KEY, "top"),
        block=_block().id,
        item=drawn_function()[0].id,
        row=BlockRow.TOP,
        style=EndStyle.SOLID,
        x=0,
        y=0,
        width=40,
        height=12,
        pins=pins,
        produced_by=PRODUCED_BY,
    )


def _wire(points: tuple[RoutePoint, ...], run_b: tuple[RoutePoint, ...] = ()) -> CoreWire:
    return CoreWire(
        id=Id(kind="layout.core_wire", value="d" * 32),
        key=(*_KEY, "wire"),
        block=_block().id,
        conductor=_CONDUCTOR,
        run_a=points,
        run_b=run_b or _RUN_B,
        text_x=10,
        text_y=30,
        stub_a=False,
        stub_b=False,
        produced_by=PRODUCED_BY,
    )


_PINS = (
    PinCell(index=0, port=_PORT_A, x=4, landed=True),
    PinCell(index=1, port=_PORT_B, x=8, landed=False),
)
_POINTS = (RoutePoint(index=0, x=4, y=12), RoutePoint(index=1, x=4, y=30))
_RUN_B = (RoutePoint(index=0, x=4, y=62), RoutePoint(index=1, x=4, y=80))


def _freeze(*records: Any) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _model() -> Model:
    return _freeze(*_plant(), _block(), _box(), _end(_PINS), _wire(_POINTS))


def test_cable_records_freeze_and_round_trip() -> None:
    """All four kinds freeze, read back through `layout_of` and survive dumps and loads."""
    model = _model()
    assert loads(dumps(model)) == model
    assert layout_of(model, CableBlock)[_block().id].sheet_format == sheet_format().id
    assert layout_of(model, EndBox)[_end().id].pins == _PINS
    assert layout_of(model, CoreWire)[_wire(_POINTS).id].run_a == _POINTS
    assert layout_of(model, CoreWire)[_wire(_POINTS).id].run_b == _RUN_B


def test_a_block_may_use_the_house_sheet_and_a_unit_reading() -> None:
    """`sheet_format=None` is the house sheet, as for a page; it freezes without a record."""
    model = _freeze(*_plant()[:-1], _block(sheet_format=None))
    assert layout_of(model, CableBlock)[_block().id].sheet_format is None


def test_an_end_box_has_no_cable_field() -> None:
    """Q9: one end box per item in the block, so it never names one cable."""
    assert "cable" not in {field.name for field in dataclasses.fields(EndBox)}


def test_pins_are_stored_in_index_order() -> None:
    """`EndBox.pins` is sorted by `index`, whatever order it was built in."""
    assert _end(tuple(reversed(_PINS))).pins == _PINS


def test_a_pin_index_may_not_repeat() -> None:
    """Two pins with one `index` have no order."""
    with pytest.raises(SchemaError):
        _end((_PINS[0], dataclasses.replace(_PINS[1], index=0)))


def test_core_points_are_stored_in_index_order() -> None:
    """Each run of a `CoreWire` is sorted by `index`."""
    assert _wire(tuple(reversed(_POINTS))).run_a == _POINTS
    assert _wire(_POINTS, tuple(reversed(_RUN_B))).run_b == _RUN_B


def test_a_core_point_index_may_not_repeat() -> None:
    """Two vertices with one `index` have no order."""
    with pytest.raises(SchemaError):
        _wire((_POINTS[0], RoutePoint(index=0, x=1, y=1)))
    with pytest.raises(SchemaError):
        _wire(_POINTS, (_RUN_B[0], RoutePoint(index=0, x=1, y=1)))


def test_each_pass_removes_only_its_own_kinds() -> None:
    """Q3: the schematic and cable passes name disjoint ids to remove."""
    model = _freeze(*_plant(), group_node(), drawing_set(), page(), _block(), _box())
    schematic = {drawing_set().id, page().id}
    assert set(derived_layout_ids(model)) == schematic
    assert set(derived_layout_ids(model, CABLE_KINDS)) == {_block().id, _box().id}


def test_the_cable_kinds_are_the_four_records() -> None:
    """`CABLE_KINDS` holds the four cable record classes and nothing else."""
    assert set(CABLE_KINDS) == {CableBlock, CableBox, CoreWire, EndBox}
