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
    '#set document(title: "Demo cabinet", author: "demo", date: datetime('
    'year: 2026, month: 9, day: 22))\n#set text(font: "DejaVu Sans", size:'
    ' 3.42934mm)\n#set page(width: 420mm, height: 297mm, numbering: "i", f'
    "ooter: none)\n#show heading.where(level: 1): set text(size: 6.85867mm"
    ")\n#show heading.where(level: 2): set text(size: 4.80107mm)\n#show hea"
    "ding.where(level: 3): set text(size: 3.42934mm)\n#show table: set tex"
    "t(size: 2.46912mm)\n#set page(margin: (left: 10mm, top: 10mm, right: "
    "10mm, bottom: 30mm), background: [#place(top+left, dx: 5mm, dy: 5mm,"
    " rect(width: 410mm, height: 287mm, stroke: 0.5mm))\n#place(top+left, "
    "dx: 5mm, dy: 0mm, block(width: 410mm, height: 5mm, grid(columns: (1f"
    "r, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr), rows: (1fr,), stroke: none, g"
    "rid.vline(x: 1, stroke: 0.25mm), grid.vline(x: 2, stroke: 0.25mm), g"
    "rid.vline(x: 3, stroke: 0.25mm), grid.vline(x: 4, stroke: 0.25mm), g"
    "rid.vline(x: 5, stroke: 0.25mm), grid.vline(x: 6, stroke: 0.25mm), g"
    "rid.vline(x: 7, stroke: 0.25mm), align(center+horizon, text(size: 2."
    '46912mm, "1")), align(center+horizon, text(size: 2.46912mm, "2")), a'
    'lign(center+horizon, text(size: 2.46912mm, "3")), align(center+horiz'
    'on, text(size: 2.46912mm, "4")), align(center+horizon, text(size: 2.'
    '46912mm, "5")), align(center+horizon, text(size: 2.46912mm, "6")), a'
    'lign(center+horizon, text(size: 2.46912mm, "7")), align(center+horiz'
    'on, text(size: 2.46912mm, "8")))))\n#place(top+left, dx: 5mm, dy: 292'
    "mm, block(width: 410mm, height: 5mm, grid(columns: (1fr, 1fr, 1fr, 1"
    "fr, 1fr, 1fr, 1fr, 1fr), rows: (1fr,), stroke: none, grid.vline(x: 1"
    ", stroke: 0.25mm), grid.vline(x: 2, stroke: 0.25mm), grid.vline(x: 3"
    ", stroke: 0.25mm), grid.vline(x: 4, stroke: 0.25mm), grid.vline(x: 5"
    ", stroke: 0.25mm), grid.vline(x: 6, stroke: 0.25mm), grid.vline(x: 7"
    ', stroke: 0.25mm), align(center+horizon, text(size: 2.46912mm, "1"))'
    ', align(center+horizon, text(size: 2.46912mm, "2")), align(center+ho'
    'rizon, text(size: 2.46912mm, "3")), align(center+horizon, text(size:'
    ' 2.46912mm, "4")), align(center+horizon, text(size: 2.46912mm, "5"))'
    ', align(center+horizon, text(size: 2.46912mm, "6")), align(center+ho'
    'rizon, text(size: 2.46912mm, "7")), align(center+horizon, text(size:'
    ' 2.46912mm, "8")))))\n#place(top+left, dx: 0mm, dy: 5mm, block(width:'
    " 5mm, height: 267mm, grid(columns: (1fr,), rows: (1fr, 1fr, 1fr, 1fr"
    ", 1fr, 1fr), stroke: none, grid.hline(y: 1, stroke: 0.25mm), grid.hl"
    "ine(y: 2, stroke: 0.25mm), grid.hline(y: 3, stroke: 0.25mm), grid.hl"
    "ine(y: 4, stroke: 0.25mm), grid.hline(y: 5, stroke: 0.25mm), align(c"
    'enter+horizon, text(size: 2.46912mm, "A")), align(center+horizon, te'
    'xt(size: 2.46912mm, "B")), align(center+horizon, text(size: 2.46912m'
    'm, "C")), align(center+horizon, text(size: 2.46912mm, "D")), align(c'
    'enter+horizon, text(size: 2.46912mm, "E")), align(center+horizon, te'
    'xt(size: 2.46912mm, "F")))))\n#place(top+left, dx: 415mm, dy: 5mm, bl'
    "ock(width: 5mm, height: 267mm, grid(columns: (1fr,), rows: (1fr, 1fr"
    ", 1fr, 1fr, 1fr, 1fr), stroke: none, grid.hline(y: 1, stroke: 0.25mm"
    "), grid.hline(y: 2, stroke: 0.25mm), grid.hline(y: 3, stroke: 0.25mm"
    "), grid.hline(y: 4, stroke: 0.25mm), grid.hline(y: 5, stroke: 0.25mm"
    '), align(center+horizon, text(size: 2.46912mm, "A")), align(center+h'
    'orizon, text(size: 2.46912mm, "B")), align(center+horizon, text(size'
    ': 2.46912mm, "C")), align(center+horizon, text(size: 2.46912mm, "D")'
    '), align(center+horizon, text(size: 2.46912mm, "E")), align(center+h'
    'orizon, text(size: 2.46912mm, "F")))))\n#place(top+left, dx: 5mm, dy:'
    " 272mm, block(width: 410mm, height: 20mm, grid(columns: (60mm, 60mm,"
    " 100mm, 55mm, 35mm, 35mm, 45mm, 20mm), rows: (10mm, 10mm), stroke: 0"
    ".5mm, grid.cell(colspan: 3, align(center+horizon, stack(dir: ttb, sp"
    'acing: 1mm, text(size: 2.46912mm, "Title"), text(size: 3.42934mm, st'
    'rong(text("Demo cabinet")))))), align(center+horizon, stack(dir: ttb'
    ', spacing: 1mm, text(size: 2.46912mm, "Number"), text(size: 3.42934m'
    'm, text("DEMO-1")))), align(center+horizon, stack(dir: ttb, spacing:'
    ' 1mm, text(size: 2.46912mm, "Revision"), text(size: 3.42934mm, text('
    '"1.1")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, text('
    'size: 2.46912mm, "Revision date"), text(size: 3.42934mm, text("2026-'
    '09-22")))), grid.cell(rowspan: 2, pad(x: 1mm, y: 1mm, block(width: 4'
    '3mm, height: 18mm, clip: true, text(size: 2.46912mm, "")))), grid.ce'
    "ll(rowspan: 2, align(center+horizon, [])), align(center+horizon, sta"
    'ck(dir: ttb, spacing: 1mm, text(size: 2.46912mm, "Customer"), text(s'
    'ize: 3.42934mm, text("Demo Co")))), align(center+horizon, stack(dir:'
    ' ttb, spacing: 1mm, text(size: 2.46912mm, "Author"), text(size: 3.42'
    '934mm, text("demo")))), align(center+horizon, stack(dir: ttb, spacin'
    'g: 1mm, text(size: 2.46912mm, "Page title"), text(size: 3.42934mm, t'
    'ext("Cover")))), align(center+horizon, stack(dir: ttb, spacing: 1mm,'
    ' text(size: 2.46912mm, "Scope"), text(size: 3.42934mm, text("C1 Demo'
    ' cabinet")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, t'
    'ext(size: 2.46912mm, "Sheet"), text(size: 3.42934mm, text("")))), al'
    "ign(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 2.46912"
    'mm, "Page"), [#text(size: 3.42934mm, context (str(here().page()) + "'
    ' of " + str(locate(<fr-last>).page())))<fransys-page-counter>])))))]'
    ")\n#context counter(page).update(here().page());\n#align(center, [\n#he"
    'ading(level: 1, text("Harness drawing — C1 Demo cabinet"))\n#heading('
    'level: 1, text("Cover heading"))\n#par(text("Cover text with ") + str'
    'ong(text("bold")) + text(" and ") + emph(text("italic")) + text(".")'
    ")\n])\n#place(bottom + center)[#table(columns: (auto, auto, 120mm, aut"
    'o, auto, auto), stroke: 0.18mm, table.header(strong(text("Revision")'
    '), strong(text("Date")), strong(text("Description")), strong(text("C'
    'reated")), strong(text("Checked")), strong(text("Approved"))), text('
    '"1.1"), text("2026-09-22"), text("Release"), text("OJB"), text(""), '
    'text(""))]\n#pagebreak()\n#set page(margin: (left: 10mm, top: 10mm, ri'
    "ght: 10mm, bottom: 30mm), background: [#place(top+left, dx: 5mm, dy:"
    " 5mm, rect(width: 410mm, height: 287mm, stroke: 0.5mm))\n#place(top+l"
    "eft, dx: 5mm, dy: 0mm, block(width: 410mm, height: 5mm, grid(columns"
    ": (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr), rows: (1fr,), stroke: no"
    "ne, grid.vline(x: 1, stroke: 0.25mm), grid.vline(x: 2, stroke: 0.25m"
    "m), grid.vline(x: 3, stroke: 0.25mm), grid.vline(x: 4, stroke: 0.25m"
    "m), grid.vline(x: 5, stroke: 0.25mm), grid.vline(x: 6, stroke: 0.25m"
    "m), grid.vline(x: 7, stroke: 0.25mm), align(center+horizon, text(siz"
    'e: 2.46912mm, "1")), align(center+horizon, text(size: 2.46912mm, "2"'
    ')), align(center+horizon, text(size: 2.46912mm, "3")), align(center+'
    'horizon, text(size: 2.46912mm, "4")), align(center+horizon, text(siz'
    'e: 2.46912mm, "5")), align(center+horizon, text(size: 2.46912mm, "6"'
    ')), align(center+horizon, text(size: 2.46912mm, "7")), align(center+'
    'horizon, text(size: 2.46912mm, "8")))))\n#place(top+left, dx: 5mm, dy'
    ": 292mm, block(width: 410mm, height: 5mm, grid(columns: (1fr, 1fr, 1"
    "fr, 1fr, 1fr, 1fr, 1fr, 1fr), rows: (1fr,), stroke: none, grid.vline"
    "(x: 1, stroke: 0.25mm), grid.vline(x: 2, stroke: 0.25mm), grid.vline"
    "(x: 3, stroke: 0.25mm), grid.vline(x: 4, stroke: 0.25mm), grid.vline"
    "(x: 5, stroke: 0.25mm), grid.vline(x: 6, stroke: 0.25mm), grid.vline"
    "(x: 7, stroke: 0.25mm), align(center+horizon, text(size: 2.46912mm, "
    '"1")), align(center+horizon, text(size: 2.46912mm, "2")), align(cent'
    'er+horizon, text(size: 2.46912mm, "3")), align(center+horizon, text('
    'size: 2.46912mm, "4")), align(center+horizon, text(size: 2.46912mm, '
    '"5")), align(center+horizon, text(size: 2.46912mm, "6")), align(cent'
    'er+horizon, text(size: 2.46912mm, "7")), align(center+horizon, text('
    'size: 2.46912mm, "8")))))\n#place(top+left, dx: 0mm, dy: 5mm, block(w'
    "idth: 5mm, height: 267mm, grid(columns: (1fr,), rows: (1fr, 1fr, 1fr"
    ", 1fr, 1fr, 1fr), stroke: none, grid.hline(y: 1, stroke: 0.25mm), gr"
    "id.hline(y: 2, stroke: 0.25mm), grid.hline(y: 3, stroke: 0.25mm), gr"
    "id.hline(y: 4, stroke: 0.25mm), grid.hline(y: 5, stroke: 0.25mm), al"
    'ign(center+horizon, text(size: 2.46912mm, "A")), align(center+horizo'
    'n, text(size: 2.46912mm, "B")), align(center+horizon, text(size: 2.4'
    '6912mm, "C")), align(center+horizon, text(size: 2.46912mm, "D")), al'
    'ign(center+horizon, text(size: 2.46912mm, "E")), align(center+horizo'
    'n, text(size: 2.46912mm, "F")))))\n#place(top+left, dx: 415mm, dy: 5m'
    "m, block(width: 5mm, height: 267mm, grid(columns: (1fr,), rows: (1fr"
    ", 1fr, 1fr, 1fr, 1fr, 1fr), stroke: none, grid.hline(y: 1, stroke: 0"
    ".25mm), grid.hline(y: 2, stroke: 0.25mm), grid.hline(y: 3, stroke: 0"
    ".25mm), grid.hline(y: 4, stroke: 0.25mm), grid.hline(y: 5, stroke: 0"
    '.25mm), align(center+horizon, text(size: 2.46912mm, "A")), align(cen'
    'ter+horizon, text(size: 2.46912mm, "B")), align(center+horizon, text'
    '(size: 2.46912mm, "C")), align(center+horizon, text(size: 2.46912mm,'
    ' "D")), align(center+horizon, text(size: 2.46912mm, "E")), align(cen'
    'ter+horizon, text(size: 2.46912mm, "F")))))\n#place(top+left, dx: 5mm'
    ", dy: 272mm, block(width: 410mm, height: 20mm, grid(columns: (60mm, "
    "60mm, 100mm, 55mm, 35mm, 35mm, 45mm, 20mm), rows: (10mm, 10mm), stro"
    "ke: 0.5mm, grid.cell(colspan: 3, align(center+horizon, stack(dir: tt"
    'b, spacing: 1mm, text(size: 2.46912mm, "Title"), text(size: 3.42934m'
    'm, strong(text("Demo cabinet")))))), align(center+horizon, stack(dir'
    ': ttb, spacing: 1mm, text(size: 2.46912mm, "Number"), text(size: 3.4'
    '2934mm, text("DEMO-1")))), align(center+horizon, stack(dir: ttb, spa'
    'cing: 1mm, text(size: 2.46912mm, "Revision"), text(size: 3.42934mm, '
    'text("1.1")))), align(center+horizon, stack(dir: ttb, spacing: 1mm, '
    'text(size: 2.46912mm, "Revision date"), text(size: 3.42934mm, text("'
    '2026-09-22")))), grid.cell(rowspan: 2, pad(x: 1mm, y: 1mm, block(wid'
    'th: 43mm, height: 18mm, clip: true, text(size: 2.46912mm, "")))), gr'
    "id.cell(rowspan: 2, align(center+horizon, [])), align(center+horizon"
    ', stack(dir: ttb, spacing: 1mm, text(size: 2.46912mm, "Customer"), t'
    'ext(size: 3.42934mm, text("Demo Co")))), align(center+horizon, stack'
    '(dir: ttb, spacing: 1mm, text(size: 2.46912mm, "Author"), text(size:'
    ' 3.42934mm, text("demo")))), align(center+horizon, stack(dir: ttb, s'
    'pacing: 1mm, text(size: 2.46912mm, "Page title"), text(size: 3.42934'
    'mm, text("Notes")))), align(center+horizon, stack(dir: ttb, spacing:'
    ' 1mm, text(size: 2.46912mm, "Scope"), text(size: 3.42934mm, text("C1'
    ' Demo cabinet")))), align(center+horizon, stack(dir: ttb, spacing: 1'
    'mm, text(size: 2.46912mm, "Sheet"), text(size: 3.42934mm, text("")))'
    "), align(center+horizon, stack(dir: ttb, spacing: 1mm, text(size: 2."
    '46912mm, "Page"), [#text(size: 3.42934mm, context (str(here().page()'
    ') + " of " + str(locate(<fr-last>).page())))<fransys-page-counter>])'
    "))))])\n#context counter(page).update(here().page());\n#heading(level:"
    ' 1, text("Notes"))\n#par(text("Notes text."))\n#metadata(none) <fr-las'
    "t>\n"
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
