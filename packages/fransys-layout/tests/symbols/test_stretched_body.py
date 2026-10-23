"""R450.3: the body of a stretched, turned symbol is read alone, so an odd length is no error."""

import pytest

from electrical_symbols import LIBRARY, MARKER_TURNED
from fransys_layout.symbols import library_symbol, stretched_body, symbol_shape

pytestmark = pytest.mark.rule("PAGE-FRAME")

_SYMBOL = library_symbol(LIBRARY, MARKER_TURNED)
_NATURAL = symbol_shape(_SYMBOL, LIBRARY).body


@pytest.mark.parametrize("extra", [0, 1, 2, 3])
def test_the_body_is_the_stretched_length_along_the_axis_at_any_parity(extra: int) -> None:
    body = stretched_body(_SYMBOL, "R0", "y", _NATURAL.h + extra, LIBRARY)
    assert (body.w, body.h) == (_NATURAL.w, _NATURAL.h + extra)


def test_a_turn_swaps_the_two_extents() -> None:
    body = stretched_body(_SYMBOL, "R90", "y", _NATURAL.h + 3, LIBRARY)
    assert (body.w, body.h) == (_NATURAL.h + 3, _NATURAL.w)


def test_the_check_can_fail() -> None:
    long = stretched_body(_SYMBOL, "R0", "y", _NATURAL.h + 3, LIBRARY)
    assert long != stretched_body(_SYMBOL, "R0", "y", _NATURAL.h + 2, LIBRARY)
