"""`port_points` gives each port of a drawn symbol as the page point its wire end meets (R391)."""

from typing import TYPE_CHECKING

from electrical_symbols import GENERIC_BOX_KEY, LIBRARY
from fransys_layout.drawing import DrawnSymbol, port_points

if TYPE_CHECKING:
    from fransys_layout.core import Orientation


def _box(x: int, y: int, orient: Orientation = "R0") -> DrawnSymbol:
    return DrawnSymbol(
        id="a",
        key=GENERIC_BOX_KEY,
        x=x,
        y=y,
        orient=orient,
        texts=(("P1",), ("P2",)),
        offsets=(("P1", 8), ("P2", 40)),
    )


def test_generic_box_ports_sit_at_the_symbol_origin_plus_their_offsets():
    assert port_points(_box(10, 20), LIBRARY) == (((18, 4), "P1"), ((50, 36), "P2"))


def test_a_turned_symbol_moves_its_ports():
    straight = port_points(_box(10, 20), LIBRARY)
    turned = port_points(_box(10, 20, "R90"), LIBRARY)
    assert [i for _, i in turned] == [i for _, i in straight]
    assert [p for p, _ in turned] != [p for p, _ in straight]


def test_the_symbol_position_shifts_every_port():
    a = port_points(_box(0, 0), LIBRARY)
    b = port_points(_box(100, 50), LIBRARY)
    assert [(p[0] + 100, p[1] + 50) for p, _ in a] == [p for p, _ in b]
