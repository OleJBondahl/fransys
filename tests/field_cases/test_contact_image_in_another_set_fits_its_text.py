"""Field case: a contact image whose contact stands in another drawing set fits its own text.

The engineering shape: a contactor with a coil and contacts in a cabinet, and an add-on contact
block of that contactor in a field location, wired there to local loads only. The block's contacts
stand in another drawing set than the coil, so the coil's contact table names them with a location
prefix ("53-54 +FLDp1:2A"), not the bare cell of the same set.

The bug: layout sizes the contact image from the same-set text of that place, so the box is
narrower than the text derive prints and the entry overflows the box.
The fix: decision model-0144, one function gives the partner's position text and layout measures
that text.
"""

import tempfile
from pathlib import Path

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from fransys.colours import BU

_WIRE = (BU, 0.5)


def _built():
    """Coil Q1 in CAB; its add-on block in FLD, wired to two lamps there."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.location("FLD", "Field")
    psu = d.device("T1", "DEMO-PSU-24")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    block = d.device(None, "DEMO-CTR-BLOCK-1NO1NC", name="blk", parent=q, place="FLD")
    lamp = d.device("P1", "DEMO-LAMP-24", place="FLD")
    d.detail.wire(psu.output["+"], q.coil["A1"], wire=_WIRE)
    d.detail.wire(psu.output["-"], q.coil["A2"], wire=_WIRE)
    d.detail.wire(psu.output["+"], q.aux["13"], wire=_WIRE)
    d.detail.wire(q.aux["14"], lamp["1"], wire=_WIRE)
    d.detail.wire(psu.output["-"], lamp["2"], wire=_WIRE)
    d.detail.wire(lamp["1"], block.no["53"], wire=_WIRE)
    d.detail.wire(block.no["54"], lamp["2"], wire=_WIRE)
    d.detail.wire(lamp["1"], block.nc["61"], wire=_WIRE)
    d.detail.wire(block.nc["62"], lamp["2"], wire=_WIRE)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


@pytest.fixture(scope="module")
def tables() -> list[list[str]]:
    """Each contact table the pages draw, as its entries (NO then NC): the strings that size it."""
    return [
        [cell for row in symbol.texts[1:] for cell in row if cell]
        for drawing in drawn_pages(_built().model).values()
        for symbol in drawing.symbols
        if symbol.key == "contact-head"
    ]


def test_an_entry_names_a_place_in_another_set(tables) -> None:
    """The case is not vacuous: one entry carries the location prefix."""
    assert any("+FLD" in entry for entries in tables for entry in entries)


def test_the_box_is_as_wide_as_its_widest_text(tables) -> None:
    """The box is sized from the text derive prints: the other set's entry holds its prefix whole.

    The Drawing carries no table width (symdef fits the table to these strings), so the texts that
    size the box are what is read.
    """
    assert tables
    assert any(entry.startswith("53-54 +FLD") for entries in tables for entry in entries)
