"""`PAGE_UNDERFILLED`: a schematic page whose drawn content covers under half the content box.

The invented sheet is 1280 x 886 G. A symbol's keep-out is 56 x 32 G around its origin.
"""

import pytest
from samples import SHEET, hid, page_plan, placed

from fransys_layout.lint import lint_fill
from fransys_layout.lint._harness import NO_INK
from fransys_layout.lint.codes import ALL_CODES, PAGE_UNDERFILLED
from fransys_layout.lint.naming import append_pages_and_designations, where_drawn
from fransys_layout.stages import Layout
from fransys_model.kernel import Severity


def _layout(*functions) -> Layout:
    return Layout(
        pages=(page_plan(("a",)),),
        placed=functions,
        routes=(),
        decisions=(),
        markers=(),
        labels=(),
    )


def _spanning(bottom_origin: int) -> Layout:
    """Two functions: the keep-outs span the content width and `bottom_origin + 16 - 0` high."""
    return _layout(placed(1, x=8, y=16), placed(2, x=1232, y=bottom_origin))


def test_the_code_is_listed() -> None:
    assert PAGE_UNDERFILLED in ALL_CODES


def test_a_nearly_empty_page_is_reported_with_set_page_share_and_its_functions() -> None:
    (finding,) = lint_fill(_layout(placed(1, x=104, y=96), placed(2, x=104, y=304)), sheet=SHEET)
    assert finding.code == PAGE_UNDERFILLED
    assert finding.severity is Severity.INFO
    assert finding.subjects == (hid("function", 1), hid("function", 2))
    assert finding.message == "drawn content covers 1 % of the content box"


def test_a_page_spanning_exactly_half_is_left_alone() -> None:
    assert lint_fill(_spanning(427), sheet=SHEET) == ()


def test_a_page_one_unit_under_half_is_reported_and_the_share_is_floored() -> None:
    (finding,) = lint_fill(_spanning(426), sheet=SHEET)
    assert "covers 49 % of" in finding.message


def test_a_full_page_gets_none() -> None:
    assert lint_fill(_spanning(800), sheet=SHEET) == ()


def test_each_page_is_judged_alone() -> None:
    layout = _layout(placed(1, x=8, y=16), placed(2, x=1232, y=800), placed(3, x=104, y=96, page=2))
    (finding,) = lint_fill(layout, sheet=SHEET)
    (named,) = append_pages_and_designations({}, where_drawn(layout, (), NO_INK, {}), [finding])
    assert named.message == "drawn content covers 0 % of the content box (p1.2)"
    assert finding.subjects == (hid("function", 3),)


def test_a_pin_view_is_named_by_its_real_function() -> None:
    layout = _layout(placed(1, x=104, y=96), placed(2, x=104, y=304))
    (finding,) = lint_fill(
        layout, sheet=SHEET, pin_functions={hid("function", 2): hid("function", 9)}
    )
    assert finding.subjects == (hid("function", 1), hid("function", 9))


@pytest.mark.parametrize(
    ("printed", "count"),
    [(None, 1), (frozenset({1}), 1), (frozenset({2}), 0)],
    ids=["every set", "set 1 printed", "set 1 not printed"],
)
def test_a_page_of_a_set_nobody_prints_gets_no_finding(
    printed: frozenset[int] | None, count: int
) -> None:
    layout = _layout(placed(1, x=104, y=96), placed(2, x=104, y=304))
    assert len(lint_fill(layout, sheet=SHEET, printed=printed)) == count
