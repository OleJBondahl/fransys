"""A terminal stands at each of its wires' far pins, several copies on one page (model-0220).

The caller names the wires to draw this way. Each wire's terminal end gets a copy of its own,
attached at the far pin in the far function's column: a stage handle with stage ports, and the
wire rewired to it, so every later stage draws it as one more function wired to one device.
`real` maps each stage handle back to the model's id. A far pin facing E or W, a pin that
already holds an attached cell, and a host in a set that does not draw the terminal take none.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.stages.attach import _entry, _with_attached
from fransys_layout.stages.tags import TagTexts
from fransys_layout.stages.types import Home
from fransys_model.kernel import Id

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from fransys_layout.stages.types import (
        Column,
        Connection,
        DrawnFunction,
        FunctionSpec,
        Handle,
        LabelRequest,
        Layout,
        PortRef,
    )
    from fransys_model.kernel import Finding

    type _Entry = tuple[Handle, str, int, Handle, str, bool]


@dataclass(frozen=True, slots=True)
class WireCopies:
    """The run with a copy at each named wire: its specs, drawn functions, wires and columns."""

    functions: tuple[FunctionSpec, ...]
    drawn: tuple[DrawnFunction, ...]
    connections: tuple[Connection, ...]
    columns: tuple[Column, ...]
    real: Mapping[Handle, Handle]  # each copy's function and port handle to the model's id


def copy_handle(handle: Id[Any], far_port: Id[Any]) -> Id[Any]:
    """The stage handle of `handle` copied at the wire to `far_port`."""
    return Id(kind=handle.kind, value=f"{handle.value}@{far_port.value}")


def with_wire_copies(
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    functions: tuple[FunctionSpec, ...],
    connections: tuple[Connection, ...],
    wires: AbstractSet[Handle],
) -> WireCopies:
    """The run with each `wires` conductor's terminal end drawn by a copy at its far pin."""
    spec_of = {one.function: one for one in functions}
    drawn_of = {one.function: one for one in drawn}
    seats = _Seats(_hosts(columns), _sets(columns), {}, {})
    planned = _planned(connections, wires, seats, spec_of, drawn_of)
    shared = _shared(connections, planned)
    specs, drawns, real, rewired = [], [], {}, {}
    for c, end, handle in planned:
        # a net of its own, unless another wire names the far pin: the router never runs a
        # copy's wire along another copy's line
        far = end[1].port
        net = c.physical_net if far in shared else copy_handle(c.physical_net, far)
        spec, one, names, wire = _copy_of((c, end, handle, net), spec_of, drawn_of)
        specs.append(spec)
        drawns.append(one)
        real |= names
        rewired[c.handle] = wire
    return WireCopies(
        functions=(*functions, *specs),
        drawn=(*drawn, *drawns),
        connections=tuple(rewired.get(c.handle, c) for c in connections),
        columns=tuple(_copied(column, seats, real) for column in columns),
        real=real,
    )


def _planned(
    connections: Iterable[Connection],
    wires: AbstractSet[Handle],
    seats: _Seats,
    spec_of: Mapping[Handle, FunctionSpec],
    drawn_of: Mapping[Handle, DrawnFunction],
) -> list[tuple[Connection, tuple[PortRef, PortRef], Handle]]:
    """Each `wires` conductor that takes a copy: the wire, its ends and the copy's handle."""
    found = []
    for c in sorted(connections, key=lambda one: one.handle):
        end = _copied_end(c, spec_of) if c.handle in wires else None
        handle = end and _seated(seats, end, drawn_of)
        if end is not None and handle is not None:
            found.append((c, end, handle))
    return found


def _shared(connections: Iterable[Connection], planned: Sequence[tuple[Any, ...]]) -> set[Handle]:
    """The ports a wire that takes no copy also ends at: a copy's wire there keeps its net."""
    copied = {one[0].handle for one in planned}
    return {ref.port for c in connections if c.handle not in copied for ref in (c.a, c.b)}


@dataclass(frozen=True, slots=True)
class _Seats:
    """Where copies go: each function's own column, its sets, the new and the adopted cells."""

    hosts: Mapping[Handle, Column]
    sets: Mapping[Handle, set[Any]]
    found: dict[object, list[_Entry]]
    adopted: dict[tuple[object, Handle, Handle | None, str], Handle]


