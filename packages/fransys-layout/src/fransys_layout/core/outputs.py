"""Values of the placer core, output side: placement, routes, text, layout, score, scene."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .errors import CoreError
from .scene_facts import SceneFacts, page_fill, scene_facts
from .values import StandClass

if TYPE_CHECKING:  # jsonform resolves these names from the module, so no run-time import
    from collections.abc import Mapping

    from .annex_values import AnnexBox
    from .flow_values import FlowGraph
    from .values import XY, Box, Finding, MarkerKind, Orientation, PagePlan, PinRef, PlacementProblem, Ref, Side, Size, WireKind


@dataclass(frozen=True, slots=True)
class PinXY:
    """A pin's name and its absolute x and y on the page."""

    pin: str
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Placed:
    """body and footprint are absolute; a box's body spans its spread pins."""

    sym: str
    page: int
    x: int
    y: int
    orient: Orientation
    body: Box
    footprint: Box
    pin_xy: tuple[PinXY, ...]


@dataclass(frozen=True, slots=True)
class Gap:
    """The space between two neighbouring columns of one row; tracks is its track count."""

    id: str
    page: int
    left: str
    right: str
    x0: int
    x1: int
    tracks: int
    y0: int | None = None
    y1: int | None = None


@dataclass(frozen=True, slots=True)
class Trunk:
    """A fan's trunk on one page: its span, its lane count and the row it stands in."""

    fan: str
    page: int
    y: int
    x0: int
    x1: int
    lanes: int
    row: int
    """Index of the row its trunk stands in."""
    lane_ends: tuple[tuple[int, int] | None, ...]
    """(x0, x1) of each lane j, first tap to last; None: lane j has no tap in the row."""
    stood: tuple[tuple[bool, bool], ...] = ()
    """Per lane j, whether its arrow's box stood at the (left, right) end; False: no room, the marker is MARKER_UNPLACED (layout-0507).
    Empty: all stood."""
    room: tuple[int, int] = (0, 0)
    """The G the solve held above and below the trunk line (`place_trunk.held_room`): the spans read it, never recompute it."""


@dataclass(frozen=True, slots=True)
class PagePlacement:
    """One page's placed symbols, gaps, trunks, row sizes and row bands."""

    page: int
    placed: tuple[Placed, ...]
    gaps: tuple[Gap, ...]
    trunks: tuple[Trunk, ...]
    rows: tuple[tuple[int, int], ...]
    """(height, width) of each row, in G."""
    bands: tuple[tuple[int, int], ...]
    """(top, bottom) of each row in grid units, in row order."""
    spans: Mapping[str, tuple[int, int]] = field(default_factory=dict)
    """(top, bottom) the solve placed for each column id and block id, in G (layout-0374)."""
    hangings: Mapping[str, tuple[Box, ...]] = field(default_factory=dict)
    """By symbol, the absolute boxes of the markers hung at its placed pins, set once by the placer (layout-0547)."""


@dataclass(frozen=True, slots=True)
class Placement:
    """The placement of every page, with the findings the placer raised and the unit frames each page holds (R900)."""

    pages: tuple[PagePlacement, ...]
    findings: tuple[Finding, ...] = ()
    outlines: tuple[Outline, ...] = ()


@dataclass(frozen=True, slots=True)
class Wire:
    """One wire of one net; a bundle trunk is one wire per conductor, each with its `lane`."""

    net: str
    page: int
    points: tuple[XY, ...]
    kind: WireKind
    lane: int | None = field(default=None, kw_only=True)
    """The conductor's lane index when the wire is one conductor of a bundle trunk."""


@dataclass(frozen=True, slots=True)
class Demand:
    """How many tracks one gap needs for the wires routed through it."""

    gap: str
    tracks: int


@dataclass(frozen=True, slots=True)
class Counts:
    """The crossing, bend, excess, length and detour counts of one page's routes."""

    crossings: int
    bends: int
    excess: int
    length: int


