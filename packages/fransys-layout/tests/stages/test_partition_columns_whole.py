"""EF-A2 part 2: a column is never cut across pages (D2), however the pages are packed.

Packing cuts a too-wide unit between its columns and never inside one, and a column that fits
no page is a separate question (not asserted here). The stage-level check runs `partition` over
a mixed set of groups and loose columns; the engine-level check runs the invented cabinet on
several sheet widths and reads where each column's functions were placed.
"""

import dataclasses
from collections import defaultdict
from decimal import Decimal

import pytest
from layout_cabinet import build_cabinet
from samples import NO_HINTS, PROFILE, SHEET, column, hid

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.stages import ColumnWidth, GroupInfo, LocationInfo, partition
from fransys_layout.stages.partition import ColumnTables
from fransys_model.kernel import Origin, freeze, make_id
from fransys_model.layout import Profile, SheetFormat

_ORIGIN = Origin(file="tests/stages/test_partition_columns_whole.py", line=1, note="columns whole")
_WIDTHS = {"a": 400, "b": 300, "c": 500, "d": 350, "e": 450, "f": 250, "g": 600, "h": 200}


def _info(number: int) -> GroupInfo:
    return GroupInfo(
        group=hid("aspect_node", number),
        key=("invented", f"group{number}"),
        label=f"G{number}",
        description=f"Invented group {number}",
    )


@pytest.mark.parametrize("content_width", [500, 700, 900, 1100, 1280])
def test_every_column_is_on_exactly_one_page_whatever_the_content_width(
    content_width: int,
) -> None:
    """Groups of one to three columns and loose ones: each column key is on one page, once."""
    columns = (
        column("a", (1, 2), group=1),
        column("b", (3,), group=1),
        column("c", (4,), group=2),
        column("d", (5, 6), group=2),
        column("e", (7,), group=2),
        column("f", (8,), group=3),
        column("g", (9,), group=None),
        column("h", (10,), group=None),
    )
    widths = tuple(ColumnWidth(column=("invented", name), width=w) for name, w in _WIDTHS.items())
    sheet = dataclasses.replace(SHEET, content_width=content_width)
    pages, _ = partition(
        columns,
        ColumnTables(
            widths=widths,
            groups=(_info(1), _info(2), _info(3)),
            locations=(LocationInfo(location=hid("aspect_node", 100), label="C1"),),
            units=(),
        ),
        hints=NO_HINTS,
        profile=PROFILE,
        sheet=sheet,
    )
    on_pages = [planned.column for page in pages for planned in page.columns]
    assert sorted(on_pages) == sorted(one.key for one in columns)
    if content_width < sum(_WIDTHS.values()):
        assert len(pages) > 1


def _cabinet_on(width_mm: int):
    """The cabinet on an authored sheet `width_mm` wide, the house profile values otherwise."""
    draft = build_cabinet()
    sheet = SheetFormat(
        id=make_id(SheetFormat, ("test", "sheet")),
        key=("test", "sheet"),
        name="narrower",
        width_mm=width_mm + 20,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=width_mm,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    profile = Profile(
        id=make_id(Profile, ("test", "profile")),
        key=("test", "profile"),
        sheet_format=sheet.id,
        column_gap=DEFAULT_PROFILE.column_gap,
        row_gap=DEFAULT_PROFILE.row_gap,
        route_margin=DEFAULT_PROFILE.route_margin,
        text_height=DEFAULT_PROFILE.text_height,
        marker_padding=DEFAULT_PROFILE.marker_padding,
        route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
        route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
        band_ranks=DEFAULT_PROFILE.band_ranks,
        group_ranks=DEFAULT_PROFILE.group_ranks,
    )
    draft.extend((sheet, profile), origin=_ORIGIN)
    model = freeze(draft)
    return stage_results(model, read_inputs(model))[0]


@pytest.mark.parametrize("width_mm", [400, 300, 200, 158, 120, 100])
def test_no_column_of_the_cabinet_has_its_functions_on_two_pages(width_mm: int) -> None:
    """Each column's placements share one page, and the narrower sheets do split the cabinet."""
    layout = _cabinet_on(width_mm).layout
    pages_of: defaultdict[tuple[str, ...], set[tuple[int, int]]] = defaultdict(set)
    for placed in layout.placed:
        pages_of[placed.column].add((placed.drawing_set, placed.page))
    assert pages_of
    assert [key for key, pages in pages_of.items() if len(pages) > 1] == []
    if width_mm <= 200:
        assert len(layout.pages) > 2
