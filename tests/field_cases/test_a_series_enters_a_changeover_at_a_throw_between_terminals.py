"""Field case: a series between two fixed terminals enters a changeover at its throw.

The engineering shape: a field terminal X6:2 feeds the make throw of a relay changeover, and the
changeover's common goes on to terminal X7:2. No supply stands in the series to name the direction.

The bug: a changeover throw in a series was always entered at its common, so the call
`d.series(x6[2], k1.co_1.no, x7[2])` wired X6:2 to the common and the throw to X7:2, the reverse
of the circuit; the wires had to be written with `d.detail.wire` and pin names.

Decision author-0055 (API-FRICTION-2 C15): a throw between two fixed terminals is entered at the
throw and left at the common. With a supply or a device beside it the common stays the entry, as
S7 rules. The rewrite keeps the throw spelling; a selector is the explicit form.
"""

from typing import Any

import fransys as fr
from fransys.colours import BK


def _name(key: tuple[str, ...]) -> tuple[str, str]:
    """The item and pin of a port key; a terminal's pin is its number."""
    return key[0], key[2] if "terminal" in key else key[-1]


def _ends(d: fr.Design) -> set[frozenset]:
    """Every conductor as the two (item, pin) it joins."""
    model = fr.build(d).model
    conductors: list[Any] = list(model.tables["conductor"].values())
    return {frozenset(_name(model.key_of(p) or ()) for p in (c.a, c.b)) for c in conductors}


def _design() -> tuple[fr.Design, fr.TerminalStrip, fr.TerminalStrip, fr.Device]:
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
    d.series(x6[2], k1.co_1.no, k2.coil, wire=(BK, 1.5))
    assert _ends(d) == {
        frozenset((("X6", "2"), ("K1", "11"))),
        frozenset((("K1", "14"), ("K2", "A1"))),
    }
