"""Stage inputs and outputs: small frozen values, free of the model vocabulary.

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
from fransys_layout.stages.texts.candidates import TextPlacement
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
type OrderKey = tuple[tuple[tuple[int, int, str], ...], str]  # `natural_key`'s shape, a value

# The `Id.kind` the engine gives a unit-boundary stand-in handle (a port or function on no
# net, where a chain stops at the unit edge). A stage-side convention, not vocabulary.
EDGE_KIND = "edge"


def _sort(obj: object, **keys: Callable[[Any], Any]) -> None:
    """Store each named tuple field of a frozen value sorted by its key (`__post_init__` only)."""
    for name, key in keys.items():
        object.__setattr__(obj, name, tuple(sorted(getattr(obj, name), key=key)))


@register_enum
class Role(Enum):
    """What kind of circuit a column is, declared strongest first."""

    POWER = "power"
    CONTROL = "control"
    SIGNAL = "signal"


@register_enum
class Home(Enum):
    """Where a function's home is, as a cell or a spec states it (layout-0129).

    `HERE`: the cell stands at its function's home. `MOVED`: the home moved to the pin it serves.
    `ELSEWHERE`: drawn away from its home, a replica; on a spec, a home that is not drawn.
    """

    HERE = "here"
    MOVED = "moved"
    ELSEWHERE = "elsewhere"


ROLE_ORDER: tuple[Role, ...] = (Role.POWER, Role.CONTROL, Role.SIGNAL)


@register_enum
class LinkCase(Enum):
    """How a cut connection is drawn; `CROSS_UNIT` is never a marker."""

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
    """The drawable area of a sheet, already in grid units, and its frame grid."""

    name: str
    content_width: int
    content_height: int
    frame_columns: int
    frame_rows: int
    inset: int = 0  # the gap kept between the frame line and ink, on every side (layout-0187)

    @property
    def inner_width(self) -> int:
        """The width the ink may use: the content width less the inset twice."""
        return self.content_width - 2 * self.inset

    @property
    def inner_height(self) -> int:
        """The height the ink may use: the content height less the inset twice."""
        return self.content_height - 2 * self.inset

    @property
    def right(self) -> int:
        """The x of the right edge of the inset box."""
        return self.content_width - self.inset

    @property
    def bottom(self) -> int:
        """The y of the bottom edge of the inset box."""
        return self.content_height - self.inset


@value
class Profile:
    """Every tunable of the stages, in grid units."""

    column_gap: int
    row_gap: int
    row_spacing: int  # The keep-out gap between consecutive rows of a column
    text_height: int
    marker_padding: int
    table_base: int  # A contact table with no rows; each row adds `text_height` (contact_rows)
    heading_room: int  # The heading line a stacked contact table carries above its columns
    band_ranks: frozendict[str, int]
    group_ranks: frozendict[str, int]
    route_turn_penalty: int
    route_crossing_penalty: int
    route_margin: int
    hide_unused_pins: bool = False  # Leave out the pins and functions with no conductor
    texts: frozendict[str, TextPlacement] = (
        frozendict()
    )  # the caller's text placement, by kind (seam 1)


@value
class SymbolRule:
    """One row of the default symbol table: function kind, optional part category, symbol."""

    kind: str
    category: str | None
    symbol: str
    port_map: frozendict[str, str] = frozendict()
    gender: str | None = None  # Read only for kind connector


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
    """One model port to be drawn: `throw` its changeover role, `rank`/`current` its facts."""

    port: Id[Any]
    name: str
    physical_net: Id[Any]
    role: Role
    throw: str | None = None
    pole: int = 0  # a changeover port's pole: its common's place in the pole order
    line: bool = False  # the part states this port on its pole's line side
    rank: int | None = None
    current: str | None = None
    strip_side: str | None = None  # a terminal port's `PortRole` value, internal or external
    group: int = 0  # The side order of the port's function in its item box, 0 outside one
    channel: bool = False  # A PLC channel's pin, of a box that also holds other functions
    stand: int = 0  # layout-0132: the width in G of the power symbol and text at the pin
    order: int = 0  # Rank of the name in natural order among the function's ports, a value


@value
class PolePair:
    """The two model ports one pole joins: `first` is its line end, `second` its load end (0106)."""

    index: int
    first: str
    second: str


@value
class KindRoles:
    """What the stages treat specially about one function kind; the engine fills it."""

    terminal: bool = False
    narrow: bool = False
    boxy: bool = False
    sets_group: bool = True
    gendered: bool = False
    coil: bool = False
    contacts_apart: bool = False  # owns contacts drawn apart: a coil, or a box (layout-0123)
    contact: bool = False
    contact_closed: bool = False
    contact_changeover: bool = False
    plc_channel: bool = False
    item_view: bool = False  # stands for a whole item: its function is the item's id


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
    designation: str = ""  # The item's reference designation, "" unnumbered
    designation_order: int = 0  # Rank of the designation in natural order, a value
    strip_text: str = ""  # A terminal's strip tag, "" for any other function
    point_text: str = ""  # A terminal's own point text, in full ("-X2:U:1")
    # A pin view's real connector function; the view's handle is the pin's port
    pin_function: Id[Any] | None = None
    gender: str | None = None  # The connector facet's gender
    unit: Id[Any] | None = None
    # A positioned child's parent designation and position: a rack module's slot
    rack: str = ""
    rack_position: int | None = None
    roles: KindRoles = KindRoles()
    item_parent: Id[Any] | None = None
    rest: str | None = None  # layout-0105: `link_state` of the first switched link
    protection_type: str | None = None  # layout-0105: a protection's type value
    operated_by: str | None = None  # layout-0220: `derive.operated_by`'s value
    home: Home = Home.HERE  # layout-0120: ELSEWHERE for a unit-boundary rail terminal (replicas)

    def __post_init__(self) -> None:
        """Sort `ports` by `order`, then name, and `pole_pairs` by index; paths keep their order."""
        _sort(self, ports=lambda p: (p.order, p.name), pole_pairs=lambda p: p.index)

    @property
    def drawing_set_key(self) -> tuple[Id[Any] | None, Id[Any] | None]:
        """The key of a column holding just this function: its unit, and its leaf location."""
        return drawing_set_of(self.unit, self.location_path[-1] if self.location_path else None)


@value
class DrawnPort:
    """A model port bound to the symbol port it is drawn at."""

    port: Id[Any]
    symbol_port: str
    ac: bool = False  # The pin's supply current is AC
    group: int = 0  # Its function's side order in an item box, kept whole on a box side
    channel: bool = False  # A PLC channel's pin
    stand: int = 0  # layout-0132: the width in G of the power symbol and text at the pin
    order: int = 0  # Its `PortSpec.order`, the tie-break of a box port nobody placed


@value
class FedPin:
    """Layout-0107: a pin of the fed box and the feeder's pin wired to it."""

    fed: Id[Any]
    feeder: Id[Any]


