"""A marker's keep-out boxes grow with its text and equal the plain ones when it fits."""

from electrical_symbols import LIBRARY, MARKER_SLOT
from fransys_layout.symbols import fitted_marker, fitted_marker_views, library_symbol, marker_views

_SYMBOL = library_symbol(LIBRARY, "reference-marker")
_LONG = "-W1 → -H1 p2:1B 2B 3B 4B 5B 6B"


def _views(text: str):
    return fitted_marker_views(_SYMBOL, MARKER_SLOT, text, LIBRARY)


def test_a_long_text_gives_a_longer_box_than_a_short_one() -> None:
    assert _views(_LONG)["R0"].w > _views("#1")["R0"].w
    assert _views(_LONG)["R270"].w > _views("#1")["R270"].w


def test_a_text_that_fits_gives_the_plain_boxes() -> None:
    assert dict(_views("#1")) == dict(marker_views(_SYMBOL, LIBRARY))


def test_the_check_can_fail() -> None:
    assert dict(_views(_LONG)) != dict(marker_views(_SYMBOL, LIBRARY))


def test_the_fitted_marker_grows_for_a_long_text_and_is_the_symbol_when_it_fits() -> None:
    grown = fitted_marker(_SYMBOL, MARKER_SLOT, _LONG, LIBRARY)
    assert marker_views(grown, LIBRARY)["R0"].w > marker_views(_SYMBOL, LIBRARY)["R0"].w
    assert fitted_marker(_SYMBOL, MARKER_SLOT, "#1", LIBRARY) == _SYMBOL
