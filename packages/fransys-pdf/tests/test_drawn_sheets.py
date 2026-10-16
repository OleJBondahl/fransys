"""`derive.drawn_sheets`: the drawn pages and sheets pdf reads as plain rows (OUTPUT-DOORS)."""

from _build import document, drawing_set, layout_page, location, model, sheet_format

from fransys_model.derive import (
    document_sheet,
    kind_sheet,
    mixed_sheet_groups,
    schematic_page_ids,
)
from fransys_model.layout import a2_sheet_format
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind
_SCHEMATIC = (K.SCHEMATIC,)


def _cabinet(*formats):
    """A cabinet document whose one drawing set has a page per entry of `formats`."""
    c1 = location("C1", "Demo cabinet")
    ds = drawing_set("ds1", location=c1)
    records: list = [c1, ds]
    for index, fmt in enumerate(formats, start=1):
        records += [] if fmt is None else [fmt]
        records.append(layout_page(f"p{index}", drawing_set=ds, number=index, sheet_format=fmt))
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover")
    return model(*records, doc), doc


def test_schematic_page_ids_are_the_pages_in_number_order() -> None:
    a4 = sheet_format("a4", width_mm=210, height_mm=297)
    m, doc = _cabinet(a4, a4)
    ids = schematic_page_ids(m, doc.id, _SCHEMATIC)
    assert len(ids) == 2
    assert schematic_page_ids(m, doc.id, (K.COVER,)) == ()


def test_mixed_sheet_groups_name_each_format_with_its_page_numbers() -> None:
    a4 = sheet_format("a4", width_mm=210, height_mm=297)
    a3 = sheet_format("a3", width_mm=420, height_mm=297)
    m, doc = _cabinet(a4, a3, a4)
    got = [(g.name, g.numbers) for g in mixed_sheet_groups(m, doc.id, _SCHEMATIC)]
    assert got == [("a4", (1, 3)), ("a3", (2,))]


def test_one_format_or_no_schematic_is_not_mixed() -> None:
    a4 = sheet_format("a4", width_mm=210, height_mm=297)
    a3 = sheet_format("a3", width_mm=420, height_mm=297)
    same, doc = _cabinet(a4, a4)
    assert mixed_sheet_groups(same, doc.id, _SCHEMATIC) == ()
    mixed, doc2 = _cabinet(a4, a3)
    assert mixed_sheet_groups(mixed, doc2.id, (K.COVER,)) == ()


def test_document_sheet_is_the_first_pages_format_in_mm() -> None:
    a4 = sheet_format("a4", width_mm=210, height_mm=297)
    m, doc = _cabinet(a4)
    row = document_sheet(m, doc.id, _SCHEMATIC)
    assert (row.width_mm, row.height_mm) == (210, 297)


def test_kind_sheet_of_a_block_diagram_is_the_house_a2_sheet() -> None:
    a2 = a2_sheet_format()
    m, _doc = _cabinet(None)
    row = kind_sheet(m, K.BLOCK_DIAGRAM)
    assert (row.width_mm, row.height_mm, row.module_mm) == (a2.width_mm, a2.height_mm, a2.module_mm)
