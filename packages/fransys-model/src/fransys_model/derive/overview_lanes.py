"""The lane of each box of a unit's level (O4), and the facts the lanes order reads (LO2).

The lanes view draws every device of the unit, one lane per function group; a strip and a box
with no group have no group lane. Stub boxes are not here: they take their host's.
"""

from typing import Any

from fransys_model.layout import BoxKey
from fransys_model.vocab.enums import Current, ItemKind
from fransys_model.vocab.tables import conductors
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Unit

from .overview import links_of
from .overview_groups import box_groups
from .overview_levels import level_box, open_strips, overview_level, strip_view, stub_far_root
from .overview_names import node_lines
from .overview_view_plain import ref_of
from .potential import port_potential_current

__all__ = [
    "lane_head",
    "overview_lane_nodes",
    "overview_lane_strips",
    "overview_power_lines",
    "overview_strip_joins",
]


def overview_lane_nodes(model: Model, unit: Id[Unit]) -> dict[BoxKey, Id[AspectNode] | None]:
    """Each box of `unit`'s level: its function group node, `None` for a strip or no group."""
    level = overview_level(model, unit)
    group: dict[Id[Any], Id[AspectNode] | None] = box_groups(model, unit, level.boxes)
    return {
        BoxKey(ref=ref_of(b.box)): None if b.kind is ItemKind.STRIP else group[b.box]
        for b in level.boxes
    }


def overview_lane_strips(model: Model, unit: Id[Unit]) -> frozenset[BoxKey]:
    """The boxes of `unit`'s level that are terminal strips, which stand in the shared lane."""
    return frozenset(
        BoxKey(ref=ref_of(b.box))
        for b in overview_level(model, unit).boxes
        if b.kind is ItemKind.STRIP
    )


def overview_power_lines(model: Model, unit: Id[Unit]) -> frozenset[tuple[BoxKey, BoxKey]]:
    """The ends of each line of `unit`'s level that carries a conductor on an AC potential."""
    records = conductors(model)
    return frozenset(
        (BoxKey(ref=ref_of(ln.ref.a)), BoxKey(ref=ref_of(ln.ref.b)))
        for ln in overview_level(model, unit).lines
        if any(
            port_potential_current(model, port) is Current.AC
            for c in ln.conductors
            for port in (records[c].a, records[c].b)
        )
    )


def lane_head(model: Model, node: Id[AspectNode]) -> str:
    """The text a lane prints: its group's folded-box text, on one line."""
    return " ".join(node_lines(model, node))


def overview_strip_joins(model: Model, unit: Id[Unit]) -> dict[BoxKey, int]:
    """Each box joined to a terminal strip: the place of the first terminal it joins.

    Strips run in box text order, each strip's terminals in the strip's own order; the place counts
    terminals over all strips. A box that joins no strip is absent. A stub box counts as joined:
    its far end is the box that joins the terminal.
    """
    place: dict[BoxKey, int] = {}
    n = 0
    for strip in open_strips(overview_level(model, unit)):
        host = ref_of(strip)
        for terminal in strip_view(model, strip, unit).terminals:
            for ln in terminal.lines:
                place.setdefault(BoxKey(ref=ref_of(ln.ref.b)), n)
            for link in links_of(model, terminal.item):
                far = link.b if link.a == terminal.item else link.a
                if level_box(model, far, unit) is None:
                    place.setdefault(BoxKey(ref=stub_far_root(model, far), at=host), n)
            n += 1
    return place
