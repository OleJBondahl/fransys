"""Values of the placer core, output side: placement, routes, text, layout, score, scene."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .geometry import rotate_side
from .scene_facts import SceneFacts, page_fill, scene_facts

if TYPE_CHECKING:  # jsonform resolves these names from the module, so no run-time import
    from collections.abc import Mapping

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
    page: int
    placed: tuple[Placed, ...]
    gaps: tuple[Gap, ...]
    trunks: tuple[Trunk, ...]
    rows: tuple[tuple[int, int], ...]
    """(height, width) of each row, in G."""
    bands: tuple[tuple[int, int], ...]
    """(top, bottom) of each row in grid units, in row order."""


@dataclass(frozen=True, slots=True)
class Placement:
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
    gap: str
    tracks: int


@dataclass(frozen=True, slots=True)
class Counts:
    crossings: int
    bends: int
    excess: int
    length: int
    detour: int


@dataclass(frozen=True, slots=True)
class PageRoutes:
    page: int
    wires: tuple[Wire, ...]
    demand: tuple[Demand, ...]
    counts: Counts


@dataclass(frozen=True, slots=True)
class Routes:
    """failed lists the net ids the router gave up on."""

    pages: tuple[PageRoutes, ...]
    failed: tuple[str, ...] = ()
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True, slots=True)
class Label:
    owner: str
    page: int
    box: Box
    corner: str


@dataclass(frozen=True, slots=True)
class Table:
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
    net: str
    page: int
    box: Box


@dataclass(frozen=True, slots=True)
class Annotations:
    labels: tuple[Label, ...] = ()
    tables: tuple[Table, ...] = ()
    markers: tuple[Marker, ...] = ()
    wire_labels: tuple[WireLabel, ...] = ()


@dataclass(frozen=True, slots=True)
class Score:
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
    area: Size
    pages: tuple[PagePlan, ...]
    placement: Placement
    routes: Routes
    annotations: Annotations
    references: tuple[Ref, ...]
    score: Score | None = None
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True, slots=True)
class ScenePin:
    """One pin at its absolute place; side is the way a wire leaves, stand a drawn supply stand.

    Pins of one node are one electrical point; box marks a movable-pin box pin.
    """

    pin: str
    x: int
    y: int
    side: Side
    net: str | None
    node: int | None
    stand: bool
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
    owner: str
    page: int
    box: Box
    corner: str


@dataclass(frozen=True, slots=True)
class SceneTable:
    coil: str
    page: int
    box: Box
    cells: tuple[str, ...]
    tier: int


@dataclass(frozen=True, slots=True)
class Scene:
    """The scorer's input: boxes with pins, wire polylines, markers, supply rails, page fill.

    rails names the nets that carry a declared supply; fill is one fraction per page, or empty
    when the source (a dump of today's engine) has no rows.
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
        side = rotate_side(f.side, p.orient)
        head = (p.sym, xy.pin) in facts.heads
        pins.append(ScenePin(xy.pin, xy.x, xy.y, side, f.net, f.node, f.stand, f.box, head))
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
    side = rotate_side(facts.pins[(m.end.sym, m.end.pin)].side, orient[m.end.sym])
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
    labels = tuple(SceneLabel(a.owner, a.page, a.box, a.corner) for a in layout.annotations.labels)
    tables = tuple(
        SceneTable(t.coil, t.page, t.box, t.cells, t.tier) for t in layout.annotations.tables
    )
    return Scene(
        layout.area,
        len(layout.pages),
        boxes,
        wires,
        markers,
        facts.rails,
        page_fill(layout),
        labels,
        tables,
        tuple((pg.page, pg.bands) for pg in layout.placement.pages),
    )
