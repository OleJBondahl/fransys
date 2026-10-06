"""Layout-0044 (spec B2, amended): board-internal connections/net groups are skipped
silently, whether or not their ends are drawn; a mixed one is not drawn and reports
`CONNECTION_TO_UNDRAWN`. Hand-built models, board `A1`'s own edge connectors included, so
every case is proven directly, not inferred from `layout_cabinet.py`'s shared fixture. Each
test builds only its own scenario, so one test's finding cannot leak into another's.

Deep dive D8: a connector is drawn as one view per wired pin (the view's handle is the pin's
port), and an idle connector is not drawn. A connection or net group dropped as board-internal
leaves its pins idle, so a test that used to see the connector drawn now sees no function at all.
"""

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.lint.codes import ALL_CODES, CONNECTION_TO_UNDRAWN
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab import (
    Conductor,
    ConductorKind,
    Function,
    FunctionKind,
    Item,
    Net,
    NetClass,
    Part,
    PartCategory,
    PcbFacet,
    Port,
    PortRole,
)
from fransys_model.vocab.tables import conductors as conductors_table

_ORIGIN = Origin(file="tests/engines/test_board_internal.py", line=1, note="layout-0044 tests")


def _board_part(key: str) -> Part:
    return Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.BOARD,
        class_code="A",
    )


def _pcb_facet(part: Part) -> PcbFacet:
    key = (*part.key, "pcb")
    return PcbFacet(id=make_id(PcbFacet, key), key=key, subject=part.id, revision="A")


def _item(
    key: str, *, designation: str, parent: Item | None = None, part: Part | None = None
) -> Item:
    return Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=None if part is None else part.id,
        parent=None if parent is None else parent.id,
        position=None,
        tag=designation,
        description="",
        installed=True,
    )


def _function(item_key: str, name: str, kind: FunctionKind) -> Function:
    key = (item_key, "fn", name)
    return Function(
        id=make_id(Function, key),
        key=key,
        item=make_id(Item, (item_key,)),
        template=None,
        name=name,
        kind=kind,
    )


def _port(function: Function, name: str) -> Port:
    key = (*function.key, name)
    return Port(
        id=make_id(Port, key),
        key=key,
        function=function.id,
        template=None,
        name=name,
        role=PortRole.GENERIC,
    )