def _seated(
    seats: _Seats, end: tuple[PortRef, PortRef], drawn_of: Mapping[Handle, DrawnFunction]
) -> Handle | None:
    """The copy's handle once a seat at the far pin is planned for it, else `None`.

    A replica of the terminal already attached at that pin becomes the copy.
    """
    own, far = end
    host = seats.hosts.get(far.function)
    if host is None or host.drawing_set_key not in seats.sets.get(own.function, ()):
        return None
    if _adjacent(host, own.function, far.function):
        return None  # its own column draws the wire (layout-0090: cells side by side)
    flipped = any(cell.flip for cell in host.cells if cell.function == far.function)
    entry = _entry(drawn_of[own.function], own, drawn_of[far.function], far, far_flipped=flipped)
    if entry is None:
        return None
    handle = copy_handle(own.function, far.port)
    held = _held(host, seats)
    pin = (far.function, entry[4])
    if pin not in held:
        seats.found.setdefault(host.key, []).append((*entry[:3], handle, *entry[4:]))
        return handle
    if held[pin] != own.function:
        return None
    seats.adopted[host.key, own.function, *pin] = handle
    return handle


def _adjacent(host: Column, own: Handle, far: Handle) -> bool:
    """`own` stands next to `far` in one lane of `host`, so the column draws their wire."""
    cells = [c for c in host.cells if c.host is None]
    at = {c.function: (c.lane, c.index) for c in cells}
    return (
        own in at and far in at and at[own][0] == at[far][0] and abs(at[own][1] - at[far][1]) == 1
    )


def _held(host: Column, seats: _Seats) -> dict[tuple[Handle | None, str], Handle | None]:
    """Each attached pin of `host`: the replica there, `None` for a home moved there.

    A home moved to a pin already draws the wire; a replica there becomes the copy.
    """
    held = {
        (c.host, c.port): c.function if c.home is Home.ELSEWHERE else None
        for c in host.cells
        if c.host is not None
    }
    return held | {(one[0], one[4]): one[3] for one in seats.found.get(host.key, ())}


def _copy_of(
    planned: tuple[Connection, tuple[PortRef, PortRef], Handle, Handle],
    spec_of: Mapping[Handle, FunctionSpec],
    drawn_of: Mapping[Handle, DrawnFunction],
) -> tuple[FunctionSpec, DrawnFunction, dict[Handle, Handle], Connection]:
    """The copy `handle` of `end`'s terminal: its spec, drawn function, ids and wire on `net`."""
    c, (own, far), handle, net = planned
    ports = {p.port: copy_handle(p.port, far.port) for p in drawn_of[own.function].ports}
    moved = replace(own, function=handle, port=ports[own.port])
    wire = replace(_rewired(c, own, moved), physical_net=net)
    return (
        _spec(spec_of[own.function], handle, ports),
        _drawn(drawn_of[own.function], handle, ports),
        {handle: own.function, wire.physical_net: c.physical_net}
        | {alias: port for port, alias in ports.items()},
        wire,
    )


def _copied(column: Column, seats: _Seats, real: Mapping[Handle, Handle]) -> Column:
    """`column` with its copies attached and its adopted replicas renamed, all marked."""
    if column.key in seats.found:
        column = _with_attached(column, seats.found[column.key])
    cells = tuple(
        replace(c, function=seats.adopted[column.key, c.function, c.host, c.port])
        if (column.key, c.function, c.host, c.port) in seats.adopted
        else c
        for c in column.cells
    )
    return _marked(replace(column, cells=cells), real)


def _copied_end(
    c: Connection, spec_of: Mapping[Handle, FunctionSpec]
) -> tuple[PortRef, PortRef] | None:
    """`(terminal end, far end)` of a wire from a terminal to a function that is none."""
    for own, far in ((c.a, c.b), (c.b, c.a)):
        if spec_of[own.function].roles.terminal and not spec_of[far.function].roles.terminal:
            return own, far
    return None


def _hosts(columns: Sequence[Column]) -> dict[Handle, Column]:
    """Each function's own column: where its cell stands at home, not attached or beside."""
    found: dict[Handle, Column] = {}
    for column in columns:
        for cell in column.cells:
            if cell.host is None and not cell.side and cell.home is not Home.ELSEWHERE:
                found.setdefault(cell.function, column)
    return found


def _sets(columns: Sequence[Column]) -> dict[Handle, set[Any]]:
    """The drawing-set keys each function is drawn in."""
    found: dict[Handle, set[Any]] = {}
    for column in columns:
        for cell in column.cells:
            found.setdefault(cell.function, set()).add(column.drawing_set_key)
    return found


