"""Field case: a field terminal X6:2 feeds the make throw of a relay changeover whose common goes on to X7:2, with no supply beside it.
The bug: a changeover throw in a series was always entered at its common, so `d.series(x6[2], k1.co_1.no, x7[2])` ran in reverse.
Fixed by author-0055 (API-FRICTION-2 C15), a throw between two fixed terminals is entered at the throw and left at the common."""

from typing import Any

import fransys as fr
from _series_ends import ends_of, pin_name
from fransys.colours import BK


def _ends(d):
    """The design's conductor ends but the ones to its closing sink `G1`."""
    return {e for e in ends_of(d, name=pin_name) if all(end[0] != "G1" for end in e)}


def _design() -> tuple[fr.Design, fr.TerminalStrip, fr.TerminalStrip, Any]:
    d = fr.design("demo_parts")
    x6 = d.terminal_strip("X6", "DEMO-TB-2.5", 4)
    x7 = d.terminal_strip("X7", "DEMO-TB-2.5", 4)
    return d, x6, x7, d.device("K1", "DEMO-RLY-2CO-24")


def test_the_make_throw_is_entered_and_the_common_leaves() -> None:
    d, x6, x7, k1 = _design()
    d.series(x6[2], k1.co_1.no, x7[2], wire=(BK, 1.5))
    assert _ends(d) == {
        frozenset((("X6", "2"), ("K1", "14"))),
        frozenset((("K1", "11"), ("X7", "2"))),
    }


def test_the_break_throw_is_entered_the_same_way() -> None:
    d, x6, x7, k1 = _design()
    d.series(x6[2], k1.co_1.nc, x7[2], wire=(BK, 1.5))
    assert _ends(d) == {
        frozenset((("X6", "2"), ("K1", "12"))),
        frozenset((("K1", "11"), ("X7", "2"))),
    }


def test_a_device_after_the_throw_keeps_the_common_as_the_entry() -> None:
    d, x6, _, k1 = _design()
    k2 = d.device("K2", "DEMO-RLY-2CO-24")
    d.series(k2.coil["A2"], d.device("G1", None, external=True, pins=("P",)).P, wire=(BK, 1.5))
    d.series(x6[2], k1.co_1.no, k2.coil, wire=(BK, 1.5))
    assert _ends(d) == {
        frozenset((("X6", "2"), ("K1", "11"))),
        frozenset((("K1", "14"), ("K2", "A1"))),
    }
