"""EF-C2 part 2: one wired set. A port on a net group, or on a conductor or net group dropped for
an undrawn end, is wired: its pin view is kept (R7 B5) and a PLC channel on it is a pin of its
module's box like an unwired one (V1, C2 is gone). Hand-built models, the helpers of
`test_board_internal.py`.
"""

import pytest

from fransys_layout.engines.schematic.read import read_inputs
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

_ORIGIN = Origin(file="tests/engines/test_read_wired.py", line=1, note="EF-C2 part 2 tests")


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


def _model(records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_a_pin_on_a_net_group_dropped_for_an_undrawn_end_keeps_its_view() -> None:
    """`X9` pins 1 and 2 share a net with `K1` on board `A1` (never drawn): the net group is
    dropped and reported, but both pins are still wired, so both keep their pin views."""
    board_part = _board_part("board-a")
    board = _item("board-a", designation="A1", part=board_part)
    k1 = _item("k1", designation="K1", parent=board)
    x9 = _item("x9", designation="X9")
    k1_fn = _function("k1", "coil", FunctionKind.COIL)
    x9_fn = _function("x9", "conn", FunctionKind.CONNECTOR)
    k1_p, x9_p1, x9_p2 = _port(k1_fn, "A1"), _port(x9_fn, "1"), _port(x9_fn, "2")
    net = _net("net-x9-k1", (k1_p, x9_p1, x9_p2))
    model = _model(
        (_pcb_facet(board_part), board_part, board, k1, x9, k1_fn, x9_fn, k1_p, x9_p1, x9_p2, net)
    )

    inputs = read_inputs(model)
    assert inputs.net_groups == ()
    assert len(inputs.read_findings) == 1
    assert {spec.function for spec in inputs.functions} == {x9_p1.id, x9_p2.id}


@pytest.mark.parametrize("wiring", ["net group", "net group with an undrawn end", "conductor"])
def test_a_plc_channel_wired_only_through_a_net_group_or_a_stranded_conductor_is_a_pin_of_its_box(
    wiring: str,
) -> None:
    """Module `DO1` has channels `do_1` and `do_2`; only `do_1` is wired, never by a kept
    conductor. Wired or not, both channels are pins of the module's one box (V1)."""
    board_part = _board_part("board-a")
    board = _item("board-a", designation="A1", part=board_part)
    module = _item("do", designation="DO1")
    drawn = _item("k1", designation="K1")
    hidden = _item("k2", designation="K2", parent=board)
    do_1, do_2 = (_function("do", name, FunctionKind.PLC_CHANNEL) for name in ("do_1", "do_2"))
    coil = _function("k1", "coil", FunctionKind.COIL)
    hidden_coil = _function("k2", "coil", FunctionKind.COIL)
    p1, p2 = _port(do_1, "1"), _port(do_2, "1")
    coil_a, hidden_a = _port(coil, "A1"), _port(hidden_coil, "A1")
    wire = {
        "net group": (_net("n", (p1, coil_a)),),
        "net group with an undrawn end": (_net("n", (p1, hidden_a)),),
        "conductor": (_conductor("c", p1, hidden_a),),
    }[wiring]
    model = _model(
        (
            _pcb_facet(board_part),
            board_part,
            board,
            module,
            drawn,
            hidden,
            do_1,
            do_2,
            coil,
            hidden_coil,
            p1,
            p2,
            coil_a,
            hidden_a,
            *wire,
        )
    )

    by_function = {spec.function: spec for spec in read_inputs(model).functions}
    assert do_1.id not in by_function
    assert do_2.id not in by_function
    box = by_function[module.id]
    assert box.kind == "item"
    assert {port.name for port in box.ports} == {"do_1.1", "do_2.1"}
    assert {port.port for port in box.ports} == {p1.id, p2.id}


def test_the_item_box_carries_the_item_view_and_channel_facts() -> None:
    """The box is the spec whose function is an item id: `roles.item_view` says so (RR-O1)."""
    module = _item("do", designation="DO1")
    do_1, do_2 = (_function("do", name, FunctionKind.PLC_CHANNEL) for name in ("do_1", "do_2"))
    p1, p2 = _port(do_1, "1"), _port(do_2, "1")
    model = _model((module, do_1, do_2, p1, p2))

    specs = read_inputs(model).functions
    assert [s.function for s in specs] == [module.id]
    assert specs[0].roles.item_view
    assert specs[0].roles.plc_channel
