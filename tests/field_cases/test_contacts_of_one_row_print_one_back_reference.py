"""Field case: the contacts of one item that stand in one row print one back reference.
The bug: each pole printed its own back reference to the coil (`p1:1B`), three identical texts in one row.
Fixed by layout-0235 (owner, 2026-09-23): contacts of one item in one row print one back reference, the leftmost one's."""

from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from fransys_layout.drawing import DrawnText
    from fransys_model.kernel import Id, Model

_WIRE = (BU, 0.5)
_BESIDE = 24  # G: how near a text stands to count as beside the tag


def _built(relays: int = 12) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Poles", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    with d.function("A", "Control"):
        psu = d.device("G1", "DEMO-PSU-24")
        k1 = d.device("K1", "DEMO-RLY-4CO-24")
        d.series(psu.output["+"], k1.coil["A1"], wire=_WIRE)
        d.series(k1.coil["A2"], psu.output["-"], wire=_WIRE)
        for i in range(relays):  # enough relays to fill page 1, so the poles stand on page 2
            relay = d.device(f"R{i}", "DEMO-RLY-2CO-24")
            d.series(psu.output["+"], relay.coil["A1"], wire=_WIRE)
            d.series(relay.coil["A2"], psu.output["-"], wire=_WIRE)
    with d.function("B", "Load"):
        k2 = d.device("K2", "DEMO-RLY-4CO-24")
        d.series(psu.output["+"], k2.coil["A1"], wire=_WIRE)
        d.series(k2.coil["A2"], psu.output["-"], wire=_WIRE)
        lamps = [d.device(f"H{i}", "DEMO-LAMP-24") for i in range(3)]
        for i, (pole, next_pole) in enumerate(zip((k1.co_1, k1.co_2, k1.co_3), (k2.co_1, k2.co_2, k2.co_3), strict=True)):
            d.series(x1[i + 1], pole[f"{i + 1}1"], wire=_WIRE)
            d.series(pole[f"{i + 1}4"], next_pole[f"{i + 1}1"], wire=_WIRE)
            d.series(next_pole[f"{i + 1}4"], lamps[i].lamp[1], wire=_WIRE)
            d.series(lamps[i].lamp[2], psu.output["-"], wire=_WIRE)
    return fr.build(d, cabinet_document(cabinet))


def _pole_references(model: Model, tag: str) -> list[tuple[Id[Any], DrawnText]]:
    """The back references printed beside the relay `tag`'s tag texts, as (page, text).

    The Drawing names no subject, so a reference belongs to the tag text it stands beside.
    """
    return [
        (page, one)
        for page, drawing in drawn_pages(model).items()
        for name in drawing.texts
        if name.text == f"-{tag}"
        for one in drawing.texts
        if one.kind == "CROSS_REFERENCE" and abs(one.box.x - name.box.x) <= _BESIDE and abs(one.box.y - name.box.y) <= _BESIDE
    ]


def test_three_poles_in_one_row_print_one_back_reference() -> None:
    model = _built().model
    pages = layout_of(model, Page)
    for tag in ("K1", "K2"):
        references = _pole_references(model, tag)
        assert {pages[page].number for page, _ in references} == {2}  # the poles stand on page 2
        assert len(references) == 1, tag


@pytest.mark.parametrize("relays", [1, 3, 8])
def test_a_fold_of_one_row_draws_every_connection(relays: int) -> None:
    """KI-362 (closed), KI-364: a fold of one row draws every connection; the G1:- legs reach the trunk."""
    assert "CONNECTION_NOT_DRAWN" not in {f.code for f in _built(relays).findings}


@pytest.mark.rule("ROW-WRAP")
@pytest.mark.parametrize("relays", [11, 12, 13, 20])
def test_a_fold_wider_than_the_page_wraps_at_a_lane(relays: int) -> None:
    """The coils fold into one column wider than the page; it wraps at a lane, every coil stays drawn (layout-0464)."""
    result = _built(relays)
    assert not {"WIDER_THAN_PAGE", "PAGE_OVERFLOW", "PLACEMENT_PROBLEM", "CONNECTION_NOT_DRAWN"} & {f.code for f in result.findings}
    drawn = {t.text for drawing in drawn_pages(result.model).values() for t in drawing.texts}
    assert {f"-R{i}" for i in range(relays)} <= drawn
