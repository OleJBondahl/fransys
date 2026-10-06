"""Derived layout kinds: what a layout pass writes (design/layout-namespace.md, decision 0010).

Only a pass writes these, and it replaces them wholesale. Every kind carries
`produced_by` (pass name and version). Coordinates are integer grid units (`G`) from
the page content-box origin, x right, y down. The authoring key of a derived record
never contains a page number or a position, so ids survive repagination; design/layout-namespace.md
lists the discriminator each kind adds to its subject's key.
"""

from itertools import pairwise

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record, value
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.connectivity import Conductor, Net
from fransys_model.vocab.core import Function, Item, Port, Unit

from .enums import LabelKind, MarkerSide, Orientation, PageRole, PlacementView, Side, StarKind
from .formats import SheetFormat
from .order import by_index, holder_of

# The slot of a power symbol's label: not `marking.<name>`, which a port named `ground` already has
POWER_SLOT = "power"


@record(kind="layout.drawing_set")
class DrawingSet:
    """One drawing set: the pages drawn for one location, by default one per top-level `+` node.

    `location=None` is the drawing set of everything without a location; a model with no
    unit gets `unit=None` throughout (units spec U1). `number` orders the drawing sets.
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
    is drawn on; `None` is the house sheet (`default_sheet_format()`), which is no
    record.
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


@record(kind="layout.symbol_placement")
class SymbolPlacement:
    """One function drawn on one page: where, how turned, and with which symbol.

    `x`, `y` is the symbol origin. `symbol` and `library_version` pin the geometry the
    position was computed against. A terminal function drawn on several pages has one
    placement per page. `view` says which view of the model the placement draws. `ports`
    and `sides` are parallel: render draws a generic box's ports (an item view's, or one whose
    names or sides are not the default ones) on the `Side.N` (top) or `Side.S` (bottom)
    side as listed; both are empty for a placement that is no such box. `port_offsets` is the
    third parallel tuple: each port's x offset from the symbol origin, in model units (grid
    units), rising along each side; empty means the default measured pitch (model-0129).
    """

    id: Id[SymbolPlacement]
    key: AuthoringKey
    function: Id[Function]
    page: Id[Page]
    x: int
    y: int
    orientation: Orientation
    poles: int
    symbol: str
    library_version: str
    produced_by: str
    view: PlacementView = PlacementView.FUNCTION
    ports: tuple[str, ...] = ()
    sides: tuple[Side, ...] = ()
    port_offsets: tuple[int, ...] = ()
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Require `ports` and `sides` to come together, one side each, `Side.N` or `Side.S`."""
        ports, sides = self.ports, self.sides
        self._check_offsets()
        if type(ports) is tuple and type(sides) is tuple:
            if len(ports) != len(sides):
                msg = (
                    f"a placement's ports and sides come together, "
                    f"got {len(ports)} and {len(sides)}"
                )
                raise SchemaError(msg, kind="layout.symbol_placement", record_id=holder_of(self))
            for side in sides:
                if side not in (Side.N, Side.S):
                    msg = f"a placement's side is Side.N or Side.S, got {side!r}"
                    raise SchemaError(
                        msg, kind="layout.symbol_placement", record_id=holder_of(self)
                    )

    def _check_offsets(self) -> None:
        """Require `port_offsets` empty, or one per port and strictly rising along each side."""
        offsets, ports, sides = self.port_offsets, self.ports, self.sides
        if type(offsets) is not tuple or not offsets:
            return
        problem = None
        if len(offsets) != len(ports):
            problem = f"one per port, got {len(offsets)} for {len(ports)} ports"
        elif len(sides) == len(ports):
            for side in (Side.N, Side.S):
                along = [x for x, one in zip(offsets, sides, strict=True) if one is side]
                if any(b <= a for a, b in pairwise(along)):
                    problem = f"strictly rising along side {side.value}, got {along}"
        if problem:
            msg = f"a placement's port_offsets are {problem}"
            raise SchemaError(msg, kind="layout.symbol_placement", record_id=holder_of(self))


@value
class RoutePoint:
    """One vertex of a `Route`; `index` is its place along the polyline."""

    index: int
    x: int
    y: int


