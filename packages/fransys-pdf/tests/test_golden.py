"""`source` compared against a golden string, for one model (spec P3, Part 5's own test).

The root byte-equality test (two writes of one compiled result, byte-equal) is Stage 2: it
needs the facade to compile. This one only needs `source` itself to be stable, and it stays
valid once Stage 2 adds the other page kinds because the fixture document is trimmed by
`remove` to `COVER` and `NOTES` (docs/decisions/pdf-0001-...md, Part 4 addendum).

CHOSEN APPEARANCE (page-frame R10, the owner's appearance pass, `pdf-0005`): this golden now
encodes the design the owner reviewed and accepted -- R5's values, the cover's dropped facts
table -- not an unfinished default. A future change to it is a design change, made with the
designer, not a routine regeneration.
"""

from _build import document, location, model, project, revision_entry
from fransys_pdf import source

from fransys_model.vocab import DocumentPreset, PageKind

_GOLDEN = (
    '#set document(title: "Demo cabinet", author: "demo", date: datetime(ye'
    'ar: 2026, month: 9, day: 22))\n#set text(font: "Liberation Serif", size'
    ": 10pt)\n#set page(width: 420mm, height: 297mm)\n#show heading.where(lev"
    "el: 1): set text(size: 16pt)\n#show heading.where(level: 2): set text(s"
    "ize: 13pt)\n#show heading.where(level: 3): set text(size: 11pt)\n#show t"
    "able: set text(size: 9pt)\n#set page(margin: (left: 10mm, top: 10mm, ri"
    "ght: 10mm, bottom: 30mm), background: [#place(top+left, dx: 5mm, dy: 5"
    "mm, rect(width: 410mm, height: 287mm, stroke: 0.5mm))\n#place(top+left,"
    " dx: 5mm, dy: 0mm, block(width: 410mm, height: 5mm, grid(columns: (1fr"
    ", 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr), rows: (1fr,), stroke: none, grid"
    ".vline(x: 1, stroke: 0.25mm), grid.vline(x: 2, stroke: 0.25mm), grid.v"
    "line(x: 3, stroke: 0.25mm), grid.vline(x: 4, stroke: 0.25mm), grid.vli"
    "ne(x: 5, stroke: 0.25mm), grid.vline(x: 6, stroke: 0.25mm), grid.vline"
    '(x: 7, stroke: 0.25mm), align(center+horizon, text(size: 8pt, "1")), a'
    'lign(center+horizon, text(size: 8pt, "2")), align(center+horizon, text'
    '(size: 8pt, "3")), align(center+horizon, text(size: 8pt, "4")), align('
    'center+horizon, text(size: 8pt, "5")), align(center+horizon, text(size'
    ': 8pt, "6")), align(center+horizon, text(size: 8pt, "7")), align(cente'
    'r+horizon, text(size: 8pt, "8")))))\n#place(top+left, dx: 5mm, dy: 292m'
    "m, block(width: 410mm, height: 5mm, grid(columns: (1fr, 1fr, 1fr, 1fr,"
    " 1fr, 1fr, 1fr, 1fr), rows: (1fr,), stroke: none, grid.vline(x: 1, str"
    "oke: 0.25mm), grid.vline(x: 2, stroke: 0.25mm), grid.vline(x: 3, strok"
    "e: 0.25mm), grid.vline(x: 4, stroke: 0.25mm), grid.vline(x: 5, stroke:"
    " 0.25mm), grid.vline(x: 6, stroke: 0.25mm), grid.vline(x: 7, stroke: 0"
    '.25mm), align(center+horizon, text(size: 8pt, "1")), align(center+hori'
    'zon, text(size: 8pt, "2")), align(center+horizon, text(size: 8pt, "3")'
    '), align(center+horizon, text(size: 8pt, "4")), align(center+horizon, '
    'text(size: 8pt, "5")), align(center+horizon, text(size: 8pt, "6")), al'
    'ign(center+horizon, text(size: 8pt, "7")), align(center+horizon, text('
    'size: 8pt, "8")))))\n#place(top+left, dx: 0mm, dy: 5mm, block(width: 5m'
    "m, height: 267mm, grid(columns: (1fr,), rows: (1fr, 1fr, 1fr, 1fr, 1fr"
    ", 1fr), stroke: none, grid.hline(y: 1, stroke: 0.25mm), grid.hline(y: "
    "2, stroke: 0.25mm), grid.hline(y: 3, stroke: 0.25mm), grid.hline(y: 4,"
    " stroke: 0.25mm), grid.hline(y: 5, stroke: 0.25mm), align(center+horiz"
    'on, text(size: 8pt, "A")), align(center+horizon, text(size: 8pt, "B"))'
    ', align(center+horizon, text(size: 8pt, "C")), align(center+horizon, t'
    'ext(size: 8pt, "D")), align(center+horizon, text(size: 8pt, "E")), ali'
    'gn(center+horizon, text(size: 8pt, "F")))))\n#place(top+left, dx: 415mm'
    ", dy: 5mm, block(width: 5mm, height: 267mm, grid(columns: (1fr,), rows"
    ": (1fr, 1fr, 1fr, 1fr, 1fr, 1fr), stroke: none, grid.hline(y: 1, strok"
    "e: 0.25mm), grid.hline(y: 2, stroke: 0.25mm), grid.hline(y: 3, stroke:"
    " 0.25mm), grid.hline(y: 4, stroke: 0.25mm), grid.hline(y: 5, stroke: 0"
    '.25mm), align(center+horizon, text(size: 8pt, "A")), align(center+hori'
    'zon, text(size: 8pt, "B")), align(center+horizon, text(size: 8pt, "C")'
    '), align(center+horizon, text(size: 8pt, "D")), align(center+horizon, '
    'text(size: 8pt, "E")), align(center+horizon, text(size: 8pt, "F")))))\n'
    "#place(top+left, dx: 5mm, dy: 272mm, block(width: 410mm, height: 20mm,"
    " grid(columns: (60mm, 60mm, 100mm, 55mm, 35mm, 35mm, 45mm, 20mm), rows"
    ": (10mm, 10mm), stroke: 0.5mm, grid.cell(colspan: 3, align(center+hori"
    'zon, stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Title"), text(size'
    ': 12pt, strong(text("Demo cabinet")))))), align(center+horizon, stack('
    'dir: ttb, spacing: 1mm, text(size: 8pt, "Number"), text(size: 10pt, te'
    'xt("DEMO-1")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, t'
    'ext(size: 8pt, "Revision"), text(size: 10pt, text("1.1")))), align(cent'
    'er+horizon, stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Revision da'
    'te"), text(size: 10pt, text("2026-09-22")))), grid.cell(rowspan: 2, pa'
    "d(x: 1mm, y: 1mm, block(width: 43mm, height: 18mm, clip: true, text(si"
    'ze: 6pt, "")))), grid.cell(rowspan: 2, align(center+horizon, [])), ali'
    'gn(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Cust'
    'omer"), text(size: 10pt, text("Demo Co")))), align(center+horizon, sta'
    'ck(dir: ttb, spacing: 1mm, text(size: 8pt, "Author"), text(size: 10pt,'
    ' text("demo")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, '
    'text(size: 8pt, "Page title"), text(size: 10pt, text("Cover")))), alig'
    'n(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Scope'
    '"), text(size: 10pt, text("C1 Demo cabinet")))), align(center+horizon,'
    ' stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Sheet"), text(size: 10'
    'pt, text("")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, t'
    'ext(size: 8pt, "Page"), [#text(size: 10pt, context (str(counter(page).'
    'get().first()) + " of " + str(counter(page).final().first())))<fransys'
    '-page-counter>])))))])\n#align(center, [\n#heading(level: 1, text("Ha'
    'rness drawing — C1 Demo cabinet"))\n#heading(level: 1, text("Cover head'
    'ing"))\n#par(text("Cover text with ") + strong(text("bold")) + text(" a'
    'nd ") + emph(text("italic")) + text("."))\n])\n'
    "#place(bottom + center, dy: 5mm)[#table(columns: (auto, auto, 120mm, auto, auto, aut"
    'o), stroke: 0.5pt, table.header(strong(text("Revision")), strong(text("Date")), st'
    'rong(text("Description")), strong(text("Created")), strong(text("Checked")), stron'
    'g(text("Approved"))), text("1.1"), text("2026-09-22"), text("Release"), text("OJB")'
    ', text(""), text(""))]\n'
    "#pagebreak()\n#set page(ma"
    "rgin: (left: 10mm, top: 10mm, right: 10mm, bottom: 30mm), background: "
    "[#place(top+left, dx: 5mm, dy: 5mm, rect(width: 410mm, height: 287mm, "
    "stroke: 0.5mm))\n#place(top+left, dx: 5mm, dy: 0mm, block(width: 410mm,"
    " height: 5mm, grid(columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr), "
    "rows: (1fr,), stroke: none, grid.vline(x: 1, stroke: 0.25mm), grid.vli"
    "ne(x: 2, stroke: 0.25mm), grid.vline(x: 3, stroke: 0.25mm), grid.vline"
    "(x: 4, stroke: 0.25mm), grid.vline(x: 5, stroke: 0.25mm), grid.vline(x"
    ": 6, stroke: 0.25mm), grid.vline(x: 7, stroke: 0.25mm), align(center+h"
    'orizon, text(size: 8pt, "1")), align(center+horizon, text(size: 8pt, "'
    '2")), align(center+horizon, text(size: 8pt, "3")), align(center+horizo'
    'n, text(size: 8pt, "4")), align(center+horizon, text(size: 8pt, "5")),'
    ' align(center+horizon, text(size: 8pt, "6")), align(center+horizon, te'
    'xt(size: 8pt, "7")), align(center+horizon, text(size: 8pt, "8")))))\n#p'
    "lace(top+left, dx: 5mm, dy: 292mm, block(width: 410mm, height: 5mm, gr"
    "id(columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr), rows: (1fr,), st"
    "roke: none, grid.vline(x: 1, stroke: 0.25mm), grid.vline(x: 2, stroke:"
    " 0.25mm), grid.vline(x: 3, stroke: 0.25mm), grid.vline(x: 4, stroke: 0"
    ".25mm), grid.vline(x: 5, stroke: 0.25mm), grid.vline(x: 6, stroke: 0.2"
    "5mm), grid.vline(x: 7, stroke: 0.25mm), align(center+horizon, text(siz"
    'e: 8pt, "1")), align(center+horizon, text(size: 8pt, "2")), align(cent'
    'er+horizon, text(size: 8pt, "3")), align(center+horizon, text(size: 8p'
    't, "4")), align(center+horizon, text(size: 8pt, "5")), align(center+ho'
    'rizon, text(size: 8pt, "6")), align(center+horizon, text(size: 8pt, "7'
    '")), align(center+horizon, text(size: 8pt, "8")))))\n#place(top+left, d'
    "x: 0mm, dy: 5mm, block(width: 5mm, height: 267mm, grid(columns: (1fr,)"
    ", rows: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr), stroke: none, grid.hline(y: 1,"
    " stroke: 0.25mm), grid.hline(y: 2, stroke: 0.25mm), grid.hline(y: 3, s"
    "troke: 0.25mm), grid.hline(y: 4, stroke: 0.25mm), grid.hline(y: 5, str"
    'oke: 0.25mm), align(center+horizon, text(size: 8pt, "A")), align(cente'
    'r+horizon, text(size: 8pt, "B")), align(center+horizon, text(size: 8pt'
    ', "C")), align(center+horizon, text(size: 8pt, "D")), align(center+hor'
    'izon, text(size: 8pt, "E")), align(center+horizon, text(size: 8pt, "F"'
    ")))))\n#place(top+left, dx: 415mm, dy: 5mm, block(width: 5mm, height: 2"
    "67mm, grid(columns: (1fr,), rows: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr), stro"
    "ke: none, grid.hline(y: 1, stroke: 0.25mm), grid.hline(y: 2, stroke: 0"
    ".25mm), grid.hline(y: 3, stroke: 0.25mm), grid.hline(y: 4, stroke: 0.2"
    "5mm), grid.hline(y: 5, stroke: 0.25mm), align(center+horizon, text(siz"
    'e: 8pt, "A")), align(center+horizon, text(size: 8pt, "B")), align(cent'
    'er+horizon, text(size: 8pt, "C")), align(center+horizon, text(size: 8p'
    't, "D")), align(center+horizon, text(size: 8pt, "E")), align(center+ho'
    'rizon, text(size: 8pt, "F")))))\n#place(top+left, dx: 5mm, dy: 272mm, b'
    "lock(width: 410mm, height: 20mm, grid(columns: (60mm, 60mm, 100mm, 55m"
    "m, 35mm, 35mm, 45mm, 20mm), rows: (10mm, 10mm), stroke: 0.5mm, grid.ce"
    "ll(colspan: 3, align(center+horizon, stack(dir: ttb, spacing: 1mm, tex"
    't(size: 8pt, "Title"), text(size: 12pt, strong(text("Demo cabinet"))))'
    ")), align(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 8pt"
    ', "Number"), text(size: 10pt, text("DEMO-1")))), align(center+horizon,'
    ' stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Revision"), text(size:'
    ' 10pt, text("1.1")))), align(center+horizon, stack(dir: ttb, spacing: 1'
    'mm, text(size: 8pt, "Revision date"), text(size: 10pt, text("2026-09-2'
    '2")))), grid.cell(rowspan: 2, pad(x: 1mm, y: 1mm, block(width: 43mm, h'
    'eight: 18mm, clip: true, text(size: 6pt, "")))), grid.cell(rowspan: 2,'
    " align(center+horizon, [])), align(center+horizon, stack(dir: ttb, spa"
    'cing: 1mm, text(size: 8pt, "Customer"), text(size: 10pt, text("Demo Co'
    '")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: '
    '8pt, "Author"), text(size: 10pt, text("demo")))), align(center+horizon'
    ', stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Page title"), text(si'
    'ze: 10pt, text("Notes")))), align(center+horizon, stack(dir: ttb, spac'
    'ing: 1mm, text(size: 8pt, "Scope"), text(size: 10pt, text("C1 Demo cab'
    'inet")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, text(si'
    'ze: 8pt, "Sheet"), text(size: 10pt, text("")))), align(center+horizon,'
    ' stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Page"), [#text(size: 1'
    '0pt, context (str(counter(page).get().first()) + " of " + str(counter('
    "page).final().first())))<fransys-page-counter>])))))])\n#heading(lev"
    'el: 1, text("Notes"))\n#par(text("Notes text."))\n'
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


def test_source_matches_the_golden_string():
    m, doc = _demo_document()
    assert source(m, doc.id, {}) == _GOLDEN


def test_source_is_pure_same_model_same_string():
    m, doc = _demo_document()
    assert source(m, doc.id, {}) == source(m, doc.id, {})
