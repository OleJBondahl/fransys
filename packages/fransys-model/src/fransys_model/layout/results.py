"""Derived layout kinds: what a layout pass writes (design/layout-namespace.md, decision 0010).

Only a pass writes these, and it replaces them wholesale. Every kind carries
`produced_by` (pass name and version). Coordinates are integer grid units (`G`) from
the page content-box origin, x right, y down. The authoring key of a derived record
never contains a page number or a position, so ids survive repagination; design/layout-namespace.md
lists the discriminator each kind adds to its subject's key.
"""

from typing import NoReturn

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record, value
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Item, Port, Unit

from .enums import MarkerSide, Orientation, PageRole, Side, StarKind
from .formats import SheetFormat
from .order import by_index, holder_of

# The slot of a power symbol's label: not `marking.<name>`, which a port named `ground` already has
POWER_SLOT = "power"


def _refuse(rec: LinkMarker, kind: str, msg: str) -> NoReturn:
    raise SchemaError(msg, kind=kind, record_id=holder_of(rec))


def _check_size(rec: LinkMarker, owner: str, kind: str) -> None:
    for name in ("width", "height"):
        size = getattr(rec, name)
        if type(size) is int and size <= 0:
            _refuse(rec, kind, f"{owner} {name} must be positive, got {size}")


def _check_marker_numbers(rec: LinkMarker) -> None:
    kind = "layout.link_marker"
    if (rec.via_x is None) != (rec.via_y is None):
        _refuse(rec, kind, "a link marker's via_x and via_y are both set or both None")
    if type(rec.stub_extra) is int and rec.stub_extra < 0:
        _refuse(rec, kind, f"a link marker's stub_extra must not be negative, got {rec.stub_extra}")
    if type(rec.wrap_at) is int and rec.wrap_at < 1:
        _refuse(rec, kind, f"a link marker's wrap_at must be positive, got {rec.wrap_at}")


def _check_marker_stub(rec: LinkMarker) -> None:
    kind = "layout.link_marker"
    if rec.lead is False and rec.box_x is None:
        _refuse(rec, kind, "a link marker that is not the lead of a shared box needs a box_x")
    is_off = rec.star is StarKind.OFF
    if rec.facing is None:
        _refuse(rec, kind, "a link marker always stores its facing")
    if (rec.far is not None) != is_off:
        _refuse(rec, kind, "a link marker's far is set exactly when it is an off stub")
    if rec.carrier is not None and rec.far is None:
        _refuse(rec, kind, "a link marker's carrier needs a far")


@record(kind="layout.drawing_set")
class DrawingSet:
    """One drawing set: the pages drawn for one location, by default one per top-level `+` node.

    `location=None` is the drawing set of everything without a location; a model with no
    unit gets `unit=None` throughout. `number` orders the drawing sets.
    """

    id: Id[DrawingSet]
    key: AuthoringKey
    location: Id[AspectNode] | None
    unit: Id[Unit] | None = None
    number: int
    produced_by: str
    ext: frozendict[str, Value] = frozendict()


@value
class PageGroup:
    """One `=` group drawn on a `Page`; `index` is its left-to-right order."""

    group: Id[AspectNode]
    index: int


@record(kind="layout.page")
class Page:
    """One page of a drawing set: its number, its role and the groups drawn on it.

    `role` is one `PageRole`, its first unit's; roles may share a page (deep-dive D4,
    decision layout-0048). The page title is rendered from the group descriptions in
    `index` order; it is not stored. `sheet_format` names the authored sheet the page
    is drawn on; `None` is the build's default paper (`PaperChoice`).
    """

    id: Id[Page]
    key: AuthoringKey
    drawing_set: Id[DrawingSet]
    number: int
    role: PageRole
    sheet_format: Id[SheetFormat] | None
    groups: tuple[PageGroup, ...]
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `groups` in `index` order; a repeated `index` is refused."""
        groups = by_index(self.groups, PageGroup, kind="layout.page", holder=holder_of(self))
        if groups is not None:
            object.__setattr__(self, "groups", groups)


@value
class RoutePoint:
    """One vertex of a polyline; `index` is its place along the polyline."""

    index: int
    x: int
    y: int


@record(kind="layout.link_marker")
class LinkMarker:
    """One end of a signal severed by a page boundary; a plain marker (`star` is `None`) has a pair.

    A plain marker's `partner` is the marker on the other page and points back. A star marker
    keeps no pair: an `OFF` stub is its own partner, a `REF` points at one of its branches,
    a `BRANCH` at the reference. The reader's text is rendered from the partner, and the
    severed net is the physical net of `port`; neither is stored. `width`/`height` are the
    reserved box's size in G, never re-measured. `box_x` is the left edge of a shared box,
    `lead` marks the box's lead marker, `stub_extra` is extra stub length in G, `via_x`/`via_y`
    are the stub's bend (both or neither), `star` is the star point drawn, or `None`. `far`
    and `carrier` are set only on an off stub. `facing`, the side the box sits out from the port,
    is set on every marker and never re-derived. `vertical` is
    layout's decision that the text reads along its wire, bottom to top; `width`/`height`
    are then the turned box's. `wrap_at` is the words on the first line of a text layout
    broke in two, `None` for one line.
    """

    id: Id[LinkMarker]
    key: AuthoringKey
    page: Id[Page]
    port: Id[Port]
    side: MarkerSide
    partner: Id[LinkMarker]
    x: int
    y: int
    width: int
    height: int
    produced_by: str
    box_x: int | None = None
    lead: bool = True
    stub_extra: int = 0
    via_x: int | None = None
    via_y: int | None = None
    star: StarKind | None = None
    far: Id[Port] | None = None
    carrier: Id[Item] | None = None
    facing: Side | None = None
    vertical: bool = False
    wrap_at: int | None = None
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a bad size, lone `via_x`/`via_y`, a negative `stub_extra`, a boxless non-lead.

        Also a marker without `facing`, `far` on any but an off stub (or an off stub without
        it), and a `carrier` without `far`.
        """
        _check_size(self, "a link marker's", "layout.link_marker")
        _check_marker_numbers(self)
        _check_marker_stub(self)


@record(kind="layout.power_symbol")
class PowerSymbol:
    """One power symbol drawn at a port on one page: the bar, ground or protective earth.

    `symbol` is the electrical-symbols key (`power-supply`, `ground`, `protective-earth`) and
    `x`, `y` its origin, in G. `pin_x`, `pin_y` is the lead's start, the pin's point; the lead
    runs from there to the symbol's port. The record stores no printed text: a label, where it
    has one, is an ordinary `layout.label` with the port as its subject (decision model-0117).
    """

    id: Id[PowerSymbol]
    key: AuthoringKey
    port: Id[Port]
    page: Id[Page]
    symbol: str
    x: int
    y: int
    pin_x: int
    pin_y: int
    orientation: Orientation
    produced_by: str
    ext: frozendict[str, Value] = frozendict()


@value
class CrossReferencePartner:
    """One other end of a cross-referenced item, as `CROSS_REFERENCE` label text lists them.

    `port` is the partner end's port, `page` the page that end is placed on, `x` the
    drawn x of that port on that page (grid units). Stored order is the stage's to set;
    this value does not sort or canonicalise itself.
    """

    port: Id[Port]
    page: Id[Page]
    x: int
