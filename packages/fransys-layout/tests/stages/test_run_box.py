"""S20 M8: a box over several pins is two lines high, as wide as its pins, and its text breaks."""

from samples import PROFILE

from fransys_layout.geometry import Box, Point, text_width
from fransys_layout.stages.texts.stand import RUN_PIN_GAP, run_box

_TEXT = "-W3 ← X1:1 2 3 4"
_FIRST = Box(x=100, y=80, width=200, height=PROFILE.text_height + 2 * PROFILE.marker_padding)
_Y = 100


def _need(line: str) -> int:
    return text_width(line, height=PROFILE.text_height) + 2 * PROFILE.marker_padding


def _box(pins: int, text: str = _TEXT) -> tuple[Box, int | None]:
    ends = (Point(x=120, y=_Y), Point(x=120 + (pins - 1) * RUN_PIN_GAP, y=_Y))
    return run_box(_FIRST, ends, 10_000, text, PROFILE)


def test_a_two_pin_box_wraps_its_long_text_into_two_lines_inside_the_two_pin_width() -> None:
    """The one line is wider than two pins, so it breaks at a space: both lines fit the width."""
    # UNDO: stages/texts/stand.py `run_box`: leave `wrap_at` None (no wrap)
    assert _need(_TEXT) > 2 * RUN_PIN_GAP  # the premise: one line does not fit
    box, wrap_at = _box(2)
    assert wrap_at is not None
    assert box.width == 2 * RUN_PIN_GAP
    words = _TEXT.split(" ")
    assert _need(" ".join(words[:wrap_at])) <= box.width
    assert _need(" ".join(words[wrap_at:])) <= box.width
    assert box.height == 2 * PROFILE.text_height + 2 * PROFILE.marker_padding


def test_a_five_pin_box_holds_the_same_text_in_one_line() -> None:
    """The five pins' width holds the text: no break, the box still two lines high."""
    assert _need(_TEXT) <= 5 * RUN_PIN_GAP  # the premise: one line fits
    box, wrap_at = _box(5)
    assert wrap_at is None
    assert box.width == 5 * RUN_PIN_GAP
    assert box.height == 2 * PROFILE.text_height + 2 * PROFILE.marker_padding


def test_a_text_two_lines_cannot_hold_widens_the_box_about_its_centre() -> None:
    """The fallback: one long word on each side of the break, so the box widens, centred."""
    text = "A" * 40 + " " + "B" * 40
    narrow, _ = _box(2)
    box, wrap_at = _box(2, text)
    assert wrap_at == 1
    assert box.width > narrow.width
    assert box.width >= _need("A" * 40)
    assert box.x + box.width // 2 == narrow.x + narrow.width // 2


def test_a_box_stands_above_a_north_stub_and_below_a_south_one() -> None:
    """The near edge stays where the one-line box's was: it grows away from the port."""
    north, _ = _box(2)
    assert north.y + north.height == _FIRST.y + _FIRST.height
    ends = (Point(x=120, y=60), Point(x=144, y=60))
    south, _ = run_box(_FIRST, ends, 10_000, _TEXT, PROFILE)
    assert south.y == _FIRST.y
