"""A planted two-page layout with its problem and flow, built through the contract dataclasses."""

from typing import Any

from options_fixtures import core_options
from turn_fixtures import ALL_EIGHT, views_of

from fransys_layout.core import AnnexBox, Orientation
from fransys_layout.core.flow_values import Attach, Cell, Column, End, Fan, FlowGraph, Lane
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
from fransys_layout.core.sym_values import Sym
from fransys_layout.core.values import Box, BoxSpec, Facts, Net, PagePlan, Pin, PinRef, PlacementProblem, RefKind, Side, Size

BODY = Box(-8, -16, 16, 32)


def sym(sid: str, pins: tuple[Pin, ...], **kw: Any) -> Sym:
    return Sym(
        sid,
        None,
        "U1",
        {"": Size(8, 8)},
        pins,
        tuple((p.id,) for p in pins),
        views=views_of(BODY, BODY, BODY, pins, ALL_EIGHT),
        **kw,
    )


def pin(pid: str, side: Side, dy: int, node: int, end_bias: int = 0) -> Pin:
    return Pin(pid, side, 0, dy, node, end_bias)


OPTIONS = core_options()


def problem() -> PlacementProblem:
    """K a box pin, A hung under it, F a fan head with a supply stand, T a strip terminal."""
    k = sym("K", (pin("c1", "S", 16, 0),), box=BoxSpec(("c1",), 8, 16))
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
        (End("boxpin", "n1", PinRef("K", "c1"), lane=0),),
        (End("open"),),
        32,
        16,
    )
    driver = Attach(None, 0, 0, PinRef("F", "out"), net="n")
    fan = Fan("F1", ("n2",), (driver,), (), "F", 1, "E", head=driver)
    return FlowGraph((column,), (fan,), (), (), ("K", "A", "F", "T"))


def _placed(sid: str, page: int, x: int, y: int, orient: Orientation, *pins: PinXY) -> Placed:
    body = Box(x - 8, y - 16, 16, 32)
    return Placed(sid, page, x, y, orient, body, body, pins)


def layout() -> CoreLayout:
    plans = tuple(PagePlan(i, "U1", (), groups=()) for i in (1, 2))
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
        Routes((PageRoutes(2, (wire,), (), Counts(0, 0, 0, 10), (), (), ()),)),
        Annotations(
            annexes=(AnnexBox("K", 1, Box(1, 2, 3, 4), "BR"),),
            markers=(OutMarker("n1", RefKind.TAG, 2, "C3", 40, 46, PinRef("A", "in")),),
        ),
        (),
        frozenset(),
    )