def _spec(spec: FunctionSpec, handle: Handle, ports: Mapping[Handle, Handle]) -> FunctionSpec:
    return replace(
        spec,
        function=handle,
        ports=tuple(replace(p, port=ports[p.port]) for p in spec.ports),
        home=Home.ELSEWHERE,
    )


def _drawn(one: DrawnFunction, handle: Handle, ports: Mapping[Handle, Handle]) -> DrawnFunction:
    return replace(
        one, function=handle, ports=tuple(replace(p, port=ports[p.port]) for p in one.ports)
    )


def _rewired(c: Connection, old: PortRef, new: PortRef) -> Connection:
    """`c` with its end `old` moved to `new` (the connection keeps its ends in port order)."""
    a, b = (new, c.b) if c.a == old else (c.a, new)
    return replace(c, a=a, b=b)


def _marked(column: Column, real: Mapping[Handle, Handle]) -> Column:
    """`column` with each copy's cell marked as standing at its wire, away from its home."""
    return replace(
        column,
        cells=tuple(
            replace(c, at_wire=True, home=Home.ELSEWHERE) if c.function in real else c
            for c in column.cells
        ),
    )


def copy_requests(
    requests: tuple[LabelRequest, ...],
    functions: Sequence[FunctionSpec],
    real: Mapping[Handle, Handle],
) -> tuple[LabelRequest, ...]:
    """`requests` and, for each copy, its function's and its ports' requests as the copy's."""
    added = []
    for spec in functions:
        if spec.function not in real:
            continue
        own = real[spec.function]
        ports = {real[p.port]: p.port for p in spec.ports}
        for r in requests:
            subject = spec.function if r.subject == own else ports.get(r.subject)
            if subject is not None:
                function = spec.function if r.function == own else r.function
                added.append(replace(r, subject=subject, function=function))
    return (*requests, *added)


def copy_texts(
    texts: TagTexts,
    requests: tuple[LabelRequest, ...],
    functions: Sequence[FunctionSpec],
    copies: Iterable[tuple[Handle, ...]],
) -> tuple[TagTexts, tuple[LabelRequest, ...]]:
    """`texts` and `requests` that read a copy's texts and labels from the function it copies."""
    real = copy_map(copies)
    if not real:
        return texts, requests
    return _read_through(texts, real), copy_requests(requests, functions, real)


def _read_through(texts: TagTexts, real: Mapping[Handle, Handle]) -> TagTexts:
    at = real.get
    return TagTexts(
        connector_designation=lambda h: texts.connector_designation(at(h, h)),
        item_tag_text=lambda h: texts.item_tag_text(at(h, h)),
        is_device_terminal=lambda h: texts.is_device_terminal(at(h, h)),
        strip_tag_text=lambda h: texts.strip_tag_text(at(h, h)),
        point_text=lambda h: texts.point_text(at(h, h)),
        unit_tag_text=lambda h, slot, unit: texts.unit_tag_text(at(h, h), slot, unit),
    )


def copy_map(copies: Iterable[tuple[Handle, ...]]) -> dict[Handle, Handle]:
    """Each copy's handle to the model's id, from `StageInputs.copies`' pairs."""
    return {one[0]: one[1] for one in copies}


def copy_subjects(
    findings: Sequence[Finding], real: Mapping[Handle, Handle]
) -> tuple[Finding, ...]:
    """`findings` naming the model's ids where a subject is a copy's handle."""
    return tuple(
        replace(f, subjects=tuple(real.get(s, s) for s in f.subjects))
        if any(s in real for s in f.subjects)
        else f
        for f in findings
    )


def copy_layout(layout: Layout, real: Mapping[Handle, Handle]) -> Layout:
    """`layout` with each copy's placement, route ends and labels under the model's ids."""
    if not real:
        return layout
    at = real.get
    return replace(
        layout,
        placed=tuple(replace(p, function=at(p.function, p.function)) for p in layout.placed),
        routes=tuple(replace(r, a=at(r.a, r.a), b=at(r.b, r.b)) for r in layout.routes),
        labels=tuple(replace(one, subject=at(one.subject, one.subject)) for one in layout.labels),
        markers=tuple(replace(m, port=at(m.port, m.port)) for m in layout.markers),
    )


def copy_seen(
    layout: Layout, findings: Sequence[Finding], copies: Iterable[tuple[Handle, ...]]
) -> tuple[Layout, tuple[Finding, ...]]:
    """`layout` and `findings` under the model's ids: each copy is where its model id is drawn."""
    real = copy_map(copies)
    return copy_layout(layout, real), copy_subjects(findings, real)
