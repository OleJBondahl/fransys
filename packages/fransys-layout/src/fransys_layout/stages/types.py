"""Stage inputs and outputs: small frozen values, free of the model vocabulary (design/stages.md 6).

Only `engines/` knows records. It turns them into these values (`read/`) and turns
stage outputs back into derived `layout.*` records (`write/`). Engineering enums
reach a stage as their string value (`kind="coil"`), never as the enum.

Nothing here is ordered by position in a tuple unless it says so: every sequence
whose order matters carries an explicit `index`, and every tuple is stored sorted by
the key its docstring names.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import Box, Point, SymbolGeometry
from fransys_layout.geometry.box_reach import Reach
from fransys_model.kernel import AuthoringKey, Id, register_enum, value

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

# The id of the function, port, conductor, net or aspect node a value stands for.
# Stages compare and sort handles and put them in findings. They never look inside one
# and never look anything up by it. Handle order is `Id`'s own `(kind, value)` ordering.
type Handle = Id[Any]

# Per function, the `(slot, box)` pairs of its label boxes.
type FnBoxes = Mapping[Handle, list[tuple[str, Box]]]

# A function's body box, keyed by the function.
type BodyBox = tuple[Handle, Box]

# The `Id.kind` the engine gives a unit-boundary stand-in handle (a port or function on no
# net, where a chain stops at the unit edge). A stage-side convention, not vocabulary.
EDGE_KIND = "edge"


def _sort(obj: object, **keys: Callable[[Any], Any]) -> None:
    """Store each named tuple field of a frozen value sorted by its key (`__post_init__` only)."""
    for name, key in keys.items():
        object.__setattr__(obj, name, tuple(sorted(getattr(obj, name), key=key)))


@register_enum
class Role(Enum):
    """What kind of circuit a column is, declared strongest first (D4, docs/design/pages.md 6.3)."""

    POWER = "power"
    CONTROL = "control"
    SIGNAL = "signal"


ROLE_ORDER: tuple[Role, ...] = (Role.POWER, Role.CONTROL, Role.SIGNAL)


@register_enum
class LinkCase(Enum):
    """How a cut connection is drawn (design/links.md 6.6); `CROSS_UNIT` is never a marker (U2)."""

    TERMINAL_ECHO = "terminal_echo"
    TAG_ECHO = "tag_echo"
    SEVERED = "severed"
    CROSS_UNIT = "cross_unit"


@register_enum
class MarkerSide(Enum):
    """Which end of a severed signal a marker stands at."""

    OWNER = "owner"
    USER = "user"


@register_enum
class LabelKind(Enum):
    """What a label shows; the text itself is rendered from the model by output modules."""

    TAG = "tag"
    MARKING = "marking"
    WIRE = "wire"
    CROSS_REFERENCE = "cross_reference"


# --- configuration -------------------------------------------------------------------


@value
class SheetFormat:
    """The drawable area of a sheet, already in grid units, and its frame grid (links.md 6.6)."""

    name: str
    content_width: int
    content_height: int
    frame_columns: int
    frame_rows: int


@value
class Profile:
    """Every tunable of the stages, in grid units (foundations.md 2.9, engine.md 7)."""

    column_gap: int
    row_gap: int
    row_spacing: int  # R13: the keep-out gap between consecutive rows of a column
    text_height: int
    marker_padding: int
    band_ranks: frozendict[str, int]
    group_ranks: frozendict[str, int]
    route_turn_penalty: int
    route_crossing_penalty: int
    route_margin: int
    hide_unused_pins: bool = False  # V1: leave out the pins and functions with no conductor


@value
class SymbolRule:
    """One row of the default symbol table: function kind, optional part category, symbol."""

    kind: str
    category: str | None
    symbol: str
    port_map: frozendict[str, str] = frozendict()
    gender: str | None = None  # mated-pair J2: read only for kind connector


@value
class SymbolChoice:
    """An authored symbol override; the model's record guarantees one of function, part, kind."""

    choice: Id[Any]
    function: Id[Any] | None
    part: Id[Any] | None
    kind: str | None
    symbol: str
    port_map: frozendict[str, str]


# --- what is drawn -------------------------------------------------------------------


