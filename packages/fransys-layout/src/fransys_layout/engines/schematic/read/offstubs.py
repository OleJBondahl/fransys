"""C21, D10: reads of the model for the off stub rules of `stages/offstubs.py` (layout-0085).

`_stub_end` is the one place that builds an off stub's `PortText` and `OffEnd` (the plug/socket
transparency and the far end's product designation); `end_text` calls it for an end of a
conductor (with its outermost carrier) and `_join_text` for an end of a net's join (D4, no
carrier). `read_inputs` reads both through `off_texts`, and `off_reads` hands `end_text` to the
rules for a top-level unit's boundary pin whose mate ends in a stub. Nothing else is computed
up front: the rules call what `off_reads` binds to the model when they need it.
"""

import dataclasses
from functools import partial
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read.units import (
    boundary_edges,
    top_boundary_edges,
    top_level_unit,
)
from fransys_layout.stages.offstubs import OffEnd, OffReads, PortText, bridge, mate_stub
from fransys_layout.stages.types import StubText
from fransys_model.derive.designation import item_designation, port_designation
from fransys_model.derive.drawing_text import stub_far_end
from fransys_model.kernel import parent_chain
from fransys_model.vocab.tables import conductors, items, mates, ports

if TYPE_CHECKING:
    from fransys_layout.stages.types import Connection, FunctionSpec, MatedFunctions
    from fransys_model.kernel import Id, Model


def off_texts(
    model: Model, maps: FarMaps, crossing: tuple[Connection, ...], joins: tuple[Connection, ...]
) -> tuple[tuple[PortText, ...], tuple[OffEnd, ...]]:
    """C21, D4: per end of a crossing conductor, then of a net's join, its stub text and end."""
    pairs = [end_text(model, maps, c, near) for c in crossing for near in (c.a.port, c.b.port)]
    pairs.extend(_join_text(model, maps, c, near) for c in joins for near in (c.a.port, c.b.port))
    return tuple(text for text, _ in pairs), tuple(end for _, end in pairs)


def boundary_offs(
    model: Model,
    reads: OffReads,
    specs: tuple[FunctionSpec, ...],
    mates: tuple[MatedFunctions, ...],
    split: tuple[tuple[Connection, ...], tuple[Connection, ...]],
) -> tuple[tuple[Connection, ...], tuple[PortText, ...], tuple[OffEnd, ...]]:
    """W3: a unit's boundary pin mated outside its unit carries its mate's off-stub."""
    within, crossing = split
    spec_of = {spec.function: spec for spec in specs}
    edges = boundary_edges(model)
    found: list[Connection] = []
    texts: list[PortText] = []
    ends: list[OffEnd] = []
    for pair in mates:
        for near, far in ((pair.a, pair.b), (pair.b, pair.a)):
            spec, other = spec_of.get(near), spec_of.get(far)
            if spec is None or other is None or spec.unit == other.unit:
                continue
            if spec.pin_function in edges:
                got = _mate_offs(reads, within, crossing, (spec, other), (near, far))
                found.extend(got[0])
                texts.extend(got[1])
                ends.extend(got[2])
    return tuple(found), tuple(texts), tuple(ends)


def _mate_offs(
    reads: OffReads,
    within: tuple[Connection, ...],
    crossing: tuple[Connection, ...],
    specs: tuple[FunctionSpec, FunctionSpec],
    ports_: tuple[Id[Any], Id[Any]],
) -> tuple[list[Connection], list[PortText], list[OffEnd]]:
    """W3: the off-stub reads of one boundary pin `near` mated to `far` outside its unit."""
    near, far = ports_
    leaving = [c for c in crossing if far in (c.a.port, c.b.port)]
    found = [bridge(c, near, far) for c in leaving]
    texts = [dataclasses.replace(reads.end_text(c, far, near)[0], port=near) for c in leaving]
    ends: list[OffEnd] = []
    if not leaving and (stub := mate_stub(within, specs, ports_, reads)):
        found.append(stub[0])
        texts.append(stub[1])
        ends.append(stub[2])
    return found, texts, ends


@dataclasses.dataclass(frozen=True, slots=True)
class FarMaps:
    """C21: the two lookups `end_text` reads, built once per read of a model by `far_maps`."""

    partner: dict[Id[Any], Id[Any]]
    by_name: dict[tuple[Id[Any], str], Id[Any]]


def far_maps(model: Model) -> FarMaps:
    """C21: the `FarMaps` of `model`, one pass over its mates and one over its ports."""
    partner = {}
    for mate in mates(model).values():
        partner[mate.a], partner[mate.b] = mate.b, mate.a
    return FarMaps(
        partner=partner,
        by_name={(p.function, p.name): p.id for p in ports(model).values()},
    )


def end_text(
    model: Model, maps: FarMaps, c: Connection, near: Id[Any], at: Id[Any] | None = None
) -> tuple[PortText, OffEnd]:
    """C21: the off stub text and `OffEnd` of `near`, one end of `c`, printed at port `at`."""
    record = conductors(model)[c.handle]
    all_items = items(model)
    chain = tuple(parent_chain(lambda node: all_items[node].parent, record.carrier))
    carrier = chain[-1] if chain else None
    far = record.b if near == record.a else record.a
    text, end = _stub_end(model, maps, at or near, far, carrier)
    return dataclasses.replace(text, port=near), dataclasses.replace(end, port=near)


def _join_text(
    model: Model, maps: FarMaps, c: Connection, near: Id[Any]
) -> tuple[PortText, OffEnd]:
    """D4: the off stub text and `OffEnd` of `near`, one end of a net's join `c`."""
    return _stub_end(model, maps, near, c.b.port if near == c.a.port else c.a.port, None)


def _stub_end(
    model: Model, maps: FarMaps, near: Id[Any], far: Id[Any], carrier: Id[Any] | None
) -> tuple[PortText, OffEnd]:
    """C21: the one build of an off stub's `PortText` and `OffEnd`, at `near` naming `far`."""
    function = ports(model)[far].function
    far = maps.by_name.get((maps.partner.get(function), ports(model)[far].name), far)
    cable = "" if carrier is None else "-" + item_designation(model, carrier)
    head, tail = stub_far_end(model, far, near)
    text = StubText(cable=cable, far=head, port=tail)
    return PortText(port=near, text=text), OffEnd(port=near, text=text, carrier=carrier, far=far)


def off_reads(model: Model, maps: FarMaps) -> OffReads:
    """The `OffReads` of `model`: its top-level boundary edges now, the rest when a rule asks."""
    return OffReads(
        edges=top_boundary_edges(model),
        top_unit=partial(top_level_unit, model),
        end_text=partial(end_text, model, maps),
        designation=partial(port_designation, model),
    )
