"""Field case: a contact image whose contact stands in another drawing set fits its own text.

The engineering shape: a contactor with a coil and contacts in a cabinet, and an add-on contact
block of that contactor in a field location, wired there to local loads only. The block's contacts
stand in another drawing set than the coil, so the coil's contact table names them with a location
prefix ("53-54 +FLDp1:2A"), not the bare cell of the same set.

The bug: layout sizes the contact image from the same-set text of that place, so the box is
narrower than the text derive prints and the entry overflows the box (RW9).
The fix: decision model-0144, one function gives the partner's position text and layout measures
that text.
"""

import tempfile
from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_layout.geometry import text_width
from fransys_model.derive.drawing_text import contact_image
from fransys_model.layout import Label, LabelKind, layout_of, profile_of

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
    d.wire(psu.output["+"], q.coil["A1"], wire=_WIRE)
    d.wire(psu.output["-"], q.coil["A2"], wire=_WIRE)
    d.wire(psu.output["+"], q.aux["13"], wire=_WIRE)
    d.wire(q.aux["14"], lamp["1"], wire=_WIRE)
    d.wire(psu.output["-"], lamp["2"], wire=_WIRE)
    d.wire(lamp["1"], block.no["53"], wire=_WIRE)
    d.wire(block.no["54"], lamp["2"], wire=_WIRE)
    d.wire(lamp["1"], block.nc["61"], wire=_WIRE)
    d.wire(block.nc["62"], lamp["2"], wire=_WIRE)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


@pytest.fixture(scope="module")
def tables() -> list[tuple[Label, list[str], int]]:
    """Each contact label, its entries (NO then NC), and the width its text needs."""
    model = _built().model
    profile = profile_of(model)
    found = []
    for label in layout_of(model, Label).values():
        if label.kind is LabelKind.CROSS_REFERENCE and label.slot == "contacts":
            no, nc = contact_image(model, label)
            texts = (*no, *nc, "NO", "NC")
            column = max(text_width(t, height=profile.text_height) for t in texts)
            found.append((label, [*no, *nc], 2 * (column + 2 * profile.marker_padding)))
    return found


def test_an_entry_names_a_place_in_another_set(tables) -> None:
    """The case is not vacuous: one entry carries the location prefix."""
    assert any("+FLD" in entry for _, entries, _ in tables for entry in entries)


def test_the_box_is_as_wide_as_its_widest_text(tables) -> None:
    """Every contact image box is at least as wide as two columns of its widest printed entry."""
    assert tables
    assert all(label.width >= needed for label, _, needed in tables)
