"""The placed rows of the overview: each view's boxes and lines at their recorded positions.

A `PlacedView` joins one `ViewRows` to the `layout.overview_*` records the engine wrote for it,
so a reader needs no record, key or `layout` name. Positions are grid units from the view's
top-left corner (decision model-0306).
"""

from fransys_model.kernel import Id, value
from fransys_model.layout import OverviewRefKind
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Item, Unit

from .rows_overview_view import ViewRows


@value
class RefRow:
    """What a box or an open thing stands for: its `kind` and the one id the kind names."""

    kind: OverviewRefKind
    unit: Id[Unit] | None = None
    item: Id[Item] | None = None
    node: Id[AspectNode] | None = None


@value
class PlacedTab:
    """One tab outside a box edge: `x`, `y` its corner, `text_width` its text's, then its size."""

    index: int
    x: int
    y: int
    text_width: int
    width: int
    height: int


@value
class PlacedPoint:
    """One vertex of a placed line."""

    x: int
    y: int


@value
class PlacedBox:
    """A box of the view at `x`, `y` (its top-left corner), with its tabs in `index` order.

    `ref` and `at` are the box key's two references; `members` the refs of its fold's members.
    """

    ref: RefRow
    at: RefRow | None
    members: tuple[RefRow, ...]
    x: int
    y: int
    width: int
    height: int
    tabs: tuple[PlacedTab, ...]


@value
class PlacedLine:
    """A line of the view: `a`, `b` the positions of its end boxes in the view's boxes."""

    a: int
    b: int
    points: tuple[PlacedPoint, ...]
    text_x: int
    text_y: int


@value
class PlacedHead:
    """The corner `x`, `y` of the text of the lane of the group `node`."""

    node: Id[AspectNode]
    x: int
    y: int


@value
class PlacedView:
    """A view the engine placed: its rows, its boxes and lines in the rows' order, its lane heads.

    `lane_heads` is a `PlacedHead` per lane that prints a text; empty for any other view.
    """

    rows: ViewRows
    level: RefRow | None
    open: RefRow | None
    boxes: tuple[PlacedBox, ...]
    lines: tuple[PlacedLine, ...]
    lane_heads: tuple[PlacedHead, ...]


__all__ = [
    "PlacedBox",
    "PlacedHead",
    "PlacedLine",
    "PlacedPoint",
    "PlacedTab",
    "PlacedView",
    "RefRow",
]