@dataclass(frozen=True, slots=True)
class Junction:
    """One junction point on `page`, in G, and the net it joins."""

    net: str
    page: int
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class PageRoutes:
    """The routed wires, gap demand, counts and junction dots of one page.

    `dots` is written once, by `route_page`, from this page's `wires` (R535 H10, layout-0395).
    """

    page: int
    wires: tuple[Wire, ...]
    demand: tuple[Demand, ...]
    counts: Counts
    dots: tuple[Junction, ...]
    labels: tuple[AnnexBox, ...]
    """The page's annexes, placed after its fixed wires and before its A* round, in the order the problem gives them (TEXT-CANDIDATES)."""
    needs: tuple[Demand, ...]
    """The tracks the gap beside each label blocked at every candidate must hold for it: widen's first try, never a demand of a wire."""


@dataclass(frozen=True, slots=True)
class Refused:
    """A conductor no wire was drawn for; `ends` are its pins: two for a link or jog, one for a rise or a drop.

    A link of more than two ends names all of them. Each lost conductor is drawn as a reference at each
    end (ROUTE-FALLBACK-REFERENCE).
    """

    net: str
    ends: tuple[PinRef, ...] | None = None


@dataclass(frozen=True, slots=True)
class Routes:
    """failed lists the nets the router gave up on, each with the pins of its refused link."""

    pages: tuple[PageRoutes, ...]
    failed: tuple[Refused, ...] = ()
    findings: tuple[Finding, ...] = ()

    @property
    def labels(self) -> tuple[AnnexBox, ...]:
        """Every page's labels, page by page."""
        return tuple(a for p in self.pages for a in p.labels)


@dataclass(frozen=True, slots=True)
class Marker:
    """A reference at (x, y) on page, naming the far end.

    end is the pin the marker names: stage 4 fills it on the RefEnd, stage 8a copies it here.
    ref is the cut of the Ref the marker belongs to (-1: none): the ends of one Ref, and no others,
    are one pair or star, even when a fan has several Refs of one kind (R550).
    also is the RefEnd's: the other pins whose conductors the marker ends (BUNDLE).
    far is the RefEnd's: the far pins of the conductors the marker names, a line each (R1581).
    stand is the RefEnd's: PIN for a marker at its pin, so a lead wire runs to it (layout-0544).
    """

    net: str
    kind: MarkerKind
    page: int
    cell: str
    x: int
    y: int
    end: PinRef
    orient: Orientation = "R0"
    ref: int = -1
    also: tuple[PinRef, ...] = ()
    far: tuple[PinRef, ...] = ()
    stand: StandClass = StandClass.PIN


@dataclass(frozen=True, slots=True)
class Anchored:
    """An anchored item placed: its origin, turn, absolute outline, port point and lead on a page.

    `lead` runs from the pin to `port`.
    """

    sym: str
    pin: str
    page: int
    x: int
    y: int
    orient: Orientation
    outline: Box
    port: tuple[int, int]
    lead: tuple[tuple[int, int], tuple[int, int]]


@dataclass(frozen=True, slots=True)
class Outline:
    """One unit frame on a page: the frame key (a unit's render id), the hull box in G, and its run among the unit's frames there (R900, R1106)."""

    key: str
    page: int
    box: Box
    run: int


@dataclass(frozen=True, slots=True)
class Annotations:
    """The annexes (tags and the like), markers, wire labels and unit frames printed on the pages."""

    annexes: tuple[AnnexBox, ...] = ()
    markers: tuple[Marker, ...] = ()
    anchored: tuple[Anchored, ...] = ()
    outlines: tuple[Outline, ...] = ()


@dataclass(frozen=True, slots=True)
class Score:
    """The scorer's result: its penalty terms, page count, page fill and total Q."""

    P: tuple[tuple[str, int], ...]
    R: tuple[tuple[str, int], ...]
    X: int
    B: int
    D: int
    pages: int
    fill: tuple[float, ...]
    Q: float


@dataclass(frozen=True, slots=True)
class CoreLayout:
    """The placer core's full result: area, pages, placement, routes, text, score, findings.

    wired: each pin a wire or an anchored lead reaches, with its net (the empty net for an anchored lead), as `solve` computed them.
    drawn: the (pin, far pin) pairs drawn as a wire on their page, as the cut found them.
    """

    area: Size
    pages: tuple[PagePlan, ...]
    placement: Placement
    routes: Routes
    annotations: Annotations
    references: tuple[Ref, ...]
    wired: frozenset[tuple[PinRef, str]]
    score: Score | None = None
    findings: tuple[Finding, ...] = ()
    drawn: frozenset[tuple[PinRef, PinRef]] = frozenset()


