"""The three title-block findings of `fransys_render.sheet_check`, built on the pdf test models.

They moved to render with the title block (render-0019); the models come from this package's
`_build` helpers, which the render tests do not have.
"""

import dataclasses
from decimal import Decimal

from _build import document, drawing_set, layout_page, location, model
from fransys_render import sheet_check, sheets

from fransys_model.derive import document_sheets_of
from fransys_model.kernel import Severity, make_id
from fransys_model.layout import Profile, SheetFormat, default_profile
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind
_PRESET = DocumentPreset.CABINET_SCHEMATIC
_NO_SCHEMATIC_OR_LISTS = (K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.CONNECTOR_LIST, K.BOM)


def _cabinet(fmt: SheetFormat | None = None, profile: Profile | None = None):
    c1 = location("C1", "Demo cabinet")
    ds = drawing_set("ds1", location=c1)
    page = layout_page("p1", drawing_set=ds, number=1, sheet_format=fmt)
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.CONNECTOR_LIST, K.BOM),
    )
    return model(*[r for r in (c1, fmt, profile, ds, page, doc) if r is not None]), doc


def _tight(height: int) -> SheetFormat:
    key = ("sheet_format", f"tight{height}")
    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name=f"tight{height}",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=height,
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )


def _only(findings, code):
    return [f for f in findings if f.code == code]


def test_title_block_no_room_absent_for_the_house_sheets_exact_20mm_band():
    m, _doc = _cabinet()
    assert _only(sheet_check(m, document_sheets_of(m)), "TITLE_BLOCK_NO_ROOM") == []


def test_title_block_no_room_absent_for_a_20mm_band_and_present_for_a_19mm_one():
    """The off-by-one: 20 mm fits, one mm less does not."""
    m20, _doc = _cabinet(_tight(257))  # band = (297-10) - (10+257) = 20
    assert _only(sheet_check(m20, document_sheets_of(m20)), "TITLE_BLOCK_NO_ROOM") == []
    m19, doc = _cabinet(_tight(258))
    (finding,) = _only(sheet_check(m19, document_sheets_of(m19)), "TITLE_BLOCK_NO_ROOM")
    assert finding.subjects == (doc.id,)
    assert "19" in finding.message


def test_title_block_no_room_is_a_warning_naming_the_sheet_format_and_its_band_height():
    m, doc = _cabinet(_tight(265))  # band = (297-10) - (10+265) = 12
    (finding,) = _only(sheet_check(m, document_sheets_of(m)), "TITLE_BLOCK_NO_ROOM")
    assert finding.severity is Severity.WARNING
    assert finding.subjects == (doc.id,)
    assert "tight265" in finding.message
    assert "12" in finding.message


def _notice_model(notice: str):
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        remove=_NO_SCHEMATIC_OR_LISTS,
        notice=notice,
    )
    return model(c1, doc), doc


def test_notice_overflow_names_the_document_and_where_the_notice_is_authored():
    """pdf-0036: the finding reads `Document.notice`, needs no `Project`, and its fix text names
    `fr.document(notice=...)`."""
    m, doc = _notice_model("Property of Demo Co. " * 40)
    (finding,) = _only(sheet_check(m, document_sheets_of(m)), "TITLE_BLOCK_NOTICE_OVERFLOW")
    assert finding.subjects == (doc.id,)
    assert "fr.document(notice=" in finding.message


def test_a_notice_that_fits_raises_no_overflow_finding():
    m, _doc = _notice_model("(c) Demo AS")
    assert sheet_check(m, document_sheets_of(m)) == ()


def _narrow(width: int) -> SheetFormat:
    key = ("sheet_format", f"narrow{width}")
    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name=f"narrow{width}",
        width_mm=width,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=width - 20,
        content_height_mm=257,  # band 20
        frame_columns=2,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )


def test_title_block_no_room_when_the_title_width_is_under_the_authored_one():
    """The title block never shrinks: 140 mm wide leaves 100 mm of title, 135 mm only 95."""
    wide, _doc = _cabinet(_narrow(140))
    assert _only(sheet_check(wide, document_sheets_of(wide)), "TITLE_BLOCK_NO_ROOM") == []
    assert all(s.counter_box for s in sheets(document_sheets_of(wide)).values())
    narrow, doc = _cabinet(_narrow(135))
    (finding,) = _only(sheet_check(narrow, document_sheets_of(narrow)), "TITLE_BLOCK_NO_ROOM")
    assert finding.subjects == (doc.id,)
    assert "95mm wide, under the required 97.5mm" in finding.message
    drawn = sheets(document_sheets_of(narrow)).values()
    assert drawn
    assert all(s.counter_box is None and s.logo_box is None for s in drawn)


def _profile(height: str) -> Profile:
    key = ("profile", f"h{height}")
    return dataclasses.replace(
        default_profile(), id=make_id(Profile, key), key=key, text_height_mm=Decimal(height)
    )


def test_title_block_stack_overlap_is_an_error_at_a_large_text_height():
    """A 4 mm label and a 4 mm value need a 28.0669 mm band; the house sheet gives 20."""
    m, doc = _cabinet(profile=_profile("4"))
    (finding,) = _only(sheet_check(m, document_sheets_of(m)), "TITLE_BLOCK_STACK_OVERLAP")
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (doc.id,)
    assert "the title-block band is 20 mm and the text height needs at least 28.0669 mm" in (
        finding.message
    )
    assert "use a sheet format whose title-block band is at least that height" in finding.message


def test_title_block_stack_overlap_fires_one_mm_under_the_need_and_not_at_it():
    """Text 3.5 mm needs a 25.8866 mm band: `_tight(252)` gives 25, `_tight(251)` gives 26.

    A format's content height is whole mm, so 26 is the least band at or over the need.
    """
    under, doc = _cabinet(_tight(252), _profile("3.5"))
    (finding,) = _only(sheet_check(under, document_sheets_of(under)), "TITLE_BLOCK_STACK_OVERLAP")
    assert finding.subjects == (doc.id,)
    assert "band is 25 mm and the text height needs at least 25.8866 mm" in finding.message
    at, _doc = _cabinet(_tight(251), _profile("3.5"))
    assert _only(sheet_check(at, document_sheets_of(at)), "TITLE_BLOCK_STACK_OVERLAP") == []


def test_title_block_stack_overlap_absent_at_the_house_text_height():
    m, _doc = _cabinet(profile=_profile("1.8"))
    assert _only(sheet_check(m, document_sheets_of(m)), "TITLE_BLOCK_STACK_OVERLAP") == []
    assert sheet_check(m, document_sheets_of(m)) == ()
