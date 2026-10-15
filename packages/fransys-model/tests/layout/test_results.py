"""Derived layout kinds, cross-record rules."""

from dataclasses import replace

import pytest
from layout_examples import (
    PRODUCED_BY,
    drawing_set,
    drawn_function,
    function_id,
    group_node,
    page,
    sheet_format,
)

from fransys_model.kernel import (
    Draft,
    FreezeError,
    Id,
    Model,
    Origin,
    Record,
    SchemaError,
    dumps,
    freeze,
    loads,
)
from fransys_model.layout import (
    Chain,
    ChainEntry,
    Label,
    LabelKind,
    LinkMarker,
    MarkerSide,
    PoleGroup,
    Route,
    RoutePoint,
    Side,
    SideHint,
    StubEnd,
    layout_of,
)
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import Aspect, ConductorKind, PortRole

_LOW_PORT: Id[Port] = Id(kind="port", value="1" * 32)
_HIGH_PORT: Id[Port] = Id(kind="port", value="2" * 32)
_CONDUCTOR: Id[Conductor] = Id(kind="conductor", value="3" * 32)


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_results.py", line=1, note="fixture")
    draft.extend(records, origin=origin)
    return freeze(draft)


def _ports() -> tuple[Port, Port]:
    return (
        Port(
            id=_LOW_PORT,
            key=("examples", "pump1", "contactor", "fn", "main", "port", "1"),
            function=function_id("c"),
            template=None,
            name="1",
            role=PortRole.GENERIC,
        ),
        Port(
            id=_HIGH_PORT,
            key=("examples", "pump1", "contactor", "fn", "main", "port", "2"),
            function=function_id("c"),
            template=None,
            name="2",
            role=PortRole.GENERIC,
        ),
    )


