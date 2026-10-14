"""Derived layout kinds of the overview: one view per level and per open strip, boxes and lines.

They are page-less positions in grid units `G` from the view's top-left corner. An overview
engine writes them and replaces only these kinds (`OVERVIEW_KINDS`). Decision model-0198.
Texts are never stored: the page prints the `derive` overview rows, layout only measured them.
"""

from fransys_model.kernel import AuthoringKey, Id, Value, record, value
from fransys_model.vocab.core import Item, Unit

from .order import by_index, holder_of
from .overview_ref import OverviewMode, OverviewRef, check_view
from .results import RoutePoint


@record(kind="layout.overview_view")
class OverviewView:
    """One placed view: the level of `unit` (`None` is the system) drawn in `mode`.

    `level` is the box of `unit` opened as the level (a `GROUP` or the `STRIPS` box), else `None`.
    `open` is the one strip opened in it (O5); `None` is the level with every strip shut. A fold
    is never placed open (B2), so `open_at` stays `None`; it is kept to hold the schema at 15. The
    record refuses a mode the level cannot have. `produced_by` names the pass.
    """

    id: Id[OverviewView]
    key: AuthoringKey
    unit: Id[Unit] | None
    level: OverviewRef | None
    mode: OverviewMode
    open: OverviewRef | None
    open_at: OverviewRef | None
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a (unit, group, mode) pair a level cannot have."""
        check_view(self.unit, self.level, self.mode, self.open, self.open_at)


@value
class OverviewTab:
    """One tab outside a box edge, where a cable line ends; `index` is its place in the box's tabs.

    `x`, `y` is the top-left corner of the tab from the view's corner, `text_width` the width of
    its text. A line ends on the tab its last point touches; the text is the one `line_tabs` gives.
    """

    index: int
    x: int
    y: int
    text_width: int


@record(kind="layout.overview_box")
class OverviewBox:
    """The box of what `ref` stands for, or of a stub whose far end `ref` names.

    A stub box sets `stub_of`, the box inside the level it hangs on; one far end is one stub
    box. `x`, `y` is the top-left corner. `tabs` are stored in `index` order.
    """

    id: Id[OverviewBox]
    key: AuthoringKey
    view: Id[OverviewView]
    ref: OverviewRef
    stub_of: Id[OverviewBox] | None
    dashed: bool
    x: int
    y: int
    width: int
    height: int
    tabs: tuple[OverviewTab, ...]
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `tabs` in `index` order."""
        tabs = by_index(self.tabs, OverviewTab, kind="layout.overview_box", holder=holder_of(self))
        if tabs is not None:
            object.__setattr__(self, "tabs", tabs)


@record(kind="layout.overview_line")
class OverviewLine:
    """One line of a view between two of its boxes; its identity is `(a, b, kind, via, strip)`.

    `kind` is the link kind the row prints (`wire`, `cable` or `mate`); `via` is the carrier
    cable, else `None`; `strip` is the strip a pass-through line is drawn through, else `None`.
    `points` run from `a` to `b` in `index` order; `text_x`, `text_y` is
    where its text is centred.
    """

    id: Id[OverviewLine]
    key: AuthoringKey
    view: Id[OverviewView]
    a: Id[OverviewBox]
    b: Id[OverviewBox]
    kind: str
    via: Id[Item] | None
    strip: Id[Item] | None
    points: tuple[RoutePoint, ...]
    text_x: int
    text_y: int
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `points` in `index` order; a repeated `index` is refused."""
        points = by_index(
            self.points, RoutePoint, kind="layout.overview_line", holder=holder_of(self)
        )
        if points is not None:
            object.__setattr__(self, "points", points)
