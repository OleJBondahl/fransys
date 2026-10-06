"""Field case: a link marker's stub and box never stand on another function's symbol.

Engineering shape: a contactor coil and a second relay coil share a return conductor. It runs
through the one-port pass-through terminal printed on an overload relay (the same page) and lands
on a strip terminal that belongs to another group, so the strip terminal is drawn on this page as
a replica, in the strip row under the pass-through's column. The net has four ports and is drawn
as one marker per port; the pass-through's marker leaves by its free port, southward, straight
at the strip terminal below it.

The bug: every tier of the marker's row nearer than the strip terminal is refused (the terminal's
own lane runs up the column), so the placer took the first tier past it. The stub ran through the
terminal's symbol and the box stood against its far port. `place_texts` tested the box against
the symbol bodies and never the stub, so the placer saw a clear place; the lint reported
`WIRE_THROUGH_SYMBOL` and `TEXT_OVERLAP`.

The rule (decision layout-0093, M7 and M9): a box never stands on a drawn wire or on a symbol,
and neither does the stub that leads to it. The marker takes a sideways place, with a lead, that
is clear of every other function's symbol.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import LinkMarker, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_CODES = ("TEXT_OVERLAP", "WIRE_THROUGH_SYMBOL")


@fr.unit(
    "demo-cabinet",
    revision=1,
    interface_version=1,
    title="Cab",
    number="X-1",
    date="2026-10-02",
    text="First release",
    by="XX",
)
def _cabinet(u: fr.Design) -> _Open:
    """A coil pair whose return leaves through a pass-through to a replica terminal."""
    u.location("C1", "Cabinet")
    strip = u.terminal_strip("X2", "DEMO-TB-2.5", place="C1")
    with u.function("FEED", "Feed"):
        terminal = strip[1]
    with u.function("LOAD", "Load"):
        contactor = u.device("K1", "DEMO-RLY-2CO-24", place="C1")
        overload = u.device("F1", "DEMO-OVERLOAD-A2", place="C1")
        relay = u.device("K2", "DEMO-RLY-2CO-24", place="C1")
    u.wire(contactor.coil["A2"], overload.a2["A2"], wire=("BK2", 1.5))
    u.wire(overload.a2["A2"], terminal, wire=("BK2", 1.5))
    u.wire(relay.coil["A1"], contactor.coil["A1"], wire=("BK2", 1.5))
    u.wire(relay.coil["A2"], contactor.coil["A2"], wire=("BK2", 1.5))
    return _Open()


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    """One build of the coil pair in its unit, in a cabinet-schematic document."""
    d = fr.design("demo_parts")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    d.add(_cabinet, "CAB")
    cover: Path = tmp_path_factory.mktemp("cover") / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cabinet", cover=cover)
    return fr.build(d, doc)


def test_marker_stub_and_box_clear_of_foreign_symbols(built: fr.BuildResult) -> None:
    assert [f.code for f in fr.check(built) if f.code in _CODES] == []


def test_the_pass_through_carries_a_marker(built: fr.BuildResult) -> None:
    """The fixture builds the shape the docstring describes, whichever place the marker takes."""
    markers = layout_of(built.model, LinkMarker).values()
    assert [m for m in markers if "a2" in m.key and "A2" in m.key]