@value
class PortSpec:
    """One model port to be drawn: `throw` its changeover role, `rank`/`current` its V11 facts."""

    port: Id[Any]
    name: str
    physical_net: Id[Any]
    role: Role
    throw: str | None = None
    rank: int | None = None
    current: str | None = None
    strip_side: str | None = None  # a terminal port's `PortRole` value, internal or external
    group: int = 0  # V1: the side order of the port's function in its item box, 0 outside one
    channel: bool = False  # V5: a PLC channel's pin, of a box that also holds other functions


@value
class PolePair:
    """The two model ports one pole joins: `first` is its line end, `second` its load end (0106)."""

    index: int
    first: str
    second: str


# docs/design/foundations.md 2.8
@value
class KindRoles:
    """What the stages treat specially about one function kind; the engine fills it."""

    terminal: bool = False
    narrow: bool = False
    boxy: bool = False
    sets_group: bool = True
    gendered: bool = False
    coil: bool = False
    contact: bool = False
    contact_closed: bool = False
    contact_changeover: bool = False
    plc_channel: bool = False


@value
class FunctionSpec:
    """One function to be drawn; `ports` sorted by `name`, `pole_pairs` by `index`.

    `poles`, `pole_pairs` (empty with no internal link) and `roles` (`KIND_ROLES` for `kind`)
    are the engine's; `group_path` and `location_path` are empty when the item has no placement.
    """

    function: Id[Any]
    item: Id[Any]
    part: Id[Any] | None
    key: AuthoringKey
    kind: str
    category: str | None
    poles: int
    pole_pairs: tuple[PolePair, ...]
    ports: tuple[PortSpec, ...]
    group_path: tuple[Id[Any], ...]
    location_path: tuple[Id[Any], ...]
    group_hint: Id[Any] | None
    designation: str = ""  # R5: the item's reference designation, "" unnumbered
    strip_text: str = ""  # R6 D1: a terminal's strip tag, "" for any other function
    point_text: str = ""  # R6 D1: a terminal's own point text, in full ("-X2:U:1", D12)
    # R7 A: a pin view's real connector function; the view's handle is the pin's port
    pin_function: Id[Any] | None = None
    gender: str | None = None  # mated-pair J2: the connector facet's gender
    unit: Id[Any] | None = None
    # F1: a positioned child's parent designation and position: a rack module's slot
    rack: str = ""
    rack_position: int | None = None
    roles: KindRoles = KindRoles()
    item_parent: Id[Any] | None = None
    rest: str | None = None  # layout-0105: `link_state` of the first switched link
    protection_type: str | None = None  # layout-0105: a protection's type value
    rail: bool = False  # layout-0120: a unit-boundary rail terminal, drawn only as a replica

    def __post_init__(self) -> None:
        """Sort `ports` by name and `pole_pairs` by index; the paths keep their order."""
        _sort(self, ports=lambda p: p.name, pole_pairs=lambda p: p.index)

    @property
    def drawing_set_key(self) -> tuple[Id[Any] | None, Id[Any] | None]:
        """The key of a column holding just this function: its unit, and its leaf location."""
        return drawing_set_of(self.unit, self.location_path[-1] if self.location_path else None)


@value
class DrawnPort:
    """A model port bound to the symbol port it is drawn at."""

    port: Id[Any]
    symbol_port: str
    ac: bool = False  # V11: the pin's supply current is AC
    group: int = 0  # V1: its function's side order in an item box, kept whole on a box side
    channel: bool = False  # V5: a PLC channel's pin


@value
class FedPin:
    """layout-0107: a pin of the fed box and the feeder's pin wired to it."""

    fed: Id[Any]
    feeder: Id[Any]


@value
class BoxFeed:
    """layout-0107: one box wired pin to pin to a group of another, `ports` as `FedPin`s."""

    fed: Id[Any]
    feeder: Id[Any]
    ports: tuple[FedPin, ...]


