"""The designer's review metrics on the invented cabinet (deep dive F7, decision layout-0047).

All five metrics are findings: `OUT_OF_CONTENT_BOX` (texts outside), `WIRE_OVER_LABEL` and
`TEXT_CROSSED_BY_ROUTE` (crossed texts), `LONE_CELL` and `CHAIN_BROKEN` (stranded cells, cut
chains), and `TEXT_OVERLAP` (overlapping texts, or a text over a foreign body); `text_overlaps`
(`lint/_texts.py`) is unit-tested in `tests/lint/test_text_overlap.py`. The cabinet variants
that are clean stay clean here, and the variants where the engine still draws a defect are
pinned as known engine defects.
"""

from decimal import Decimal
from functools import cache
from typing import TYPE_CHECKING

import pytest
from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.lint.codes import (
    CHAIN_BROKEN,
    LONE_CELL,
    OUT_OF_CONTENT_BOX,
    TEXT_CROSSED_BY_ROUTE,
    TEXT_OVERLAP,
    WIRE_OVER_LABEL,
)
from fransys_model.kernel import Origin, freeze, make_id
from fransys_model.layout import Profile, SheetFormat

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Finding


def _narrow(draft: Draft, width_mm: int) -> None:
    """Put the cabinet on an authored sheet `width_mm` wide, the house profile values otherwise."""
    sheet = SheetFormat(
        id=make_id(SheetFormat, ("test", "sheet")),
        key=("test", "sheet"),
        name="narrow",
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
    draft.extend((sheet, profile), origin=Origin(file=__file__, line=1, note="narrow sheet"))


@cache
def _cabinet(*, reverse: bool = False, second_location: bool = False, width_mm: int | None = None):
    draft = build_cabinet(reverse=reverse, second_location=second_location)
    if width_mm is not None:
        _narrow(draft, width_mm)
    model = freeze(draft)
    inputs = read_inputs(model)
    results, findings = stage_results(model, inputs)
    return inputs, results, findings


_REVIEW_CODES = {
    OUT_OF_CONTENT_BOX,
    WIRE_OVER_LABEL,
    TEXT_CROSSED_BY_ROUTE,
    LONE_CELL,
    CHAIN_BROKEN,
    TEXT_OVERLAP,
}
_VARIANTS = [
    pytest.param({}, id="default"),
    pytest.param({"reverse": True}, id="reversed authoring order"),
    pytest.param({"second_location": True}, id="two locations"),
    pytest.param({"width_mm": 300}, id="300 mm"),
    pytest.param({"width_mm": 245}, id="245 mm"),
    pytest.param({"width_mm": 190}, id="190 mm"),
]


def _review(findings: tuple[Finding, ...]) -> list[str]:
    """The review codes of `findings`."""
    return sorted(one.code for one in findings if one.code in _REVIEW_CODES)


@pytest.mark.parametrize("variant", _VARIANTS[:3])
def test_the_invented_cabinet_has_none_of_the_five_review_defects(variant: dict) -> None:
    """All five review codes are findings now, and `_review` reads them all off `findings`.

    Every variant draws link markers, so the marker-shaped checks have something to judge.
    """
    _, results, findings = _cabinet(**variant)
    assert results.layout.markers
    assert _review(findings) == []


@pytest.mark.parametrize(
    ("width_mm", "cut"),
    [
        pytest.param(300, {"k1", "k2"}, id="300 mm: k1 aux and k2 aux"),
        pytest.param(245, {"k1", "k2"}, id="245 mm: k1 aux and k2 aux"),
        pytest.param(190, {"k1", "k2"}, id="190 mm: k1 aux and k2 aux"),
    ],
)
def test_known_engine_defect_a_chain_cut_between_two_one_cell_columns(
    width_mm: int, cut: set[str]
) -> None:
    """Known engine defect, pinned as measured: one `CHAIN_BROKEN`, engine-fixes order.

    Chain facts: each `aux` contact is a one-cell column of its own (C7 splits its chain where
    the authored group changes -- `=P1` to `=P2` -- so the engine reports
    `FUNCTION_UNPLACED_IN_COLUMN`), and it shares a net of exactly two poles with the next
    function (the other `aux`, at every width): both ends are pole ports of a switched
    internal link, so this is a genuine D1 chain link, confirmed under the tightened
    `CHAIN_BROKEN` (a false positive would have dropped out once the check reads pole ports
    instead of kind). At 190 mm the `nc_2` of the `es` column is a second such partner of
    `-K1` `aux`; deep-dive D2's column order puts the two columns side by side, so the group
    split no longer cuts that pair (`tests/engines/test_pole_link_split.py`). D1 makes each pair one
    chain; the page split puts the two on different pages and severs the wire between them into
    a marker pair. Delete this test when the engine keeps such a pair's column whole across the
    split; then a cut column would instead strand a cell (`LONE_CELL`). Not a `LONE_CELL` today:
    no column is cut, each cell is the only cell of its own column.
    """
    inputs, results, findings = _cabinet(width_mm=width_mm)
    assert results.layout.markers
    assert _review(findings) == [CHAIN_BROKEN]
    broken = next(one for one in findings if one.code == CHAIN_BROKEN)
    keys = {one.function: one.key for one in inputs.functions}
    assert {keys[one][1] for one in broken.subjects if one.kind == "function"} == cut
