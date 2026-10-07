"""HL11, HL12: the nested units drawn as one middle outline, read once (layout-0153)."""

from typing import TYPE_CHECKING

from fransys_layout.stages.middle import MiddleInterface, MiddleUnit
from fransys_model.derive import connector_box_lines
from fransys_model.derive.drawing_text import outline_title
from fransys_model.vocab.membership import units
from fransys_model.vocab.tables import ports
from fransys_model.vocab.tables import units as unit_table

from .harness_lines import line_reads
from .interfaces import interface_reads

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.edges import InterfaceEdge
    from fransys_layout.stages.types import FunctionSpec
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Unit

    from .harness_lines import LineRead


def middle_units(model: Model, functions: Sequence[FunctionSpec]) -> tuple[MiddleUnit, ...]:
    """HL12: each unit with a harness line at one of its interfaces, in unit id order."""
    views: dict[Id[Function], list[Id[Function]]] = {}
    for spec in functions:
        if spec.pin_function is not None:
            views.setdefault(spec.pin_function, []).append(spec.function)
    lines = line_reads(model)
    mated: dict[Id[Function], tuple[Id[Function] | None, LineRead]] = {
        end.mates: (end.plug, line) for line in lines.lines for end in line.ends if end.mates
    }
    found = []
    for unit in units(model):
        reads = interface_reads(model, unit)
        if any(read.line for read in reads):
            found.append(_unit(model, unit, reads, mated, views))
    return tuple(found)


def _unit(
    model: Model,
    unit: Id[Unit],
    reads: Sequence[InterfaceEdge],
    mated: Mapping[Id[Function], tuple[Id[Function] | None, LineRead]],
    views: Mapping[Id[Function], list[Id[Function]]],
) -> MiddleUnit:
    """One middle unit: its interfaces with their views, plugs and box texts, and its lines.

    `top` marks a top-level unit: its lines to another top-level unit leave (HL20, condition 2).
    """
    host = unit_table(model)[unit].parent  # its sheet prints in this unit (layout-0159)
    interfaces = []
    for read in reads:
        plug, line = mated.get(read.function, (None, None))
        interfaces.append(
            MiddleInterface(
                edge=read,
                views=tuple(sorted(views.get(read.function, ()))),
                plug=plug,
                plug_views=tuple(sorted(views.get(plug, ()))) if plug is not None else (),
                lines=connector_box_lines(model, read.function, unit=host),
                plug_lines=connector_box_lines(model, plug, unit=host) if plug is not None else (),
                far=_far(model, read.function, line, views),
                conductors=frozenset(line.conductors) if line is not None else frozenset(),
            )
        )
    return MiddleUnit(
        unit=unit,
        interfaces=tuple(interfaces),
        carried=frozenset(c for one in interfaces for c in one.conductors),
        title=outline_title(model, unit),
        top=host is None,
    )


def _far(
    model: Model,
    interface: Id[Function],
    line: LineRead | None,
    views: Mapping[Id[Function], list[Id[Function]]],
) -> frozenset[Id[Function]]:
    """The functions at the line's ends other than `interface`'s, with their pin views (HL13)."""
    table = ports(model)
    found: set[Id[Function]] = set()
    for end in line.ends if line is not None else ():
        if end.mates != interface:
            found.update(f for f in (end.plug, end.mates) if f is not None)
            found.update(table[port].function for port in end.ports)
    return frozenset((*found, *(view for f in found for view in views.get(f, ()))))
