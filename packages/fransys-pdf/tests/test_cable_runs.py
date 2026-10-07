"""Cable block pages group by part (pdf-0020, amended by pdf-0022).

One run of pages per part number, parts in part-number order, blocks in the cable list's order
inside a run. A run's part heading is the page header: the part number alone on its first page,
and the same text with " (cont.)" after it on every later page of the run. A block is a stand-in
SVG here (render is not imported); it never splits across pages.
"""

import re
from dataclasses import replace

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
from fransys_pdf._cable_runs import Block, _flow
from fransys_pdf._drawings import _cable_runs

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.kernel import render_id
from fransys_model.layout import default_sheet_format
from fransys_model.vocab import ConductorKind, DocumentPreset, PageKind, documents

K = PageKind
_PX_PER_MM = 60 / 25.4  # the compiled pages are rasterised at 60 ppi
_BODY_Y = (46, 635)  # rows of a 60 ppi A3 page between its header band and its title block


def _svg(width_mm: int, height_mm: int, tag: str) -> str:
    """A stand-in block SVG: a black rectangle of the given size in mm, tagged by a comment."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}"><!--{tag}-->'
        f'<rect width="{width_mm}" height="{height_mm}"/></svg>'
    )


def _system_document(
    spec: dict[str, list[tuple[str, int]]], size: tuple[int, int]
) -> tuple[str, dict[str, str]]:
    """The HARNESS_DRAWING source of a SYSTEM document holding `spec`'s lone cables, and its svgs.

    `spec` maps a part key to its cables, each `(cable key, core count)`. Every cable is its own
    block, a `size` stand-in tagged by its key.
    """
    end_a, end_b = pin("ea", "XA"), pin("eb", "XB")
    records: list = [project(), *end_a, *end_b]
    svgs = {}
    for part_key, cables in spec.items():
        cable_part = part(part_key, description=f"Invented {part_key} cable")
        product = cable_product_facet(part_key, subject=cable_part.id, core_count=4)
        colours = ("black",) * max(cores for _, cores in cables)
        records += [cable_part, replace(product, core_colours=colours)]
        for cable_key, cores in cables:
            cable = item(cable_key, description="Cable", part=cable_part.id)
            records += [cable, cable_facet(cable_key, subject=cable.id, length_mm=None)]
            svgs[cable_block_key(None, cable.id)] = _svg(*size, cable_key)
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
        "d-system",
        preset=DocumentPreset.SYSTEM,
        cover="# Cover",
        remove=(K.COVER, K.NOTES, K.CABLE_LIST, K.BOM),
    )
    return source(model(*records, doc), doc.id, svgs), svgs


def _runs(text: str) -> list[list[str]]:
    """Per `#page` of `text`, the block tags in the order they are written."""
    pages = text.split("#page(")[1:]
    return [re.findall(r"<!--(\w+)-->", page) for page in pages]


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


def _hand_blocks(*mpns: str) -> tuple[Block, ...]:
    """Blocks `w1`, `w2`, ... in the given order, each in the run of its part number."""
    return tuple(Block(f"w{n}", mpn, mpn) for n, mpn in enumerate(mpns, 1))


def _hand_runs(blocks: tuple[Block, ...], size: tuple[int, int]) -> str:
    """The run pages of hand-built `blocks`, each a `size` stand-in, for the house sheet."""
    harness = item("harness1", description="Demo harness")
    doc = document(
        "d-harness",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        remove=(K.COVER, K.CONTENTS, K.BOM),
    )
    m = model(project(), harness, doc)
    svgs = {block.key: _svg(*size, block.key) for block in blocks}
    return _cable_runs(m, documents(m)[doc.id], default_sheet_format(), blocks, svgs)


def test_blocks_group_by_part_in_part_number_order() -> None:
    """Two parts, interleaved authoring: two runs, parts by number, blocks by designation."""
    text, _ = _system_document(
        {
            "zz-cbl": [("w5", 2), ("w1", 2), ("w3", 2)],
            "aa-cbl": [("w4", 2), ("w2", 2)],
        },
        (40, 30),
    )
    assert _runs(text) == [["w2", "w4"], ["w1", "w3", "w5"]]
    assert _heading_runs(text) == [
        "SIM-AA-CBL, Invented aa-cbl cable, 2 x 0.5 mm²",
        "SIM-ZZ-CBL, Invented zz-cbl cable, 2 x 0.5 mm²",
    ]


def test_blocks_of_a_part_keep_the_cable_lists_designation_order() -> None:
    """-W2 and -W10 in one part print in derive's order (`harness_cables`: natural designation
    order, so -W2 first), not a second rule of this module's own."""
    text, _ = _system_document({"aa-cbl": [("w10", 1), ("w2", 1)]}, (40, 30))
    assert _runs(text) == [["w2", "w10"]]


def test_a_page_holds_blocks_not_a_core_table() -> None:
    """Acceptance 10, pdf half: each block's SVG is an embedded image; no table, no headers."""
    text, _ = _system_document({"aa-cbl": [("w1", 3)]}, (40, 30))
    assert 'format: "svg")' in text
    assert "<!--w1-->" in text
    for old in ("#table(", "table.header(", '"Core"', '"From"', '"To"', '"Label"'):
        assert old not in text


def test_the_part_line_is_written_once_at_the_top_of_the_page() -> None:
    """Part number, description, cores x gauge: in the header only, once for the run."""
    text, _ = _system_document({"aa-cbl": [(f"w{n}", 25) for n in range(1, 4)]}, (40, 30))
    assert text.count("Invented aa-cbl cable") == 1
    header = text.split("header: {")[1].split("background:")[0]
    assert "SIM-AA-CBL, Invented aa-cbl cable, 25 x 0.5 mm²" in header


