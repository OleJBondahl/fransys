"""The stage values (`stages/types.py`): sorted tuples and the closed value
set."""

import dataclasses
from collections.abc import Callable

import pytest
from samples import PROFILE, SHEET, column, connection, drawn, function_spec, hid, page_plan, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import (
    Cell,
    Chain,
    ChainEntry,
    Column,
    ColumnWidth,
    DrawnPort,
    GroupInfo,
    GroupSet,
    LabelKind,
    LabelRequest,
    LinkCase,
    LinkDecision,
    LinkMarker,
    LocationInfo,
    MarkerSide,
    NetGroup,
    OrderHint,
    PageHints,
    PlacedLabel,
    PlannedColumn,
    PlannedGroup,
    PolePair,
    PortRef,
    PortSpec,
    Role,
    Route,
    RoutePoint,
    SymbolChoice,
    SymbolRule,
    UnitInfo,
)

# A builder makes one value and passes each order-carrying tuple through `order`, which
# either keeps the sorted order or reverses it.
type Order = Callable[[tuple], tuple]


def _keep(items: tuple) -> tuple:
    return items


def _reverse(items: tuple) -> tuple:
    return items[::-1]


def _ref(number: int) -> PortRef:
    return PortRef(function=hid("function", number), port=hid("port", number))


def _port_spec(name: str, number: int) -> PortSpec:
    return PortSpec(
        port=hid("port", number), name=name, physical_net=hid("net", 1), role=Role.POWER
    )


def _function_spec_of(order: Order):
    return dataclasses.replace(
        function_spec(1),
        ports=order((_port_spec("11", 1), _port_spec("12", 2), _port_spec("13", 3))),
        pole_pairs=order(
            (PolePair(index=0, first="11", second="12"), PolePair(index=1, first="13", second="14"))
        ),
    )


def _drawn_of(order: Order):
    ports = (
        DrawnPort(port=hid("port", 1), symbol_port="in"),
        DrawnPort(port=hid("port", 2), symbol_port="out"),
    )
    return dataclasses.replace(drawn(1), ports=order(ports))


def _net_group_of(order: Order):
    return NetGroup(
        net=hid("net", 1),
        physical_net=hid("net", 1),
        role=Role.POWER,
        ports=order((_ref(1), _ref(2), _ref(3))),
    )


def _chain_of(order: Order):
    entries = tuple(ChainEntry(function=hid("function", i), index=i) for i in range(3))
    return Chain(chain=hid("chain", 1), key=("invented", "c"), entries=order(entries))


def _column_of(order: Order):
    cells = tuple(Cell(function=hid("function", i), index=i) for i in range(3))
    return Column(
        key=("invented", "c"), cells=order(cells), group=None, role=Role.CONTROL, location=None
    )


def _group_set_of(order: Order):
    return GroupSet(groups=order(tuple(hid("g", n) for n in (1, 2, 3))))


def _page_hints_of(order: Order):
    return PageHints(
        keep_together=order(
            (
                GroupSet(groups=(hid("g", 1), hid("g", 2))),
                GroupSet(groups=(hid("g", 1), hid("g", 3))),
            )
        ),
        break_before=order((hid("g", 1), hid("g", 2))),
        order=order(
            (
                OrderHint(before=hid("g", 1), after=hid("g", 2)),
                OrderHint(before=hid("g", 1), after=hid("g", 3)),
                OrderHint(before=hid("g", 2), after=hid("g", 1)),
            )
        ),
    )


def _page_plan_of(order: Order):
    groups = (PlannedGroup(group=hid("g", 1), index=0), PlannedGroup(group=hid("g", 2), index=1))
    columns = (
        PlannedColumn(column=("invented", "a"), index=0),
        PlannedColumn(column=("invented", "b"), index=1),
    )
    return dataclasses.replace(page_plan(("a", "b")), groups=order(groups), columns=order(columns))


def _route_of(order: Order):
    points = tuple(RoutePoint(index=i, at=Point(x=8 * i, y=0)) for i in range(4))
    return Route(
        connection=hid("conductor", 1),
        physical_net=hid("net", 1),
        drawing_set=1,
        page=1,
        a=hid("port", 1),
        b=hid("port", 2),
        points=order(points),
    )


BUILDERS = {
    "FunctionSpec": _function_spec_of,
    "DrawnFunction": _drawn_of,
    "NetGroup": _net_group_of,
    "Chain": _chain_of,
    "Column": _column_of,
    "GroupSet": _group_set_of,
    "PageHints": _page_hints_of,
    "PagePlan": _page_plan_of,
    "Route": _route_of,
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_a_reversed_tuple_gives_a_value_equal_to_the_sorted_one(name: str) -> None:
    """Every order-carrying tuple is stored sorted by its documented key at construction."""
    assert BUILDERS[name](_reverse) == BUILDERS[name](_keep)


def _samples() -> list[object]:
    """One instance of every kind of field: enums, frozendicts, handles, nested tuples."""
    return [
        SHEET,
        PROFILE,
        SymbolRule(
            kind="contact_no",
            category=None,
            symbol="make-contact",
            port_map=frozendict({"13": "in"}),
        ),
        SymbolChoice(
            choice=hid("choice", 1),
            function=hid("function", 1),
            part=None,
            kind=None,
            symbol="make-contact",
            port_map=frozendict({"13": "in"}),
        ),
        function_spec(1),
        drawn(1),
        connection(1, 1, 2),
        column("a", (1, 2)),
        page_plan(("a", "b")),
        placed(1, x=0, y=0),
        _page_hints_of(_keep),
        _net_group_of(_keep),
        _chain_of(_keep),
        LinkDecision(
            connection=hid("conductor", 1),
            a=hid("port", 1),
            b=hid("port", 2),
            case=LinkCase.SEVERED,
        ),
        LinkMarker(
            connection=hid("conductor", 1),
            port=hid("port", 1),
            side=MarkerSide.OWNER,
            drawing_set=1,
            page=1,
            at=Point(x=0, y=0),
            box=Box(x=0, y=0, width=24, height=8),
            partner_page=2,
        ),
        LabelRequest(
            kind=LabelKind.CROSS_REFERENCE, subject=hid("function", 1), slot="tag", text="/2.3"
        ),
        PlacedLabel(
            kind=LabelKind.TAG,
            subject=hid("function", 1),
            slot="tag",
            drawing_set=1,
            page=1,
            box=Box(x=0, y=0, width=8, height=8),
        ),
        ColumnWidth(column=("invented", "a"), width=64),
        GroupInfo(group=hid("g", 1), key=("invented", "g"), label="power", description="Power"),
        LocationInfo(location=hid("l", 1), label="cabinet"),
        UnitInfo(unit=hid("unit", 1)),
    ]
