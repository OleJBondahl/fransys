"""HL1, HL5, HL6: which conductors a harness line carries and which connectors get a box."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read.units import function_unit
from fransys_layout.stages.box_views import BoxSpec
from fransys_layout.stages.connector_boxes import has_cells
from fransys_model.derive import (
    connector_at_line_end,
    connector_box_lines,
    harness_line_ends,
    line_conductors,
    unit_subtree,
)
from fransys_model.derive.drawing_text import port_marking
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import boundaries, conductors, functions, items, ports
from fransys_model.vocab.tables import units as unit_table

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.types import FunctionSpec
    from fransys_model.derive import HarnessLineEnd
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Conductor
    from fransys_model.vocab.core import Function, Item, Port


@dataclass(frozen=True)
class LineRead:
    """One line: its owner (a harness or a cable), its ends and the conductors it carries."""

    owner: Id[Item]
    ends: tuple[HarnessLineEnd, ...]
    conductors: tuple[Id[Conductor], ...]
    unit: Id[Any] | None = None  # the unit whose sheet holds both its ends (`_sheet_unit`)


@dataclass(frozen=True)
class LineReads:
    """Every line of the model, by owner id, and every conductor some line carries."""

    lines: tuple[LineRead, ...]
    carried: frozenset[Id[Conductor]]
    top: frozenset[Id[Any]] = frozenset()  # the top-level units


def line_reads(model: Model) -> LineReads:
    """One `LineRead` per line `derive.line_conductors` holds, sorted by owner id (HL1)."""
    table = items(model)
    edges: dict[Id[Any], set[Id[Any]]] = {}
    for one in boundaries(model).values():
        edges.setdefault(one.unit, set()).add(one.function)
    lines = tuple(
        LineRead(owner, ends, ids, _sheet_unit(model, table[owner].unit, ends, edges))
        for owner, ids in sorted(line_conductors(model).items())
        for ends in (harness_line_ends(model, owner),)
    )
    top = frozenset(one.id for one in unit_table(model).values() if one.parent is None)
    return LineReads(lines, frozenset(id_ for line in lines for id_ in line.conductors), top)


def _sheet_unit(
    model: Model,
    unit: Id[Any] | None,
    ends: Sequence[HarnessLineEnd],
    edges: Mapping[Id[Any], set[Id[Any]]],
) -> Id[Any] | None:
    """The unit whose sheet draws a line owned in `unit`: the sheet that holds both its ends.

    A nested unit's line from its own boundary plug (`edges`) out to its parent's things is the
    parent's (risk 9a, layout-0158); the owner keeps it in its lists.
    """
    parent = unit_table(model)[unit].parent if unit is not None else None
    edge = edges.get(unit, set())
    if unit is None or parent is None or not any(end.plug in edge for end in ends):
        return unit
    inside = unit_subtree(model, unit)
    table, fns, pins = items(model), functions(model), ports(model)
    out = any(
        table[fns[pins[port].function].item].unit not in inside
        for end in ends
        for port in end.ports
    )
    return parent if out else unit


def drawn_on(line: LineRead, unit: Id[Any] | None, top: frozenset[Id[Any]]) -> bool:
    """Whether a set drawing `unit` draws `line`: its own unit's, or a top-level one.

    A top-level line also leaves a top-level unit's sheet; a boundary-only unit hides its lines.
    """
    return line.unit == unit or (line.unit is None and unit in top)


def boxed_functions(model: Model) -> frozenset[Id[Function]]:
    """HL6: every connector function at a line's end."""
    return frozenset(
        function.id
        for function in functions(model).values()
        if function.kind is FunctionKind.CONNECTOR and connector_at_line_end(model, function.id)
    )


def plug_functions(lines: LineReads) -> frozenset[Id[Function]]:
    """Every plug of every line."""
    return frozenset(end.plug for line in lines.lines for end in line.ends if end.plug is not None)


@dataclass(frozen=True)
class BoxRead:
    """HL5: one boxed connector: its text lines, plug or unit interface, and each pin's marking.

    `wired` holds the pins a conductor no line carries lands on: the pins that may get a cell.
    """

    function: Id[Function]
    lines: tuple[str, ...]
    plug: bool
    black_box: bool
    markings: tuple[tuple[Id[Port], str], ...]
    wired: frozenset[Id[Port]]


def box_reads(model: Model, lines: LineReads) -> tuple[BoxRead, ...]:
    """One `BoxRead` per boxed connector (`boxed_functions`), sorted by function id."""
    plugs, interfaces = plug_functions(lines), {b.function for b in boundaries(model).values()}
    wired = frozenset(
        end
        for conductor in conductors(model).values()
        if conductor.id not in lines.carried
        for end in (conductor.a, conductor.b)
    )
    boxed, own = boxed_functions(model), {}
    for port in sorted(ports(model).values(), key=lambda port: port.id):
        if port.function in boxed:
            own.setdefault(port.function, []).append((port.id, port_marking(model, port.id)))
    return tuple(
        BoxRead(
            function,
            connector_box_lines(model, function, unit=function_unit(model, function)),
            function in plugs,
            function in interfaces,
            tuple(own.get(function, ())),
            frozenset(port for port, _ in own.get(function, ()) if port in wired),
        )
        for function in sorted(boxed)
    )


def box_specs(model: Model, functions: Sequence[FunctionSpec]) -> tuple[BoxSpec, ...]:
    """HL5, HL6: one `BoxSpec` per boxed connector drawn as pin views, its cells by `has_cells`."""
    views: dict[Id[Function], list[Id[Port]]] = {}
    for spec in functions:
        if spec.pin_function is not None:
            views.setdefault(spec.pin_function, []).append(spec.function)
    return tuple(
        BoxSpec(
            read.function,
            read.lines,
            tuple(
                (port, marking)
                for port, marking in read.markings
                if has_cells(
                    plug=read.plug, black_box=read.black_box, board=False, wired=bool(read.wired)
                )
            ),
            tuple(sorted(views[read.function])),
        )
        for read in box_reads(model, line_reads(model))
        if read.function in views
    )


def plug_mates(lines: LineReads) -> dict[Id[Function], Id[Function]]:
    """Each plug of every line to the connector it mates (HL4)."""
    return {
        end.plug: end.mates
        for line in lines.lines
        for end in line.ends
        if end.plug is not None and end.mates is not None
    }
