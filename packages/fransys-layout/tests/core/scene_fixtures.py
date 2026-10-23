"""A planted two-page layout with its problem and flow, built through the contract dataclasses."""

from options_fixtures import core_options
from turn_fixtures import ALL_EIGHT, views_of

from fransys_layout.core import AnnexBox
from fransys_layout.core.outputs import (
    Annotations,
    CoreLayout,
    Counts,
    PagePlacement,
    PageRoutes,
    PinXY,
    Placed,
    Placement,
    Routes,
    Table,
    Wire,
)
from fransys_layout.core.outputs import Marker as OutMarker
from fransys_layout.core.sym_values import Sym
from fransys_layout.core.values import (
    Attach,
    Box,
    BoxSpec,
    Cell,
    Column,
    CycleSplit,
    End,
    Facts,
    Fan,
    FlowGraph,
    Lane,
    Net,
    PagePlan,
    Pin,
    PinRef,
    PlacementProblem,
    RefKind,
    Side,
    Size,
)

BODY = Box(-8, -16, 16, 32)


def sym(sid: str, pins: tuple[Pin, ...], **kw: object) -> Sym:
    return Sym(
        sid,
        None,
        "U1",
        Size(8, 8),
        pins,
        tuple((p.id,) for p in pins),
        views=views_of(BODY, BODY, BODY, pins, ALL_EIGHT),
        **kw,  # ty: ignore[invalid-argument-type] -- optional Sym fields by name
    )


def pin(pid: str, side: Side, dy: int, node: int, end_bias: int = 0) -> Pin:
    return Pin(pid, side, 0, dy, node, end_bias)


OPTIONS = core_options(
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    parallel_pitch=48,
    driver_first=True,
    arrow_sides=("E", "W"),
)


def problem() -> PlacementProblem:
    """K a box pin, A hung under it, F a fan head with a supply stand, T a strip terminal."""
    k = sym("K", (pin("c1", "S", 16, 0),), box=BoxSpec(("c1",), "N", 16, 8))
    a = sym("A", (pin("in", "N", -16, 0), pin("out", "S", 16, 1)))
    f = sym("F", (pin("out", "S", 16, 0), pin("p", "N", -16, 1, -1)), row_group=None)
    t = sym("T", (pin("s", "S", 16, 0),), row_group="X1")
    return PlacementProblem(
        Size(100, 100),
        (k, a, f, t),
        (
            Net("n1", (PinRef("K", "c1"), PinRef("A", "in"))),
            Net("n2", (PinRef("F", "out"), PinRef("A", "out"), PinRef("T", "s"))),
        ),
        Facts(),
    )


def flow() -> FlowGraph:
    column = Column(
        "C1",
        (Lane((Cell("A", "R180", "in", "out"),), 0),),
        (End("boxpin", "n1", PinRef("K", "c1")),),
        (End("open"),),
        32,
        16,
    )
    driver = Attach(None, 0, 0, PinRef("F", "out"), net="n")
    fan = Fan("F1", ("n2",), (driver,), (), "F", 1, "E", head=driver)
    return FlowGraph((column,), (fan,), (), (), CycleSplit(0, 0, 0), ("K", "A", "F", "T"))


def _placed(sid: str, page: int, x: int, y: int, orient: str, *pins: PinXY) -> Placed:
    body = Box(x - 8, y - 16, 16, 32)
    return Placed(sid, page, x, y, orient, body, body, pins)  # ty: ignore[invalid-argument-type] -- orient literal


def layout() -> CoreLayout:
    plans = tuple(PagePlan(i, "U1", (), forced_end=False, groups=()) for i in (1, 2))
    page1 = PagePlacement(
        1,
        (
            _placed("K", 1, 40, 30, "R0", PinXY("c1", 40, 46)),
            _placed("F", 1, 70, 30, "R0", PinXY("out", 70, 46), PinXY("p", 70, 14)),
        ),
        (),
        (),
        ((20, 50),),
        ((0, 30),),
    )
    page2 = PagePlacement(
        2,
        (
            _placed("A", 2, 40, 30, "R180", PinXY("in", 40, 46), PinXY("out", 40, 14)),
            _placed("T", 2, 70, 30, "R0", PinXY("s", 70, 46)),
        ),
        (),
        (),
        (),
        (),
    )
    wire = Wire("n2", 2, ((40, 14), (40, 4)), "riser")
    return CoreLayout(
        Size(100, 100),
        plans,
        Placement((page1, page2)),
        Routes((PageRoutes(2, (wire,), (), Counts(0, 0, 0, 10, 0)),)),
        Annotations(
            annexes=(AnnexBox("K", 1, Box(1, 2, 3, 4), "BR"),),
            tables=(Table("K", 1, ("3C", "2:3C"), Box(5, 6, 7, 8), 2),),
            markers=(OutMarker("n1", RefKind.TAG, 2, "C3", 40, 46, PinRef("A", "in")),),
        ),
        (),
        frozenset(),
    )
