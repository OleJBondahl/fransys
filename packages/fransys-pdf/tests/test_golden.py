"""`source` compared against a golden string, for one model.

The root byte-equality test (two writes of one compiled result, byte-equal) is Stage 2: it
needs the facade to compile. This one only needs `source` itself to be stable, and it stays
valid once Stage 2 adds the other page kinds because the fixture document is trimmed by
`remove` to `COVER` and `NOTES`.

CHOSEN APPEARANCE (the owner's appearance pass, `pdf-0005`): this golden now encodes
the design the owner reviewed and accepted -- the values, the cover's dropped facts table -- not an
unfinished default. A future change to it is a design change, not a routine regeneration.
"""

from _build import document, location, model, project, revision_entry, source

from fransys_model.derive import SheetBackground, SheetKey
from fransys_model.vocab import DocumentPreset, PageKind

_MEASURE = (
    "#place(hide(context layout(size => {\n"
    "  let cover = measure(block(width: size.width, fr-cover)).height\n"
    "  let table = measure(block(width: size.width, fr-table)).height\n"
    "  if cover + table > size.height {\n"
    "    let mm = h => str(calc.round(h.mm(), digits: 1))\n"
    '    panic("COVER_OVERFLOW cover=" + mm(cover) + " table=" + mm(table)'
    ' + " available=" + mm(size.height))\n'
    "  }\n"
    "})))"
)

_GOLDEN = (
    '#set document(title: "Demo cabinet", author: "demo", date: datetime('
    'year: 2026, month: 9, day: 22))\n#set text(font: "DejaVu Sans", size:'
    ' 3.42934mm)\n#set page(width: 420mm, height: 297mm, numbering: "i", f'
    "ooter: none)\n#show heading.where(level: 1): set text(size: 6.85867mm"
    ")\n#show heading.where(level: 2): set text(size: 4.80107mm)\n#show hea"
    "ding.where(level: 3): set text(size: 3.42934mm)\n#show table: set tex"
    "t(size: 2.46912mm)\n#set page(margin: (left: 10mm, top: 10mm, right: "
    '10mm, bottom: 30mm), background: [#place(top+left, image(bytes("<svg'
    '/>"), format: "svg"))\n#place(top+left, dx: 300mm, dy: 282mm, box(wid'
    "th: 30mm, height: 2.5mm, align(center+horizon, [#text(size: 3.42934m"
    'm, context (str(here().page()) + " of " + str(locate(<fr-last>).page'
    "())))<fransys-page-counter>])))])\n#context counter(page).update(here"
    '().page());\n#let fr-cover = align(center, [\n#heading(level: 1, text("Harness drawin'
    'g — C1 Demo cabinet"))\n#heading(level: 1, text("Cover heading"))\n#pa'
    'r(text("Cover text with ") + strong(text("bold")) + text(" and ") + '
    'emph(text("italic")) + text("."))\n])\n#fr-cover\n#let fr-table = table('
    "columns: (auto, auto, 120mm, auto, auto, auto), stroke: 0.18mm, tabl"
    'e.header(strong(text("Revision")), strong(text("Date")), strong(text'
    '("Description")), strong(text("Created")), strong(text("Checked")), '
    'strong(text("Approved"))), text("1.1"), text("2026-09-22"), text("Re'
    'lease"), text("OJB"), text(""), text(""))\n#place(bottom + center, fr-table)\n'
    + _MEASURE
    + "\n#pagebreak()\n#set page(ma"
    "rgin: (left: 10mm, top: 10mm, right: 10mm, bottom: 30mm), background"
    ': [#place(top+left, image(bytes("<svg/>"), format: "svg"))\n#place(to'
    "p+left, dx: 300mm, dy: 282mm, box(width: 30mm, height: 2.5mm, align("
    "center+horizon, [#text(size: 3.42934mm, context (str(here().page()) "
    '+ " of " + str(locate(<fr-last>).page())))<fransys-page-counter>])))'
    "])\n#context counter(page).update(here().page());\n#heading(level: 1, "
    'text("Notes"))\n#par(text("Notes text."))\n#metadata(none) <fr-last>\n'
)


def _demo_document():
    c1 = location("C1", "Demo cabinet")
    p = project(
        title="Demo cabinet",
        number="DEMO-1",
        customer="Demo Co",
        revision=1,
        author="demo",
    )
    entry = revision_entry("r1", unit=None, revision=1, date="2026-09-22")
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=c1,
        cover="# Cover heading\n\nCover text with **bold** and *italic*.",
        notes="Notes text.",
        remove=(PageKind.CONTENTS, PageKind.HARNESS_DRAWING, PageKind.BOM),
    )
    return model(c1, p, entry, doc), doc


def _stub_sheets(doc):
    """A fixed background per page, so the golden pins pdf's own text and not render's drawing."""
    stub = SheetBackground("<svg/>", (300.0, 282.0, 30.0, 2.5), (390.0, 267.0, 20.0, 20.0), 90.0)
    return {SheetKey(doc.id, kind, 0): stub for kind in (PageKind.COVER, PageKind.NOTES)}


def test_source_matches_the_golden_string():
    m, doc = _demo_document()
    assert source(m, doc.id, {}, _stub_sheets(doc)) == _GOLDEN


def test_source_is_pure_same_model_same_string():
    m, doc = _demo_document()
    assert source(m, doc.id, {}, _stub_sheets(doc)) == source(m, doc.id, {}, _stub_sheets(doc))
