"""Cable table pages group by part (pdf-0020, amending pdf-0018 CT2).

One run of pages per part number, parts in part-number order, cables in designation order inside
a run. A run's part heading is the page header: the part number alone on its first page, and the
same text with " (cont.)" after it on every later page of the run. A cable's table never splits
across pages unless that one cable alone is taller than a page.
"""

import re
from dataclasses import replace
from itertools import pairwise

import typst
from _build import (
    cable_facet,
    cable_product_facet,
    conductor,
    core_facet,
    document,
    item,
    model,
    part,
    pin,
    project,
)
from _png import Box, decode_png, ink_bbox
from fransys_pdf import source
from fransys_pdf._cable_runs import _flow
from fransys_pdf._drawings import _cable_runs
from fransys_pdf._typst import literal

from fransys_model.derive import HarnessCable, HarnessCore
from fransys_model.kernel import make_id
from fransys_model.layout import default_sheet_format
from fransys_model.vocab import Conductor, ConductorKind, DocumentPreset, PageKind, Port, documents

K = PageKind


def _doc_source(spec: dict[str, list[tuple[str, int]]]) -> str:
    """The HARNESS_DRAWING source of one harness holding `spec`'s cables.

    `spec` maps a part key to its cables, each `(cable key, core count)`.
    """
    harness = item("harness1", description="Demo harness")
    end_a, end_b = pin("ea", "XA"), pin("eb", "XB")
    records: list = [project(), harness, *end_a, *end_b]
    for part_key, cables in spec.items():
        cable_part = part(part_key, description=f"Invented {part_key} cable")
        product = cable_product_facet(part_key, subject=cable_part.id, core_count=4)
        colours = ("black",) * max(cores for _, cores in cables)
        records += [cable_part, replace(product, core_colours=colours)]
        for cable_key, cores in cables:
            cable = item(cable_key, description="Cable", parent=harness.id, part=cable_part.id)
            records += [cable, cable_facet(cable_key, subject=cable.id, length_mm=None)]
            for n in range(1, cores + 1):
                core = conductor(
                    f"{cable_key}-{n}",
                    a=end_a[2].id,
                    b=end_b[2].id,
                    kind=ConductorKind.CORE,
                    carrier=cable.id,
                )
                records += [core, core_facet(f"{cable_key}-{n}", subject=core.id, index=n)]
    doc = document(
        "d-harness",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        remove=(K.COVER, K.CONTENTS, K.BOM),
    )
    return source(model(*records, doc), doc.id, {})


def _runs(text: str) -> list[list[str]]:
    """Per `#page` of `text`, the cable designations in the order they are written."""
    pages = text.split("#page(")[1:]
    return [re.findall(r'strong\(text\("(-HARNESS1-W\d+)', page) for page in pages]


def _heading_runs(text: str) -> list[str]:
    """The part line each run's header is built for, in page order."""
    return re.findall(r'header: \{ context \{ let first = [^}]*?strong\(text\("([^"]+)"', text)


def _rasters(text: str) -> list:
    """The compiled pages as 60 ppi rasters (the A3 sheet is 992 px wide)."""
    result = typst.Compiler(text.encode("utf-8")).compile(format="png", ppi=60)
    assert result is not None
    return [decode_png(p) for p in ([result] if isinstance(result, bytes) else result)]


def _heading_width(page) -> int:
    """Width in pixels of the ink in the header band, where the part heading is printed."""
    x0, _, x1, _ = ink_bbox(page, Box(15, 400, 30, 38)) or (0, 0, 0, 0)
    return x1 - x0


def test_cables_group_by_part_in_part_number_order() -> None:
    """Two parts, interleaved authoring: two runs, parts by number, cables by designation."""
    text = _doc_source(
        {
            "zz-cbl": [("w5", 2), ("w1", 2), ("w3", 2)],
            "aa-cbl": [("w4", 2), ("w2", 2)],
        }
    )
    assert _runs(text) == [
        ["-HARNESS1-W2", "-HARNESS1-W4"],
        ["-HARNESS1-W1", "-HARNESS1-W3", "-HARNESS1-W5"],
    ]
    assert _heading_runs(text) == [
        "SIM-AA-CBL, Invented aa-cbl cable, 2 x 0.5 mm²",
        "SIM-ZZ-CBL, Invented zz-cbl cable, 2 x 0.5 mm²",
    ]


