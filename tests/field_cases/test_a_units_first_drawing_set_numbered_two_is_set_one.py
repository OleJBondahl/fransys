"""Field case: a container unit holds a cabinet unit, and the document numbers the drawing sets design-wide, so the cabinet's set is 2.
The bug: the PDF's sheet text said p1.1, but the render check and the derived reference text printed the design-wide p2.1.
Fixed by render-0018 (amends render-0015), every printed page reference names its set by set_rank, and page_reference_text prints it."""

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from test_a_unit_boundary_port_wired_inside_and_out import _supply_cab

from fransys_model.derive.page_destination import page_destination
from fransys_model.derive.page_reference_text import page_reference_text
from fransys_model.layout import DrawingSet, Page, layout_of

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}


def _built() -> Model:
    @fr.unit("demo-container", **_UNIT)
    def container(c: Any) -> Any:
        io = c.add(_supply_cab, "U1")
        lamp = c.device("H1", "DEMO-LAMP-24")
        c.series(lamp["1"], io.T1.output["+"], wire=("WH", 0.5))
        c.series(lamp["2"], io.T1.output["-"], wire=("WH", 0.5))
        return io

    d = fr.design("demo_parts")
    d.add(container, "C1", place=None)
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-container", cover=root / "c.md")
    inner = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-supply-cab", cover=root / "c.md")
    return fr.build(d, cover, inner).model  # its own document: one printer per set (R331)


def _inner_page(model: Model) -> Page:
    sets = layout_of(model, DrawingSet)
    (page,) = (p for p in layout_of(model, Page).values() if sets[p.drawing_set].number == 2)
    return page


def test_a_units_first_set_numbered_two_is_named_set_one_everywhere() -> None:
    model = _built()
    page = _inner_page(model)
    assert page_destination(model, page) == "p1.1"
    assert page_reference_text(model, page, with_location=True).endswith("p1.1")


@pytest.mark.rule("G12-UNIT-SCOPE")
def test_a_conductor_leaving_the_documents_unit_ends_in_a_stub_naming_the_far_end_and_no_page() -> None:
    model = _built()
    drawing = drawn_pages(model)[next(p.id for p in layout_of(model, Page).values() if p.id != _inner_page(model).id)]
    shown = [t.text for t in drawing.texts] + [text for one in drawing.symbols for _, text in one.slots]
    assert {"← -U1-T1:+", "→ -U1-T1:-"} <= set(shown)
    assert not any(t.startswith("p1.1:") for t in shown)
