"""Field case: a unit whose first drawing set is numbered 2 is set 1 of its own PDF.

The engineering shape: a container unit holds a cabinet unit. The document numbers the sets
design-wide, so the container's set is 1 and the cabinet unit's set is 2. Each unit's PDF counts
its own sets, so the cabinet unit's page is `p1.1` in the PDF the engineer holds.

The bug: the PDF's named destination and sheet text said `p1.1` (`set_rank`), but the render
check text and the drawing's own derived reference text printed the design-wide `p2.1`, a page
no PDF shows. The rule (render-0018, amending render-0015): every printed page reference names
its set by `set_rank`, and `page_reference_text` is the one function that prints it.
"""

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages

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


class _Supply(NamedTuple):
    T1: Any


@fr.unit("demo-supply-cab", **_UNIT)
def _supply_cab(u: Any) -> _Supply:
    t1 = u.device("T1", "DEMO-PSU-24", interface=("output",))
    lamp = u.device("H2", "DEMO-LAMP-24")
    u.detail.wire(lamp["1"], t1.output["+"], wire=("WH", 0.5))
    u.detail.wire(lamp["2"], t1.output["-"], wire=("WH", 0.5))
    return _Supply(t1)


def _built() -> Model:
    @fr.unit("demo-container", **_UNIT)
    def container(c: Any) -> _Supply:
        io = c.add(_supply_cab, "U1")
        lamp = c.device("H1", "DEMO-LAMP-24")
        c.detail.wire(lamp["1"], io.T1.output["+"], wire=("WH", 0.5))
        c.detail.wire(lamp["2"], io.T1.output["-"], wire=("WH", 0.5))
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


def test_a_reference_from_another_page_names_the_units_first_set_one() -> None:
    model = _built()
    page = _inner_page(model)
    other = next(p for p in layout_of(model, Page).values() if p.id != page.id)
    drawing = drawn_pages(model)[other.id]
    shown = [t.text for t in drawing.texts]
    shown += [text for one in drawing.symbols for _, text in one.slots]
    assert any(text.startswith("p1.1:") for text in shown)
