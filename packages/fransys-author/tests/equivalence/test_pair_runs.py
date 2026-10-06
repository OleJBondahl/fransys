"""EA5, EA9: two named runs on one strip fed by a DC supply, by hand and by series, one model."""

from typing import TYPE_CHECKING

from fransys_author import Design
from fransys_author.surface import design
from fransys_author.surface.colours import BU

from .conftest import assert_same_model
from .series_parts import pair_library

if TYPE_CHECKING:
    from fransys_model.kernel import Draft

VALVE, SENSOR = "valve supply", "sensor supply"
_PARTS = (("K1", "TEST-KM-3P"), ("K2", "TEST-KM-3P"), ("S1", "TEST-BTN-NO"))


def engine(lib: Draft) -> Draft:
    e = Design(lib)
    c1 = e.location("C1", "")
    x3 = e.strip("X3", at=c1)
    g1 = e.item("TEST-PSU-24V", name="G1", tag="G1", at=c1)
    k1, k2, s1 = (e.item(m, name=t, tag=t, at=c1) for t, m in _PARTS)
    out = g1.fn("out")
    e.supply("24VDC", current="dc", rails={"24V": ("24", None), "0V": ("0", None)})
    e.net("24V", out["+"], cls="power", potential="24V")
    e.net("0V", out["-"], cls="power", potential="0V")
    valve = [x3.terminal("TEST-TERM", VALVE, index=n) for n in range(1, 9)]
    e.bridge(*valve)
    sensor = [x3.terminal("TEST-TERM", SENSOR, index=n) for n in range(1, 5)]
    wire = e.wiring(colour="BU", gauge="0.75")
    for terminal, load in ((valve[0], k1.fn("coil")["A1"]), (valve[1], k2.fn("coil")["A1"])):
        wire(out["+"], terminal.inner)
        wire(terminal.outer, load)
    for coil in (k1.fn("coil"), k2.fn("coil")):
        wire(coil["A2"], out["-"])
    wire(out["+"], sensor[0].inner)
    wire(sensor[0].outer, s1.fn("contact")["13"])
    wire(s1.fn("contact")["14"], out["-"])
    return e.draft()


def surface(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    dc = d.dc_supply("24VDC", d.device("G1", "TEST-PSU-24V"))
    x3 = d.terminal_strip("X3", "TEST-TERM")
    valve, sensor = x3.run(VALVE, 8, bridged=True), x3.run(SENSOR, 4)
    k1, k2, s1 = (d.device(t, m) for t, m in _PARTS)
    d.series(dc.plus, valve, k1.coil, dc.minus, wire=(BU, 0.75))
    d.series(dc.plus, valve, k2.coil, dc.minus, wire=(BU, 0.75))
    d.series(dc.plus, sensor, s1.contact, dc.minus, wire=(BU, 0.75))
    return d.draft()


def test_two_runs_fed_by_series_by_hand_and_by_series_is_one_model() -> None:
    assert_same_model(pair_library(), engine, surface)
