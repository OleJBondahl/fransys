"""Field case: a contactor's wired NO aux contact and an unwired NC contact, on the coil's own cabinet page.
The bug: an unwired NC contact was drawn alone, and the table printed a page prefix even on the coil's own page.
Fixed by model-0136 (a same-page place prints the cell only) and layout-0112 (a contact is never drawn unwired)."""

import functools
from typing import Any

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU


def _plant(d) -> None:
    psu = d.device("T1", "DEMO-PSU-24")
    mains = d.device("P2", "DEMO-LAMP-24")
    lamp = d.device("P1", "DEMO-LAMP-24")
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.series(psu.input["L"], mains["1"], wire=blue)
    d.series(psu.input["N"], mains["2"], wire=blue)
    d.series(psu.output["+"], q.coil["A1"], wire=blue)
    d.series(psu.output["-"], q.coil["A2"], wire=blue)
    d.series(psu.output["+"], q.aux["13"], wire=blue)
    d.series(q.aux["14"], lamp["1"], wire=blue)
    d.series(psu.output["-"], lamp["2"], wire=blue)
    for pole, pin in enumerate("UVW"):
        d.series(psu.output["+"], q.main[str(2 * pole + 1)], wire=blue)
        d.series(q.main[str(2 * pole + 2)], motor.motor[pin], wire=blue)


@functools.cache
def _built(*, hide: bool):
    """The built result of `_plant` in one cabinet document, built once per switch setting."""
    d = fr.design("demo_parts", place="CAB")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    _plant(d)
    doc = unit_document(cab)
    return fr.build(d, doc)


def _placed(model, pin: str) -> list[Any]:
    """Every drawn symbol that prints the pin marking `pin`."""
    return [
        s
        for drawing in drawn_pages(model).values()
        for s in drawing.symbols
        if any(slot.startswith("marking.") and text == pin for slot, text in s.slots)
    ]


def test_the_unwired_contact_is_on_no_page_with_the_switch_on() -> None:
    """The NC auxiliary (pin 21) has no symbol; the NO auxiliary (pin 13) has one."""
    model = _built(hide=True).model
    assert _placed(model, "21") == []
    assert _placed(model, "13")


def test_the_unwired_contact_is_on_no_page_with_the_switch_off() -> None:
    """The switch does not matter: the pin 21 contact has no symbol, the pin 13 one has."""
    # UNDO: layout, draw a contact without a conductor again (the unused-contact filter removed)
    model = _built(hide=False).model
    assert _placed(model, "21") == []
    assert _placed(model, "13")


def test_no_lone_cell_with_the_switch_on() -> None:
    """The unwired contact is not drawn, so it is no lone cell."""
    # UNDO: read/unused.py:without_unused, the spare branch removed (the spare comes back as a cell)
    on = [f for f in _built(hide=True).findings if f.code == "LONE_CELL"]
    assert on == []


def test_no_lone_cell_with_the_switch_off() -> None:
    """With the switch off the unwired contact is still not drawn, so it is no lone cell."""
    # UNDO: layout, draw a contact without a conductor again (the unused-contact filter removed)
    off = [f for f in _built(hide=False).findings if f.code == "LONE_CELL"]
    assert off == []
