"""Hand-built contract values with every optional field set once, for the values tests."""

import dataclasses

from fransys_layout.core import outputs, values
from fransys_layout.core.outputs import (
    Annotations,
    CoreLayout,
    Counts,
    Demand,
    Gap,
    Label,
    PagePlacement,
    PageRoutes,
    PinXY,
    Placed,
    Placement,
    Routes,
    Scene,
    SceneBox,
    SceneMarker,
    ScenePin,
    SceneWire,
    Score,
    Table,
    Trunk,
    Wire,
)
from fransys_layout.core.outputs import Marker as OutMarker
from fransys_layout.core.values import (
    Attach,
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
    Rail,
    Ref,
    RefEnd,
    RowPlan,
    Size,
    Stand,
    Sym,
    Unit,
)

BOX = Box(0, 0, 16, 32)
PIN = values.Pin("1", "N", 8, 0, 0, "SUPPLY")


def problem() -> PlacementProblem:
    box_sym = Sym(
        id="K1",
        group="G1",
        unit="U1",
        text="=K1",
        text_w=24,
        body=BOX,
        keepout=BOX,
        footprint=BOX,
        pins=(PIN, values.Pin("2", "S", 8, 32, 1)),
        nodes=(("1",), ("2",)),
        orientations=frozenset({"R0", "R180"}),
        box=BoxSpec(("1", "2"), "N", 16, 8),
        row_footprint=Box(0, 0, 16, 16),
        row_group="RG",
        band=1,
        item="I1",
        child_of="K0",
        table_rows=2,
        boundary_of="U2",
    )
    plain = dataclasses.replace(
        box_sym, id="K2", group=None, box=None, row_footprint=None, row_group=None
    )
    return PlacementProblem(
        area=Size(800, 600),
        symbols=(box_sym, plain),
        nets=(
            Net(
                "N1",
                (PinRef("K1", "1"), PinRef("K2", "1")),
                Rail(0, "SUPPLY"),
                Bundle("B", 1),
                crosses_unit=True,
            ),
            Net("N2", (PinRef("K1", "2"), PinRef("K2", "2"))),
        ),
        facts=Facts(
            keep_whole=(frozenset({"K1", "K2"}),),
            units=(Unit("U1", "U0", (PinRef("K1", "1"),)),),
            mates=((PinRef("K1", "1"), PinRef("K2", "1")),),
        ),
        hints=Hints(
            group_order=("G1",),
            break_before=frozenset({"G1"}),
            keep_together=(frozenset({"K1", "K2"}),),
            order_pairs=(("K1", "K2"),),
            chains=(("K1", "K2"),),
            draw_in=(("K1", "U1"),),
            sides=((PinRef("K1", "1"), "E"),),
            page_titles=(("U1", "Power"),),
        ),
    )


def layout() -> CoreLayout:
    plan = PagePlan(1, "U1", (RowPlan(("C1",), ("b1",), 64),), forced_end=True, title="Power")
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
                    (Trunk("F1", 1, 24, 0, 64, 2),),
                    ((0, 64),),
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
            ("N2",),
            (Finding("ROUTE_FAILED", "N2"),),
        ),
        annotations=Annotations(
            (Label("K1", 1, "=K1", BOX, "TL"),),
            (Table("K1", 1, ("a", "b"), BOX, 1),),
            (OutMarker("N1", "tag", 1, "K1", "1/3", 2, 4, 4, PinRef("K1", "1")),),
        ),
        references=(Ref("N1", "arrow", ends),),
        score=Score((("P1", 0),), (("R1", 1),), 1, 2, 3, 1, (0.5,), 4.5),
        findings=(Finding("LANE_TURNED", "turned", 1, "K1"),),
    )


def flow_values() -> tuple[object, ...]:
    """The stage 1 to 4 values that no problem or layout holds, each with optionals set."""
    cell = Cell("K1", "R90", "1", "2")
    end = End("fan", "N1", PinRef("K1", "1"), "SUPPLY", "F1", 0)
    column = Column("C1", (Lane((cell,), 8),), (end,), (end,), 32, 16)
    attach = Attach("C1", 0, 0, PinRef("K1", "1"))
    fan = Fan("F1", ("N1",), (attach,), (attach,), "K1", 1, "E", (("K2", (1, 0)),))
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
        pin_edges=(("1", "N"),),
        fixed_order=True,
    )
    finding = Finding("FILL_UNDER_MIN", "thin", 1, "p1")
    return (
        FlowGraph(
            (column,),
            (fan,),
            (CrossLink("N1", (attach,)),),
            (Stand("K1", "1", "SUPPLY", 0),),
            CycleSplit(1, 2, 3),
            ("K1",),
        ),
        BlockList("U1", (block,), (finding,)),
        PageSpec(
            (PagePlan(1, "U1", (RowPlan(("C1",), ("b1",), 64),), forced_end=False, title="T"),),
            (Ref("N1", "tag", (RefEnd(1, "C1", None),)),),
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
    pin = ScenePin("1", 16, 8, "N", "N1", 0, stand=True, box=True)
    box = SceneBox("K1", 1, BOX, BOX, (pin,), attached=True, head=True, strip="X1")
    return Scene(
        Size(800, 600),
        1,
        (box,),
        (SceneWire("N1", 1, ((0, 0), (8, 0)), 2),),
        (SceneMarker("N1", "tag", 1, 4, 4, "K1", "1"),),
        frozenset({"N1"}),
        (0.5,),
    )


def all_values() -> tuple[object, ...]:
    return (problem(), layout(), *flow_values(), scene_value())


def modules() -> tuple[object, object]:
    return values, outputs