def _conductor() -> Conductor:
    return Conductor(
        id=_CONDUCTOR,
        key=("examples", "pump1", "wire", "1"),
        a=_LOW_PORT,
        b=_HIGH_PORT,
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def _other_group() -> AspectNode:
    return AspectNode(
        id=Id(kind="aspect_node", value="4" * 32),
        key=("examples", "function", "pump2"),
        aspect=Aspect.FUNCTION,
        parent=None,
        label="PUMP2",
        description="Invented pump 2",
    )


def _label(*, function: bool, port: bool, conductor: bool) -> Label:
    return Label(
        id=Id(kind="layout.label", value="5" * 32),
        key=("layout", "example-engine", "label", "examples", "pump1", "contactor", "tag", "tag"),
        page=page().id,
        function=function_id("c") if function else None,
        port=_LOW_PORT if port else None,
        conductor=_CONDUCTOR if conductor else None,
        kind=LabelKind.TAG,
        slot="tag",
        x=72,
        y=96,
        width=16,
        height=8,
        produced_by=PRODUCED_BY,
    )


def _route(
    *,
    conductor: bool = True,
    net: bool = False,
    a: Id[Port] = _LOW_PORT,
    b: Id[Port] = _HIGH_PORT,
    points: tuple[RoutePoint, ...] = (
        RoutePoint(index=0, x=64, y=96),
        RoutePoint(index=1, x=64, y=160),
    ),
) -> Route:
    return Route(
        id=Id(kind="layout.route", value="6" * 32),
        key=("layout", "example-engine", "route", "examples", "pump1", "wire", "1"),
        page=page().id,
        conductor=_CONDUCTOR if conductor else None,
        net=Id(kind="net", value="7" * 32) if net else None,
        a=a,
        b=b,
        points=points,
        produced_by=PRODUCED_BY,
    )


def _marker_key(port_name: str, partner_name: str, side: MarkerSide) -> tuple[str, ...]:
    """The port key, the side and the partner port key."""
    port_key = ("examples", "port", port_name)
    partner_key = ("examples", "port", partner_name)
    return ("layout", "example-engine", "link_marker", *port_key, side.value, *partner_key)


def _marker(  # noqa: PLR0913 -- one param per LinkMarker field a test needs to vary
    value: str,
    partner: str,
    *,
    port: Id[Port],
    names: tuple[str, str],
    side: MarkerSide,
    width: int,
    height: int,
) -> LinkMarker:
    return LinkMarker(
        id=Id(kind="layout.link_marker", value=value * 32),
        key=_marker_key(*names, side),
        page=page().id,
        port=port,
        side=side,
        partner=Id(kind="layout.link_marker", value=partner * 32),
        x=64,
        y=200,
        width=width,
        height=height,
        produced_by=PRODUCED_BY,
        facing=Side.E,
    )


def _marker_pair() -> tuple[LinkMarker, LinkMarker]:
    return (
        _marker(
            "8", "9", port=_LOW_PORT, names=("1", "2"), side=MarkerSide.OWNER, width=13, height=8
        ),
        _marker(
            "9", "8", port=_HIGH_PORT, names=("2", "1"), side=MarkerSide.USER, width=13, height=8
        ),
    )


def _side_hint(value: str, side: Side = Side.N) -> SideHint:
    return SideHint(
        id=Id(kind="layout.side_hint", value=value * 32),
        key=("examples", "layout", "side_hint", value),
        function=function_id("c"),
        side=side,
    )


def _engineering() -> tuple[Record, ...]:
    return (*drawn_function(), *_ports(), _conductor(), group_node(), _other_group())


@pytest.mark.parametrize("side", [Side.E, Side.W])
def test_a_side_hint_is_above_or_below_only(side: Side) -> None:
    with pytest.raises(SchemaError):
        _side_hint("a", side)


def _pole_group(*functions: str) -> PoleGroup:
    return PoleGroup(
        id=Id(kind="layout.pole_group", value="d" * 32),
        key=("examples", "layout", "pole_group"),
        functions=tuple(function_id(one) for one in functions),
        selector=True,
    )


def test_a_pole_group_keeps_the_authors_pole_order() -> None:
    """The order is the pole order (author-0046): it is never sorted."""
    assert _pole_group("c", "a", "b").functions == tuple(map(function_id, "cab"))


@pytest.mark.parametrize("functions", [(), ("a", "a")])
def test_a_pole_group_lists_one_function_or_more_each_once(functions: tuple[str, ...]) -> None:
    with pytest.raises(SchemaError, match="each once"):
        _pole_group(*functions)


def test_a_chain_beside_freezes_round_trips_and_needs_its_host() -> None:
    """A chain's `beside` is a function of the model; a dangling host is refused."""
    entry = ChainEntry(function=function_id("c"), index=0)
    chain = Chain(
        id=Id(kind="layout.chain", value="c" * 32),
        key=("examples", "layout", "chain", "c"),
        entries=(entry,),
        beside=function_id("c"),
    )
    model = _freeze((*_engineering(), chain))
    assert loads(dumps(model)) == model
    with pytest.raises(FreezeError):
        _freeze((*_engineering(), replace(chain, beside=function_id("z"))))


def _stub_end(marker: Id[LinkMarker], index: int, *, placed: bool) -> StubEnd:
    return StubEnd(
        id=Id(kind="layout.stub_end", value=str(index) * 32),
        key=("layout", "example-engine", "stub_end", str(index)),
        marker=marker,
        index=index,
        port=_HIGH_PORT,
        page=page().id if placed else None,
        x=24 if placed else 0,
        y=40 if placed else 0,
        produced_by=PRODUCED_BY,
    )


def test_stub_ends_freeze_round_trip_and_need_their_marker() -> None:
    """A placed and an unplaced far end resolve; one without a marker is refused."""
    owner, user = _marker_pair()
    ends = (_stub_end(owner.id, 1, placed=True), _stub_end(owner.id, 2, placed=False))
    base = (*_engineering(), sheet_format(), drawing_set(), page(), owner, user)
    model = _freeze((*base, *ends))
    assert loads(dumps(model)) == model
    assert [e.page is None for e in layout_of(model, StubEnd).values()].count(True) == 1
    with pytest.raises(FreezeError):
        _freeze((*base, _stub_end(Id(kind="layout.link_marker", value="7" * 32), 1, placed=True)))


# ---- typed fields of SymbolPlacement, LinkMarker and Label -----------------
