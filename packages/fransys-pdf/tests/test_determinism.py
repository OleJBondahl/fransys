"""Determinism: the authored date, never the clock."""

from decimal import Decimal

from _build import document, location, model, project, revision_entry
from fransys_pdf._geometry import document_metadata
from fransys_pdf._links import page_links

from fransys_model.derive import SheetRow, document_row
from fransys_model.derive.page_nav import PageAnchor, ReferenceLink
from fransys_model.vocab import DocumentPreset


def _metadata(*records):
    """`document_metadata` of a location document about `C1`, in the model of `records`."""
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover")
    m = model(c1, doc, *records)
    return document_metadata(m, document_row(m, doc.id))


def test_date_is_the_authored_revision_date_not_auto():
    entry = revision_entry("r1", unit=None, revision=1, date="2026-09-22")
    text = _metadata(project(title="T", author="A"), entry)
    assert "date: datetime(year: 2026, month: 9, day: 22)" in text
    assert "auto" not in text


def test_title_and_author_come_from_the_project():
    text = _metadata(project(title="Demo cabinet", author="demo"))
    assert 'title: "Demo cabinet"' in text
    assert 'author: "demo"' in text


def test_no_project_gives_date_none_and_empty_title_and_author():
    text = _metadata()
    assert "date: none" in text
    assert 'title: ""' in text
    assert 'author: ""' in text


def test_a_pages_links_and_anchors_are_the_same_source_every_time_and_name_each_destination_once():
    """PDF-LINKS: a link and an anchor each print one Typst element, and the same inputs print the same text."""
    sheet = SheetRow(
        width_mm=420, height_mm=297, content_x_mm=15, content_y_mm=10, content_width_mm=390, content_height_mm=250, module_mm=Decimal("2.5")
    )
    links = (ReferenceLink(x=4, y=8, width=40, height=2, target="p2:B2"),)
    anchors = (PageAnchor(label="p2:B2", x=Decimal(15), y=Decimal("41.25")),)
    m = model()
    text = page_links(m, sheet, links, anchors)
    assert text == page_links(m, sheet, links, anchors)
    assert text.count('#label("p2:B2")') == 1
    assert text.count("link(<p2:B2>") == 1
    assert "dx: 15.000mm, dy: 41.250mm" in text
