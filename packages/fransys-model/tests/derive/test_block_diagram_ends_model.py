"""`end_box`, `diagram_lines` and `diagram_facts` (BLOCK-DIAGRAMS BD1 to BD3).

Invented plants: a top-level device, a unit instance `U1` holding a strip and a connector, a
nested board unit, and top-level cables between them.
"""

from cable_drawing_builders import cable, device
from plant import Plant
from query_builders import make_core

from fransys_model.derive.block_diagram import (
    DIAGRAM_CABLE_FANOUT,
    DIAGRAM_CABLE_ONE_BOX,
    DIAGRAM_LOOSE_WIRE,
    BoxEnd,
    box_order,
    diagram_facts,
    diagram_lines,
    end_box,
)
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item


def _core(plant: Plant, key: str, carrier, a, b) -> None:
    """A core of `carrier` between ports `a` and `b`; the index is the key's last number."""
    make_core(plant, key, carrier, (a, b), index=int(key.rsplit("-", 1)[1]))


def _unit(plant: Plant, key: str, *, tag: str | None, parent=None):
    return plant.unit(key, tag=tag, parent=parent)


def _plug_to(plant: Plant, cable_id, key: str, mated_key: str):
    """A plug `key` of `cable_id`, mated to the connector function of item `mated_key`."""
    plug, ports = device(plant, key, key.upper(), "1", parent=cable_id)
    plant.mate(plant.function_id(key, "f"), plant.function_id(mated_key, "f"), key=f"mate-{key}")
    return plug, ports


def _station():
    """Top-level motor `M1`; unit `U1` with strip `X1`, connector `C1` and a child board unit."""
    plant = Plant()
    cabinet = _unit(plant, "u1", tag="U1")
    board = _unit(plant, "board", tag=None, parent=cabinet)
    motor, motor_ports = device(plant, "m1", "M1", "U", "V", external=True)
    strip, strip_ports = device(plant, "x1", "X1", "1", "2", unit=cabinet)
    conn, conn_ports = device(plant, "c1", "C1", "1", unit=cabinet)
    inner, inner_ports = device(plant, "inner", "A1", "1", unit=board)
    return (
        plant,
        cabinet,
        board,
        (motor, motor_ports),
        (strip, strip_ports),
        (conn, conn_ports),
        (
            inner,
            inner_ports,
        ),
    )


def test_a_cable_from_a_top_level_item_to_a_unit_strip_is_one_system_line() -> None:
    """The motor box and the cabinet's instance box; the strip's end reaches the instance."""
    plant, cabinet, _, (motor, mp), (strip, sp), *_ = _station()
    w1 = cable(plant, "w1", "W1")
    _core(plant, "w1-1", w1, mp["U"], sp["1"])
    model = plant.model()
    assert end_box(model, sp["1"], None) == BoxEnd(box=cabinet, landed=strip, anchored=False)
    assert end_box(model, mp["U"], None) == BoxEnd(box=motor, landed=motor, anchored=False)
    (line,) = diagram_lines(model, None)
    assert (line.cable, {line.a, line.b}, line.designation) == (w1, {motor, cabinet}, "-W1")
    assert diagram_facts(model, None) == ()


def test_a_plug_crosses_its_mate_to_the_connector_item_and_the_box_around_it() -> None:
    """`-W3`'s plug mates `C1` of the cabinet: the line reaches the cabinet through the mate."""
    plant, cabinet, _, (motor, mp), _, (conn, _), _ = _station()
    w3 = cable(plant, "w3", "W3")
    _plug, plug_ports = _plug_to(plant, w3, "p3", "c1")
    _core(plant, "w3-1", w3, mp["V"], plug_ports["1"])
    model = plant.model()
    assert end_box(model, plug_ports["1"], None) == BoxEnd(box=cabinet, landed=conn, anchored=True)
    (line,) = diagram_lines(model, None)
    assert {line.a, line.b} == {motor, cabinet}


def test_an_unmated_plug_reaches_no_box_so_its_cable_runs_inside_one_box() -> None:
    """No mate: the end reaches nothing, one box remains, `DIAGRAM_CABLE_ONE_BOX` fires."""
    plant, _, _, (_, mp), *_ = _station()
    w3 = cable(plant, "w3", "W3")
    _plug, plug_ports = device(plant, "p3", "P3", "1", parent=w3)
    _core(plant, "w3-1", w3, mp["V"], plug_ports["1"])
    model = plant.model()
    assert end_box(model, plug_ports["1"], None) is None
    assert diagram_lines(model, None) == ()
    assert [(f.code, f.subject) for f in diagram_facts(model, None)] == [
        (DIAGRAM_CABLE_ONE_BOX, w3)
    ]


