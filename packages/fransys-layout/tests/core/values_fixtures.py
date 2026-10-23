"""Hand-built contract values with every optional field set once, for the values tests."""

import dataclasses

from turn_fixtures import views_of

from fransys_layout.core import Annex, AnnexBox, Spot, outputs, values
from fransys_layout.core.outputs import (
    Anchored,
    Annotations,
    CoreLayout,
    Counts,
    Demand,
    Gap,
    PagePlacement,
    PageRoutes,
    PinXY,
    Placed,
    Placement,
    Refused,
    Routes,
    Scene,
    SceneBox,
    SceneLabel,
    SceneMarker,
    ScenePin,
    SceneTable,
    SceneWire,
    Score,
    Table,
    Trunk,
    Wire,
    WireLabel,
)
from fransys_layout.core.outputs import Marker as OutMarker
from fransys_layout.core.series_values import Parallel, Series
from fransys_layout.core.sym_values import Sym
from fransys_layout.core.values import (
    Anchor,
    Attach,
    BiasedEnd,
    Block,
    BlockList,
    Box,
    BoxSpec,
    Bundle,
    Cell,
    Column,
    CrossLink,
    CutResult,
    CycleSplit,
    End,
    Facts,
    Fan,
    Finding,
    FlowGraph,
    Hints,
    Lane,
    Net,
    PagePlan,
    PageSpec,
    PinRef,
    PlacementProblem,
    Pose,
    Ref,
    RefEnd,
    RefKind,
    RowPlan,
    Size,
    Unit,
)

BOX = Box(0, 0, 16, 32)
PIN = values.Pin("1", "N", 8, 0, 0, -1, 1)


def problem() -> PlacementProblem:
    pins = (PIN, values.Pin("2", "S", 8, 32, 1))
    row_footprint = Box(0, 0, 16, 16)
    box_sym = Sym(
        id="K1",
        group="G1",
        unit="U1",
        label=Size(24, 8),
        pins=pins,
        nodes=(("1",), ("2",)),
        views=views_of(BOX, BOX, BOX, pins, ("R0", "R180"), row_footprint=row_footprint),
        box=BoxSpec(("1", "2"), "N", 16, 8),
        row_group="RG",
        band=1,
        item="I1",
        child_of="K0",
        boundary_of="U2",
    )
    plain = dataclasses.replace(
        box_sym,
        id="K2",
        group=None,
        box=None,
        row_group=None,
        views=views_of(BOX, BOX, BOX, pins, ("R0", "R180")),
    )
    return PlacementProblem(
        area=Size(800, 600),
        symbols=(box_sym, plain),
        nets=(
            Net(
                "N1",
                (PinRef("K1", "1"), PinRef("K2", "1")),
                Bundle("B", 1),
                crosses_unit=True,
                label=Size(16, 8),
            ),
            Net("N2", (PinRef("K1", "2"), PinRef("K2", "2"))),
        ),
        facts=Facts(
            keep_whole=(frozenset({"K1", "K2"}),),
            units=(Unit("U1", "U0", (PinRef("K1", "1"),)),),
            mates=((PinRef("K1", "1"), PinRef("K2", "1")),),
            series=(Series(("K1", Parallel(("K2", Series(("K3", "K4")))))),),
        ),
        anchors=(Anchor(PinRef("K1", "1"), (("E", Pose("R90", (8, 0), BOX, (8, 0))),)),),
        hints=Hints(
            group_order=("G1",),
            break_before=frozenset({"G1"}),
            keep_together=(frozenset({"K1", "K2"}),),
            order_pairs=(("K1", "K2"),),
            chains=(("K1", "K2"),),
            draw_in=(("K1", "U1"),),
            sides=((PinRef("K1", "1"), "E"),),
        ),
        annexes=(Annex("K1", Size(16, 8), "tags", {"R0": (Spot("TL", "TL", 0, -8, "up", 8),)}),),
    )


