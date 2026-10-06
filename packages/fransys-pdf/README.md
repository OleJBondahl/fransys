Fransys output: document assembly to Typst source.

Output contract: pure function of a Model returning str, bytes or a tuple of pages. No file I/O, no clock, no randomness. Same model digest, same bytes.

`source(model, document, svgs) -> str` returns the complete, self-contained Typst source of
one document: every drawing SVG is inlined, so the source references no file. The facade
compiles it (third-party dependency `typst`, pinned per the pdf spec's decision record); this
package never depends on `typst` itself. `check(model, svgs) -> tuple[Finding, ...]` takes the
same SVG mapping, because it is the only way to tell a missing drawing-set page from one that
is present. `font_dir()` returns the path to the vendored Liberation Serif
faces, through `importlib.resources`, reading nothing.

`document_pages(model, document)` resolves a document's page list (its preset's pages, plus
`add`, minus `remove`, in canonical order; the notes page dropped when there is no notes
text). `PRESET_PAGES` maps each preset to its default pages, and `page_kinds(preset, add=, remove=)`
resolves a page list from a preset.

Unit documents (decisions pdf-0012, pdf-0014, model-0061). A document whose `unit` is set names
the unit, not the project: its title block prints `Unit.title` and `Unit.number` with an empty
customer, the revision and date of the unit's own revision, and the author and notice from
`Project`; the PDF metadata title and date come from the same `document_facts`. A system
document (`unit=None`) is unchanged. `check` gives one `TITLE_BLOCK_UNIT_IDENTITY_MISSING`
(`WARNING`) per unit document whose unit has an empty title or number, naming the empty field or
fields; the cell prints empty, with no fallback text. The terminal and connector lists print no
heading line for the unit's own sole root (the unit's own set never prints its own tag), only its
table.

Harness pages (decisions pdf-0015 to pdf-0018). CONTENTS's rows are
`derive.rows.ContentsRow` (model-0106): this package holds no copy of the row shape or the ends
join. `requests_harness_pages(pages)` is true when a
page list holds `CONTENTS` or `HARNESS_DRAWING`, the kinds that show cables; the cable choice
reads it. A `HARNESS_DRAWING` page is a table page per cable, built from `derive`'s
`HarnessCable` row, with no SVG (pdf-0018, cable-tables spec CT2 and CT3). Its heading holds the
cable's fields, and the table has one row per core. On the system document only, the heading
also carries the `by others` note (`derive.drawing_text.external_note()`), naming the cable or
the ends supplied by others. WireViz drew these pages until decision 0055 archived it; our own
cable drawings come later (0056). A unit document keys its cable pages by
`derive.unit_cable_page_key(unit, cable)` and prints its cables unit-relative (model-0090). So a
harness that is a unit's appears twice: absolute in its item document, unit-relative in the
unit's. `CONTENTS` is left out when the document's subject has no cable (pdf-0019).

Rules moved from docstrings (docstring sweep, LC3). Page frame: margin strips take their depth
from `content_x_mm` and `content_y_mm`, a `1fr` row or column fills it so labels centre, and
only interior ticks are drawn (pdf-0004; the 5 mm margin is model-0051). The title block is one `grid()`: Title spans c1 to c3,
Notice and Logo span both rows (pdf-0010). The notice wraps and is clipped at its box, never cut
with an ellipsis (pdf-0010). Cover: lists are flattened to centred paragraphs because Typst lists
ignore `align(center)` (pdf-0010). The revision table has auto columns but a 120 mm wrapping
description, so it centres narrower than the content box. It sits at the content box bottom,
shows the project history when there is no unit, and project facts appear in the title block only
(pdf-0005, pdf-0010). A unit document's cover lists that unit's own history only. A nested unit's revision shows in the parent's BOM, never on the parent's cover (owner 2026-09-23). CONTENTS lists the cables `harness_cables_for` returns.

Document selection: a location document draws only the top-level set at its location. A unit
document draws all of that unit's sets, ordered by `number` (layout-0045). A drawing set is
skipped only if it has placements, all black-box replicas, and no conductor route or link marker;
an empty set is not skipped. The sheet format is the first drawing-set page's format by
`number`, else the house sheet; mixed formats are reported by `DOCUMENT_MIXED_SHEET_FORMATS`. A
unit document's date is that of the history entry matching the unit's current revision, empty
if none (`REVISION_CURRENT_MISSING`). Page titles that overflow fall back to the `=` group
labels of the unit's own groups (pdf-0010, model-0097).

Text pages: SCHEMATIC with no drawing set, or any page missing from `svgs`, gives one `No
drawings.` page with its own title block, never a partial set. A harness document naming a
cable-less harness does the same (title `Harness drawing`). A SYSTEM document with no top-level
cable gives no page and the `DOCUMENT_NO_TOP_LEVEL_CABLES` INFO (U3). A cable page has the scope
cell of the item's designation, else `subject_label`. Its per-core table has the columns Core,
From, To and Label, with no colour or screening (CT2, CT3). The SYSTEM "by others" line lists the
cable if external, then its external ends in `cable_end_rank` order, never a blank end
(model-0048, wireviz-0010).

Terminal and list tables: each Bridge mark is a `place(...)` call and takes no flow space. The
Bridge cell is `breakable: false` because a breakable `auto` row resolves `%` against the page;
`inset: 0pt` makes neighbouring half-lines meet at the shared border (pdf-0007). `_terminal_table`
is not a `_table` call because the Bridge column draws its own cell content. The PDF drops jumper
partners from the ends columns; the CSV keeps them. A column of unbounded text is `1fr`, a
code-like column is `auto` (pdf-0008). A `None` marking prints the port name, an empty one prints
nothing (pdf-0012). An end inside the list context prints short; one outside prints its location
path first (model-0054).

Status: done. Work package `pdf` (decisions pdf-0001, pdf-0002): the pure package, list and BOM
pages, harness pages (cable tables since pdf-0018), and the schematic pages from `fransys_render`, compiled by the
facade. Work package `page frame` (pdf-0003 to pdf-0005, R11 in pdf-0010): the frame, grid and
title block on every page, drawn as the Typst page background.
