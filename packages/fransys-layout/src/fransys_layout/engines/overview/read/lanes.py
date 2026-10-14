"""Overview engine, reading: the lane of each box of a lanes view (O4).

One lane per function group, in the schematic's group order (ranks, then order hints); the strips
and the boxes with no group stand in the no-group lane, which stands last. A stub box takes its
host's lane.
"""

from typing import Any
lazy from collections.abc import Sequence
lazy from collections.abc import Set as AbstractSet

from fransys_layout.engines.overview.read.lane_rule import lane_rule
from fransys_layout.engines.overview.read.values import LanePlan
from fransys_layout.engines.schematic.read.reading import group_infos, page_hints
from fransys_layout.geometry import HintError
from fransys_layout.stages import group_order
from fransys_model.derive import (
    lane_head,
    natural_key,
    overview_lane_nodes,
    overview_lane_strips,
    overview_power_lines,
    overview_strip_joins,
    overview_stub_west,
)
from fransys_model.layout import BoxKey
from fransys_model.layout.tables import profile_of
lazy from fransys_layout.stages import GroupInfo
lazy from fransys_model.derive import ViewBox, ViewRows
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit


def _ordered(model: Model, unit: Id[Any] | None, used: AbstractSet[Id[Any]]) -> list[Id[Any]]:
    """`used` groups in the shared order; a hint cycle (the schematic reports it) is ignored."""
    infos: list[GroupInfo] = [i for i in group_infos(model) if i.group in used]
    ranks = profile_of(model, unit).group_ranks
    try:
        found = group_order(infos, group_ranks=ranks, order_hints=page_hints(model).order)
    except HintError:
        found = group_order(infos, group_ranks=ranks, order_hints=())
    return [i.group for i in found]


def reader_rank(boxes: Sequence[ViewBox]) -> tuple[int, ...]:
    """Each box's place in reader order, the natural order of its first line (layout-0230).

    The one home of that order: `lane_plan` takes its inner boxes in it, `LanePlan.rank` carries it.
    """
    order = sorted(
        range(len(boxes)), key=lambda n: natural_key(boxes[n].lines[0] if boxes[n].lines else "")
    )
    return tuple(order.index(n) for n in range(len(boxes)))


def inner_keys(boxes: Sequence[ViewBox], rank: Sequence[int]) -> list[BoxKey]:
    """The keys of the level's own boxes (no stubs) in the order `rank` gives."""
    return [
        boxes[n].key
        for n in sorted(range(len(rank)), key=rank.__getitem__)
        if boxes[n].key.at is None
    ]


def lane_plan(model: Model, unit: Id[Unit], rows: ViewRows) -> LanePlan:
    """Each box's lane (LO4), the west stubs (LO1) and power lines (LO2), and each lane's text."""
    nodes = overview_lane_nodes(model, unit)
    order = _ordered(model, unit, {n for n in nodes.values() if n is not None})
    rank = reader_rank(rows.boxes)
    keys = inner_keys(rows.boxes, rank)
    pairs = [(ln.a, ln.b) for ln in rows.lines if ln.a in keys and ln.b in keys]
    group = {k: None if (n := nodes.get(k)) is None else order.index(n) for k in keys}
    lane = lane_rule(keys, group, overview_lane_strips(model, unit), pairs, len(order))
    power = overview_power_lines(model, unit)
    joins = overview_strip_joins(model, unit)
    return LanePlan(
        lanes=tuple(
            lane[b.key] if b.key.at is None else lane.get(BoxKey(ref=b.key.at), len(order))
            for b in rows.boxes
        ),
        head_owners=tuple(order),
        head_texts=tuple(lane_head(model, n) for n in order),
        west=tuple(
            b.key.at is not None and overview_stub_west(model, unit, b.key.ref) for b in rows.boxes
        ),
        power=tuple((ln.a, ln.b) in power or (ln.b, ln.a) in power for ln in rows.lines),
        join=tuple(joins.get(b.key, -1) for b in rows.boxes),
        rank=rank,
    )