def layout() -> CoreLayout:
    plan = PagePlan(1, "U1", (RowPlan(("C1",), ("b1",), 64),), forced_end=True, groups=("G1",))
    ends = (RefEnd(1, "C1", PinRef("K1", "1"), 0), RefEnd(2, None, None))
    return CoreLayout(
        area=Size(800, 600),
        pages=(plan,),
        placement=Placement(
            (
                PagePlacement(
                    1,
                    (Placed("K1", 1, 8, 8, "R0", BOX, BOX, (PinXY("1", 16, 8),)),),
                    (Gap("g1", 1, "C1", "C2", 0, 8, 2, 0, 64),),
                    (Trunk("F1", 1, 24, 0, 64, 2, 0),),
                    ((0, 64),),
                    ((0, 64),),
                    {"C1": (0, 64)},
                ),
            ),
            (Finding("PAGE_OVERFLOW", "too tall", 1, "K1"),),
        ),
        routes=Routes(
            (
                PageRoutes(
                    1,
                    (Wire("N1", 1, ((0, 0), (8, 0)), "routed", 2),),
                    (Demand("g1", 2),),
                    Counts(0, 1, 2, 8, 0),
                ),
            ),
            (Refused("N2", (PinRef("K1", "1"), PinRef("K2", "1"))),),
            (Finding("ROUTE_FAILED", "N2"),),
        ),
        annotations=Annotations(
            (AnnexBox("K1", 1, BOX, "TL"),),
            (Table("K1", 1, ("3C", "2:3C"), BOX, 1),),
            (OutMarker("N1", RefKind.TAG, 1, "3C", 4, 4, PinRef("K1", "1"), "R90"),),
            (WireLabel("N1", 1, BOX),),
            (Anchored("K1", "1", 1, 24, 8, "R90", BOX, (24, 8), ((16, 8), (24, 8))),),
        ),
        references=(Ref("N1", RefKind.ARROW, ends),),
        score=Score((("P1", 0),), (("R1", 1),), 1, 2, 3, 1, (0.5,), 4.5),
        findings=(Finding("LANE_TURNED", "turned", 1, "K1"),),
        wired=frozenset({(PinRef("K1", "1"), "N1")}),
    )


def flow_values() -> tuple[object, ...]:
    """The stage 1 to 4 values that no problem or layout holds, each with optionals set."""
    cell = Cell("K1", "R90", "1", "2")
    end = End("fan", "N1", PinRef("K1", "1"), "F1", 0)
    column = Column("C1", (Lane((cell,), 8),), (end,), (end,), 32, 16, (("n1",),))
    attach = Attach("C1", 0, 0, PinRef("K1", "1"), 1)
    fan = Fan("F1", ("N1",), (attach,), (attach,), "K1", 1, "E", (("K2", (1, 0)),), attach)
    block = Block(
        "b1",
        "card",
        "U1",
        ("C1",),
        "K1",
        "F1",
        "G1",
        64,
        32,
        short=True,
        keep_whole=True,
        forced_break_before=True,
        seat="beside",
        pin_edges=(("1", "N"),),
        fixed_order=True,
        rise=8,
    )
    finding = Finding("FILL_UNDER_MIN", "thin", 1, "p1")
    return (
        FlowGraph(
            (column,),
            (fan,),
            (CrossLink("N1", (attach,)),),
            (BiasedEnd("K1", "1", 0),),
            CycleSplit(1, 2, 3),
            ("K1",),
            (finding,),
        ),
        BlockList("U1", (block,), (finding,)),
        PageSpec(
            (
                PagePlan(
                    1, "U1", (RowPlan(("C1",), ("b1",), 64),), forced_end=False, groups=("G1",)
                ),
            ),
            (Ref("N1", RefKind.TAG, (RefEnd(1, "C1", None),)),),
            (finding,),
        ),
        CutResult(
            PageSpec((), ()),
            FlowGraph((), (), (), (), CycleSplit(0, 0, 0), ()),
            (BlockList("U1", ()),),
        ),
    )


def scene_value() -> Scene:
    """A scene with every optional field of the scene values set once."""
    pin = ScenePin("1", 16, 8, "N", "N1", 0, biased=True, box=True, head=True)
    box = SceneBox("K1", 1, BOX, BOX, (pin,), attached=True, strip="X1", orient="R180")
    return Scene(
        Size(800, 600),
        1,
        (box,),
        (SceneWire("N1", 1, ((0, 0), (8, 0)), 2, "trunk"),),
        (SceneMarker("N1", RefKind.TAG, 1, 4, 4, "K1", "1", "3C", "S"),),
        frozenset({"N1"}),
        (0.5,),
        (SceneLabel("K1", 1, BOX, "TL"),),
        (SceneTable("K1", 1, BOX, ("3C", "2:3C"), 1),),
        ((1, ((0, 16),)),),
    )


def all_values() -> tuple[object, ...]:
    return (problem(), layout(), *flow_values(), scene_value())


def modules() -> tuple[object, object]:
    return values, outputs
