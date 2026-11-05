"""Field case: two pins of a box wired to each other, or both wired to one coil pin, beside a coil on two other pins.
The bug: the net had no path and drew no wire.
Fixed by layout-0440 (CROSS-HALF-TAGS): a net across the halves of a box is a tag pair."""

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BU


def _build(*, to_box: bool) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("PLC", "Controller"):
        box = d.device("A1", None, pins=("P1", "P2", "P3", "P4"), external=True)
    with d.function("B", "Relays"):
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        k2 = d.device("K2", "DEMO-RLY-2CO-24")
        d.series(box["P1"], box["P4"] if to_box else k1.coil["A1"], wire=(BU, 0.5))
        if not to_box:
            d.series(box["P4"], k1.coil["A1"], wire=(BU, 0.5))
            d.series(k1.coil["A2"], k2.coil["A2"], wire=(BU, 0.5))
        d.series(box["P2"], k2.coil["A1"], wire=(BU, 0.5))
        d.series(box["P3"], k2.coil["A2"], wire=(BU, 0.5))
    return fr.build(d, unit_document(cab))


@pytest.mark.parametrize("to_box", [True, False], ids=["pin-to-pin", "two-pins-one-coil"])
def test_a_wire_between_box_pins_or_to_one_coil_pin_routes(*, to_box: bool) -> None:
    assert not [f for f in _build(to_box=to_box).findings if f.code == "CONNECTION_NOT_DRAWN"]