def _turned_round(points: tuple[RoutePoint, ...]) -> tuple[RoutePoint, ...]:
    """The polyline read the other way: the same `index` slots, the points in reverse."""
    return tuple(
        RoutePoint(index=slot.index, x=point.x, y=point.y)
        for slot, point in zip(points, reversed(points), strict=True)
    )


@record(kind="layout.route")
class Route:
    """The orthogonal polyline drawing one connection between two ports on one page.

    Exactly one of `conductor`, `net` is set: the `Conductor` it draws, or the declared
    `Net` it draws a leg of when no conductor exists (a board-realised or unrealised
    net). `a`/`b` are stored in id order; `points` run from `a` to `b`, ordered by
    `index`. The reference back to the model is what lets a checker prove that what is
    drawn is what is connected.
    """

    id: Id[Route]
    key: AuthoringKey
    page: Id[Page]
    conductor: Id[Conductor] | None
    net: Id[Net] | None
    a: Id[Port]
    b: Id[Port]
    points: tuple[RoutePoint, ...]
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Require exactly one of `conductor`/`net`; store `a`/`b` in id order, `points` sorted.

        Turning `a` and `b` round reverses the polyline: the points keep their `index`
        slots and swap places, so `points` still runs from `a` to `b`.
        """
        holder = holder_of(self)
        if (self.conductor is None) == (self.net is None):
            msg = "a route draws either a conductor or a leg of a net, not both and not neither"
            raise SchemaError(msg, kind="layout.route", record_id=holder)
        first, second = self.a, self.b
        ends_are_ids = type(first) is Id and type(second) is Id
        if ends_are_ids and first == second:
            msg = "a route joins two different ports"
            raise SchemaError(msg, kind="layout.route", record_id=holder)
        points = by_index(self.points, RoutePoint, kind="layout.route", holder=holder)
        if points is None:
            return
        if ends_are_ids and second < first:
            object.__setattr__(self, "a", second)
            object.__setattr__(self, "b", first)
            points = _turned_round(points)
        object.__setattr__(self, "points", points)


@record(kind="layout.link_marker")
class LinkMarker:
    """One end of a signal severed by a page boundary; a plain marker (`star` is `None`) has a pair.

    A plain marker's `partner` is the marker on the other page and points back. A star marker
    keeps no pair: an `OFF` stub is its own partner, a `REF` points at one of its branches,
    a `BRANCH` at the reference. The reader's text is rendered from the partner, and the
    severed net is the physical net of `port`; neither is stored. `width`/`height` are the
    reserved box's size in G, never re-measured. `box_x` is the left edge of a shared box,
    `lead` marks the box's lead marker, `stub_extra` is extra stub length in G, `via_x`/`via_y`
    are the stub's bend (both or neither), `star` is the star point drawn, or `None`. `far`,
    `carrier` and `facing` are set only on an off stub and never re-derived. `vertical` is
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

        Also an off stub without `far` and `facing`, either on any other marker, and a
        `carrier` without `far`.
        """
        holder = holder_of(self)
        if type(self.width) is int and self.width <= 0:
            msg = f"a link marker's width must be positive, got {self.width}"
            raise SchemaError(msg, kind="layout.link_marker", record_id=holder)
        if type(self.height) is int and self.height <= 0:
            msg = f"a link marker's height must be positive, got {self.height}"
            raise SchemaError(msg, kind="layout.link_marker", record_id=holder)
        if (self.via_x is None) != (self.via_y is None):
            msg = "a link marker's via_x and via_y are both set or both None"
            raise SchemaError(msg, kind="layout.link_marker", record_id=holder)
        if type(self.stub_extra) is int and self.stub_extra < 0:
            msg = f"a link marker's stub_extra must not be negative, got {self.stub_extra}"
            raise SchemaError(msg, kind="layout.link_marker", record_id=holder)
        if type(self.wrap_at) is int and self.wrap_at < 1:
            msg = f"a link marker's wrap_at must be positive, got {self.wrap_at}"
            raise SchemaError(msg, kind="layout.link_marker", record_id=holder)
        if self.lead is False and self.box_x is None:
            msg = "a link marker that is not the lead of a shared box needs a box_x"
            raise SchemaError(msg, kind="layout.link_marker", record_id=holder)
        is_off = self.star is StarKind.OFF
        if (self.far is not None) != is_off or (self.facing is not None) != is_off:
            msg = "a link marker's far and facing are set exactly when it is an off stub"
            raise SchemaError(msg, kind="layout.link_marker", record_id=holder)
        if self.carrier is not None and self.far is None:
            msg = "a link marker's carrier needs a far"
            raise SchemaError(msg, kind="layout.link_marker", record_id=holder)


@record(kind="layout.outline")
class Outline:
    """The dash-dot boundary of one unit instance's black box on one page (units spec U1).

    `x`, `y` is the rectangle's top-left corner, `width`/`height` its size, in G. Layout
    works it out from the black-box members' bodies and measured labels; render draws it
    and never measures anything (I2a, deep dive; the title is an ordinary label, slot
    `"outline_title"`).
    """

    id: Id[Outline]
    key: AuthoringKey
    unit: Id[Unit]
    page: Id[Page]
    x: int
    y: int
    width: int
    height: int
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a non-positive `width` or `height`."""
        holder = holder_of(self)
        if type(self.width) is int and self.width <= 0:
            msg = f"an outline's width must be positive, got {self.width}"
            raise SchemaError(msg, kind="layout.outline", record_id=holder)
        if type(self.height) is int and self.height <= 0:
            msg = f"an outline's height must be positive, got {self.height}"
            raise SchemaError(msg, kind="layout.outline", record_id=holder)


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


