"""The overview engine's lanes placement (O4): one lane per function group, stage columns."""

from typing import TYPE_CHECKING

from fransys_layout.engines.overview.lanes.channels import channels, end_ys, reaches
from fransys_layout.engines.overview.lanes.frame import (
    box_sizes,
    corridors,
    head_rise,
    raw_ends,
    rows,
)
from fransys_layout.engines.overview.lanes.plan import make_plan
from fransys_layout.engines.overview.lanes.route import Room, column_xs, sheet

if TYPE_CHECKING:
    from fransys_layout.engines.diagram.values import PlacedSheet
    from fransys_layout.engines.overview.read.values import ViewFacts


def place_lanes(facts: ViewFacts) -> PlacedSheet:
    """The one sheet of a lanes view, boxes in lanes and stages, lines in channels and corridors."""
    plan = make_plan(facts)
    raw = raw_ends(facts, plan.stage)
    size = box_sizes(facts, raw)
    high = {b: h for b, (_, h) in size.items()}
    found = corridors(facts, plan)
    layout = rows(plan, high, found, head_rise(facts, plan))
    by = end_ys(raw, layout.box_y, high, facts, plan.stage)
    chans = channels(facts, plan, by, reaches(raw, plan.stage), layout.track_y)
    xs, wide = column_xs(plan, {b: w for b, (w, _) in size.items()}, chans)
    return sheet(facts, plan, by, Room(chans, xs, wide, layout.box_y, size), layout.head_y)
