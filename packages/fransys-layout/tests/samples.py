"""Hand-made, invented stage inputs shared by the acceptance tests (design/package-layout.md 9).

Stage tests build their inputs here, not from the model and not from the symbol
library, so a stage can be tested alone. All data is invented.
"""

import dataclasses
from typing import TYPE_CHECKING, Any, cast

from fransys_layout.engines.schematic.defaults import kind_roles
from fransys_layout.geometry import (
    Box,
    Facing,
    Orientation,
    Point,
    PortGeometry,
    SlotGeometry,
    SymbolGeometry,
    ThroughPath,
    port_page_at,
)
from fransys_layout.stages import (
    Cell,
    Column,
    Connection,
    DrawnFunction,
    DrawnPort,
    FunctionSpec,
    PageHints,
    PagePlan,
    PlacedFunction,
    PlannedColumn,
    PlannedGroup,
    PolePair,
    PortRef,
    PortSpec,
    Profile,
    Role,
    SheetFormat,
)
from fransys_layout.stages.references import CutLocations, links
from fransys_layout.stages.references.types import MarkerScene
from fransys_layout.stages.stacking import StackedPort
from fransys_layout.stages.texts.echoes import echo_requests
from fransys_layout.stages.texts.markers import link_markers, placed_world
from fransys_model.kernel import Id

if TYPE_CHECKING:
    from fransys_layout.stages.references.types import OffStubs

SHEET = SheetFormat(
    name="invented sheet", content_width=1280, content_height=886, frame_columns=8, frame_rows=6
)

PROFILE = Profile(
    column_gap=48,
    row_gap=32,
    row_spacing=104,
    text_height=8,
    marker_padding=0,  # 0 so the facing/position stage tests keep their unpadded box math
    band_ranks=frozendict({"protection": 1, "contact_no": 2, "load": 4}),
    group_ranks=frozendict({"power": 2, "control": 3}),
    route_turn_penalty=4,
    route_crossing_penalty=16,
    route_margin=64,
)

NO_HINTS = PageHints(keep_together=(), break_before=(), order=())


def hid(kind: str, number: int) -> Id[Any]:
    """An invented id of `kind`; equal `number`, equal id."""
    return Id(kind=kind, value=f"{number:032x}")


def through_geometry(key: str = "make-contact", *, half_height: int = 16) -> SymbolGeometry:
    """A vertical two-port symbol: `in` on top facing N, `out` below facing S, on x = 0."""
    return SymbolGeometry(
        key=key,
        poles=1,
        orientation=Orientation.R0,
        body=Box(x=-8, y=-half_height, width=16, height=2 * half_height),
        keepout=Box(x=-8, y=-half_height, width=56, height=2 * half_height),
        through=ThroughPath(start="in", end="out"),
        ports=(
            PortGeometry(name="in", at=Point(x=0, y=-half_height), facing=Facing.N),
            PortGeometry(name="out", at=Point(x=0, y=half_height), facing=Facing.S),
        ),
        slots=(
            SlotGeometry(
                slot="marking.in",
                at=Point(x=16, y=-12),
                side=Facing.E,
                box=Box(x=16, y=-16, width=16, height=8),
            ),
            SlotGeometry(
                slot="tag",
                at=Point(x=16, y=0),
                side=Facing.E,
                box=Box(x=16, y=-4, width=32, height=8),
            ),
        ),
    )


def function_spec(
    number: int,
    *,
    kind: str = "contact_no",
    group: int | None = 1,
    role: Role = Role.CONTROL,
) -> FunctionSpec:
    """Function `number` with model ports `13` and `14`, in `=` group `group`.

    Port `13` is on physical net `number - 1` and port `14` on net `number`, so
    functions with consecutive numbers are joined in series, as `connection` wires them.
    """
    return FunctionSpec(
        function=hid("function", number),
        item=hid("item", number),
        part=None,
        key=("invented", f"fn{number}"),
        kind=kind,
        category=None,
        poles=1,
        pole_pairs=(PolePair(index=0, first="13", second="14"),),
        ports=(
            PortSpec(
                port=hid("port", number * 10 + 1),
                name="13",
                physical_net=hid("net", number - 1),
                role=role,
            ),
            PortSpec(
                port=hid("port", number * 10 + 2),
                name="14",
                physical_net=hid("net", number),
                role=role,
            ),
        ),
        group_path=() if group is None else (hid("aspect_node", group),),
        location_path=(hid("aspect_node", 100),),
        group_hint=None,
        roles=kind_roles(kind),  # the engine stamps the roles; a hand-built spec does it here
    )


def drawn(number: int, *, kind: str = "contact_no") -> DrawnFunction:
    """Function `number` drawn as the through symbol: port `13` at `in`, `14` at `out`."""
    return DrawnFunction(
        function=hid("function", number),
        item=hid("item", number),
        key=("invented", f"fn{number}"),
        kind=kind,
        geometry=through_geometry(),
        ports=(
            DrawnPort(port=hid("port", number * 10 + 1), symbol_port="in"),
            DrawnPort(port=hid("port", number * 10 + 2), symbol_port="out"),
        ),
        primary_in="in",
        primary_out="out",
        roles=kind_roles(kind),
    )


