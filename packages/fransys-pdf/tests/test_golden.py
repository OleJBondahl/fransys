"""`source` compared against a golden string, for one model.

The root byte-equality test (two writes of one compiled result, byte-equal) is Stage 2: it
needs the facade to compile. This one only needs `source` itself to be stable, and it stays
valid once Stage 2 adds the other page kinds because the fixture document is trimmed by
`remove` to `COVER` and `NOTES`.

CHOSEN APPEARANCE (the owner's appearance pass, `pdf-0005`): this golden now encodes
the design the owner reviewed and accepted -- the values, the cover's dropped facts table -- not an
unfinished default. A future change to it is a design change, not a routine regeneration.
"""

from _build import document, location, model, project, revision_entry
from fransys_pdf import source

from fransys_model.vocab import DocumentPreset, PageKind

_GOLDEN = (
    '#set document(title: "Demo cabinet", author: "demo", date: datetime(ye'
    'ar: 2026, month: 9, day: 22))\n#set text(font: "DejaVu Sans", size: 3.4'
    "2934mm)\n#set page(width: 420mm, height: 297mm)\n#show heading.where(lev"
    "el: 1): set text(size: 6.85867mm)\n#show heading.where(level: 2): set t"
    "ext(size: 4.80107mm)\n#show heading.where(level: 3): set text(size: 3.4"
    "2934mm)\n#show table: set text(size: 2.46912mm)\n#set page(margin: (left"
    ": 10mm, top: 10mm, right: 10mm, bottom: 30mm), background: [#place(top"
    "+left, dx: 5mm, dy: 5mm, rect(width: 410mm, height: 287mm, stroke: 0.5"
    "mm))\n#place(top+left, dx: 5mm, dy: 0mm, block(width: 410mm, height: 5m"
    "m, grid(columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr), rows: (1fr,"
    "), stroke: none, grid.vline(x: 1, stroke: 0.25mm), grid.vline(x: 2, st"
    "roke: 0.25mm), grid.vline(x: 3, stroke: 0.25mm), grid.vline(x: 4, stro"
    "ke: 0.25mm), grid.vline(x: 5, stroke: 0.25mm), grid.vline(x: 6, stroke"
    ": 0.25mm), grid.vline(x: 7, stroke: 0.25mm), align(center+horizon, tex"
    't(size: 2.46912mm, "1")), align(center+horizon, text(size: 2.46912mm, '
    '"2")), align(center+horizon, text(size: 2.46912mm, "3")), align(center'
    '+horizon, text(size: 2.46912mm, "4")), align(center+horizon, text(size'
    ': 2.46912mm, "5")), align(center+horizon, text(size: 2.46912mm, "6")),'
    ' align(center+horizon, text(size: 2.46912mm, "7")), align(center+horiz'
    'on, text(size: 2.46912mm, "8")))))\n#place(top+left, dx: 5mm, dy: 292mm'
    ", block(width: 410mm, height: 5mm, grid(columns: (1fr, 1fr, 1fr, 1fr, "
    "1fr, 1fr, 1fr, 1fr), rows: (1fr,), stroke: none, grid.vline(x: 1, stro"
    "ke: 0.25mm), grid.vline(x: 2, stroke: 0.25mm), grid.vline(x: 3, stroke"
    ": 0.25mm), grid.vline(x: 4, stroke: 0.25mm), grid.vline(x: 5, stroke: "
    "0.25mm), grid.vline(x: 6, stroke: 0.25mm), grid.vline(x: 7, stroke: 0."
    '25mm), align(center+horizon, text(size: 2.46912mm, "1")), align(center'
    '+horizon, text(size: 2.46912mm, "2")), align(center+horizon, text(size'
    ': 2.46912mm, "3")), align(center+horizon, text(size: 2.46912mm, "4")),'
    ' align(center+horizon, text(size: 2.46912mm, "5")), align(center+horiz'
    'on, text(size: 2.46912mm, "6")), align(center+horizon, text(size: 2.46'
    '912mm, "7")), align(center+horizon, text(size: 2.46912mm, "8")))))\n#pl'
    "ace(top+left, dx: 0mm, dy: 5mm, block(width: 5mm, height: 267mm, grid("
    "columns: (1fr,), rows: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr), stroke: none, g"
    "rid.hline(y: 1, stroke: 0.25mm), grid.hline(y: 2, stroke: 0.25mm), gri"
    "d.hline(y: 3, stroke: 0.25mm), grid.hline(y: 4, stroke: 0.25mm), grid."
    "hline(y: 5, stroke: 0.25mm), align(center+horizon, text(size: 2.46912m"
    'm, "A")), align(center+horizon, text(size: 2.46912mm, "B")), align(cen'
    'ter+horizon, text(size: 2.46912mm, "C")), align(center+horizon, text(s'
    'ize: 2.46912mm, "D")), align(center+horizon, text(size: 2.46912mm, "E"'
    ')), align(center+horizon, text(size: 2.46912mm, "F")))))\n#place(top+le'
    "ft, dx: 415mm, dy: 5mm, block(width: 5mm, height: 267mm, grid(columns:"
    " (1fr,), rows: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr), stroke: none, grid.hlin"
    "e(y: 1, stroke: 0.25mm), grid.hline(y: 2, stroke: 0.25mm), grid.hline("
    "y: 3, stroke: 0.25mm), grid.hline(y: 4, stroke: 0.25mm), grid.hline(y:"
    ' 5, stroke: 0.25mm), align(center+horizon, text(size: 2.46912mm, "A"))'
    ', align(center+horizon, text(size: 2.46912mm, "B")), align(center+hori'
    'zon, text(size: 2.46912mm, "C")), align(center+horizon, text(size: 2.4'
    '6912mm, "D")), align(center+horizon, text(size: 2.46912mm, "E")), alig'
    'n(center+horizon, text(size: 2.46912mm, "F")))))\n#place(top+left, dx: '
    "5mm, dy: 272mm, block(width: 410mm, height: 20mm, grid(columns: (60mm,"
    " 60mm, 100mm, 55mm, 35mm, 35mm, 45mm, 20mm), rows: (10mm, 10mm), strok"
    "e: 0.5mm, grid.cell(colspan: 3, align(center+horizon, stack(dir: ttb, "
    'spacing: 1mm, text(size: 2.46912mm, "Title"), text(size: 3.42934mm, st'
    'rong(text("Demo cabinet")))))), align(center+horizon, stack(dir: ttb, '
    'spacing: 1mm, text(size: 2.46912mm, "Number"), text(size: 3.42934mm, t'
    'ext("DEMO-1")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, '
    'text(size: 2.46912mm, "Revision"), text(size: 3.42934mm, text("1.1")))'
    "), align(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 2.46"
    '912mm, "Revision date"), text(size: 3.42934mm, text("2026-09-22")))), '
    "grid.cell(rowspan: 2, pad(x: 1mm, y: 1mm, block(width: 43mm, height: 1"
    '8mm, clip: true, text(size: 2.46912mm, "")))), grid.cell(rowspan: 2, a'
    "lign(center+horizon, [])), align(center+horizon, stack(dir: ttb, spaci"
    'ng: 1mm, text(size: 2.46912mm, "Customer"), text(size: 3.42934mm, text'
    '("Demo Co")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, te'
    'xt(size: 2.46912mm, "Author"), text(size: 3.42934mm, text("demo")))), '
    "align(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 2.46912"
    'mm, "Page title"), text(size: 3.42934mm, text("Cover")))), align(cente'
    'r+horizon, stack(dir: ttb, spacing: 1mm, text(size: 2.46912mm, "Scope"'
    '), text(size: 3.42934mm, text("C1 Demo cabinet")))), align(center+hori'
    'zon, stack(dir: ttb, spacing: 1mm, text(size: 2.46912mm, "Sheet"), tex'
    't(size: 3.42934mm, text("")))), align(center+horizon, stack(dir: ttb, '
    'spacing: 1mm, text(size: 2.46912mm, "Page"), [#text(size: 3.42934mm, c'
    'ontext (str(counter(page).get().first()) + " of " + str(counter(page).'
    "final().first())))<fransys-page-counter>])))))])\n#align(center, [\n#hea"
    'ding(level: 1, text("Harness drawing — C1 Demo cabinet"))\n#heading(lev'
    'el: 1, text("Cover heading"))\n#par(text("Cover text with ") + strong(t'
    'ext("bold")) + text(" and ") + emph(text("italic")) + text("."))\n])\n#p'
    "lace(bottom + center)[#table(columns: (auto, auto, 120mm, aut"
    'o, auto, auto), stroke: 0.18mm, table.header(strong(text("Revision")),'
    ' strong(text("Date")), strong(text("Description")), strong(text("Creat'
    'ed")), strong(text("Checked")), strong(text("Approved"))), text("1.1")'
    ', text("2026-09-22"), text("Release"), text("OJB"), text(""), text("")'
    ")]\n#pagebreak()\n#set page(margin: (left: 10mm, top: 10mm, right: 10mm,"
    " bottom: 30mm), background: [#place(top+left, dx: 5mm, dy: 5mm, rect(w"
    "idth: 410mm, height: 287mm, stroke: 0.5mm))\n#place(top+left, dx: 5mm, "
    "dy: 0mm, block(width: 410mm, height: 5mm, grid(columns: (1fr, 1fr, 1fr"
    ", 1fr, 1fr, 1fr, 1fr, 1fr), rows: (1fr,), stroke: none, grid.vline(x: "
    "1, stroke: 0.25mm), grid.vline(x: 2, stroke: 0.25mm), grid.vline(x: 3,"
    " stroke: 0.25mm), grid.vline(x: 4, stroke: 0.25mm), grid.vline(x: 5, s"
    "troke: 0.25mm), grid.vline(x: 6, stroke: 0.25mm), grid.vline(x: 7, str"
    'oke: 0.25mm), align(center+horizon, text(size: 2.46912mm, "1")), align'
    '(center+horizon, text(size: 2.46912mm, "2")), align(center+horizon, te'
    'xt(size: 2.46912mm, "3")), align(center+horizon, text(size: 2.46912mm,'
    ' "4")), align(center+horizon, text(size: 2.46912mm, "5")), align(cente'
    'r+horizon, text(size: 2.46912mm, "6")), align(center+horizon, text(siz'
    'e: 2.46912mm, "7")), align(center+horizon, text(size: 2.46912mm, "8"))'
    ")))\n#place(top+left, dx: 5mm, dy: 292mm, block(width: 410mm, height: 5"
    "mm, grid(columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr), rows: (1fr"
    ",), stroke: none, grid.vline(x: 1, stroke: 0.25mm), grid.vline(x: 2, s"
    "troke: 0.25mm), grid.vline(x: 3, stroke: 0.25mm), grid.vline(x: 4, str"
    "oke: 0.25mm), grid.vline(x: 5, stroke: 0.25mm), grid.vline(x: 6, strok"
    "e: 0.25mm), grid.vline(x: 7, stroke: 0.25mm), align(center+horizon, te"
    'xt(size: 2.46912mm, "1")), align(center+horizon, text(size: 2.46912mm,'
    ' "2")), align(center+horizon, text(size: 2.46912mm, "3")), align(cente'
    'r+horizon, text(size: 2.46912mm, "4")), align(center+horizon, text(siz'
    'e: 2.46912mm, "5")), align(center+horizon, text(size: 2.46912mm, "6"))'
    ', align(center+horizon, text(size: 2.46912mm, "7")), align(center+hori'
    'zon, text(size: 2.46912mm, "8")))))\n#place(top+left, dx: 0mm, dy: 5mm,'
    " block(width: 5mm, height: 267mm, grid(columns: (1fr,), rows: (1fr, 1f"
    "r, 1fr, 1fr, 1fr, 1fr), stroke: none, grid.hline(y: 1, stroke: 0.25mm)"
    ", grid.hline(y: 2, stroke: 0.25mm), grid.hline(y: 3, stroke: 0.25mm), "
    "grid.hline(y: 4, stroke: 0.25mm), grid.hline(y: 5, stroke: 0.25mm), al"
    'ign(center+horizon, text(size: 2.46912mm, "A")), align(center+horizon,'
    ' text(size: 2.46912mm, "B")), align(center+horizon, text(size: 2.46912'
    'mm, "C")), align(center+horizon, text(size: 2.46912mm, "D")), align(ce'
    'nter+horizon, text(size: 2.46912mm, "E")), align(center+horizon, text('
    'size: 2.46912mm, "F")))))\n#place(top+left, dx: 415mm, dy: 5mm, block(w'
    "idth: 5mm, height: 267mm, grid(columns: (1fr,), rows: (1fr, 1fr, 1fr, "
    "1fr, 1fr, 1fr), stroke: none, grid.hline(y: 1, stroke: 0.25mm), grid.h"
    "line(y: 2, stroke: 0.25mm), grid.hline(y: 3, stroke: 0.25mm), grid.hli"
    "ne(y: 4, stroke: 0.25mm), grid.hline(y: 5, stroke: 0.25mm), align(cent"
    'er+horizon, text(size: 2.46912mm, "A")), align(center+horizon, text(si'
    'ze: 2.46912mm, "B")), align(center+horizon, text(size: 2.46912mm, "C")'
    '), align(center+horizon, text(size: 2.46912mm, "D")), align(center+hor'
    'izon, text(size: 2.46912mm, "E")), align(center+horizon, text(size: 2.'
    '46912mm, "F")))))\n#place(top+left, dx: 5mm, dy: 272mm, block(width: 41'
    "0mm, height: 20mm, grid(columns: (60mm, 60mm, 100mm, 55mm, 35mm, 35mm,"
    " 45mm, 20mm), rows: (10mm, 10mm), stroke: 0.5mm, grid.cell(colspan: 3,"
    " align(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 2.4691"
    '2mm, "Title"), text(size: 3.42934mm, strong(text("Demo cabinet")))))),'
    " align(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 2.4691"
    '2mm, "Number"), text(size: 3.42934mm, text("DEMO-1")))), align(center+'
    'horizon, stack(dir: ttb, spacing: 1mm, text(size: 2.46912mm, "Revision'
    '"), text(size: 3.42934mm, text("1.1")))), align(center+horizon, stack('
    'dir: ttb, spacing: 1mm, text(size: 2.46912mm, "Revision date"), text(s'
    'ize: 3.42934mm, text("2026-09-22")))), grid.cell(rowspan: 2, pad(x: 1m'
    "m, y: 1mm, block(width: 43mm, height: 18mm, clip: true, text(size: 2.4"
    '6912mm, "")))), grid.cell(rowspan: 2, align(center+horizon, [])), alig'
    "n(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 2.46912mm, "
    '"Customer"), text(size: 3.42934mm, text("Demo Co")))), align(center+ho'
    'rizon, stack(dir: ttb, spacing: 1mm, text(size: 2.46912mm, "Author"), '
    'text(size: 3.42934mm, text("demo")))), align(center+horizon, stack(dir'
    ': ttb, spacing: 1mm, text(size: 2.46912mm, "Page title"), text(size: 3'
    '.42934mm, text("Notes")))), align(center+horizon, stack(dir: ttb, spac'
    'ing: 1mm, text(size: 2.46912mm, "Scope"), text(size: 3.42934mm, text("'
    'C1 Demo cabinet")))), align(center+horizon, stack(dir: ttb, spacing: 1'
    'mm, text(size: 2.46912mm, "Sheet"), text(size: 3.42934mm, text("")))),'
    " align(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 2.4691"
    '2mm, "Page"), [#text(size: 3.42934mm, context (str(counter(page).get()'
    '.first()) + " of " + str(counter(page).final().first())))<fransys-page'
    '-counter>])))))])\n#heading(level: 1, text("Notes"))\n#par(text("Notes t'
    'ext."))\n'
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
