"""R450.3: the body of a stretched, turned symbol is read alone, so an odd length is no error."""

import pytest

from electrical_symbols import LIBRARY, MARKER_TURNED
from fransys_layout.core import Box, grid_out
from fransys_layout.symbols import library_symbol, ports_at_one_node, stretched_body, symbol_shape

pytestmark = pytest.mark.rule("PAGE-FRAME")

_SYMBOL = library_symbol(LIBRARY, MARKER_TURNED)
_NATURAL = symbol_shape(_SYMBOL, LIBRARY).body


@pytest.mark.parametrize("extra", [0, 1, 2, 3])
def test_the_body_is_the_stretched_length_along_the_axis_at_any_parity(extra: int) -> None:
    body = stretched_body(_SYMBOL, "R0", {"y": _NATURAL.h + extra}, LIBRARY)
    assert (body.w, body.h) == (_NATURAL.w, _NATURAL.h + extra)


def test_a_turn_swaps_the_two_extents() -> None:
    body = stretched_body(_SYMBOL, "R90", {"y": _NATURAL.h + 3}, LIBRARY)
    assert (body.w, body.h) == (_NATURAL.h + 3, _NATURAL.w)


def test_the_check_can_fail() -> None:
    long = stretched_body(_SYMBOL, "R0", {"y": _NATURAL.h + 3}, LIBRARY)
    assert long != stretched_body(_SYMBOL, "R0", {"y": _NATURAL.h + 2}, LIBRARY)


def test_a_reach_grows_outward_to_whole_cells_and_never_shrinks() -> None:
    """R1693: a box of 4 G past the grid on each side grows to the next cell; a whole box stays."""
    assert grid_out(Box(-12, -20, 24, 40), 8) == Box(-16, -24, 32, 48)
    assert grid_out(Box(-16, -24, 32, 48), 8) == Box(-16, -24, 32, 48)
    assert grid_out(Box(3, 5, 4, 4), 8) == Box(0, 0, 8, 16)


def test_ports_at_one_node_names_the_pins_a_symbol_draws_at_one_node_and_a_switch_has_none() -> None:
    """R2092: a terminal's four pins are one node; the in and out pin of an overload pole are two nodes."""
    terminal = ports_at_one_node(symbol_shape(library_symbol(LIBRARY, "terminal"), LIBRARY))
    assert terminal == {frozenset({"n", "e", "s", "w"})}
    assert ports_at_one_node(symbol_shape(library_symbol(LIBRARY, "thermal-overload"), LIBRARY)) == frozenset()