@value
class BoxFeed:
    """Layout-0107: one box wired pin to pin to a group of another, `ports` as `FedPin`s."""

    fed: Id[Any]
    feeder: Id[Any]
    ports: tuple[FedPin, ...]


@value
class DeviceChain:
    """LC2: devices of one block wired hop to hop, `members` top to bottom (layout-0215).

    Each hop is a `BoxFeed`, the upper device its feeder; a ring's `closing` hop draws as markers.
    """

    members: tuple[Id[Any], ...]
    hops: tuple[BoxFeed, ...]
    closing: BoxFeed | None = None


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
    reach: tuple[Reach, ...] = ()  # The room each box pin's attached contact needs
    fed_by: tuple[BoxFeed, ...] = ()  # layout-0107: the feeders whose pins stand over this box's
    feeds: Id[Any] | None = None  # layout-0107: the box this one stands over, pin over pin
    chained: bool = False  # layout-0215: a device chain's box, its pins set by its hops

    @property
    def stand(self) -> int:
        """Layout-0132: the width in G of the widest power symbol and text standing at a pin."""
        return max((p.stand for p in self.ports), default=0)

    def __post_init__(self) -> None:
        """Sort `ports` by model port handle."""
        _sort(self, ports=lambda p: p.port)


# --- connectivity --------------------------------------------------------------------


@value
class PortRef:
    """One end of a connection: a port and its function; `symbol_port` overrides."""

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
    """How `port` on a power net is drawn: its `PowerKind` value, `symbol` key and `text`."""

    port: Id[Any]
    kind: str
    symbol: str
    text: str | None


@value
class RailEnd:
    """A drawn pin end of a conductor the engine does not draw, and that conductor's handle."""

    ref: PortRef
    connection: Id[Any]


@value
class Rail:
    """A declared rail: a `Net` with a potential, its raw ports sorted (layout-0034)."""

    net: Id[Any]
    potential: str
    ports: tuple[Id[Any], ...]

    def __post_init__(self) -> None:
        """Sort `ports` by handle."""
        _sort(self, ports=lambda port: port)


@value
class ChainEntry:
    """One function of an authored chain, at its explicit position.

    `box` marks a function drawn in its item's box: `function` is then the box's item view.
    """

    function: Id[Any]
    index: int
    box: bool = False


@value
class Chain:
    """An authored series chain: one column. `entries` is sorted by `index`."""

    chain: Id[Any]
    key: AuthoringKey
    entries: tuple[ChainEntry, ...]
    beside: Id[Any] | None = None  # layout-0174: the host function this chain stands beside

    def __post_init__(self) -> None:
        """Sort `entries` by index."""
        _sort(self, entries=lambda entry: entry.index)


