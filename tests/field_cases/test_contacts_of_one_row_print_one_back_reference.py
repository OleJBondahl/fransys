"""Field case: the contacts of one item that stand in one row print one back reference.

The engineering shape: a relay K1 with four changeover contacts whose coil stands on page 1,
among a dozen other relays, and whose first three poles each feed the matching pole of a second
such relay K2 (a pole link), side by side in one row on page 2.

The bug: each pole printed its own back reference to the coil ("p1:1B"), three identical texts
in one row, one per pole, where one back reference was meant.
The rule (decision layout-0235, the owner's "few references", 2026-09-23): contact functions of
one item that stand in one row print one back reference, the leftmost one's, beside the item's
tag. The coil's contact table still lists every pole.
"""

from typing import TYPE_CHECKING

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from _tables_on import TABLES_ON
from fransys.colours import BU

from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from fransys_layout.drawing import DrawnText
    from fransys_model.kernel import Id, Model

_WIRE = (BU, 0.5)
_BESIDE = 24  # G: how near a text stands to count as beside the tag


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Poles", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    with d.function("A", "Control"):
        psu = d.device("G1", "DEMO-PSU-24")
        k1 = d.device("K1", "DEMO-RLY-4CO-24")
        d.detail.wire(psu.output["+"], k1.coil["A1"], wire=_WIRE)
        d.detail.wire(k1.coil["A2"], psu.output["-"], wire=_WIRE)
        for i in range(12):  # enough relays to fill page 1, so the poles stand on page 2
            relay = d.device(f"R{i}", "DEMO-RLY-2CO-24")
            d.detail.wire(psu.output["+"], relay.coil["A1"], wire=_WIRE)
            d.detail.wire(relay.coil["A2"], psu.output["-"], wire=_WIRE)
    with d.function("B", "Load"):
        k2 = d.device("K2", "DEMO-RLY-4CO-24")
        d.detail.wire(psu.output["+"], k2.coil["A1"], wire=_WIRE)
        d.detail.wire(k2.coil["A2"], psu.output["-"], wire=_WIRE)
        lamps = [d.device(f"H{i}", "DEMO-LAMP-24") for i in range(3)]
        for i, (pole, next_pole) in enumerate(
            zip((k1.co_1, k1.co_2, k1.co_3), (k2.co_1, k2.co_2, k2.co_3), strict=True)
        ):
            d.detail.wire(x1[i + 1], pole[f"{i + 1}1"], wire=_WIRE)
            d.detail.wire(pole[f"{i + 1}4"], next_pole[f"{i + 1}1"], wire=_WIRE)
            d.detail.wire(next_pole[f"{i + 1}4"], lamps[i].lamp[1], wire=_WIRE)
    return fr.build(d, cabinet_document(cabinet), settings=TABLES_ON)


def _pole_references(model: Model, tag: str) -> list[tuple[Id, DrawnText]]:
    """The back references printed beside the relay `tag`'s tag texts, as (page, text).

    The Drawing names no subject, so a reference belongs to the tag text it stands beside.
    """
    return [
        (page, one)
        for page, drawing in drawn_pages(model).items()
        for name in drawing.texts
        if name.text == f"-{tag}"
        for one in drawing.texts
        if one.kind == "CROSS_REFERENCE"
        and abs(one.box.x - name.box.x) <= _BESIDE
        and abs(one.box.y - name.box.y) <= _BESIDE
    ]


def test_three_poles_in_one_row_print_one_back_reference() -> None:
    model = _built().model
    pages = layout_of(model, Page)
    for tag in ("K1", "K2"):
        references = _pole_references(model, tag)
        assert {pages[page].number for page, _ in references} == {2}  # the poles stand on page 2
        assert len(references) == 1, tag


def test_the_row_raises_no_text_finding() -> None:
    codes = {f.code for f in _built().findings}
    assert not {"TEXT_OVERLAP", "LABEL_UNPLACED", "ANNEX_UNPLACED"} & codes
