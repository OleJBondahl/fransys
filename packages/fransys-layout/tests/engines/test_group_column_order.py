"""A group's column order does not depend on the content width (deep-dive D2, EF-A2 part 7).

In key order `=P1` runs `es`, `p1/control`, `p1/power`, then `-K1` `aux`; the `x2` terminal
replica is attached to a host column (V4), so it has no column of its own. Wire 17 joins `-K1`
`aux` to `es` (a D1 pole link), so `-K1` `aux` stands right after `es`,
on the one page of `=P1` at 300 mm and on every page order that follows at a narrow width.
"""

import pytest
from narrow_cabinet import narrow_results

from fransys_model.kernel import AuthoringKey, make_id
from fransys_model.vocab import AspectNode

_P1 = make_id(AspectNode, ("p1",))
_ES = ("cabinet", "es")
_K1_AUX = ("chain", "=P1+C1-K1", "cabinet", "k1", "fn", "aux")
_CONTROL = ("cabinet", "p1", "control")
_POWER = ("cabinet", "p1", "power")
_EXPECTED = [_ES, _K1_AUX, _CONTROL, _POWER]


def _p1_order(width_mm: int) -> list[AuthoringKey]:
    """The columns of `=P1` in the order its pages hold them, first page first."""
    results = narrow_results(width_mm)[0]
    mine = {column.key for column in results.columns if column.group == _P1}
    pages = sorted(results.layout.pages, key=lambda plan: (plan.drawing_set, plan.number))
    return [planned.column for plan in pages for planned in plan.columns if planned.column in mine]


@pytest.mark.parametrize("width_mm", [300, 200, 150, 100])
def test_the_columns_of_p1_stand_in_one_order_at_every_width(width_mm: int) -> None:
    """`-K1` `aux` is right after `es`, and the order is the same at 300 mm and at 100 mm."""
    assert _p1_order(width_mm) == _EXPECTED


def test_p1_is_one_page_at_300_mm_and_several_at_100_mm() -> None:
    """The widths compared really differ: the order is not the same because nothing split."""
    pages_of_p1 = {
        width: sum(
            any(g.group == _P1 for g in plan.groups)
            for plan in narrow_results(width)[0].layout.pages
        )
        for width in (300, 100)
    }
    assert pages_of_p1[300] == 1
    assert pages_of_p1[100] > 1