def connection(number: int, upper: int, lower: int, *, role: Role = Role.CONTROL) -> Connection:
    """Conductor `number` from port `14` of function `upper` to port `13` of function `lower`."""
    return Connection(
        handle=hid("conductor", number),
        physical_net=hid("net", number),
        role=role,
        a=PortRef(function=hid("function", upper), port=hid("port", upper * 10 + 2)),
        b=PortRef(function=hid("function", lower), port=hid("port", lower * 10 + 1)),
    )


def column(name: str, numbers: tuple[int, ...], *, group: int | None = 1) -> Column:
    """A column named `name` whose cells are functions `numbers`, top to bottom."""
    return Column(
        key=("invented", name),
        cells=tuple(Cell(function=hid("function", n), index=i) for i, n in enumerate(numbers)),
        group=None if group is None else hid("aspect_node", group),
        role=Role.CONTROL,
        location=hid("aspect_node", 100),
    )


def page_plan(names: tuple[str, ...], *, number: int = 1, group: int = 1) -> PagePlan:
    """Page `number` of drawing set 1 holding the columns `names`, left to right."""
    return PagePlan(
        drawing_set=1,
        location=hid("aspect_node", 100),
        number=number,
        role=Role.CONTROL,
        title="Invented group",
        groups=(PlannedGroup(group=hid("aspect_node", group), index=0),),
        columns=tuple(
            PlannedColumn(column=("invented", name), index=i) for i, name in enumerate(names)
        ),
    )


def placed(number: int, *, x: int, y: int, page: int = 1, name: str = "a") -> PlacedFunction:
    """Function `number` placed with its origin at `(x, y)` on `page`."""
    return PlacedFunction(
        function=hid("function", number),
        drawing_set=1,
        page=page,
        column=("invented", name),
        at=Point(x=x, y=y),
        geometry=through_geometry(),
    )


def built_links(connections, net_groups, placed_functions, drawn_functions, **options):
    """`references.links` (S9's decisions), then what `texts` builds of them on the placed pages.

    Returns `(decisions, markers, cross-reference requests, findings)`: each marker decision
    built into its `LinkMarker` and each tag-echo cut into its `CROSS_REFERENCE` request, both
    read off `placed_functions` as the engine's `texts` reads the placed pages.
    """
    scene = MarkerScene(
        placed_functions,
        drawn_functions,
        options["sheet"],
        options["profile"],
        options.get("digits", frozendict()),
    )
    locations = CutLocations(options["location_paths"], options["units"], options["function_units"])
    decisions, markers, echoes, findings = links(connections, net_groups, scene, locations)
    built = link_markers(
        markers,
        placed_world(placed_functions, drawn_functions),
        wired=frozenset(),
        sheet=options["sheet"],
        profile=options["profile"],
    )
    requests = echo_requests(
        echoes,
        placed_functions,
        drawn_functions,
        sheet=options["sheet"],
        location_paths=options["location_paths"],
    )
    return decisions, built, requests, findings


def standing(scene: MarkerScene, off: OffStubs) -> OffStubs:
    """`off` with S14's stands and column order read off `scene`'s hand-built placements."""
    stands, order = stands_of(scene.seats, scene.drawn)
    return dataclasses.replace(off, stands=stands, order=order)


def built(scene: MarkerScene, decisions: tuple, *, wired: frozenset = frozenset()) -> tuple:
    """What `texts` builds of `decisions` on `scene`'s hand-built placements (S9)."""
    placed_functions = cast("tuple[PlacedFunction, ...]", scene.seats)
    return link_markers(
        decisions,
        placed_world(placed_functions, scene.drawn),
        wired=wired,
        sheet=scene.sheet,
        profile=scene.profile,
    )


def stands_of(placed_functions: tuple, drawn_functions: tuple) -> tuple:
    """S14's inputs read off hand-built placements, as `place` would stack those pages.

    `(stands, order)`: each drawn port's `StackedPort` by `(port, (set, page))` (its y as the
    offset, its x, its facing), and each page's columns left to right by their first placed x.
    """
    ports = {one.function: one.ports for one in drawn_functions}
    stands = {}
    firsts: dict = {}
    for one in placed_functions:
        page = (one.drawing_set, one.page)
        at = {g.name: g for g in one.geometry.ports}
        for port in ports[one.function]:
            g = at.get(port.symbol_port)
            if g is not None:
                spot = port_page_at(one.at, g)
                stands[port.port, page] = StackedPort(
                    row=0, offset=spot.y, x=spot.x, facing=g.facing
                )
        column = firsts.setdefault(page, {})
        column[one.column] = min(column.get(one.column, one.at.x), one.at.x)
    order = {
        page: tuple(sorted(columns, key=lambda key: columns[key]))
        for page, columns in firsts.items()
    }
    return stands, order