def test_a_table_moves_whole_to_the_next_page() -> None:
    """Nine 25-core cables: eight columns fill page 1, the ninth starts page 2 under its
    designation, whole down to core 25, so no table splits.
    """
    text = _doc_source({"aa-cbl": [(f"w{n}", 25) for n in range(1, 10)]})
    pages = _rasters(text)
    assert len(pages) == 2
    assert ink_bbox(pages[1], Box(15, 130, 49, 55)) is not None
    assert ink_bbox(pages[1], Box(15, 130, 396, 412)) is not None


def test_tables_fill_a_column_then_stand_side_by_side() -> None:
    """Two 25-core tables, each over half the page body: one page, the second in a column to
    the right, since it does not fit under the first.
    """
    text = _doc_source({"aa-cbl": [("w1", 25), ("w2", 25)]})
    (page,) = _rasters(text)
    assert ink_bbox(page, Box(15, 130, 55, 300)) is not None
    assert ink_bbox(page, Box(135, 250, 55, 300)) is not None


def test_a_single_cable_longer_than_a_page_splits_and_repeats_the_heading() -> None:
    """The exception: one 80-core cable cannot fit a page, so its table breaks across pages."""
    text = _doc_source({"aa-cbl": [("w1", 80)]})
    widths = [_heading_width(page) for page in _rasters(text)]
    assert len(widths) == 2
    assert widths[1] > widths[0] > 0


def test_cables_of_a_part_keep_the_cable_lists_designation_order() -> None:
    """-W2 and -W10 in one part print in derive's order (`harness_cables`: natural designation
    order, so -W2 first), not a second rule of this module's own."""
    text = _doc_source({"aa-cbl": [("w10", 1), ("w2", 1)]})
    assert _runs(text) == [["-HARNESS1-W2", "-HARNESS1-W10"]]


def _bare_cable(designation: str, mpn: str | None) -> HarnessCable:
    return HarnessCable(
        cable=item(f"c{designation}", description="Cable").id,
        designation=designation,
        mpn=mpn,
        description=None,
        core_count=None,
        gauge_mm2=None,
        shielded=None,
        length_mm=None,
        cores=(),
        ends=(),
    )


def test_cables_with_no_part_number_form_the_last_run_headed_no_part_number() -> None:
    """Derive gives every real cable a part, so bare rows stand in. The part run comes first;
    the cables with no part number share one last run, in the given order, under the heading
    "No part number" whose continuation reads "No part number (cont.)" like any other run's.
    """
    harness = item("harness1", description="Demo harness")
    doc = document(
        "d-harness",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        remove=(K.COVER, K.CONTENTS, K.BOM),
    )
    m = model(project(), harness, doc)
    cables = (_bare_cable("-W1", None), _bare_cable("-W2", "SIM-A"), _bare_cable("-W3", None))
    text = _cable_runs(m, documents(m)[doc.id], default_sheet_format(), cables)
    pages = text.split("#page(")[1:]
    assert len(pages) == 2
    assert 'strong(text("-W2' in pages[0]
    assert 'text("SIM-A" + if' in pages[0]
    assert pages[1].index('strong(text("-W1') < pages[1].index('strong(text("-W3')
    assert 'text("No part number" + if here().page() > first { " (cont.)" }' in pages[1]


def test_a_wide_block_that_would_widen_its_column_past_the_page_moves_on() -> None:
    """A 250 mm-tall block fills column 1 (100 mm wide). A narrow block opens column 2; the wide
    330 mm block would fit that column's height but widen it past the 400 mm page, so it
    starts page 2. Checked against the first block's width alone it would run off page 1.
    """
    tall = "#rect(width: 100mm, height: 250mm)"
    narrow = "#rect(width: 50mm, height: 40mm)"
    wide = "#rect(width: 330mm, height: 10mm)"
    page = "#set page(width: 400mm, height: 300mm, margin: 0mm)\n"
    text = page + _flow([tall, narrow, wide], 400, 280)
    result = typst.Compiler(text.encode("utf-8")).compile(format="png", ppi=20)
    assert result is not None
    assert not isinstance(result, bytes)
    assert len(result) == 2


