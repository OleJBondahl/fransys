"""The lane of each box of a unit's level (O4): its function group, none for a strip.

The lanes view draws every device of the unit, one lane per function group; the strips and the
boxes with no group stand in the no-group lane. Stub boxes are not here: they take their host's.
"""

from typing import Any

from fransys_model.layout import BoxKey
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Unit

from .overview_groups import box_groups, group_text
from .overview_levels import overview_level
from .overview_view_plain import ref_of
from .rows import ItemKind

__all__ = ["lane_head", "overview_lane_nodes"]


def overview_lane_nodes(model: Model, unit: Id[Unit]) -> dict[BoxKey, Id[AspectNode] | None]:
    """Each box of `unit`'s level: its function group node, `None` for a strip or no group."""
    level = overview_level(model, unit)
    group: dict[Id[Any], Id[AspectNode] | None] = box_groups(model, unit, level.boxes)
    return {
        BoxKey(ref=ref_of(b.box)): None if b.kind is ItemKind.STRIP else group[b.box]
        for b in level.boxes
    }


def lane_head(model: Model, node: Id[AspectNode]) -> str:
    """The text a lane prints: its group's folded-box text, on one line."""
    return " ".join(group_text(model, node))
