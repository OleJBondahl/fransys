"""Field case: a relay's contact table sits at its coil's home, not on the parent's black box.

The engineering shape: a unit "cab" holds a relay K1 (its coil handed up as interface), a supply
and a lamp, the contact 11-14 feeding the lamp. The design adds the unit as "U1" and prints a
cabinet schematic of "cab". The parent's set draws the unit as a black box with a replica of
the coil; the unit's own set draws the relay in full.

The bug (reported against v0.14.0): the contact table (the contact image) stood on the replica on
the parent's black box, and the contact's tag read "p1.1:1A", a page of a set no document prints.
`contact_images` and the back references took the first placement of the coil over all pages.
The rule (decision layout-0184, amending layout-0045): a function's contact image and its contacts'
back references live at its home, its own placement in its own unit's set. A replica on the
parent's black box is a cell away from its home (layout-0129) and hosts no image.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _tables_on import TABLES_ON

from fransys_model.layout import DrawingSet, Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_layout.drawing import Drawing, DrawnSymbol
    from fransys_model.kernel import Model


class _Io(NamedTuple):
    k1: fr.Device


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _cab(c: fr.Design) -> _Io:
    k1 = c.device("K1", "DEMO-RLY-2CO-24", interface=("coil",))
    h1 = c.device("H1", "DEMO-LAMP-24")
    psu = c.device("G1", "DEMO-PSU-24")
    wire = ("WH", 0.75)
    c.detail.wire(psu.output["+"], k1.coil["A1"], wire=wire)
    c.detail.wire(k1.coil["A2"], psu.output["-"], wire=wire)
    c.detail.wire(psu.output["+"], k1.co_1["11"], wire=wire)
    c.detail.wire(k1.co_1["14"], h1.lamp["1"], wire=wire)
    c.detail.wire(h1.lamp["2"], psu.output["-"], wire=wire)
    return _Io(k1)


@pytest.fixture(scope="module")
def model(tmp_path_factory: pytest.TempPathFactory) -> Model:
    root: Path = tmp_path_factory.mktemp("home")
    (root / "own.md").write_text("# Cab\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    return fr.build(
        d,
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=root / "own.md"),
        settings=TABLES_ON,
    ).model


def _symbols(model: Model, key: str) -> list[tuple[int, DrawnSymbol, Drawing]]:
    """Each drawn symbol of library `key` with the number of the drawing set of its page."""
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    return [
        (sets[pages[pid].drawing_set].number, s, d)
        for pid, d in drawn_pages(model).items()
        for s in d.symbols
        if s.key == key
    ]


def test_the_table_stands_on_the_units_own_page(model: Model) -> None:
    """The coil's table is in the set that also draws the contact, not the parent's black box."""
    (table_set, _, table_page) = _symbols(model, "contact-head")[0]
    contact_sets = {number for number, _, _ in _symbols(model, "change-over-contact")}
    assert table_set in contact_sets
    assert any(s.key == "operating-device" for s in table_page.symbols), "the coil is on the page"


def test_the_contacts_tag_names_a_page_of_its_own_set(model: Model) -> None:
    """co_1's tag reads a bare page and cell: no set prefix, so no page of another set."""
    ((_, contact, page),) = _symbols(model, "change-over-contact")
    tag = min(
        (t for t in page.texts if t.kind == "TAG"),
        key=lambda t: abs(t.box.x - contact.x) + abs(t.box.y - contact.y),
    )
    assert ":" in tag.text, "the tag carries the coil's page and cell"
    assert "." not in tag.text.split(":")[0]