@value
class DrawnFunction:
    """A function with its symbol chosen (output of `resolve`). `ports` is sorted by `port`."""

    function: Id[Any]
    item: Id[Any]
    key: AuthoringKey
    kind: str
    geometry: SymbolGeometry
    ports: tuple[DrawnPort, ...]
    primary_in: str | None
    primary_out: str | None
    roles: KindRoles = KindRoles()
    reach: tuple[Reach, ...] = ()  # V5: the room each box pin's attached contact needs
    fed_by: tuple[BoxFeed, ...] = ()  # layout-0107: the feeders whose pins stand over this box's
    feeds: Id[Any] | None = None  # layout-0107: the box this one stands over, pin over pin

    def __post_init__(self) -> None:
        """Sort `ports` by model port handle."""
        _sort(self, ports=lambda p: p.port)


# --- connectivity --------------------------------------------------------------------


@value
class PortRef:
    """One end of a connection: a port and its function; R7 B5 `symbol_port` overrides."""

    function: Id[Any]
    port: Id[Any]
    symbol_port: str = ""


@value
class Connection:
    """One conductor: `(handle, a.port, b.port)`, `a`/`b` stored in port-handle order."""

    handle: Id[Any]
    physical_net: Id[Any]
    role: Role
    a: PortRef
    b: PortRef

    def __post_init__(self) -> None:
        """Swap the ends if they came in the other order, so `a.port < b.port`."""
        if self.b.port < self.a.port:
            a, b = self.a, self.b
            object.__setattr__(self, "a", b)
            object.__setattr__(self, "b", a)


@value
class NetGroup:
    """A declared or board-realised net with no conductors; `ports` sorted by port handle."""

    net: Id[Any]
    physical_net: Id[Any]
    role: Role
    ports: tuple[PortRef, ...]

    def __post_init__(self) -> None:
        """Sort `ports` by port handle."""
        _sort(self, ports=lambda ref: ref.port)


# --- columns -------------------------------------------------------------------------


@value
class PowerEnd:
    """D5: how `port` on a power net is drawn: its `PowerKind` value, `symbol` key and `text`."""

    port: Id[Any]
    kind: str
    symbol: str
    text: str | None


@value
class RailEnd:
    """V3: a drawn pin end of a conductor the engine does not draw, and that conductor's handle."""

    ref: PortRef
    connection: Id[Any]


@value
class Rail:
    """A declared rail: a `Net` with a potential, its raw ports sorted (WP16, layout-0034)."""

    net: Id[Any]
    potential: str
    ports: tuple[Id[Any], ...]

    def __post_init__(self) -> None:
        """Sort `ports` by handle."""
        _sort(self, ports=lambda port: port)


@value
class ChainEntry:
    """One function of an authored chain, at its explicit position."""

    function: Id[Any]
    index: int


@value
class Chain:
    """An authored series chain: one column. `entries` is sorted by `index`."""

    chain: Id[Any]
    key: AuthoringKey
    entries: tuple[ChainEntry, ...]

    def __post_init__(self) -> None:
        """Sort `entries` by index."""
        _sort(self, entries=lambda entry: entry.index)


@value
class Cell:
    """One function in a column at its explicit position; cells of one `index` are a row (R4)."""

    function: Id[Any]
    index: int
    lane: int = 0
    side: bool = False
    flip: bool = False  # R5: a side element drawn at R180, its other port on top
    mirror: bool = False  # D1: a turned directed pole is flipped top to bottom (MR180)
    low: bool = False  # R5: a one-port side element on its host's bottom port
    carrier: Id[Any] | None = None  # D2: the function whose cell a side element stands beside
    host: Id[Any] | None = None  # R7.1: an attachment's host function in this column
    port: str = ""  # R7.1: the host's symbol port the attachment sits at
    face: bool = False  # R7 A: the lower pin of a mated pair, face to face with host
    replica: bool = False  # R7 B8: a replica terminal attached in another group's column
    moved: bool = False  # D4 V5: a contact or coil whose home moved to the pin it serves
    span_port: str = ""  # C12: the symbol port that sits under this cell's lane


@value
class MatedFunctions:
    """Two drawn functions plugged together (a model `Mate`), for chain discovery (R4)."""

    a: Id[Any]
    b: Id[Any]