@value
class Cell:
    """One function in a column at its explicit position; cells of one `index` are a row."""

    function: Id[Any]
    index: int
    lane: int = 0
    side: bool = False
    flip: bool = False  # A side element drawn at R180, its other port on top
    mirror: bool = False  # A turned directed pole is flipped top to bottom (MR180)
    low: bool = False  # A one-port side element on its host's bottom port
    carrier: Id[Any] | None = None  # The function whose cell a side element stands beside
    host: Id[Any] | None = None  # An attachment's host function in this column
    port: str = ""  # The host's symbol port the attachment sits at
    face: bool = False  # The lower pin of a mated pair, face to face with host
    home: Home = Home.HERE  # layout-0129: ELSEWHERE a replica, MOVED a home at its pin
    span_port: str = ""  # The symbol port that sits under this cell's lane
    at_wire: bool = False  # layout-0216: a copy drawn at its wire's far pin, keyed by its host


@value
class MatedFunctions:
    """Two drawn functions plugged together (a model `Mate`), for chain discovery."""

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
    beside: Id[Any] | None = None  # layout-0174: the host function this column stands beside

    def __post_init__(self) -> None:
        """Sort `cells` by row, then lane."""
        _sort(self, cells=lambda cell: (cell.index, cell.lane))

    @property
    def away(self) -> bool:
        """Every cell is drawn away from its home: a replica column (layout-0129)."""
        return all(cell.home is Home.ELSEWHERE for cell in self.cells)

    @property
    def drawing_set_key(self) -> tuple[Id[Any] | None, Id[Any] | None]:
        """The `(unit, location)` that `partition` step 1 files the column under."""
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
    order: int = 0  # Rank of the label in natural order, passed in by the read layer
    designation: str = ""  # The signed path (`=G1`), what names a group with no description


@value
class LocationInfo:
    """What `partition` needs to know about one `+` node."""

    location: Id[Any]
    label: str
    path: tuple[Id[Any], ...] = ()  # Root-to-leaf node ids; the labels are in `locations`
    order: int = 0  # Rank of the label in natural order, passed in by the read layer


@value
class UnitInfo:
    """What `partition` needs to know about one model `Unit` (`location`: layout-0081)."""

    unit: Id[Any]
    location: Id[Any] | None = None
    order: int = 0  # Rank of the unit designation in natural order, passed in


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
    """Page hints: `keep_together` by groups, `break_before` by handle, `order`."""

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
    """What an off stub names of its end: the cable, the far device and the far port.

    `cable` is the outermost carrier's `-designation`, `far`/`port` the far end's head and tail
    (`stub_far_end`); `line`: the carrier draws as a line, so the stub prints no port (layout-0154).
    """

    cable: str
    far: str
    port: str
    line: bool = False


@value
class LinkMarker:
    """One end of a severed signal. `partner_*` locate the other end (layout-0043)."""

    connection: Id[Any]
    port: Id[Any]
    side: MarkerSide
    drawing_set: int
    page: int
    at: Point
    box: Box
    partner_page: int
    # A bundle row's markers share one box (the lead draws box and text),
    # or a marker is pushed `stub_extra` further out so it clears its neighbour
    shared_box: bool = False
    lead: bool = True
    stub_extra: int = 0
    # A net drawn as one marker per port: "ref" (lists the others) or "branch"
    # (names the reference); `star_partner` is the port the text is about
    star: str = ""
    star_partner: Id[Any] | None = None
    star_partner_set: int = 0
    # An "off" stub's own text (no partner to derive it from); on a "ref" it is
    # the text of the off stub on the same port, merged into the reference's marker
    text: str = ""
    # EF-C: an "off" stub's own end; one conductor end's text, so two stubs on one port tell
    # apart and `write/markers.py` finds the end's far port; `None` otherwise
    end_text: StubText | None = None
    # A star reference on a wired port leaves the wire here, E, one grid out along it
    turn: Point | None = None
    # (model-0114): an N or S marker's text reads along its wire; `box` is the turned box
    vertical: bool = False
    # (model-0115): an off-stub run's text breaks after this many words; `None` for one line
    wrap_at: int | None = None
    # A power end, drawn as this symbol key with this text; `""` for a reference
    symbol: str = ""
    symbol_text: str = ""
    # The symbol's lead in whole grids, longer when a nearer one would collide
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
    function: Id[Any] | None = None  # a MARKING's function, when its port is drawn by two


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
    function: Id[Any] | None = None  # a MARKING's function, when its port is drawn by two


@value
class PlacedOutline:
    """The dash-dot boundary of one unit instance's black box on one page."""

    unit: Id[Any]
    lead: Id[Any]
    drawing_set: int
    page: int
    box: Box


@value
class PlacedExternalOutline:
    """The dashed boundary of one run of an external item's symbols on one page."""

    item: Id[Any]
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
    external_outlines: tuple[PlacedExternalOutline, ...] = ()
