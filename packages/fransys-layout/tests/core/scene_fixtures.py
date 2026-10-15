"""A planted two-page layout with its problem and flow, built through the contract dataclasses."""

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
    Wire,
)
from fransys_layout.core.outputs import Marker as OutMarker
from fransys_layout.core.values import (
    Box,
    BoxSpec,
    Cell,
    Column,
    CycleSplit,
    End,
    Fan,
    FlowGraph,
    Lane,
    Net,
    PagePlan,
    Pin,
    PinRef,
    PlacementProblem,
    Rail,
    Side,
    Size,
    Sym,
)

BODY = Box(-8, -16, 16, 32)


def sym(sid: str, pins: tuple[Pin, ...], **kw: object) -> Sym:
    return Sym(
        sid,
        None,
        "U1",
        sid,
        8,
        BODY,
        BODY,
        BODY,
        pins,
        tuple((p.id,) for p in pins),
        frozenset({"R0", "R180"}),
        **kw,  # ty: ignore[invalid-argument-type] -- optional Sym fields by name
    )


def pin(pid: str, side: Side, dy: int, node: int, stand: str | None = None) -> Pin:
    return Pin(pid, side, 0, dy, node, stand)  # ty: ignore[invalid-argument-type] -- Power literal


def problem() -> PlacementProblem:
    """K a box pin, A hung under it, F a fan head with a supply stand, T a strip terminal."""
    k = sym("K", (pin("c1", "S", 16, 0),), box=BoxSpec(("c1",), "N", 16, 8))
    a = sym("A", (pin("in", "N", -16, 0), pin("out", "S", 16, 1)))
    f = sym("F", (pin("out", "S", 16, 0), pin("p", "N", -16, 1, "SUPPLY")), row_group=None)
    t = sym("T", (pin("s", "S", 16, 0),), row_group="X1")
    return PlacementProblem(
        Size(100, 100),
        (k, a, f, t),
        (
            Net("n1", (PinRef("K", "c1"), PinRef("A", "in"))),
            Net("n2", (PinRef("F", "out"), PinRef("A", "out"), PinRef("T", "s"))),
            Net("n3", (PinRef("F", "p"),), Rail(0, "SUPPLY")),
        ),
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
    fan = Fan("F1", ("n2",), (), (), "F", 1, "E")
    return FlowGraph((column,), (fan,), (), (), CycleSplit(0, 0, 0), ("K", "A", "F", "T"))


def _placed(sid: str, page: int, x: int, y: int, orient: str, *pins: PinXY) -> Placed:
    body = Box(x - 8, y - 16, 16, 32)
    return Placed(sid, page, x, y, orient, body, body, pins)  # ty: ignore[invalid-argument-type] -- orient literal


def layout() -> CoreLayout:
    plans = tuple(PagePlan(i, "U1", (), forced_end=False, title="") for i in (1, 2))
    page1 = PagePlacement(
        1,
        (
            _placed("K", 1, 40, 30, "R0", PinXY("c1", 40, 46)),
            _placed("F", 1, 70, 30, "R0", PinXY("out", 70, 46), PinXY("p", 70, 14)),
        ),
        (),
        (),
        ((20, 50),),
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
    )
    wire = Wire("n2", 2, ((40, 14), (40, 4)), "straight", 1)
    return CoreLayout(
        Size(100, 100),
        plans,
        Placement((page1, page2)),
        Routes((PageRoutes(2, (wire,), (), Counts(0, 0, 0, 10, 0)),)),
        Annotations(
            markers=(OutMarker("n1", "tag", 2, "A", "K.c1", 0, 40, 46, PinRef("A", "in")),)
        ),
        (),
    )