@record(kind="layout.label")
class Label:
    """Where one piece of text sits; the text is rendered from its subject, never stored.

    Exactly one of `function`, `port`, `conductor` is set: the subject whose
    designation, name or wire label is shown. `slot` is the symbol slot the position
    came from (`"tag"`, `"marking.13"`, `"value"`), or `""` for a wire label. `x`, `y`
    is the top-left corner of the label box; `width`/`height` are its size in G, written
    by layout from the box it reserved (D13). The subject of a `WIRE` label is always a
    `conductor`: a net-realised route has no wire label. `partners` lists the other ends
    of the same item for a `CROSS_REFERENCE` label, and is empty for every other kind.
    """

    id: Id[Label]
    key: AuthoringKey
    page: Id[Page]
    function: Id[Function] | None
    port: Id[Port] | None
    conductor: Id[Conductor] | None
    kind: LabelKind
    slot: str
    x: int
    y: int
    width: int
    height: int
    produced_by: str
    partners: tuple[CrossReferencePartner, ...] = ()
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Require a positive size, one subject, a `WIRE` conductor, cross-reference partners."""
        if type(self.width) is int and self.width <= 0:
            msg = f"a label's width must be positive, got {self.width}"
            raise SchemaError(msg, kind="layout.label", record_id=holder_of(self))
        if type(self.height) is int and self.height <= 0:
            msg = f"a label's height must be positive, got {self.height}"
            raise SchemaError(msg, kind="layout.label", record_id=holder_of(self))
        subjects = sum(
            subject is not None for subject in (self.function, self.port, self.conductor)
        )
        if subjects != 1:
            msg = f"a label has exactly one of function, port and conductor, not {subjects}"
            raise SchemaError(msg, kind="layout.label", record_id=holder_of(self))
        if self.kind is LabelKind.WIRE and self.conductor is None:
            msg = "a wire label belongs to a conductor"
            raise SchemaError(msg, kind="layout.label", record_id=holder_of(self))
        partners = self.partners
        if type(partners) is tuple and all(
            type(partner) is CrossReferencePartner for partner in partners
        ):
            has_partners = len(partners) > 0
            if self.kind is LabelKind.CROSS_REFERENCE and not has_partners:
                msg = "a cross-reference label needs at least one partner"
                raise SchemaError(msg, kind="layout.label", record_id=holder_of(self))
            if self.kind is not LabelKind.CROSS_REFERENCE and has_partners:
                msg = "only a cross-reference label carries partners"
                raise SchemaError(msg, kind="layout.label", record_id=holder_of(self))
