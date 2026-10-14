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

from fransys_model.derive.drawing_text import cross_reference_text
from fransys_model.layout import DrawingSet, Label, Page, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_model.kernel import Model


class _Io(NamedTuple):
    k1: fr.Device


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _cab(c: fr.Design) -> _Io:
    k1 = c.device("K1", "DEMO-RLY-2CO-24", interface=("coil",))
    h1 = c.device("H1", "DEMO-LAMP-24")
    psu = c.device("G1", "DEMO-PSU-24")
    wire = ("WH", 0.75)
    c.wire(psu.output["+"], k1.coil["A1"], wire=wire)
    c.wire(k1.coil["A2"], psu.output["-"], wire=wire)
    c.wire(psu.output["+"], k1.co_1["11"], wire=wire)
    c.wire(k1.co_1["14"], h1.lamp["1"], wire=wire)
    c.wire(h1.lamp["2"], psu.output["-"], wire=wire)
    return _Io(k1)


@pytest.fixture(scope="module")
def model(tmp_path_factory: pytest.TempPathFactory) -> Model:
    root: Path = tmp_path_factory.mktemp("home")
    (root / "own.md").write_text("# Cab\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    return fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=root / "own.md")
    ).model


def _set_of(model: Model, label: Label) -> int:
    pages = layout_of(model, Page)
    return layout_of(model, DrawingSet)[pages[label.page].drawing_set].number


def _label(model: Model, name: str, slot: str) -> Label:
    (found,) = (
        one
        for one in layout_of(model, Label).values()
        if one.function is not None
        and one.partners
        and one.slot == slot
        and functions(model)[one.function].name == name
    )
    return found


def test_the_table_stands_on_the_units_own_page(model: Model) -> None:
    """The coil's table is in the set that also draws the contact, not the parent's black box."""
    table = _label(model, "coil", "contacts")
    contact_set = _set_of(model, _label(model, "co_1", "tag"))
    assert _set_of(model, table) == contact_set
    own = {(p.function, p.page) for p in layout_of(model, SymbolPlacement).values()}
    assert (table.function, table.page) in own


def test_the_contacts_tag_names_a_page_of_its_own_set(model: Model) -> None:
    """co_1's tag reads a bare page and cell: no set prefix, so no page of another set."""
    text = cross_reference_text(model, _label(model, "co_1", "tag"))
    assert text
    assert "." not in text.split(":")[0]
