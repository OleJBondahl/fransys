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

import re
import tempfile
from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive.drawing_text import contact_image
from fransys_model.layout import Label, LabelKind, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items


def _plant(d) -> None:
    psu = d.device("T1", "DEMO-PSU-24")
    mains = d.device("P2", "DEMO-LAMP-24")
    lamp = d.device("P1", "DEMO-LAMP-24")
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.wire(psu.input["L"], mains["1"], wire=blue)
    d.wire(psu.input["N"], mains["2"], wire=blue)
    d.wire(psu.output["+"], q.coil["A1"], wire=blue)
    d.wire(psu.output["-"], q.coil["A2"], wire=blue)
    d.wire(psu.output["+"], q.aux["13"], wire=blue)
    d.wire(q.aux["14"], lamp["1"], wire=blue)
    d.wire(psu.output["-"], lamp["2"], wire=blue)
    for pole, pin in enumerate("UVW"):
        d.wire(psu.output["+"], q.main[str(2 * pole + 1)], wire=blue)
        d.wire(q.main[str(2 * pole + 2)], motor.motor[pin], wire=blue)


def _built(*, hide: bool):
    """The built result of `_plant` in one cabinet document."""
    d = fr.design("demo_parts", place="CAB")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    _plant(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _placed(model, name: str) -> list:
    """Every placement of Q1's function `name`."""
    (item,) = (one.id for one in items(model).values() if one.key[-1] == "Q1")
    return [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if functions(model)[p.function].item == item and functions(model)[p.function].name == name
    ]


def _table(model) -> tuple[list[str], list[str]]:
    """Q1's contact table, its NO and NC entries as render prints them."""
    (item,) = (one.id for one in items(model).values() if one.key[-1] == "Q1")
    (label,) = (
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE
        and one.slot == "contacts"
        and one.function is not None
        and functions(model)[one.function].item == item
    )
    return contact_image(model, label)


def test_the_unwired_contact_is_on_no_page_with_the_switch_on() -> None:
    """The NC auxiliary has no placement; the NO auxiliary has one."""
    model = _built(hide=True).model
    assert _placed(model, "aux_nc") == []
    assert _placed(model, "aux")


def test_the_unwired_contact_is_on_no_page_with_the_switch_off() -> None:
    """The switch does not matter: aux_nc has no placement, aux has one."""
    # UNDO: layout, draw a contact without a conductor again (the unused-contact filter removed)
    model = _built(hide=False).model
    assert _placed(model, "aux_nc") == []
    assert _placed(model, "aux")


def test_the_table_reads_na_for_the_unwired_contact_with_the_switch_on() -> None:
    """The NC row is "21-22 N/A"."""
    # UNDO: derive/contact_entries.py:spare_entries, return two empty lists
    _, nc = _table(_built(hide=True).model)
    assert nc == ["21-22 N/A"]


def test_the_table_reads_na_for_the_unwired_contact_with_the_switch_off() -> None:
    """The NC row is "21-22 N/A" with the switch off too."""
    # UNDO: derive/contact_entries.py:spare_entries, the N/A text removed
    _, nc = _table(_built(hide=False).model)
    assert nc == ["21-22 N/A"]


@pytest.mark.parametrize("hide", [True, False])
def test_a_same_page_entry_prints_the_cell_only(*, hide: bool) -> None:
    """The NO rows are "13-14 2A"-shaped: the pair, then a bare cell, never "p1:"."""
    # UNDO: derive, print the page prefix on a same-page reference again
    no, _ = _table(_built(hide=hide).model)
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