@value
class Column:
    """The unit of placement: cells sorted by `(index, lane)`, drawn top to bottom.

    `key` orders columns (the chain key, or the first cell's function key). `unit` is `None`
    for a model with no units.
    """

    key: AuthoringKey
    cells: tuple[Cell, ...]
    group: Id[Any] | None
    role: Role
    location: Id[Any] | None
    unit: Id[Any] | None = None

    def __post_init__(self) -> None:
        """Sort `cells` by row, then lane."""
        _sort(self, cells=lambda cell: (cell.index, cell.lane))

    @property
    def drawing_set_key(self) -> tuple[Id[Any] | None, Id[Any] | None]:
        """The `(unit, location)` that `partition` step 1 files the column under (pages.md 6.3)."""
        return drawing_set_of(self.unit, self.location)


def drawing_set_of(
    unit: Id[Any] | None, location: Id[Any] | None
) -> tuple[Id[Any] | None, Id[Any] | None]:
    """The drawing-set key of something in `unit` at `location`: the one rule (layout-0081)."""
    if unit is not None:
        return (unit, None)
    return (None, location)


# --- partition -----------------------------------------------------------------------


@value
class GroupInfo:
    """What `partition` needs to know about one `=` node; `label` keys `Profile.group_ranks`."""

    group: Id[Any]
    key: AuthoringKey
    label: str
    description: str


@value
class LocationInfo:
    """What `partition` needs to know about one `+` node."""

    location: Id[Any]
    label: str
    path: tuple[Id[Any], ...] = ()  # RW9: root-to-leaf node ids; the labels are in `locations`


@value
class UnitInfo:
    """What `partition` needs to know about one model `Unit` (`location`: layout-0081)."""

    unit: Id[Any]
    location: Id[Any] | None = None


@value
class OrderHint:
    """An authored order between two groups."""

    before: Id[Any]
    after: Id[Any]


@value
class GroupSet:
    """Groups an author wants on one page. `groups` is sorted by handle."""

    groups: tuple[Id[Any], ...]

    def __post_init__(self) -> None:
        """Sort `groups` by handle."""
        _sort(self, groups=lambda group: group)


@value
class PageHints:
    """Page hints (pages.md 6.3): `keep_together` by groups, `break_before` by handle, `order`."""

    keep_together: tuple[GroupSet, ...]
    break_before: tuple[Id[Any], ...]
    order: tuple[OrderHint, ...]

    def __post_init__(self) -> None:
        """Sort the three tuples by the keys the docstring names."""
        _sort(
            self,
            keep_together=lambda together: together.groups,
            break_before=lambda group: group,
            order=lambda hint: (hint.before, hint.after),
        )


@value
class ColumnWidth:
    """The estimated width of one column: widest keep-out box plus the column gap."""

    column: AuthoringKey
    width: int


@value
class PlannedGroup:
    """One group on a page, at its explicit position."""

    group: Id[Any] | None
    index: int


@value
class PlannedColumn:
    """One column on a page, at its explicit position from the left."""

    column: AuthoringKey
    index: int


@value
class PagePlan:
    """One planned page, numbered from 1 in its set; `groups`, `columns` sorted by `index`."""

    drawing_set: int
    location: Id[Any] | None
    unit: Id[Any] | None = None
    number: int
    role: Role
    title: str
    groups: tuple[PlannedGroup, ...]
    columns: tuple[PlannedColumn, ...]

    def __post_init__(self) -> None:
        """Sort `groups` and `columns` by index."""
        _sort(self, groups=lambda group: group.index, columns=lambda column: column.index)


# --- place ---------------------------------------------------------------------------


@value
class PlacedFunction:
    """A drawn function at its page position; identity is `(function, drawing_set, page)`."""

    function: Id[Any]
    drawing_set: int
    page: int
    column: AuthoringKey
    at: Point
    geometry: SymbolGeometry
    carrier: Id[Any] | None = None


# --- route ---------------------------------------------------------------------------


@value
class RoutePoint:
    """One vertex of a route, at its explicit position along the polyline."""

    index: int
    at: Point


