"""Derived layout kinds, cross-record rules."""

from dataclasses import replace

import pytest
from layout_examples import (
    drawn_function,
    function_id,
    group_node,
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
    PoleGroup,
    Side,
    SideHint,
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
