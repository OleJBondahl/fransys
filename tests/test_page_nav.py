"""The links and the outline the PDF reads from the model (NV2, NV3, PAGES-NAV).

The canary design (several drawing sets, cross references between pages) is built once. Every
link comes from a `Label.partners` record; nothing parses a printed text.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pypdfium2
import pytest
from pypdfium2 import raw
from test_reader_order import _design

from fransys_model.derive import page_destination
from fransys_model.derive.contact_image import cross_reference_text
from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.page_nav import outline_sheets, reference_links
from fransys_model.derive.sheets import sheets
from fransys_model.layout import Label, LabelKind, Page, layout_of, sheet_format_of
from fransys_model.vocab import PageKind, documents

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, object]:
    root = tmp_path_factory.mktemp("nav")
    d, cabinet = _design("a-")
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "c.md")
    result = fr.build(d, doc)
    return result, doc


def _tag_references(model) -> list[Label]:
    return [
        label
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.CROSS_REFERENCE and label.slot == "tag"
    ]


def _sheet_ids(found):
    """The page ids of `found`, a diagram sheet kept as it is (`outline_sheets` takes either)."""
    return [s.id if isinstance(s, Page) else s for s in found]


def test_a_single_partner_label_links_its_whole_text_to_the_partners_page(built) -> None:
    model = built[0].model
    pages = layout_of(model, Page)
    known = set(pages)
    label = next(ref for ref in _tag_references(model) if ref.partners[0].page != ref.page)
    (link,) = [
        found
        for found in reference_links(model, label.page, known)
        if (found.x, found.y) == (label.x, label.y)
    ]
    assert link.target == page_destination(model, pages[label.partners[0].page])
    assert link.height == label.height
    assert link.width <= label.width
    assert cross_reference_text(model, label)


def test_a_partner_outside_the_pdf_or_on_the_same_page_gets_no_link(built) -> None:
    model = built[0].model
    pages = layout_of(model, Page)
    label = next(ref for ref in _tag_references(model) if ref.partners[0].page != ref.page)
    here = label.page
    others = set(pages) - {label.partners[0].page}
    assert not [
        found
        for found in reference_links(model, here, others)
        if (found.x, found.y) == (label.x, label.y)
    ]


def test_the_outline_has_a_sheet_entry_per_sheet_and_no_terminals_or_pins(built) -> None:
    model = built[0].model
    (record,) = documents(model).values()
    found = sheets(model, record.id, (PageKind.SCHEMATIC,))
    outline = outline_sheets(model, _sheet_ids(found))
    assert [entry.destination for entry in outline] == [page_destination(model, s) for s in found]
    assert all(entry.title.startswith("Sheet ") for entry in outline)
    everything = [name for entry in outline for name in entry.entries]
    assert everything
    assert not [name for name in everything if ":" in name]


def test_an_item_on_two_sheets_has_an_entry_under_each_in_designation_order(built) -> None:
    model = built[0].model
    outline = outline_sheets(model, layout_of(model, Page))
    with_relays = [e for e in outline if {"-K1", "-K2", "-K10"} <= set(e.entries)]
    assert len(with_relays) >= 2
    for entry in with_relays:
        assert entry.entries.index("-K2") < entry.entries.index("-K10")


def _toc(pdf: pypdfium2.PdfDocument) -> list[tuple[int, str, int]]:
    """Each outline entry as (level, title, 0-based landing page), in outline order."""
    return [(b.level, b.get_title(), b.get_dest().get_index()) for b in pdf.get_toc()]


def _landing(pdf: pypdfium2.PdfDocument, name: str) -> int:
    dest = raw.FPDF_GetNamedDestByName(pdf.raw, name.encode("utf-8"))
    return raw.FPDFDest_GetDestPageIndex(pdf.raw, dest)


def _written(root: Path, cover_pages: int) -> tuple[fr.BuildResult, pypdfium2.PdfDocument]:
    d, cabinet = _design("a-")
    # A cover taller than its page is COVER_OVERFLOW (pdf-0047): the extra pages are notes pages.
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    if cover_pages:
        notes = "\n\n".join("Notes line. " * 120 for _ in range(cover_pages))
        (root / "c.notes.md").write_text(notes, encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "c.md")
    result = fr.build(d, doc)
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    (pdf_path,) = (root / "out").glob("*.pdf")
    return result, pypdfium2.PdfDocument(pdf_path)


@pytest.mark.parametrize("cover_pages", [0, 16])
def test_the_pdf_outline_nests_designations_under_each_sheet_and_lands_on_its_page(
    tmp_path: Path, cover_pages: int
) -> None:
    result, pdf = _written(tmp_path, cover_pages)
    try:
        model = result.model
        (record,) = documents(model).values()
        expected = outline_sheets(
            model, _sheet_ids(sheets(model, record.id, (PageKind.SCHEMATIC,)))
        )
        toc = _toc(pdf)
        at = [i for i, (_, title, _) in enumerate(toc) if title.startswith("Sheet ")]
        assert len(at) == len(expected)
        for start, entry in zip(at, expected, strict=True):
            level, title, page = toc[start]
            assert (level, title, page) == (0, entry.title, _landing(pdf, entry.destination))
            below = toc[start + 1 : start + 1 + len(entry.entries)]
            assert below == [(1, name, page) for name in entry.entries]
    finally:
        pdf.close()


def _link_annotations(pdf: pypdfium2.PdfDocument, index: int) -> list[tuple[tuple, int]]:
    """Each /Link annotation of page `index` as ((left, top, right, bottom) in mm, target page)."""
    page = pdf.get_page(index)
    found = []
    try:
        for n in range(raw.FPDFPage_GetAnnotCount(page.raw)):
            annot = raw.FPDFPage_GetAnnot(page.raw, n)
            if raw.FPDFAnnot_GetSubtype(annot) != raw.FPDF_ANNOT_LINK:
                continue
            rect = raw.FS_RECTF()
            raw.FPDFAnnot_GetRect(annot, rect)
            height = page.get_height()
            mm = 25.4 / 72
            box = (
                rect.left * mm,
                (height - rect.top) * mm,
                rect.right * mm,
                (height - rect.bottom) * mm,
            )
            dest = raw.FPDFLink_GetDest(pdf.raw, raw.FPDFAnnot_GetLink(annot))
            found.append((box, raw.FPDFDest_GetDestPageIndex(pdf.raw, dest)))
            raw.FPDFPage_CloseAnnot(annot)
    finally:
        page.close()
    return found


def test_each_reference_label_is_a_link_over_its_box_to_the_partners_sheet(tmp_path) -> None:
    result, pdf = _written(tmp_path, 0)
    try:
        model = result.model
        (record,) = documents(model).values()
        printed = [
            p for p in sheets(model, record.id, (PageKind.SCHEMATIC,)) if isinstance(p, Page)
        ]
        pages = {page.id: page for page in printed}
        total = 0
        for page in printed:
            sheet = sheet_format_of(model, page.sheet_format)
            expected = reference_links(model, page.id, set(pages))
            actual = _link_annotations(pdf, _landing(pdf, page_destination(model, page)))
            total += len(expected)
            got = sorted(actual)
            want = sorted(
                (
                    (
                        float(grid_to_mm(sheet.content_x_mm, link.x, sheet.module_mm)),
                        float(grid_to_mm(sheet.content_y_mm, link.y, sheet.module_mm)),
                        round(
                            float(
                                grid_to_mm(sheet.content_x_mm, link.x + link.width, sheet.module_mm)
                            ),
                            1,
                        ),
                        round(
                            float(
                                grid_to_mm(
                                    sheet.content_y_mm, link.y + link.height, sheet.module_mm
                                )
                            ),
                            1,
                        ),
                    ),
                    _landing(pdf, link.target),
                )
                for link in expected
            )
            assert [t for _, t in got] == [t for _, t in want]
            for (box, _), (spot, _) in zip(got, want, strict=True):
                assert box == pytest.approx(spot, abs=0.1)
        assert total >= 2
    finally:
        pdf.close()


def test_the_links_change_no_printed_page(tmp_path, monkeypatch) -> None:
    """Links are invisible (NV1): every page's text and pixels equal those of a build without."""
    from fransys_pdf import _drawings

    _, with_links = _written(_sub(tmp_path, "with"), 0)
    monkeypatch.setattr(_drawings, "page_links", lambda *_: "")
    _, without = _written(_sub(tmp_path, "without"), 0)
    try:
        assert len(with_links) == len(without) > 2
        for index in range(len(with_links)):
            one, two = with_links.get_page(index), without.get_page(index)
            assert one.get_textpage().get_text_range() == two.get_textpage().get_text_range()
            assert one.render(scale=1).to_pil().tobytes() == two.render(scale=1).to_pil().tobytes()
            one.close()
            two.close()
    finally:
        with_links.close()
        without.close()


def _sub(root, name):
    (root / name).mkdir()
    return root / name


def _parent(toc: list[tuple[int, str, int]], name: str) -> str:
    """The title of the level-0 entry the first level-1 entry `name` sits under."""
    at = next(i for i, (level, title, _) in enumerate(toc) if level == 1 and title == name)
    return next(title for level, title, _ in reversed(toc[:at]) if level == 0)


def test_a_list_pages_designations_sit_under_that_pages_title_never_under_a_sheet(
    tmp_path: Path,
) -> None:
    _, pdf = _written(tmp_path, 0)
    try:
        toc = _toc(pdf)
    finally:
        pdf.close()
    assert _parent(toc, "-X1") == "Terminal list"
    # the canary's only connectors at C1 are a harness's plugs, which no location document draws
    # (pdf-0043), so it has no connector list
    assert "Connector list" not in {title for level, title, _ in toc if level == 0}
