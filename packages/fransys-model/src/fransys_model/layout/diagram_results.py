"""Derived layout kinds of the block diagram: one sheet per reading and number, boxes and lines.

They are page-less: a sheet holds boxes, lines and markers, in grid units `G` from the
sheet's top-left corner. `lay_out_diagrams` writes them and replaces only these kinds
(`DIAGRAM_KINDS`). Decision model-0167. Texts are never stored: render prints the derive
functions, layout only measured them.
"""

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record, value
from fransys_model.vocab.core import Item, Unit

from .enums import Side
from .order import by_index, holder_of
from .results import RoutePoint


@record(kind="layout.diagram_sheet")
class DiagramSheet:
    """One diagram sheet of one reading; `unit` is the reading (`None` is the absolute one).

    `number` runs 1..n left to right: the number its title block and every marker that
    names it print. `produced_by` names the pass.
    """

    id: Id[DiagramSheet]
    key: AuthoringKey
    unit: Id[Unit] | None
    number: int
    produced_by: str
    ext: frozendict[str, Value] = frozendict()


@value
class TabCell:
    """One tab on a `DiagramBox` edge; `index` is its place in the box's tab order.

    `line` is the cable of the line the tab belongs to, `None` for a tab no line uses.
    `side` is the edge, `y` the tab's place on it and `text_width` the width of its text.
    """

    index: int
    line: Id[Item] | None
    side: Side
    y: int
    text_width: int


@value
class BoxRef:
    """What a diagram box stands for: a unit instance or an item, exactly one of the two."""

    unit: Id[Unit] | None
    item: Id[Item] | None

    def __post_init__(self) -> None:
        """Require exactly one of `unit`/`item`."""
        if (self.unit is None) == (self.item is None):
            msg = "exactly one of `unit` and `item` is set"
            raise SchemaError(msg, kind="layout.diagram_box")


@record(kind="layout.diagram_box")
class DiagramBox:
    """The box of a unit instance or of an item (`subject`) on a sheet.

    `dashed` is a box drawn dashed because it stands for something by others. `x`, `y` is the
    top-left corner. `tabs` are stored in `index` order.
    """

    id: Id[DiagramBox]
    key: AuthoringKey
    sheet: Id[DiagramSheet]
    subject: BoxRef
    dashed: bool
    x: int
    y: int
    width: int
    height: int
    tabs: tuple[TabCell, ...]
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `tabs` in `index` order; a repeated `index` is refused."""
        tabs = by_index(self.tabs, TabCell, kind="layout.diagram_box", holder=holder_of(self))
        if tabs is not None:
            object.__setattr__(self, "tabs", tabs)


@record(kind="layout.diagram_line")
class DiagramLine:
    """One line of one cable between two boxes; its identity is `(cable, a, b)`.

    A fan-out writes one line per pair. `a` and `b` are the subjects of the boxes it joins,
    `points` run
    from `a` to `b` in `index` order, and `text_x`, `text_y` is where its text is centred.
    """

    id: Id[DiagramLine]
    key: AuthoringKey
    sheet: Id[DiagramSheet]
    cable: Id[Item]
    a: BoxRef
    b: BoxRef
    points: tuple[RoutePoint, ...]
    text_x: int
    text_y: int
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `points` in `index` order; a repeated `index` is refused."""
        points = by_index(
            self.points, RoutePoint, kind="layout.diagram_line", holder=holder_of(self)
        )
        if points is not None:
            object.__setattr__(self, "points", points)


@record(kind="layout.diagram_marker")
class DiagramMarker:
    """The marker where a `DiagramLine` leaves its sheet; it names the other sheet by number."""

    id: Id[DiagramMarker]
    key: AuthoringKey
    sheet: Id[DiagramSheet]
    line: Id[DiagramLine]
    at_sheet: int
    x: int
    y: int
    produced_by: str
    ext: frozendict[str, Value] = frozendict()
