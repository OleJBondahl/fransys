"""The placement core: plain values in, plain values out. It imports nothing outside the stdlib."""

from .annex_values import Annex, AnnexBox, Spot
from .clearance import own_end
from .errors import CoreError
from .geometry import inside, overlaps, stub_views
from .jsonform import from_plain, to_plain
from .keys import natural_key
from .order import order_blocks
from .outline import outline_hull
from .outputs import Anchored, CoreLayout, Marker, Placed, Placement, Wire
from .page_graph import PageGraph, page_graph
from .row_extent import grid_out, grid_up
from .series_tree import leaves_of
from .series_values import Parallel, Series, SeriesPart
from .sides import SIDE_STEP
from .solve import solve
from .sym_values import Sym
from .topology import build_flow
from .values import (
    Anchor,
    Box,
    BoxSpec,
    Bundle,
    CutEnd,
    Facts,
    Finding,
    Hints,
    Net,
    Options,
    Orientation,
    PagePlan,
    Pin,
    PinRef,
    PlacementProblem,
    Pose,
    Side,
    Size,
    Unit,
)

__all__ = (
    "SIDE_STEP",
    "Anchor",
    "Anchored",
    "Annex",
    "AnnexBox",
    "Box",
    "BoxSpec",
    "Bundle",
    "CoreError",
    "CoreLayout",
    "CutEnd",
    "Facts",
    "Finding",
    "Hints",
    "Marker",
    "Net",
    "Options",
    "Orientation",
    "PageGraph",
    "PagePlan",
    "Parallel",
    "Pin",
    "PinRef",
    "Placed",
    "Placement",
    "PlacementProblem",
    "Pose",
    "Series",
    "SeriesPart",
    "Side",
    "Size",
    "Spot",
    "Sym",
    "Unit",
    "Wire",
    "build_flow",
    "from_plain",
    "grid_out",
    "grid_up",
    "inside",
    "leaves_of",
    "natural_key",
    "order_blocks",
    "outline_hull",
    "overlaps",
    "own_end",
    "page_graph",
    "solve",
    "stub_views",
    "to_plain",
)
