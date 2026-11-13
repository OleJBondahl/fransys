"""`mate_pairs`: the one home of a mate's port pairs, equal port names paired once; `MateEnd` reads them."""

from types import SimpleNamespace

from _expected_codes import expect_codes
from plant import Plant

from fransys_model.checks import check_mates_disabled
from fransys_model.derive import FunctionSymbol, far_pins, required_drawn, stub_far, stub_text_at
from fransys_model.derive.facts.mates import mate_pairs
from fransys_model.derive.far_pins import reach
from fransys_model.derive.rows_drawn import ConductorEnd, MateEnd


def test_a_plug_and_a_socket_pair_their_pins_by_name_and_skip_the_unmatched_one() -> None:
    """Pins 1 and 2 meet by name; the plug's pin 3 has no namesake on the socket."""
    plant = Plant()
    plug = [plant.pin("plug", "J1", name) for name in ("1", "2", "3")]
    socket = [plant.pin("socket", "J1", name) for name in ("1", "2", "4")]
    plant.mate(Plant.function_id("plug", "J1"), Plant.function_id("socket", "J1"))
    pairs = mate_pairs(plant.model())
    assert {frozenset(pair[1:]) for pair in pairs} == {
        frozenset((plug[0], socket[0])),
        frozenset((plug[1], socket[1])),
    }
    assert pairs == tuple(sorted(pairs))


def _mated():
    plant = Plant()
    plant.item("plug", designation="X1")
    plant.item("socket", designation="X2")
    plug = plant.pin("plug", "J1", "1")
    socket = plant.pin("socket", "J1", "1")
    mate = plant.mate(Plant.function_id("plug", "J1"), Plant.function_id("socket", "J1"))
    return plant.model(), plug, socket, mate


def test_a_mated_pin_reaches_its_partner_through_a_mate_end() -> None:
    """MateEnd (model-0445): `reach` gives the mate's far pin, `far_pins` and `stub_far` read it; a mate carries no cable."""
    model, plug, socket, mate = _mated()
    assert reach(model, [plug]) == [MateEnd(mate=mate, port=plug, far=socket)]
    assert reach(model, [socket]) == [MateEnd(mate=mate, port=socket, far=plug)]
    assert far_pins(model, [plug]) == ((plug, socket),)
    assert stub_far(model, [plug]) == ((plug, socket, None),)


def test_a_conductor_end_comes_before_a_mate_end_at_one_pin() -> None:
    """S3: the pin's first end is its conductor even when the mate's far pin prints first, so `far_port` and `cut_lines` read the conductor."""
    plant = Plant()
    plant.item("plug", designation="X1")
    plant.item("socket", designation="X2")
    plant.item("dev", designation="X9")
    plug = plant.pin("plug", "J1", "1")
    socket = plant.pin("socket", "J1", "1")
    far = plant.pin("dev", "J1", "1")
    mate = plant.mate(Plant.function_id("plug", "J1"), Plant.function_id("socket", "J1"))
    wire = plant.wire(plug, far, key="w")
    first, second = reach(plant.model(), [plug])
    assert first == ConductorEnd(conductor=wire, port=plug, far=far)
    assert second == MateEnd(mate=mate, port=plug, far=socket)


def test_a_mate_end_prints_as_a_stub_to_its_partner_and_is_owed() -> None:
    """A mate stub prints `stub_text_at`'s carrier-free text; `required_drawn` owes the mate end beside the function symbols (R2223.1)."""
    model, plug, socket, _ = _mated()
    text = stub_text_at(model, None, stub_far(model, [plug])[0], north=False)
    assert "→" in text
    owed = [row for row in required_drawn(model, [plug, socket]) if not isinstance(row, FunctionSymbol)]
    assert {(row.port, row.far) for row in owed} == {(plug, socket), (socket, plug)}
    assert all(isinstance(row, MateEnd) for row in owed)


def test_a_mate_stays_refused_at_the_check() -> None:
    """MATES_DISABLED: the mate is an ERROR finding, so no consumer build reaches `MateEnd` (mates return in MATES-RETURN C)."""
    model, _, _, mate = _mated()
    (found,) = check_mates_disabled(model)
    assert found.subjects == (mate,)
    expect_codes(SimpleNamespace(findings=[found]), "MATES_DISABLED")