@dataclass(frozen=True, slots=True)
class ScenePin:
    """One pin at its absolute place; side is the way a wire leaves, biased a chain-end pin.

    Pins of one node are one electrical point; box marks a movable-pin box pin.
    """

    pin: str
    x: int
    y: int
    side: Side
    net: str | None
    node: int | None
    biased: bool
    box: bool
    head: bool


@dataclass(frozen=True, slots=True)
class SceneBox:
    """attached: heads a column hung on a box pin. group: the strip it stands in."""

    sym: str
    page: int
    body: Box
    footprint: Box
    pins: tuple[ScenePin, ...]
    attached: bool
    group: str | None
    orient: Orientation


@dataclass(frozen=True, slots=True)
class SceneWire:
    """A wire polyline in the scene, with its net, page and kind."""

    net: str
    page: int
    points: tuple[XY, ...]
    kind: WireKind


@dataclass(frozen=True, slots=True)
class SceneMarker:
    """A printed reference at (x, y) on page; box and pin name the symbol pin it stands at."""

    net: str
    kind: MarkerKind
    page: int
    x: int
    y: int
    box: str
    pin: str
    cell: str
    side: Side


@dataclass(frozen=True, slots=True)
class SceneLabel:
    """A label in the scene: its owner, page, box and corner."""

    owner: str
    page: int
    box: Box
    corner: str


@dataclass(frozen=True, slots=True)
class Scene:
    """The scorer's input: boxes with pins, wire polylines, markers, skipped nets, page fill.

    `rails` names the nets the pair-cut score skips: a problem has none, a dump of today's engine
    names its fixed-level nets; fill is one fraction per page, or empty without rows.
    """

    area: Size
    pages: int
    boxes: tuple[SceneBox, ...]
    wires: tuple[SceneWire, ...]
    markers: tuple[SceneMarker, ...]
    rails: frozenset[str]
    fill: tuple[float, ...]
    labels: tuple[SceneLabel, ...]
    bands: tuple[tuple[int, tuple[tuple[int, int], ...]], ...]
    """(page, the (top, bottom) of each of its rows): P6 reads the row of a box here (layout-0294).

    A source that has no rows (a dump of today's engine) passes `()`: a page is one row.
    """


def _scene_box(p: Placed, facts: SceneFacts) -> SceneBox:
    pins = []
    for xy in p.pin_xy:
        f = facts.pins.get((p.sym, xy.pin))
        if f is None:
            msg = f"scene: {p.sym}.{xy.pin} is not a pin of the problem"
            raise CoreError(msg)
        side = f.sides[p.orient]
        head = (p.sym, xy.pin) in facts.heads
        pins.append(ScenePin(xy.pin, xy.x, xy.y, side, f.net, f.node, f.biased, f.box, head))
    return SceneBox(
        p.sym,
        p.page,
        p.body,
        p.footprint,
        tuple(pins),
        p.sym in facts.attached,
        facts.strips.get(p.sym),
        p.orient,
    )


def _scene_marker(m: Marker, facts: SceneFacts, orient: Mapping[str, Orientation]) -> SceneMarker:
    side = facts.pins[(m.end.sym, m.end.pin)].sides[orient[m.end.sym]]
    return SceneMarker(m.net, m.kind, m.page, m.x, m.y, m.end.sym, m.end.pin, m.cell, side)


def scene(layout: CoreLayout, problem: PlacementProblem, flow: FlowGraph) -> Scene:
    """Flatten a CoreLayout into the scorer's scene; the facts it lacks come from problem, flow."""
    facts = scene_facts(problem, flow)
    boxes = tuple(_scene_box(p, facts) for pg in layout.placement.pages for p in pg.placed)
    wires = tuple(SceneWire(w.net, w.page, w.points, w.kind) for pg in layout.routes.pages for w in pg.wires)
    orient = {b.sym: b.orient for b in boxes}
    markers = tuple(_scene_marker(m, facts, orient) for m in layout.annotations.markers)
    labels = tuple(SceneLabel(a.owner, a.page, a.box, a.spot) for a in layout.annotations.annexes)
    return Scene(
        layout.area,
        len(layout.pages),
        boxes,
        wires,
        markers,
        frozenset(),
        page_fill(layout),
        labels,
        tuple((pg.page, pg.bands) for pg in layout.placement.pages),
    )
