"""The links and the outline the PDF reads from the model (NV2, NV3, PAGES-NAV).

The canary design (several drawing sets, cross references between pages) is built once. Every
link is a rectangle of a page's drawing that jumps to the partner's page; nothing parses a printed
"""

import importlib
import re
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

import fransys as fr
import pypdfium2
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys._link_boxes import link_boxes, where_links
from fransys._settings_library import library_of
from pypdfium2 import raw
from test_end_to_end import _flags
from test_reader_order import _design_and_rest, _other_documents

from fransys_model.derive import (
    cell_destination,
    document_export_name,
    documents,
    function_placements,
    function_role,
    mm_per_division,
    page_destination,
    page_nav,
)
from fransys_model.derive import drawn_pages as document_pages
from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.marker_text import marker_line_targets
from fransys_model.derive.page_nav import reference_links
from fransys_model.derive.page_reference_text import pdf_page
from fransys_model.derive.sheets import sheets
from fransys_model.kernel import id_namespace
from fransys_model.layout import FrameCell, LinkMarker, Page, layout_of, sheet_format_of
from fransys_model.vocab import PageKind, aspect_nodes

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_model.derive.page_nav import ReferenceLink
    from fransys_model.kernel import Id


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, object]:
    root = tmp_path_factory.mktemp("nav")
    d, cabinet, rest = _design_and_rest("a-")
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "c.md")
    result = fr.build(d, doc, *_other_documents(rest, root / "c.md"))
    return result, doc


def _cabinet_document(model):
    """The cabinet's document: the others print the lamp locations and the boards."""
    nodes = aspect_nodes(model)
    (record,) = (r for r in documents(model).values() if r.location and nodes[r.location].key[-1] == "C1")
    return record


def links_of(result) -> dict[Any, Any]:
    """Each drawn page's reference links, as the build gives the PDF."""
    model = result.model
    document = _cabinet_document(model).id
    boxes = link_boxes(model, result.drawings, library_of(result.settings))
    return {page.id: reference_links(model, document, page.id, boxes) for page in document_pages(model, document)}


def _all_links(result) -> list[tuple[Id[Page], ReferenceLink]]:
    """Each link the build kept, with the page it lies on."""
    return [(page, link) for page, found in links_of(result).items() for link in found]


def test_a_single_partner_label_links_its_whole_text_to_the_partners_page(built) -> None:
    model = built[0].model
    pages = layout_of(model, Page)
    drawn = drawn_pages(model)
    page, link = next((page, link) for page, link in _all_links(built[0]) if link.target != page_destination(model, pages[page]))
    assert link.target in {page_destination(model, other) for other in pages.values()}
    (text,) = [t for t in drawn[page].texts if (t.box.x, t.box.y) == (link.x, link.y)]
    assert link.height == text.box.h
    assert link.width <= text.box.w


def test_a_partner_outside_the_pdf_or_on_the_same_page_gets_no_link(built) -> None:
    model = built[0].model
    pages = layout_of(model, Page)
    found = _all_links(built[0])
    assert found
    here = {page: page_destination(model, pages[page]) for page in pages}
    assert not [page for page, link in found if link.target == here[page]]
    assert {link.target for _, link in found} <= set(here.values())


def _toc(pdf: pypdfium2.PdfDocument) -> list[tuple[int, str, int]]:
    """Each outline entry as (level, title, 0-based landing page), in outline order."""
    return [(b.level, b.get_title(), b.get_dest().get_index()) for b in pdf.get_toc()]


def _landing(pdf: pypdfium2.PdfDocument, name: str) -> int:
    dest = raw.FPDF_GetNamedDestByName(pdf.raw, name.encode("utf-8"))
    index: int = int(raw.FPDFDest_GetDestPageIndex(pdf.raw, dest))
    return index


def _written(root: Path, cover_pages: int) -> tuple[fr.BuildResult, pypdfium2.PdfDocument]:
    d, cabinet, rest = _design_and_rest("a-")
    # A cover taller than its page is COVER_OVERFLOW (pdf-0047): the extra pages are notes pages.
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    if cover_pages:
        notes = "\n\n".join("Notes line. " * 120 for _ in range(cover_pages))
        (root / "c.notes.md").write_text(notes, encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "c.md")
    result = fr.build(d, doc, *_other_documents(rest, root / "c.md"))
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    (pdf_path,) = (root / "out").glob("*C1.pdf")  # the cabinet's; the other documents write theirs
    return result, pypdfium2.PdfDocument(pdf_path)


