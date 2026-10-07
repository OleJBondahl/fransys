"""EA6, EA12, EA14: a DC supply, a contact into a PLC channel and a PLC-driven coil, one model."""

from typing import TYPE_CHECKING

from fransys_author import Design
from fransys_author.surface import DO, design
from fransys_author.surface.colours import BU

from .conftest import assert_same_model
from .series_parts import series_library

if TYPE_CHECKING:
    from fransys_model.kernel import Draft

PARTS = {
    "G1": "TEST-PSU-24V",
    "S1": "TEST-BTN-NO",
    "A1": "TEST-PLC-CH",
    "K1": "TEST-KM-3P",
}
COILS = {"K1": "PUMP_RUN"}


def engine(lib: Draft) -> Draft:
    e = Design(lib)
    c1 = e.location("C1", "")
    i = {tag: e.item(mpn, name=tag, tag=tag, at=c1) for tag, mpn in PARTS.items()}
    out = i["G1"].fn("out")
    e.supply(
        "24VDC",
        current="dc",
        rails={"P24": ("24", None), "P0": ("0", None)},
        pins=[out["+"], out["-"]],
    )
    e.net("P24", out["+"], cls="power", potential="P24")
    e.net("P0", out["-"], cls="power", potential="P0")
    wire = e.wiring(colour="BU", gauge="0.75")
    contact, coil = i["S1"].fn("contact"), i["K1"].fn("coil")
    wire(out["+"], contact["13"])
    wire(contact["14"], i["A1"].fn("channel")["CH"])
    wire(out["+"], coil["A1"])
    wire(coil["A2"], out["-"])
    coil.plc("do", "PUMP_RUN", 5)
    return e.draft()


def surface(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    g1 = d.device("G1", "TEST-PSU-24V")
    dc = d.dc_supply("24VDC", g1, names=("P24", "P0"))
    s1, a1, k1 = (
        d.device("S1", "TEST-BTN-NO"),
        d.device("A1", "TEST-PLC-CH"),
        d.device("K1", "TEST-KM-3P"),
    )
    d.series(dc.plus, s1.contact, a1.channel, wire=(BU, 0.75))
    d.series(dc.plus, k1.coil, dc.minus, wire=(BU, 0.75))
    k1.coil.plc(DO, "PUMP_RUN", 5)
    return d.draft()


def _driven(d, dc, device, signal: str) -> None:
    d.series(dc.plus, device.coil, dc.minus, wire=(BU, 0.75))
    device.coil.plc(DO, signal, 5)


def efficient(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    i = {tag: d.device(tag, mpn) for tag, mpn in PARTS.items()}
    dc = d.dc_supply("24VDC", i["G1"], names=("P24", "P0"))
    d.series(dc.plus, i["S1"].contact, i["A1"].channel, wire=(BU, 0.75))
    for tag, signal in COILS.items():
        _driven(d, dc, i[tag], signal)
    return d.draft()


def test_the_supply_and_the_plc_by_hand_by_series_and_by_helper_are_one_model() -> None:
    assert_same_model(series_library(), engine, surface, efficient)
