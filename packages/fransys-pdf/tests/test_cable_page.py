"""A `HARNESS_DRAWING` cable page's own logo, notice and sheet counter (spec page-frame R3,
R11.3, R11.4).

`_drawings._cable_page` builds each cable page's own `TitleBlockFields`: the document's real
logo, the project's real notice, and an always-empty `sheet_counter` -- only a `Page` record
carries the sheet position a counter names, a `HarnessCable` carries none. No existing test in
this package checks a cable page's own logo, notice or sheet_counter:
`test_unit_harness_drawings.py`'s cable-page tests are all about which cable's SVG gets picked
and drawing-set scoping, never the title block.

Every other page kind of a `HARNESS_DRAWING` document (`COVER`, `CONTENTS`, `BOM`) is prefixed
by `document.py`'s own `_section_prefix`, which independently embeds the very same
`logo=record.logo`/`notice=project_notice(model)`. A check against the whole document's source
would therefore see the real logo and notice regardless of what `_cable_page` itself builds, so
every fixture below removes every page kind but `HARNESS_DRAWING` -- the only way a mutant
inside `_cable_page` alone can be told apart from those other, unmutated pages' own copies of
the same fields.
"""

from _build import (
    cable_facet,
    cable_product_facet,
    document,
    item,
    model,
    part,
    project,
    revision_entry,
)
from fransys_pdf import source
from fransys_pdf._frame import _value
from fransys_pdf._typst import literal

from fransys_model.kernel.ids import render_id
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind
_SVG_LOGO = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<rect x="0" y="0" width="10" height="10"/></svg>'
)
_NOTICE = "ACME Corp proprietary: do not copy"


def _cable_only_source() -> str:
    """A `HARNESS_DRAWING` document stripped to just its own cable page: a real logo, a real
    project notice, a real revision date, and one real child cable.

    The revision date matters as much as the page-kind removals above: with no `Revision`
    entry, `document_facts`' own `revision_date` is `""` too (`_geometry.project_facts`), which
    would make `sheet_counter`'s own empty one-line field indistinguishable from that one's --
    so `sheet_counter` stays the *only* empty field this page renders.
    """
    p = project(notice=_NOTICE)
    entry = revision_entry("r1", unit=None, revision=1, date="2026-01-01")
    harness = item("harness1", description="Demo harness")
    cable_part = part("cable1", description="Demo cable part")
    cable_product = cable_product_facet("cable1", subject=cable_part.id, core_count=0)
    cable = item("cable1", description="Demo cable", parent=harness.id, part=cable_part.id)
    facet = cable_facet("cable1", subject=cable.id, length_mm=None)
    doc = document(
        "d-harness",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        logo=_SVG_LOGO,
        remove=(K.COVER, K.CONTENTS, K.BOM),
    )
    m = model(p, entry, harness, cable_part, cable_product, cable, facet, doc)
    svgs = {render_id(cable.id): "<svg>cable-drawing</svg>"}
    return source(m, doc.id, svgs)


def test_cable_page_embeds_the_documents_own_logo():
    """R11.3: the cable page's logo cell carries the document's own real logo SVG, not the
    empty `None` default (survivor ids 32 and 38: `logo=record.logo` dropped or replaced by
    `logo=None`, both leaving `TitleBlockFields.logo` at its own `None` default)."""
    text = _cable_only_source()
    assert literal(_SVG_LOGO) in text


def test_cable_page_shows_the_projects_own_notice():
    """R11.4: the cable page's notice cell carries the project's own notice text, not the empty
    default (survivor id 37: the `notice=project_notice(model)` keyword is dropped from the
    fields, so `notice` falls back to `TitleBlockFields`' own `""` default)."""
    text = _cable_only_source()
    assert literal(_NOTICE) in text


def test_cable_page_sheet_counter_is_always_empty():
    """R3: a cable page carries no sheet position of its own (survivor id 44:
    `sheet_counter=""` -> `sheet_counter="XXXX"`). With every other one-line field non-empty
    (module and helper docstrings above), `text("")` in the returned source can only be the
    Sheet cell's own value."""
    text = _cable_only_source()
    assert _value("") in text
    assert _value("XXXX") not in text