def _conductor(key: str, a: Port, b: Port) -> Conductor:
    return Conductor(
        id=make_id(Conductor, (key,)),
        key=(key,),
        a=a.id,
        b=b.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def _net(key: str, ports: tuple[Port, ...]) -> Net:
    return Net(
        id=make_id(Net, (key,)),
        key=(key,),
        name=None,
        net_class=NetClass.CONTROL,
        ports=tuple(sorted(p.id for p in ports)),
    )


def test_the_code_is_listed() -> None:
    """It is one of the package's codes, so `ALL_CODES` and its scan test know it."""
    assert CONNECTION_TO_UNDRAWN in ALL_CODES


def test_a_net_group_wholly_on_one_board_is_skipped_with_no_finding() -> None:
    """`X1`-`X2`, a declared net with no conductor, both connectors on `A1`."""
    board_part = _board_part("board-a")
    board = _item("board-a", designation="A1", part=board_part)
    x1 = _item("x1", designation="X1", parent=board)
    x2 = _item("x2", designation="X2", parent=board)
    x1_fn = _function("x1", "conn", FunctionKind.CONNECTOR)
    x2_fn = _function("x2", "conn", FunctionKind.CONNECTOR)
    x1_p1, x2_p1 = _port(x1_fn, "1"), _port(x2_fn, "1")
    net = _net("net-x1-x2", (x1_p1, x2_p1))

    draft = Draft()
    draft.extend(
        (_pcb_facet(board_part), board_part, board, x1, x2, x1_fn, x2_fn, x1_p1, x2_p1, net),
        origin=_ORIGIN,
    )
    model = freeze(draft)
    assert len(model.tables["net"]) == 1, "the fixture has a net to examine"

    inputs = read_inputs(model)
    assert inputs.net_groups == ()
    assert inputs.read_findings == ()
    # D8: the dropped net was the only wiring of both pins, so both connectors are idle
    assert inputs.functions == ()


def test_a_drawn_connector_to_an_undrawn_relay_on_one_board_is_skipped_with_no_finding() -> None:
    """`X1`-`K1`: `X1` (connector) and `K1` (relay, never drawn), both on `A1`."""
    board_part = _board_part("board-a")
    board = _item("board-a", designation="A1", part=board_part)
    x1 = _item("x1", designation="X1", parent=board)
    k1 = _item("k1", designation="K1", parent=board)
    x1_fn = _function("x1", "conn", FunctionKind.CONNECTOR)
    k1_fn = _function("k1", "coil", FunctionKind.COIL)
    x1_p1, k1_p1 = _port(x1_fn, "1"), _port(k1_fn, "A1")
    conductor = _conductor("cond-x1-k1", x1_p1, k1_p1)

    draft = Draft()
    draft.extend(
        (_pcb_facet(board_part), board_part, board, x1, k1, x1_fn, k1_fn, x1_p1, k1_p1, conductor),
        origin=_ORIGIN,
    )
    model = freeze(draft)
    assert len(conductors_table(model)) == 1, "the fixture has a conductor to examine"

    inputs = read_inputs(model)
    assert inputs.connections == ()
    assert inputs.read_findings == ()
    # D8: the dropped conductor was `X1`'s only wiring, so `X1` is idle; `K1` is never drawn
    assert inputs.functions == ()


def test_a_cabinet_connector_to_a_board_relay_gets_exactly_one_connection_to_undrawn() -> None:
    """`X9` (off any board, drawn) to `K1` (on `A1`, undrawn): not board-internal."""
    board_part = _board_part("board-a")
    board = _item("board-a", designation="A1", part=board_part)
    k1 = _item("k1", designation="K1", parent=board)
    x9 = _item("x9", designation="X9")
    k1_fn = _function("k1", "coil", FunctionKind.COIL)
    x9_fn = _function("x9", "conn", FunctionKind.CONNECTOR)
    k1_p1, x9_p1 = _port(k1_fn, "A1"), _port(x9_fn, "1")
    conductor = _conductor("cond-x9-k1", x9_p1, k1_p1)

    draft = Draft()
    draft.extend(
        (_pcb_facet(board_part), board_part, board, k1, x9, k1_fn, x9_fn, k1_p1, x9_p1, conductor),
        origin=_ORIGIN,
    )
    model = freeze(draft)
    assert len(conductors_table(model)) == 1, "the fixture has a conductor to examine"

    inputs = read_inputs(model)
    # D8: X9 is drawn as one view per wired pin, the view's handle the pin's port
    assert {spec.function: spec.pin_function for spec in inputs.functions} == {x9_p1.id: x9_fn.id}
    assert inputs.connections == ()
    assert len(inputs.read_findings) == 1
    (finding,) = inputs.read_findings
    assert finding.code == CONNECTION_TO_UNDRAWN
    assert finding.subjects == (k1_p1.id,)


def test_drawn_connectors_on_two_different_boards_are_kept() -> None:
    """`X1` (`A1`) to `Y1` (`A2`): two different boards share no common ancestor."""
    board_a_part, board_b_part = _board_part("board-a"), _board_part("board-b")
    board_a = _item("board-a", designation="A1", part=board_a_part)
    board_b = _item("board-b", designation="A2", part=board_b_part)
    x1 = _item("x1", designation="X1", parent=board_a)
    y1 = _item("y1", designation="Y1", parent=board_b)
    x1_fn = _function("x1", "conn", FunctionKind.CONNECTOR)
    y1_fn = _function("y1", "conn", FunctionKind.CONNECTOR)
    x1_p1, y1_p1 = _port(x1_fn, "1"), _port(y1_fn, "1")
    conductor = _conductor("cond-x1-y1", x1_p1, y1_p1)

    draft = Draft()
    draft.extend(
        (
            _pcb_facet(board_a_part),
            _pcb_facet(board_b_part),
            board_a_part,
            board_b_part,
            board_a,
            board_b,
            x1,
            y1,
            x1_fn,
            y1_fn,
            x1_p1,
            y1_p1,
            conductor,
        ),
        origin=_ORIGIN,
    )
    model = freeze(draft)

    inputs = read_inputs(model)
    # D8: one view per wired pin, its handle the pin's port, its `pin_function` the connector
    views = {spec.function: spec.pin_function for spec in inputs.functions}
    assert views == {x1_p1.id: x1_fn.id, y1_p1.id: y1_fn.id}
    handles = {c.handle for c in inputs.connections}
    assert conductor.id in handles
    assert inputs.read_findings == ()