@value
class Route:
    """The polyline of a conductor or net-group edge `(connection, a, b)`; `points` by `index`."""

    connection: Id[Any]
    physical_net: Id[Any]
    drawing_set: int
    page: int
    a: Id[Any]
    b: Id[Any]
    points: tuple[RoutePoint, ...]

    def __post_init__(self) -> None:
        """Sort `points` by index."""
        _sort(self, points=lambda point: point.index)


# --- links ---------------------------------------------------------------------------


@value
class LinkDecision:
    """How one cut is drawn. `(connection, a, b)` identifies it, `a`, `b` as `links` built them."""

    connection: Id[Any]
    a: Id[Any]
    b: Id[Any]
    case: LinkCase


@value
class StubText:
    """C21: what an off stub names of its end: the cable, the far device and the far port.

    `cable` is the outermost carrier's `-designation` (`""` for none), `far` and `port` the far
    end's head and tail as `derive.drawing_text.stub_far_end` gives them (`+EXT-M1`, `:U1`).
    """

    cable: str
    far: str
    port: str


@value
class LinkMarker:
    """One end of a severed signal. `partner_*` locate the other end (links.md 6.6, layout-0043)."""

    connection: Id[Any]
    port: Id[Any]
    side: MarkerSide
    drawing_set: int
    page: int
    at: Point
    box: Box
    partner_page: int
    # R6 D2: a bundle row's markers share one box (the lead draws box and text),
    # or a marker is pushed `stub_extra` further out so it clears its neighbour
    shared_box: bool = False
    lead: bool = True
    stub_extra: int = 0
    # R7 B4: a net drawn as one marker per port: "ref" (lists the others) or "branch"
    # (names the reference); `star_partner` is the port the text is about
    star: str = ""
    star_partner: Id[Any] | None = None
    star_partner_set: int = 0
    # C21: an "off" stub's own text (no partner to derive it from); D9 (F7): on a "ref" it is
    # the text of the off stub on the same port, merged into the reference's marker
    text: str = ""
    # EF-C: an "off" stub's own end; one conductor end's text, so two stubs on one port tell
    # apart and `write/markers.py` finds the end's far port; `None` otherwise
    end_text: StubText | None = None
    # I4: a star reference on a wired port leaves the wire here, E, one grid out along it
    turn: Point | None = None
    # S20 M1 (model-0114): an N or S marker's text reads along its wire; `box` is the turned box
    vertical: bool = False
    # S20 M8 (model-0115): a C21 run's text breaks after this many words; `None` for one line
    wrap_at: int | None = None
    # D5 (step 6): a power end, drawn as this symbol key with this text; `""` for a reference
    symbol: str = ""
    symbol_text: str = ""
    # D5 ruled 2026-10-02: the symbol's lead in whole grids, longer when a nearer one would collide
    symbol_grids: int = 1


# --- labels --------------------------------------------------------------------------


@value
class RequestPartner:
    """A cross-referenced item's other end; `links._references` sorts by set, page, column, port."""

    port: Id[Any]
    drawing_set: int
    page: int
    x: int


@value
class LabelRequest:
    """One label to place. `text` is used only to measure; it is not stored in a record."""

    kind: LabelKind
    subject: Id[Any]
    slot: str
    text: str
    partners: tuple[RequestPartner, ...] = ()
    level: bool = False


@value
class PlacedLabel:
    """A label at its page position. A record keeps only the box's top-left corner."""

    kind: LabelKind
    subject: Id[Any]
    slot: str
    drawing_set: int
    page: int
    box: Box
    partners: tuple[RequestPartner, ...] = ()
    unplaced: bool = False


@value
class PlacedOutline:
    """I2a (units U1): the dash-dot boundary of one unit instance's black box on one page."""

    unit: Id[Any]
    lead: Id[Any]
    drawing_set: int
    page: int
    box: Box


# --- whole result --------------------------------------------------------------------


@value
class Layout:
    """Everything the stages produced for one model; input of `lint` and of `write/`."""

    pages: tuple[PagePlan, ...]
    placed: tuple[PlacedFunction, ...]
    routes: tuple[Route, ...]
    decisions: tuple[LinkDecision, ...]
    markers: tuple[LinkMarker, ...]
    labels: tuple[PlacedLabel, ...]
    outlines: tuple[PlacedOutline, ...] = ()
