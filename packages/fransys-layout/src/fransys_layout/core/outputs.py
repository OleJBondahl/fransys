"""Values of the placer core, output side: placement, routes, text, layout, score, scene."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .scene_facts import SceneFacts, page_fill, scene_facts

if TYPE_CHECKING:  # jsonform resolves these names from the module, so no run-time import
    from collections.abc import Mapping

    from .annex_values import AnnexBox
    from .values import (
        XY,
        Box,
        Finding,
        FlowGraph,
        MarkerKind,
        Orientation,
        PagePlan,
        PinRef,
        PlacementProblem,
        Ref,
        Side,
        Size,
        WireKind,
    )


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


@dataclass(frozen=True, slots=True)
class Placement:
    """The placement of every page, with the findings the placer raised."""

    pages: tuple[PagePlacement, ...]
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True, slots=True)
class Wire:
    """lanes > 1 is a bundle trunk."""

    net: str
    page: int
    points: tuple[XY, ...]
    kind: WireKind
    lanes: int = 1


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
    detour: int


@dataclass(frozen=True, slots=True)
class PageRoutes:
    """The routed wires, gap demand and counts of one page."""

    page: int
    wires: tuple[Wire, ...]
    demand: tuple[Demand, ...]
    counts: Counts


@dataclass(frozen=True, slots=True)
class Refused:
    """A net the router gave up on; `ends` are the two pins of the link it refused, if it has any.

    A link of more than two ends names its first two; a refusal that is no link (a trunk, a rise)
    names none. No refused net gets a tag in its place: the ERROR stands alone (R424).
    """

    net: str
    ends: tuple[PinRef, PinRef] | None = None


@dataclass(frozen=True, slots=True)
class Routes:
    """failed lists the nets the router gave up on, each with the pins of its refused link."""

    pages: tuple[PageRoutes, ...]
    failed: tuple[Refused, ...] = ()
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True, slots=True)
class Table:
    """A contact table printed beside a coil: its cells, box and tier."""

    coil: str
    page: int
    cells: tuple[str, ...]
    box: Box
    tier: int


@dataclass(frozen=True, slots=True)
class Marker:
    """A reference at (x, y) on page, naming the far end.

    end is the pin the marker names: stage 4 fills it on the RefEnd, stage 8a copies it here.
    """

    net: str
    kind: MarkerKind
    page: int
    cell: str
    x: int
    y: int
    end: PinRef
    orient: Orientation = "R0"


@dataclass(frozen=True, slots=True)
class WireLabel:
    """A net's name printed on a wire, at a box on one page."""

    net: str
    page: int
    box: Box


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
class Annotations:
    """The annexes (tags and the like), tables, markers and wire labels printed on the pages."""

    annexes: tuple[AnnexBox, ...] = ()
    tables: tuple[Table, ...] = ()
    markers: tuple[Marker, ...] = ()
    wire_labels: tuple[WireLabel, ...] = ()
    anchored: tuple[Anchored, ...] = ()


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

    wired: each wired pin with its net, as `solve` computed them with its Options.
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
    """attached: heads a column hung on a box pin. strip: its strip."""

    sym: str
    page: int
    body: Box
    footprint: Box
    pins: tuple[ScenePin, ...]
    attached: bool
    strip: str | None
    orient: Orientation


@dataclass(frozen=True, slots=True)
class SceneWire:
    """A wire polyline in the scene, with its net, page, lane count and kind."""

    net: str
    page: int
    points: tuple[XY, ...]
    lanes: int
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
class SceneTable:
    """A contact table in the scene: its coil, page, box, cells and tier."""

    coil: str
    page: int
    box: Box
    cells: tuple[str, ...]
    tier: int


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
    tables: tuple[SceneTable, ...]
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
            raise ValueError(msg)
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
    wires = tuple(
        SceneWire(w.net, w.page, w.points, w.lanes, w.kind)
        for pg in layout.routes.pages
        for w in pg.wires
    )
    orient = {b.sym: b.orient for b in boxes}
    markers = tuple(_scene_marker(m, facts, orient) for m in layout.annotations.markers)
    labels = tuple(SceneLabel(a.owner, a.page, a.box, a.spot) for a in layout.annotations.annexes)
    tables = tuple(
        SceneTable(t.coil, t.page, t.box, t.cells, t.tier) for t in layout.annotations.tables
    )
    return Scene(
        layout.area,
        len(layout.pages),
        boxes,
        wires,
        markers,
        frozenset(),
        page_fill(layout),
        labels,
        tables,
        tuple((pg.page, pg.bands) for pg in layout.placement.pages),
    )
