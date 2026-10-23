"""A split table carries the heading from `derive.continued_heading` (pdf-0027, pdf-0053)."""

from fransys_pdf._cable_runs import _header
from fransys_pdf._lists import _carried
from fransys_pdf._tables import table_source
from pdf_library import freeze

from fransys_model.derive import continued_heading
from fransys_model.kernel import Draft

MODEL = freeze(Draft())
_ROW = ["text(1)", "text(2)"]
# Captured from main, then the carried heading gained a trailing empty block (R286, LISTS).
_TWELVE_ROWS = (
    "#[#set table.cell(breakable: false)\n#table(columns: (0pt, auto, 1fr), "
    "stroke: 0.18mm, table.header(table.cell(colspan: 3, stroke: none, inse"
    "t: 0pt)[#context { let p = here().position(); let q = locate(<term0>)."
    "position(); let first = p.page == q.page and calc.abs(p.x - q.x) < 3mm"
    " and calc.abs(p.y - q.y) < 5mm; if first [] else { heading(level: 2, o"
    'utlined: false, bookmarked: false, text("-X1 (cont.)")); block(height: 0pt) } }], table.ce'
    "ll(stroke: none, inset: 0pt)[], text(a), text(b)), table.cell(rowspan:"
    " 2, stroke: none, inset: 0pt)[], text(1), text(2), text(1), text(2), t"
    "able.cell(stroke: none, inset: 0pt)[], text(1), text(2), table.cell(st"
    "roke: none, inset: 0pt)[], text(1), text(2), table.cell(stroke: none, "
    "inset: 0pt)[], text(1), text(2), table.cell(stroke: none, inset: 0pt)["
    "], text(1), text(2), table.cell(stroke: none, inset: 0pt)[], text(1), "
    "text(2), table.cell(stroke: none, inset: 0pt)[], text(1), text(2), tab"
    "le.cell(stroke: none, inset: 0pt)[], text(1), text(2), table.cell(stro"
    "ke: none, inset: 0pt)[], text(1), text(2), table.cell(rowspan: 2, stro"
    "ke: none, inset: 0pt)[], text(1), text(2), text(1), text(2)) <term0>\n]"
)


def test_a_twelve_row_table_is_the_source_main_produced():
    got = table_source(
        ["auto", "1fr"],
        ["text(a)", "text(b)"],
        [_ROW] * 12,
        rule="0.18mm",
        heading=("-X1 (cont.)", "term0"),
    )
    assert got == _TWELVE_ROWS


def test_the_carried_heading_is_the_derive_text():
    title = continued_heading(MODEL, "-X1")
    got = table_source(["auto"], ["text(a)"], [_ROW] * 6, rule="0.18mm", heading=(title, "t"))
    assert f'text("{title}")' in got


def test_a_cable_run_header_prints_the_derive_text_after_its_first_page():
    header = _header(("PN-1", continued_heading(MODEL, "PN-1")), "run-0")
    assert continued_heading(MODEL, "PN-1") in header
    assert 'text("PN-1")' not in header or "else" in header


def test_a_list_table_with_no_title_carries_no_heading():
    assert _carried(MODEL, "") == ""
    assert _carried(MODEL, "-X1") == continued_heading(MODEL, "-X1")
