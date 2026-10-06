"""V3: a pin wired to a rail gets one symbol marker per page, and none where it already has one.

Function 1 is seated on page 1 of drawing set 1; its port `12` is the rail end.
"""

from samples import PROFILE, SHEET, drawn, hid, placed

from fransys_layout.stages.references.rails import rail_markers
from fransys_layout.stages.references.types import MarkerScene
from fransys_layout.stages.types import PortRef, RailEnd

_PORT = hid("port", 12)
_END = RailEnd(ref=PortRef(function=hid("function", 1), port=_PORT), connection=hid("conductor", 1))
_SCENE = MarkerScene((placed(1, x=64, y=160),), (drawn(1),), SHEET, PROFILE)


def test_a_rail_end_gets_one_marker_on_its_page_even_when_it_ends_two_wires() -> None:
    """(a) Two rail wires at one pin are one marker, its own partner, at the pin."""
    # UNDO: references/rails.py `rail_markers`: `key = (end.ref.port, *page)` -> `end.connection`
    twice = (_END, RailEnd(ref=_END.ref, connection=hid("conductor", 2)))
    found = rail_markers(twice, _SCENE, frozenset(), {}, frozenset())
    assert [(one.port, one.partner, one.drawing_set, one.page) for one in found] == [
        (_PORT, _PORT, 1, 1)
    ]


def test_a_pin_that_already_has_a_power_marker_gets_no_second() -> None:
    """(b) A `(port, set, page)` in `taken` is skipped: never two symbols at a pin."""
    # UNDO: references/rails.py `rail_markers`: `key not in taken` -> `True`
    assert rail_markers((_END,), _SCENE, frozenset(), {}, {(_PORT, 1, 1)}) == ()


def test_a_pin_exempt_in_its_set_gets_no_marker() -> None:
    """(c) An end at a unit's boundary, exempt in the set, takes no marker there."""
    # UNDO: references/rails.py `rail_markers`: `shown(world, end.ref, exempt)` -> `frozenset()`
    assert rail_markers((_END,), _SCENE, frozenset({(_PORT, 1)}), {}, frozenset()) == ()


def test_a_black_box_end_gets_no_marker_in_its_black_box_set() -> None:
    """(d) A nested unit's boundary port, a black box in set 1, ends its lead at the outline."""
    # UNDO: references/rails.py `rail_markers`: `page[0] not in outward.get(...)` -> `True`
    outward = {_END.ref.function: frozenset({1})}
    assert rail_markers((_END,), _SCENE, frozenset(), outward, frozenset()) == ()