def _sheet_entries(toc) -> list[tuple[int, str, list[str]]]:
    """Each sheet entry (`<n>` or `<n>: <title>`) as (landing page, title, the level-1 names under it), in order."""
    found: list[tuple[int, str, list[str]]] = []
    inside = False
    for level, title, page in toc:
        if level == 0:
            inside = re.fullmatch(r"\d+(: .*)?", title) is not None
            if inside:
                found.append((page, title, []))
        elif inside:
            assert page == found[-1][0]
            found[-1][2].append(title)
    return found


def test_the_outline_has_a_sheet_entry_per_sheet_and_no_terminals_or_pins(tmp_path) -> None:
    result, pdf = _written(tmp_path, 0)
    try:
        model = result.model
        record = _cabinet_document(model)
        found = sheets(model, record.id, (PageKind.SCHEMATIC,), ())
        entries = _sheet_entries(_toc(pdf))
        assert [page for page, _, _ in entries] == [_landing(pdf, page_destination(model, s)) for s in found]
        assert all(title.split(":")[0] == str(pdf_page(model, s)) for (_, title, _), s in zip(entries, found, strict=True))
        everything = [name for _, _, names in entries for name in names]
        assert everything
        assert not [name for name in everything if ":" in name]
    finally:
        pdf.close()


def test_an_item_on_two_sheets_has_an_entry_under_each_in_designation_order(tmp_path) -> None:
    _, pdf = _written(tmp_path, 0)
    try:
        entries = _sheet_entries(_toc(pdf))
    finally:
        pdf.close()
    with_relays = [names for _, _, names in entries if {"-K1", "-K2", "-K10"} <= set(names)]
    assert len(with_relays) >= 2
    for names in with_relays:
        assert names.index("-K2") < names.index("-K10")


@pytest.mark.parametrize("cover_pages", [0, 16])
def test_the_pdf_outline_nests_designations_under_each_sheet_and_lands_on_its_page(tmp_path: Path, cover_pages: int) -> None:
    result, pdf = _written(tmp_path, cover_pages)
    try:
        model = result.model
        record = _cabinet_document(model)
        found = sheets(model, record.id, (PageKind.SCHEMATIC,), ())
        toc = _toc(pdf)
        at = [i for i, (_, title, _) in enumerate(toc) if re.fullmatch(r"\d+(: .*)?", title)]
        assert len(at) == len(found)
        entries = _sheet_entries(toc)
        for start, sheet, (page, title, names) in zip(at, found, entries, strict=True):
            level, _, landing = toc[start]
            assert (level, landing) == (0, _landing(pdf, page_destination(model, sheet)))
            assert title.split(":")[0] == str(pdf_page(model, sheet))
            below = toc[start + 1 : start + 1 + len(names)]
            assert below == [(1, name, page) for name in names]
    finally:
        pdf.close()