def test_a_block_moves_whole_to_the_next_page() -> None:
    """Nine 45 x 200 mm blocks: eight columns fill page 1, the ninth starts page 2 alone and
    whole, its full 200 mm height inked, so no block splits (acceptance 10's probe).
    """
    text, _ = _system_document({"aa-cbl": [(f"w{n}", 1) for n in range(1, 10)]}, (45, 200))
    first, second = _rasters(text)
    height = ink_bbox(second, Box(20, 130, *_BODY_Y))
    assert height is not None
    assert abs((height[3] - height[1] + 1) - 200 * _PX_PER_MM) <= 3
    assert ink_bbox(second, Box(150, 970, *_BODY_Y)) is None
    assert ink_bbox(first, Box(850, 970, *_BODY_Y)) is not None


def test_blocks_fill_a_column_then_stand_side_by_side() -> None:
    """Three 100 x 120 mm blocks: two fill column 1 (244 of the 251 mm body), the third stands
    in a column to the right whole, not split across the first column's end.
    """
    text, _ = _system_document({"aa-cbl": [("w1", 1), ("w2", 1), ("w3", 1)]}, (100, 120))
    (page,) = _rasters(text)
    left = ink_bbox(page, Box(20, 265, *_BODY_Y))
    right = ink_bbox(page, Box(265, 515, *_BODY_Y))
    assert left is not None
    assert right is not None
    assert abs((left[3] - left[1] + 1) - (2 * 120 + 4) * _PX_PER_MM) <= 4
    assert abs((right[3] - right[1] + 1) - 120 * _PX_PER_MM) <= 3


def test_a_continuation_page_puts_cont_after_the_part_line() -> None:
    """Nine 45 x 200 mm blocks of one part overflow page 1; page 2's header is the part line
    and " (cont.)", wider than page 1's.
    """
    text, _ = _system_document({"aa-cbl": [(f"w{n}", 1) for n in range(1, 10)]}, (45, 200))
    widths = [_heading_width(page) for page in _rasters(text)]
    assert len(widths) == 2
    assert widths[1] > widths[0] > 0


def test_blocks_with_no_part_number_form_the_last_run_headed_no_part_number() -> None:
    """The part run comes first; the blocks with no part number share one last run, in the given
    order, under the heading "No part number" whose continuation reads "No part number (cont.)"
    like any other run's.
    """
    text = _hand_runs(_hand_blocks("", "SIM-A", ""), (40, 30))
    pages = text.split("#page(")[1:]
    assert len(pages) == 2
    assert "<!--w2-->" in pages[0]
    assert 'text("SIM-A" + if' in pages[0]
    assert pages[1].index("<!--w1-->") < pages[1].index("<!--w3-->")
    assert 'text("No part number" + if here().page() > first { " (cont.)" }' in pages[1]


def test_a_no_part_number_run_longer_than_a_page_continues_under_its_heading() -> None:
    """Nine tall blocks with no part number: the second page carries the heading
    "No part number (cont.)", wider than page 1's "No part number".
    """
    text = _hand_runs(_hand_blocks(*[""] * 9), (45, 200))
    widths = [_heading_width(page) for page in _rasters(text)]
    assert len(widths) == 2
    assert widths[1] > widths[0] > 0


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


# -- a harness is one block (CD9, Q8) -----------------------------------------------------------


def _harness_source(*, has_part: bool) -> tuple[str, str]:
    """An item document over a harness of two cables; its source and its one block key."""
    cable_part = part("cbl", description="Invented cable")
    records: list = [
        project(),
        cable_part,
        cable_product_facet("cbl", subject=cable_part.id, core_count=0),
    ]
    harness_part = part("hh", description="Invented harness") if has_part else None
    if harness_part is not None:
        records.append(harness_part)
    harness = item(
        "harness1",
        description="Demo harness",
        part=None if harness_part is None else harness_part.id,
    )
    cables = [
        item(f"w{n}", description="Cable", parent=harness.id, part=cable_part.id) for n in (1, 2)
    ]
    records += [harness, *cables]
    records += [cable_facet(f"w{n}", subject=c.id, length_mm=None) for n, c in enumerate(cables, 1)]
    doc = document(
        "d-harness",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        remove=(K.COVER, K.CONTENTS, K.BOM),
    )
    m = model(*records, doc)
    key = cable_block_key(None, harness.id)
    return source(m, doc.id, {key: _svg(60, 40, "harness")}), key


def test_a_harness_of_two_cables_is_one_block_in_the_no_part_run() -> None:
    """Two cables of a harness with no part of its own: one block, keyed by the harness, in the
    "No part number" run, not the cables' own part run.
    """
    text, _ = _harness_source(has_part=False)
    assert _runs(text) == [["harness"]]
    assert _heading_runs(text) == ["No part number"]


def test_a_harness_block_goes_in_the_run_of_the_harnesss_own_part() -> None:
    """The harness has a part: its block is in that part's run, headed by that part's line."""
    text, _ = _harness_source(has_part=True)
    assert _runs(text) == [["harness"]]
    assert _heading_runs(text) == ["SIM-HH, Invented harness"]


def test_the_block_key_is_the_renders_id_of_the_subject_in_the_absolute_reading() -> None:
    """A SYSTEM document reads absolutely: the key is `render_id` of the lone cable itself."""
    text, svgs = _system_document({"aa-cbl": [("w1", 1)]}, (40, 30))
    (key,) = svgs
    assert render_id(item("w1", description="Cable").id) == key
    assert "<!--w1-->" in text
