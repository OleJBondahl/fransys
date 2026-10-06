"""EA5, EA7, EA12, EA14: a strip, a four-core cable with a GNYE core and a motor, one model."""

from typing import TYPE_CHECKING

from fransys_author import Design
from fransys_author.surface import design
from fransys_author.surface.colours import BK

from .conftest import assert_same_model
from .series_parts import pair_library

if TYPE_CHECKING:
    from fransys_model.kernel import Draft


def engine(lib: Draft) -> Draft:
    e = Design(lib)
    c1 = e.location("C1", "")
    q1 = e.item("TEST-MCB-3P", name="Q1", tag="Q1", at=c1)
    x1 = e.strip("X1", at=c1)
    w1 = e.cable("TEST-CBL-4", name="W1", tag="W1", length_mm=5000, at=c1)
    m1 = e.item("TEST-MOTOR-3P", name="M1", tag="M1", at=c1)
    wire = e.wiring(colour="BK", gauge="2.5")
    terminals = [x1.terminal("TEST-TERM", index=n) for n in (1, 2, 3)]
    for out, terminal in zip("246", terminals, strict=True):
        wire(q1.fn("main")[out], terminal.inner)
    for number, (terminal, pin) in enumerate(zip(terminals, "UVW", strict=True), start=1):
        w1.core(number, terminal.outer, m1.fn("load")[pin])
    w1.core(4, x1.terminal("DEMO-TB-PE-2.5", index=4).outer, m1.fn("load")["PE"])
    return e.draft()


def surface(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    q1, m1 = d.device("Q1", "TEST-MCB-3P"), d.device("M1", "TEST-MOTOR-3P")
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="DEMO-TB-PE-2.5")
    d.series(q1.main, x1, d.cable("W1", "TEST-CBL-4", length_m=5), m1, wire=(BK, 2.5))
    return d.draft()


def _field(d, table: dict[str, str]) -> None:
    q1, m1 = (d.device(tag, mpn) for tag, mpn in table.items())
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="DEMO-TB-PE-2.5")
    w1 = d.cable("W1", "TEST-CBL-4", length_m=5)
    d.series(q1.main, x1, w1, m1, wire=(BK, 2.5))


def efficient(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    _field(d, {"Q1": "TEST-MCB-3P", "M1": "TEST-MOTOR-3P"})
    return d.draft()


def test_the_field_cable_by_hand_by_series_and_by_helper_is_one_model() -> None:
    assert_same_model(pair_library(), engine, surface, efficient)