def _link_annotations(pdf: pypdfium2.PdfDocument, index: int) -> list[tuple[tuple[Any, ...], int]]:
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
        record = _cabinet_document(model)
        printed = [p for p in sheets(model, record.id, (PageKind.SCHEMATIC,), ()) if isinstance(p, Page)]
        total = 0
        for page in printed:
            sheet = sheet_format_of(model, page.sheet_format)
            expected = links_of(result)[page.id]
            actual = _link_annotations(pdf, _landing(pdf, page_destination(model, page)))
            total += len(expected)
            got = sorted(actual)
            want = sorted(
                (
                    (
                        float(grid_to_mm(sheet.content_x_mm, link.x, mm_per_division(model, sheet))),
                        float(grid_to_mm(sheet.content_y_mm, link.y, mm_per_division(model, sheet))),
                        round(
                            float(
                                grid_to_mm(
                                    sheet.content_x_mm,
                                    link.x + link.width,
                                    mm_per_division(model, sheet),
                                )
                            ),
                            1,
                        ),
                        round(
                            float(
                                grid_to_mm(
                                    sheet.content_y_mm,
                                    link.y + link.height,
                                    mm_per_division(model, sheet),
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
    assert _parent(toc, "-S1") == "Connector list"


# PDF-LINKS (designer R2077): every reference to a place in the same PDF is a link that lands on that place's cell.
_MM = 25.4 / 72


def _read_links(pdf: pypdfium2.PdfDocument, index: int) -> list[Any]:
    """Each /Link annotation of page `index`: its (left, top, right, bottom) in mm, the page index it lands on and the mm from the top it lands at."""
    page = pdf.get_page(index)
    found = []
    try:
        for n in range(raw.FPDFPage_GetAnnotCount(page.raw)):
            annot = raw.FPDFPage_GetAnnot(page.raw, n)
            if raw.FPDFAnnot_GetSubtype(annot) == raw.FPDF_ANNOT_LINK:
                rect = raw.FS_RECTF()
                raw.FPDFAnnot_GetRect(annot, rect)
                height = page.get_height()
                box = (rect.left * _MM, (height - rect.top) * _MM, rect.right * _MM, (height - rect.bottom) * _MM)
                dest = raw.FPDFLink_GetDest(pdf.raw, raw.FPDFAnnot_GetLink(annot))
                flags, y = [raw.FPDF_BOOL() for _ in range(3)], raw.FS_FLOAT()
                raw.FPDFDest_GetLocationInPage(dest, *flags, raw.FS_FLOAT(), y, raw.FS_FLOAT())
                found.append((box, raw.FPDFDest_GetDestPageIndex(pdf.raw, dest), (height - y.value) * _MM))
            raw.FPDFPage_CloseAnnot(annot)
    finally:
        page.close()
    return found


def _landings(model, document) -> dict[str, tuple[int, float, float]]:
    """Each cell destination label of `document`'s pages to (pdf page index, cell top in mm, cell height in mm), recomputed, never parsed."""
    found = {}
    for page in document_pages(model, document):
        sheet = sheet_format_of(model, page.sheet_format)
        rows = sheet.content_height_mm / sheet.frame_rows
        for column in range(1, sheet.frame_columns + 1):
            for row in range(sheet.frame_rows):
                label = cell_destination(model, page, FrameCell(column=column, row=chr(ord("A") + row)))
                found[label] = (pdf_page(model, page) - 1, sheet.content_y_mm + row * rows, rows)
    return found


def _expected(result, document) -> dict[Any, list[ReferenceLink]]:
    """Each drawn page of `document` to the links the build gives its PDF: its markers' lines and its where-texts."""
    model = result.model
    boxes = link_boxes(model, result.drawings, library_of(result.settings))
    return {
        page.id: [*reference_links(model, document, page.id, boxes), *where_links(result.drawings[page.id])]
        for page in document_pages(model, document)
    }


def _compare(result, root: Path) -> list[tuple[Any, int]]:
    """Write `result`; each annotation equals its expected link: box, page, cell top within one cell. Returns (link, own page index)."""
    fr.write(result, root)
    model, seen = result.model, []
    for record in documents(model).values():
        pdf = pypdfium2.PdfDocument(root / document_export_name(model, None, record))
        landing = _landings(model, record.id)
        for page, links in _expected(result, record.id).items():
            sheet = sheet_format_of(model, layout_of(model, Page)[page].sheet_format)
            scale = mm_per_division(model, sheet)
            at = pdf_page(model, layout_of(model, Page)[page]) - 1
            want = sorted(
                (
                    float(grid_to_mm(sheet.content_x_mm, link.x, scale)),
                    float(grid_to_mm(sheet.content_y_mm, link.y, scale)),
                    float(grid_to_mm(sheet.content_x_mm, link.x + link.width, scale)),
                    float(grid_to_mm(sheet.content_y_mm, link.y + link.height, scale)),
                    *landing[link.target],
                )
                for link in links
            )
            got = sorted(_read_links(pdf, at))
            assert len(got) == len(want)
            for (box, index, top), (*spot, index_want, top_want, cell) in zip(got, want, strict=True):
                assert box == pytest.approx(spot, abs=0.1)
                assert index == index_want
                assert abs(top - top_want) <= cell
            seen += [(link, at) for link in links]
        pdf.close()
    return seen


@pytest.fixture(scope="module")
def flags(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, Path]:
    d = fr.design("demo_parts")
    d.add(_flags, "U1")
    return fr.build(d, unit_document("demo-flags")), tmp_path_factory.mktemp("flags")


@pytest.mark.rule("PDF-LINKS")
def test_every_marker_line_is_a_link_over_its_box_landing_on_its_cell_even_on_the_same_page(flags) -> None:
    """Acceptance 1, 3: the marker links of the 12-circuit unit, same page included, read back from the compiled PDF."""
    result, root = flags
    seen = _compare(result, root)
    model = result.model
    landing = {label: where for record in documents(model).values() for label, where in _landings(model, record.id).items()}
    own = [(link, at) for link, at in seen if landing[link.target][0] == at]
    assert own, "a marker names a cell of its own page"
    assert len(seen) > len(own) > 0
    named = [end for m in layout_of(model, LinkMarker).values() for end in marker_line_targets(model, m) if end is not None]
    assert len(seen) == len(named)


@pytest.fixture(scope="module")
def mcc(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Path]:
    run = importlib.import_module("placement_corpus.run")
    case = next(c for c in run.circuits("standard") if c[0] == "mcc")
    return run.build("mcc", case), tmp_path_factory.mktemp("mcc")


@pytest.mark.private_input
@pytest.mark.rule("PDF-LINKS")
def test_every_where_line_of_a_terminal_copy_is_a_link_over_its_text_landing_on_the_copy(mcc) -> None:
    """Acceptance 1: a terminal placed twice in one PDF links each where line to the other placement, one per placement pair."""
    result, root = mcc
    model = result.model
    seen = _compare(result, root)
    where = [t for drawing in result.drawings.values() for t in drawing.texts if t.kind == "WHERE"]
    pairs = sum(len(p) * (len(p) - 1) for f, p in function_placements(model).items() if len(p) > 1 and function_role(model, f).terminal)
    assert len(where) == pairs > 0
    assert sum(link.target in {t.link for t in where} for link, _ in seen) >= len(where)
    assert all(t.link for t in where)


@pytest.mark.private_input
@pytest.mark.rule("PDF-LINKS")
def test_a_marker_with_two_targets_has_two_links_each_landing_on_its_own_page(mcc, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Acceptance 2: a marker box naming two ends is cut in two strips, each landing on its own end's page."""
    result, _ = mcc
    model = result.model
    markers = layout_of(model, LinkMarker)
    pages = layout_of(model, Page)
    one = next(m for m in markers.values() if m.star is None and markers[m.partner].page != m.page)
    far = markers[one.partner].page
    other = next(m for m in markers.values() if m.page not in {one.page, far})
    ends = (markers[one.partner], other)
    real = page_nav.marker_line_targets
    monkeypatch.setattr(page_nav, "marker_line_targets", lambda model, m: ends if m.id == one.id else real(model, m))
    document = next(r.id for r in documents(model).values())
    boxes = link_boxes(model, result.drawings, library_of(result.settings))
    bx, by, bw, bh = boxes[one.id]
    cut = [
        k
        for k in reference_links(model, document, one.page, boxes)
        if bx <= k.x and by <= k.y and k.x + k.width <= bx + bw and k.y + k.height <= by + bh
    ]
    landing = _landings(model, document)
    assert len(cut) == 2
    assert {landing[link.target][0] for link in cut} == {pdf_page(model, pages[end.page]) - 1 for end in ends}
    assert {k.target for k in cut} <= {link.target for link, _ in _compare(result, tmp_path)}  # the compiled PDF holds both, read back


def _flags_pdfs(root: Path, salt: str | None) -> dict[str, bytes]:
    """The 12-circuit unit built and written, under the id salt `salt` or the default ids: each PDF's bytes."""
    with id_namespace(salt) if salt else nullcontext():
        d = fr.design("demo_parts")
        d.add(_flags, "U1")
        fr.write(fr.build(d, unit_document("demo-flags")), root)
    return {pdf.name: pdf.read_bytes() for pdf in root.glob("*.pdf")}


def _pdf_links(pdfs: dict[str, bytes]) -> list[Any]:
    """Every page's annotations of every PDF: box, landing page, landing height."""
    found = []
    for name in sorted(pdfs):
        pdf = pypdfium2.PdfDocument(pdfs[name])
        found += [sorted(_read_links(pdf, index)) for index in range(len(pdf))]
        pdf.close()
    return found


def test_the_pdf_with_its_links_is_the_same_bytes_on_every_build_and_its_landings_the_same_under_a_salt(tmp_path: Path) -> None:
    """Acceptance 5: two builds write one PDF, byte for byte; under another salt the landings are the same (a marker may stand elsewhere)."""
    first = _flags_pdfs(_sub(tmp_path, "one"), None)
    assert first
    assert _flags_pdfs(_sub(tmp_path, "two"), None) == first
    links = _pdf_links(first)
    assert sum(map(len, links)) > 10
    landings = sorted((index, round(top, 3)) for page in links for _, index, top in page)
    salted = _pdf_links(_flags_pdfs(_sub(tmp_path, "salted"), "d"))
    assert sorted((index, round(top, 3)) for page in salted for _, index, top in page) == landings
