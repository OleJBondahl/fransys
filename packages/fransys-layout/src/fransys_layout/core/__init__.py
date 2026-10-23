"""The placement core: plain values in, plain values out. It imports nothing outside the stdlib."""

from .annex import place_annexes
from .annex_values import Annex, AnnexBox, Spot
from .errors import CoreError
from .geometry import inside, overlaps
from .jsonform import from_plain, to_plain
from .junctions import Junction, junctions
from .keys import natural_key
from .order import order_blocks
from .outputs import Anchored, CoreLayout, Marker, Placed, Placement, Wire
from .room import Room, joined
from .series_values import Parallel, Series, SeriesPart
from .solve import solve
from .sym_values import Sym
from .topology import build_flow
from .values import (
    Anchor,
    Box,
    BoxSpec,
    Bundle,
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
    "Anchor",
    "Anchored",
    "Annex",
    "AnnexBox",
    "Box",
    "BoxSpec",
    "Bundle",
    "CoreError",
    "CoreLayout",
    "Facts",
    "Finding",
    "Hints",
    "Junction",
    "Marker",
    "Net",
    "Options",
    "Orientation",
    "PagePlan",
    "Parallel",
    "Pin",
    "PinRef",
    "Placed",
    "Placement",
    "PlacementProblem",
    "Pose",
    "Room",
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
    "inside",
    "joined",
    "junctions",
    "natural_key",
    "order_blocks",
    "overlaps",
    "place_annexes",
    "solve",
    "to_plain",
)
