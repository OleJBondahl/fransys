"""layout-0227: a `d.poles` group draws as one multi-pole symbol, its first member's spec.

Each member's ports join the first member's spec as pole k of the group, so a group of
one-pole changeovers reads exactly as one changeover function with k poles (SERIES-GAPS S9).
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read.functions import in_marking_order
from fransys_model.layout import PoleGroup, layout_of

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages import FunctionSpec, PortRef, PortSpec
    from fransys_model.kernel import Id, Model

_THROWS = ("break", "make")


def _pole_port(port: PortSpec, pole: int, *, selector: bool) -> PortSpec:
    """`port` as pole `pole` of its group; a selector's throws face the line, its commons not."""
    line = port.throw in _THROWS if selector and port.throw is not None else port.line
    return dataclasses.replace(port, pole=pole, line=line)


def _merged(members: tuple[FunctionSpec, ...], *, selector: bool) -> FunctionSpec:
    """The first member's spec drawing every member, member k as pole k."""
    ports = in_marking_order(
        _pole_port(port, pole, selector=selector)
        for pole, member in enumerate(members)
        for port in member.ports
    )
    pairs = tuple(
        dataclasses.replace(pair, index=pole)
        for pole, member in enumerate(members)
        for pair in member.pole_pairs
    )
    gang = tuple(member.function for member in members)
    return dataclasses.replace(
        members[0], poles=len(members), pole_pairs=pairs, ports=ports, gang=gang
    )


def gang_specs(
    model: Model, specs: tuple[FunctionSpec, ...]
) -> tuple[tuple[FunctionSpec, ...], dict[Id[Any], Id[Any]]]:
    """The specs with each group merged, and each later member -> its group's first member.

    A group with a member that is not drawn draws each drawn member alone.
    """
    by_function = {spec.function: spec for spec in specs}
    merged: dict[Id[Any], FunctionSpec] = {}
    leader: dict[Id[Any], Id[Any]] = {}
    for group in sorted(layout_of(model, PoleGroup).values(), key=lambda g: g.id):
        members = [by_function.get(function) for function in group.functions]
        if None in members:
            continue
        found = tuple(member for member in members if member is not None)
        merged[found[0].function] = _merged(found, selector=group.selector)
        leader.update((member.function, found[0].function) for member in found[1:])
    kept = (merged.get(spec.function, spec) for spec in specs if spec.function not in leader)
    return tuple(kept), leader


def to_leader(ref: PortRef, leader: Mapping[Id[Any], Id[Any]]) -> PortRef:
    """`ref` named by its group's first member when its function is a later member."""
    function = leader.get(ref.function)
    return ref if function is None else dataclasses.replace(ref, function=function)
