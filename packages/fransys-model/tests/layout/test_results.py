"""Derived layout kinds, cross-record rules."""

import pytest
from layout_examples import (
    drawn_function,
    function_id,
    group_node,
)

from fransys_model.kernel import (
    Draft,
    Id,
    Model,
    Origin,
    Record,
    SchemaError,
    freeze,
)
from fransys_model.layout import PoleGroup
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import Aspect, ConductorKind, PortBoundary

_LOW_PORT: Id[Port] = Id[Port](kind="port", value="1" * 32)
_HIGH_PORT: Id[Port] = Id[Port](kind="port", value="2" * 32)
_CONDUCTOR: Id[Conductor] = Id[Conductor](kind="conductor", value="3" * 32)


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
            boundary=PortBoundary.GENERIC,
        ),
        Port(
            id=_HIGH_PORT,
            key=("examples", "pump1", "contactor", "fn", "main", "port", "2"),
            function=function_id("c"),
            template=None,
            name="2",
            boundary=PortBoundary.GENERIC,
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


def _engineering() -> tuple[Record, ...]:
    return (*drawn_function(), *_ports(), _conductor(), group_node(), _other_group())


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