def test_a_cable_inside_one_unit_is_one_box_and_a_fanout_is_one_line_per_other_box() -> None:
    """Both ends in the cabinet: one box. Three boxes: two lines and `DIAGRAM_CABLE_FANOUT`."""
    plant, cabinet, _, (motor, mp), (_, sp), (_, cp), _ = _station()
    other, op = device(plant, "k1", "K1", "1")
    inside = cable(plant, "w5", "W5")
    _core(plant, "w5-1", inside, sp["1"], cp["1"])
    fan = cable(plant, "w6", "W6")
    _core(plant, "w6-1", fan, mp["U"], sp["2"])
    _core(plant, "w6-2", fan, mp["V"], op["1"])
    model = plant.model()
    lines = diagram_lines(model, None)
    assert [line.designation for line in lines] == ["-W6", "-W6"]
    assert {line.b for line in lines} | {lines[0].a} == {motor, cabinet, other}
    assert len({line.a for line in lines}) == 1
    assert [(f.code, f.subject) for f in diagram_facts(model, None)] == [
        (DIAGRAM_CABLE_FANOUT, fan),
        (DIAGRAM_CABLE_ONE_BOX, inside),
    ]


def test_a_loose_wire_between_two_boxes_is_a_system_finding_and_a_clean_twin_is_not() -> None:
    """A cable-less wire from the motor to the cabinet fires; one inside the cabinet does not."""
    plant, _, _, (_, mp), (_, sp), (_, cp), _ = _station()
    loose = plant.wire(mp["U"], sp["1"], key="loose")
    plant.wire(sp["2"], cp["1"], key="twin")
    model = plant.model()
    assert [(f.code, f.subject) for f in diagram_facts(model, None)] == [
        (DIAGRAM_LOOSE_WIRE, loose)
    ]


def test_a_unit_reading_draws_its_own_cables_to_child_unit_instances_never_into_them() -> None:
    """Cabinet reading: the cable's plug mates a board item two levels down; the box is `board`."""
    plant, cabinet, board, _, (strip, sp), _, _ = _station()
    grand = _unit(plant, "grand", tag=None, parent=board)
    deep, _ = device(plant, "deep", "A2", "1", unit=grand)
    own = cable(plant, "wh1", "WH1", unit=cabinet)
    _plug, plug_ports = _plug_to(plant, own, "p1", "deep")
    _core(plant, "wh1-1", own, sp["1"], plug_ports["1"])
    model = plant.model()
    assert end_box(model, plug_ports["1"], cabinet) == BoxEnd(box=board, landed=deep, anchored=True)
    assert end_box(model, sp["1"], cabinet) == BoxEnd(box=strip, landed=strip, anchored=False)
    (line,) = diagram_lines(model, cabinet)
    assert {line.a, line.b} == {strip, board}
    assert diagram_lines(model, board) == ()
    assert diagram_facts(model, cabinet) == ()


def test_an_end_outside_the_reading_reaches_no_box_and_a_unit_has_no_loose_wire_fact() -> None:
    """From the board's reading the strip is outside it; a loose wire is never a unit finding."""
    plant, cabinet, board, _, (_, sp), _, (_, ip) = _station()
    plant.wire(sp["1"], ip["1"], key="loose")
    model = plant.model()
    assert end_box(model, sp["1"], board) is None
    assert diagram_facts(model, cabinet) == ()
    assert diagram_facts(model, board) == ()


def test_a_second_unit_instance_is_a_second_box() -> None:
    """Two instances of one release are two boxes in the system reading."""
    plant = Plant()
    u1 = _unit(plant, "u1", tag="U1")
    u2 = _unit(plant, "u2", tag="U2")
    _, p1 = device(plant, "a", "A", "1", unit=u1)
    _, p2 = device(plant, "b", "B", "1", unit=u2)
    w = cable(plant, "w", "W")
    _core(plant, "w-1", w, p1["1"], p2["1"])
    (line,) = diagram_lines(plant.model(), None)
    assert {line.a, line.b} == {u1, u2}
    assert make_id(Item, ("a",)) not in {line.a, line.b}


def test_box_order_sorts_by_the_lines_a_box_prints_then_by_id() -> None:
    """`box_order` is the one text order `diagram_lines` uses; two boxes of one text tie on id."""
    plant = Plant()
    u1 = _unit(plant, "u1", tag="U1")
    u2 = _unit(plant, "u2", tag="U2")
    model = plant.model()
    assert sorted((u2, u1), key=lambda box: box_order(model, box, None)) == [u1, u2]
    assert box_order(model, u1, None)[0] != box_order(model, u2, None)[0]
