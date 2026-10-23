"""Field case: a contact with no conductor is never drawn; its coil's contact table lists it "N/A".

The engineering shape: a contactor with a coil, a three-pole main contact, a wired NO auxiliary
contact and an NC auxiliary contact nobody wired, the coil and the contacts on one cabinet page.

The bug: with `d.layout.profile(hide_unused_pins=False)` the unwired NC contact was drawn as a
lone symbol, and the contact table printed a place with a page prefix ("13-14 p1:2A") even when the
contact sits on the coil's own page.
The fix: decision model-0136, a reference to a place on the same page prints the cell only
("13-14 2A"), and a contact with no conductor reads "21-22 N/A"; decision layout-0112, a contact
is never drawn without a conductor, with the switch on or off.
"""

import functools
import re
import tempfile
from pathlib import Path

import fransys as fr
import pytest
from _contact_tables import contact_table
from _drawn_pages import drawn_pages
from _tables_on import TABLES_ON
from fransys.colours import BU


def _plant(d) -> None:
    psu = d.device("T1", "DEMO-PSU-24")
    mains = d.device("P2", "DEMO-LAMP-24")
    lamp = d.device("P1", "DEMO-LAMP-24")
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.detail.wire(psu.input["L"], mains["1"], wire=blue)
    d.detail.wire(psu.input["N"], mains["2"], wire=blue)
    d.detail.wire(psu.output["+"], q.coil["A1"], wire=blue)
    d.detail.wire(psu.output["-"], q.coil["A2"], wire=blue)
    d.detail.wire(psu.output["+"], q.aux["13"], wire=blue)
    d.detail.wire(q.aux["14"], lamp["1"], wire=blue)
    d.detail.wire(psu.output["-"], lamp["2"], wire=blue)
    for pole, pin in enumerate("UVW"):
        d.detail.wire(psu.output["+"], q.main[str(2 * pole + 1)], wire=blue)
        d.detail.wire(q.main[str(2 * pole + 2)], motor.motor[pin], wire=blue)


@functools.cache
def _built(*, hide: bool):
    """The built result of `_plant` in one cabinet document, built once per switch setting."""
    d = fr.design("demo_parts", place="CAB")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    _plant(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc, settings=TABLES_ON)


def _placed(model, pin: str) -> list:
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


def test_the_table_reads_na_for_the_unwired_contact_with_the_switch_on() -> None:
    """The NC row is "21-22 N/A"."""
    # UNDO: derive/contact_entries.py:spare_entries, return two empty lists
    _, nc = contact_table(_built(hide=True).model)
    assert nc == ["21-22 N/A"]


def test_the_table_reads_na_for_the_unwired_contact_with_the_switch_off() -> None:
    """The NC row is "21-22 N/A" with the switch off too."""
    # UNDO: derive/contact_entries.py:spare_entries, the N/A text removed
    _, nc = contact_table(_built(hide=False).model)
    assert nc == ["21-22 N/A"]


@pytest.mark.parametrize("hide", [True, False])
def test_a_same_page_entry_prints_the_cell_only(*, hide: bool) -> None:
    """The NO rows are "13-14 2A"-shaped: the pair, then a bare cell, never "p1:"."""
    # UNDO: derive, print the page prefix on a same-page reference again
    no, _ = contact_table(_built(hide=hide).model)
    assert {entry.split(" ")[0] for entry in no} == {"13-14", "1-2", "3-4", "5-6"}
    assert not any("p1:" in entry for entry in no)
    assert all(re.fullmatch(r"\d+[A-Z]+", entry.split(" ")[1]) for entry in no)


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
