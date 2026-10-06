"""C21, D10: which conductors end in stubs, and the stub of a mate across a location.

The rules only: `crosses_location`, `_ends_in_stubs` and `by_location` decide which connections
end in a stub at each end, `groups_by_location` splits a net group the same way (D4), and
`mate_stub` gives a boundary pin whose mate is stubbed the bridge to a stand-in port and the stub
text of the conductor at the mate. What they read of the model (the top-level units' boundary
functions, a unit's top-level unit, the text of a conductor's end and a port's designation)
comes in as an `OffReads`, built by `read/offstubs.py`. The stub's own text is never built here:
`fransys_model.derive.drawing_text` is the only text function.
"""

import dataclasses
from dataclasses import dataclass
from itertools import combinations, pairwise
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import LayoutError
from fransys_layout.stages.types import (
    EDGE_KIND,
    Connection,
    FunctionSpec,
    NetGroup,
    PortRef,
    StubText,
)
from fransys_model.kernel import Id, UnionFind, value

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Mapping


@value
class PortText:
    """C21: the `StubText` of one off stub's near port."""

    port: Id[Any]
    text: StubText


@value
class OffEnd:
    """C21: one end of a conductor between two locations; `carrier` and `far` feed `LinkMarker`."""

    port: Id[Any]
    text: StubText
    carrier: Id[Any] | None
    far: Id[Any]


@dataclass(frozen=True, slots=True)
class OffReads:
    """What the off stub rules read of the model, built by `read/offstubs.py` (layout-0080)."""

    edges: frozenset[Id[Any]]
    top_unit: Callable[[Id[Any] | None], Id[Any] | None]
    end_text: Callable[[Connection, Id[Any], Id[Any]], tuple[PortText, OffEnd]]
    designation: Callable[[Id[Any]], str]


def off_ends(off_ends: Iterable[OffEnd], off_texts: Iterable[PortText]) -> tuple[OffEnd, ...]:
    """Each off-stub port's `OffEnd` by its text (a stand-in copies its mate's); a clash raises."""
    by_text: dict[StubText, OffEnd] = {}
    for end in off_ends:
        known = by_text.setdefault(end.text, end)
        if (known.carrier, known.far) != (end.carrier, end.far):
            msg = f"the off stub text {end.text!r} names two different far ends or carriers"
            raise LayoutError(msg)
    return tuple(dataclasses.replace(by_text[one.text], port=one.port) for one in off_texts)


def crosses_location(a: FunctionSpec | None, b: FunctionSpec | None) -> bool:
    """C21: whether `a` and `b` stand in different top-level drawing sets (layout-0081, LD7)."""
    if a is None or b is None or not a.location_path or not b.location_path:
        return False
    return a.location_path[0] != b.location_path[0] and a.drawing_set_key != b.drawing_set_key


def _ends_in_stubs(
    a: FunctionSpec | None,
    b: FunctionSpec | None,
    edges: Collection[Id[Any]],
    top_unit: Callable[[Id[Any] | None], Id[Any] | None],
) -> bool:
    """C21, D10, layout-0080: whether a conductor crosses a location or leaves a unit, so stubs."""
    if crosses_location(a, b):
        return True
    if a is None or b is None:
        return False
    return any(
        (near.pin_function in edges or near.function in edges)
        and top_unit(far.unit) != top_unit(near.unit)
        for near, far in ((a, b), (b, a))
    )


def by_location(
    specs: Iterable[FunctionSpec], connections: Iterable[Connection], reads: OffReads
) -> tuple[tuple[Connection, ...], tuple[Connection, ...]]:
    """C21, layout-0080: the connections drawn in full, and those that end in stubs."""
    spec_of = {spec.function: spec for spec in specs}
    within: list[Connection] = []
    crossing: list[Connection] = []
    for c in connections:
        stubbed = _ends_in_stubs(
            spec_of.get(c.a.function), spec_of.get(c.b.function), reads.edges, reads.top_unit
        )
        (crossing if stubbed else within).append(c)
    return tuple(within), tuple(crossing)


def groups_by_location(
    specs: Iterable[FunctionSpec], net_groups: Iterable[NetGroup], reads: OffReads
) -> tuple[tuple[NetGroup, ...], tuple[Connection, ...]]:
    """D4, S15: net groups drawn in full, and N - 1 stub joins between their N location parts."""
    spec_of = {spec.function: spec for spec in specs}
    within: list[NetGroup] = []
    joins: list[Connection] = []
    for group in net_groups:
        parts = _location_parts(group.ports, spec_of, reads)
        if len(parts) == 1:
            within.append(group)
            continue
        within.extend(dataclasses.replace(group, ports=part) for part in parts if len(part) > 1)
        joins.extend(
            Connection(
                handle=group.net,
                physical_net=group.physical_net,
                role=group.role,
                a=before[0],
                b=after[0],
            )
            for before, after in pairwise(parts)
        )
    return tuple(within), tuple(joins)


def _location_parts(
    ports: tuple[PortRef, ...], spec_of: Mapping[Id[Any], FunctionSpec], reads: OffReads
) -> list[tuple[PortRef, ...]]:
    """`ports` (sorted by handle) as `groups_by_location`'s parts, each sorted, by lowest port."""
    parts: UnionFind[Id[Any]] = UnionFind(ref.port for ref in ports)
    for one, other in combinations(ports, 2):
        if parts.find(one.port) == parts.find(other.port):
            continue
        a, b = spec_of.get(one.function), spec_of.get(other.function)
        if not _ends_in_stubs(a, b, reads.edges, reads.top_unit):
            parts.union(one.port, other.port)
    ref_of = {ref.port: ref for ref in ports}
    return sorted(
        (tuple(ref_of[port] for port in members) for members in parts.groups().values()),
        key=lambda part: part[0].port,
    )


def bridge(c: Connection, near: Id[Any], far: Id[Any]) -> Connection:
    """W3: `c` as one conductor from boundary pin `near` to a stand-in port named for `far`."""
    stand_in = Id(kind=EDGE_KIND, value=f"{far.value}-off")
    return dataclasses.replace(
        c,
        a=PortRef(function=near, port=near),
        b=PortRef(function=stand_in, port=stand_in),
    )


def mate_stub(
    within: Iterable[Connection],
    pair: tuple[FunctionSpec, FunctionSpec],
    ends: tuple[Id[Any], Id[Any]],
    reads: OffReads,
) -> tuple[Connection, PortText, OffEnd] | None:
    """D10: the stub of a boundary pin whose mate is a stub, or `None`; first by designation."""
    near, far = ends
    pin = pair[0]
    if not _ends_in_stubs(*pair, reads.edges & {pin.pin_function, pin.function}, reads.top_unit):
        return None
    ending = sorted(
        (c for c in within if far in (c.a.port, c.b.port)),
        key=lambda c: (
            reads.designation(c.b.port if c.a.port == far else c.a.port),
            c.handle,
        ),
    )
    if not ending:
        return None
    text, end = reads.end_text(ending[0], far, near)
    return (
        bridge(ending[0], near, far),
        dataclasses.replace(text, port=near),
        dataclasses.replace(end, port=near),
    )
