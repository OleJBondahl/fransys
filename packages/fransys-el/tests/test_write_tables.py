"""A coil's contact table is an Annex: bottom-right first, top-right second (R339, R345)."""

from fransys_el.placement_tables import is_table_spot, table_annexes

from fransys_layout.core import Box, Orientation, Pin, Size, Sym
from fransys_layout.core.sym_values import PinTurn, Turned

_KEEPOUT = Box(-24, -24, 48, 48)
_TABLE = Box(0, 0, 40, 30)
_PINS = (Pin("a", "N", 0, -24, 0), Pin("b", "S", -8, 24, 0), Pin("c", "S", 8, 24, 0))
_R0 = (PinTurn(0, -24, "N"), PinTurn(-8, 24, "S"), PinTurn(8, 24, "S"))
_R180 = (PinTurn(0, 24, "S"), PinTurn(8, -24, "N"), PinTurn(-8, -24, "N"))


def _coil() -> Sym:
    views: dict[Orientation, Turned] = {
        "R0": Turned(_KEEPOUT, _KEEPOUT, _KEEPOUT, _R0),
        "R180": Turned(_KEEPOUT, _KEEPOUT, _KEEPOUT, _R180),
    }
    return Sym("K", None, "", Size(0, 0), _PINS, (), views)


def _spots(orient: Orientation = "R0"):
    (annex,) = table_annexes((_coil(),), {"K": _TABLE}, (4, 2, 8))
    return annex, annex.spots[orient]


def test_the_annex_is_the_tables_size_and_stacks_by_its_coil() -> None:
    annex, _ = _spots()
    assert (annex.owner, annex.stack, annex.size) == ("K", "K", Size(40, 30))


def test_bottom_right_is_first_half_a_pitch_right_of_the_rightmost_south_pin() -> None:
    _, (low, high) = _spots()
    assert (low.name, low.grow) == ("table-BR", "down")
    assert (low.dx, low.dy) == (8 + 4 - 24, 24 + 2 - 24)
    assert (low.corner, low.clear) == ("BR", 8)
    assert (high.name, high.grow) == ("table-TR", "up")
    assert (high.dx, high.dy) == (low.dx, -24 - 2 - 30 + 24)
    assert (high.corner, high.clear) == ("TR", 8)


def test_a_half_turn_reads_the_south_pin_of_the_turned_view() -> None:
    _, (low, _) = _spots("R180")
    assert low.dx == 0 + 4 - 24


def test_a_coil_without_a_table_has_no_annex() -> None:
    assert table_annexes((_coil(),), {}, (4, 2, 8)) == ()


def test_only_a_table_spot_is_a_table_spot() -> None:
    assert is_table_spot("table-BR")
    assert not any(is_table_spot(c) for c in ("TL", "TR", "BL", "BR"))
