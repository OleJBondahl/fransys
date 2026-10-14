"""Overview engine, reading: the lane of each box of a lanes view (O4).

One lane per function group, in the schematic's group order (ranks, then order hints); the strips
and the boxes with no group stand in the no-group lane, which stands last. A stub box takes its
host's lane.
"""

from typing import Any
lazy from collections.abc import Set as AbstractSet

from fransys_layout.engines.schematic.read.reading import group_infos, page_hints
from fransys_layout.geometry import HintError
from fransys_layout.stages import group_order
from fransys_model.derive import lane_head, overview_lane_nodes
from fransys_model.layout import BoxKey
from fransys_model.layout.tables import profile_of
lazy from fransys_layout.stages import GroupInfo
lazy from fransys_model.derive import ViewRows
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


def lane_plan(
    model: Model, unit: Id[Unit], rows: ViewRows
) -> tuple[tuple[int, ...], tuple[tuple[Id[Any], str], ...]]:
    """Each box's lane in box order (the no-group lane is last), and each group lane's text."""
    nodes = overview_lane_nodes(model, unit)
    order = _ordered(model, unit, {n for n in nodes.values() if n is not None})
    last = len(order)
    lane = {k: order.index(n) if n in order else last for k, n in nodes.items()}
    lanes = tuple(
        lane.get(b.key, last) if b.key.at is None else lane.get(BoxKey(ref=b.key.at), last)
        for b in rows.boxes
    )
    return lanes, tuple((n, lane_head(model, n)) for n in order)
