"""EA5, EA6, EA12, EA14: the motor starter with its latch, by hand and by series, one model."""

from typing import TYPE_CHECKING

from fransys_author import Design
from fransys_author.surface import design
from fransys_author.surface.colours import BK, BU

from .conftest import assert_same_model
from .series_parts import pair_library

if TYPE_CHECKING:
    from fransys_model.kernel import Draft

PARTS = {
    "G1": "TEST-PSU-24V",
    "Q0": "TEST-MCB-3P",
    "Q1": "TEST-KM-3P",
    "F1": "TEST-OL-3P",
    "S1": "TEST-BTN-NC",
    "S2": "TEST-BTN-NO",
}


def engine(lib: Draft) -> Draft:
    e = Design(lib)
    c1 = e.location("C1", "")
    x0, x1 = e.strip("X0", at=c1), e.strip("X1", at=c1)
    t = [x0.terminal("TEST-TERM", index=n) for n in (1, 2, 3)]
    rails = {"L1": ("230", 0), "L2": ("230", 120), "L3": ("230", 240)}
    e.supply("400V", current="ac", rails=rails, earthing="earthed")
    for rail, term in zip(rails, t, strict=True):
        e.net(rail, term.inner, cls="power", potential=rail)
    i = {tag: e.item(mpn, name=tag, tag=tag, at=c1) for tag, mpn in PARTS.items()}
    w1 = e.cable("TEST-CBL-4", name="W1", tag="W1", at=c1)
    m1 = e.item("TEST-MOTOR-3P", name="M1", tag="M1", at=None)
    out = i["G1"].fn("out")
    e.supply("24VDC", current="dc", rails={"24V": ("24", None), "0V": ("0", None)})
    e.net("24V", out["+"], cls="power", potential="24V")
    e.net("0V", out["-"], cls="power", potential="0V")
    power = e.wiring(colour="BK", gauge="2.5")
    for a, b in zip(t, [i["Q0"].fn("main")[p] for p in "135"], strict=True):
        power(a.inner, b)
    for source, load in (("Q0", "Q1"), ("Q1", "F1")):
        for a, b in zip("246", "135", strict=True):
            power(i[source].fn("main")[a], i[load].fn("main")[b])
    x1t = [x1.terminal("TEST-TERM", index=n) for n in (1, 2, 3)]
    for a, b in zip("246", x1t, strict=True):
        power(i["F1"].fn("main")[a], b.inner)
    for n, (term, pin) in enumerate(zip(x1t, "UVW", strict=True), start=1):
        w1.core(n, term.outer, m1.fn("load")[pin])
    w1.core(4, x1.terminal("DEMO-TB-PE-2.5", index=4).outer, m1.fn("load")["PE"])
    control = e.wiring(colour="BU", gauge="0.75")
    s1, s2, k1, f1 = (i[tag] for tag in ("S1", "S2", "Q1", "F1"))
    control(out["+"], s1.fn("contact")["21"])
    for load in (s2.fn("contact")["13"], k1.fn("aux")["13"]):
        control(s1.fn("contact")["22"], load)
    control(s2.fn("contact")["14"], f1.fn("aux")["95"])
    control(k1.fn("aux")["14"], f1.fn("aux")["95"])
    control(f1.fn("aux")["96"], k1.fn("coil")["A1"])
    control(k1.fn("coil")["A2"], out["-"])
    return e.draft()


def surface(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    x0 = d.terminal_strip("X0", "TEST-TERM")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3])
    g1 = d.device("G1", "TEST-PSU-24V")
    dc = d.dc_supply("24VDC", g1)
    q0, q1 = d.device("Q0", "TEST-MCB-3P"), d.device("Q1", "TEST-KM-3P")
    f1 = d.device("F1", "TEST-OL-3P")
    s1, s2 = d.device("S1", "TEST-BTN-NC"), d.device("S2", "TEST-BTN-NO")
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="DEMO-TB-PE-2.5")
    w1 = d.cable("W1", "TEST-CBL-4")
    m1 = d.device("M1", "TEST-MOTOR-3P", place=None)
    d.series(ac, q0.main, q1.main, f1, x1, w1, m1, wire=(BK, 2.5))
    d.series(dc.plus, s1, d.parallel(s2, q1.aux), f1.aux, q1.coil, dc.minus, wire=(BU, 0.75))
    return d.draft()


def _devices(d, table: dict[str, str]) -> dict:
    return {tag: d.device(tag, mpn) for tag, mpn in table.items()}


def efficient(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    x0 = d.terminal_strip("X0", "TEST-TERM")
    ac = d.ac_supply("400V", "230", *(x0[n] for n in (1, 2, 3)))
    i = _devices(d, PARTS)
    dc = d.dc_supply("24VDC", i["G1"])
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="DEMO-TB-PE-2.5")
    w1 = d.cable("W1", "TEST-CBL-4")
    m1 = d.device("M1", "TEST-MOTOR-3P", place=None)
    d.series(ac, i["Q0"].main, i["Q1"].main, i["F1"], x1, w1, m1, wire=(BK, 2.5))
    latch = d.parallel(i["S2"], i["Q1"].aux)
    d.series(dc.plus, i["S1"], latch, i["F1"].aux, i["Q1"].coil, dc.minus, wire=(BU, 0.75))
    return d.draft()


def test_the_starter_by_hand_by_series_and_by_loop_is_one_model() -> None:
    assert_same_model(pair_library(), engine, surface, efficient)