def test_a_no_part_number_run_longer_than_a_page_continues_under_its_heading() -> None:
    """One cable with no part number and 55 cores: its second page carries the heading
    "No part number (cont.)", wider than page 1's "No part number".
    """
    cores = tuple(
        HarnessCore(
            conductor=make_id(Conductor, ("conductor", f"c{n}")),
            index=n,
            colour="black",
            label=None,
            end_a=make_id(Port, ("port", f"a{n}")),
            end_a_designation="-XA:1",
            end_b=make_id(Port, ("port", f"b{n}")),
            end_b_designation="-XB:1",
        )
        for n in range(1, 56)
    )
    harness = item("harness1", description="Demo harness")
    doc = document(
        "d-harness",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        remove=(K.COVER, K.CONTENTS, K.BOM),
    )
    m = model(project(), harness, doc)
    cable = replace(_bare_cable("-W1", None), cores=cores)
    text = _cable_runs(m, documents(m)[doc.id], default_sheet_format(), (cable,))
    assert '"No part number"' in text
    widths = [_heading_width(page) for page in _rasters(text)]
    assert len(widths) == 2
    assert widths[1] > widths[0] > 0


# -- CABLE-HEADING (pdf-0021): the part line once at the top, cables headed by designation ----

_PART_LINE = "SIM-AA-CBL, Invented aa-cbl cable, 25 x 0.5 mm²"


def _cable_headings(text: str) -> list[str]:
    """Every cable heading line written in `text`, in order: the strong text that starts `-`."""
    return re.findall(r'#strong\(text\("(-[^"]*)"\)\)', text)


def _column_count(page, y0: int, y1: int) -> int:
    """How many separate ink clusters (gaps over 8 px) lie in the horizontal band `y0`..`y1`."""
    xs = [x for x in range(15, 975) if ink_bbox(page, Box(x, x + 1, y0, y1)) is not None]
    return sum(1 for a, b in pairwise(xs) if b - a > 8) + 1 if xs else 0


def test_the_wrap_case_is_one_page_of_five_columns() -> None:
    """Five 25-core cables of one part: a column is as wide as its table, so all five stand
    side by side on one page.
    """
    text = _doc_source({"aa-cbl": [(f"w{n}", 25) for n in range(1, 6)]})
    (page,) = _rasters(text)
    assert _column_count(page, 49, 55) == 5


def test_the_part_line_is_written_once_at_the_top_of_the_page() -> None:
    """Part number, description, cores x gauge: in the header only, not in any cable heading."""
    text = _doc_source({"aa-cbl": [(f"w{n}", 25) for n in range(1, 4)]})
    assert text.count("Invented aa-cbl cable") == 1
    header = text.split("header: {")[1].split("background:")[0]
    assert literal(_PART_LINE) in header


def test_each_cable_heading_is_its_designation_only() -> None:
    """No part number, description or size follows the designation."""
    text = _doc_source({"aa-cbl": [("w1", 2), ("w2", 2)]})
    assert _cable_headings(text) == ["-HARNESS1-W1", "-HARNESS1-W2"]


def test_a_continuation_page_puts_cont_after_the_part_line() -> None:
    """Nine 25-core cables of one part overflow page 1; page 2's header is the part line
    and " (cont.)", wider than page 1's.
    """
    text = _doc_source({"aa-cbl": [(f"w{n}", 25) for n in range(1, 10)]})
    widths = [_heading_width(page) for page in _rasters(text)]
    assert len(widths) == 2
    assert widths[1] > widths[0] > 0


def test_a_no_part_run_has_its_heading_and_cables_headed_by_designation() -> None:
    """The "No part number" run keeps its header; its cables carry the designation alone."""
    harness = item("harness1", description="Demo harness")
    doc = document(
        "d-harness",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        remove=(K.COVER, K.CONTENTS, K.BOM),
    )
    m = model(project(), harness, doc)
    cables = (_bare_cable("-W1", None), _bare_cable("-W2", None))
    text = _cable_runs(m, documents(m)[doc.id], default_sheet_format(), cables)
    header = text.split("header: {")[1].split("background:")[0]
    assert '"No part number"' in header
    assert _cable_headings(text) == ["-W1", "-W2"]
