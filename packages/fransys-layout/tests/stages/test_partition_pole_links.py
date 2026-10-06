"""EF-A2 part 6: a group split avoids severing a D1 pole link (deep-dive D4), at the stage level.

One invented group of five columns, `a` to `e`, each 400 wide, on a 1280 wide page: the greedy
fill takes three columns and then two. A pole link between two columns is a boundary that no
page may end at, when another boundary that fits is clean. Since part 7 a link also moves the
later column of its pair next to the earlier one (`test_partition_link_order.py`), so a link
that spans a boundary needs a partner with several columns behind it: the tests below use those.
"""

import dataclasses

import pytest
from samples import NO_HINTS, PROFILE, SHEET, column, hid

from fransys_layout.stages import ColumnWidth, GroupInfo, LocationInfo, partition
from fransys_layout.stages.partition import GROUP_SPLIT, ColumnTables

_NAMES = ("a", "b", "c", "d", "e")
_WIDTHS = dict.fromkeys(_NAMES, 400)


def _key(name: str) -> tuple[str, str]:
    return ("invented", name)


def _plan(pole_links=(), *, names=_NAMES, widths=None):
    """Partition one group holding the columns `names`, given `pole_links` (name pairs)."""
    widths = _WIDTHS if widths is None else widths
    columns = tuple(
        dataclasses.replace(column(name, (number,)), location=hid("aspect_node", 100))
        for number, name in enumerate(names, start=1)
    )
    return partition(
        columns,
        ColumnTables(
            widths=tuple(ColumnWidth(column=_key(name), width=widths[name]) for name in names),
            groups=(
                GroupInfo(
                    group=hid("aspect_node", 1),
                    key=("invented", "group1"),
                    label="G1",
                    description="Invented group 1",
                ),
            ),
            locations=(LocationInfo(location=hid("aspect_node", 100), label="C1"),),
            units=(),
            pole_links=tuple((_key(x), _key(y)) for x, y in pole_links),
        ),
        hints=NO_HINTS,
        profile=PROFILE,
        sheet=SHEET,
    )


def _shape(plans):
    """The column names of every page, left to right."""
    return [[c.column[1] for c in plan.columns] for plan in plans]


def test_no_links_split_at_the_last_point_that_fits() -> None:
    """`pole_links=()` is today's greedy fill, and the group still reports `GROUP_SPLIT`."""
    plans, findings = _plan()
    assert _shape(plans) == [["a", "b", "c"], ["d", "e"]]
    assert [f.code for f in findings] == [GROUP_SPLIT]


def test_a_clean_point_is_preferred_to_the_last_point_that_fits() -> None:
    """Links `b`-`c` and `b`-`d` span the boundaries after `b` and `c` (`d` stands behind `c`)."""
    plans, findings = _plan([("b", "c"), ("b", "d")])
    assert _shape(plans) == [["a"], ["b", "c", "d"], ["e"]]
    assert [f.code for f in findings] == [GROUP_SPLIT]


def test_the_latest_clean_point_that_fits_is_taken() -> None:
    """A link `c`-`d` spans only the boundary after `c`: the page ends after `b` instead."""
    plans, _ = _plan([("c", "d")])
    assert _shape(plans) == [["a", "b"], ["c", "d", "e"]]


def test_a_link_inside_one_page_is_not_a_cut() -> None:
    """A link `a`-`b` is spanned by no greedy boundary, so nothing moves."""
    plans, _ = _plan([("a", "b")])
    assert _shape(plans) == [["a", "b", "c"], ["d", "e"]]


def test_no_clean_point_that_fits_takes_the_greedy_point() -> None:
    """Links from `a` to each of `b` to `e` span every boundary: the last point that fits goes."""
    plans, findings = _plan([("a", "b"), ("a", "c"), ("a", "d"), ("a", "e")])
    assert _shape(plans) == [["a", "b", "c"], ["d", "e"]]
    assert [f.code for f in findings] == [GROUP_SPLIT]


def test_a_link_near_the_end_of_the_group_moves_the_last_cut() -> None:
    """Four columns of 300 fit a page; a link `d`-`e` spans that boundary, so three go."""
    widths = dict.fromkeys(_NAMES, 300)
    assert _shape(_plan(widths=widths)[0]) == [["a", "b", "c", "d"], ["e"]]
    assert _shape(_plan([("d", "e")], widths=widths)[0]) == [["a", "b", "c"], ["d", "e"]]


def test_a_link_to_a_column_of_another_group_is_ignored() -> None:
    """Only the pairs whose two columns are both in the unit count."""
    plans, _ = _plan([("b", "z"), ("z", "d")])
    assert _shape(plans) == [["a", "b", "c"], ["d", "e"]]


def test_the_order_of_a_pair_and_of_the_pairs_does_not_matter() -> None:
    """`(d, b)` is the pair `(b, d)`; the same links in any order give the same pages."""
    forward = _plan([("b", "c"), ("b", "d"), ("d", "e")])[0]
    reverse = _plan([("e", "d"), ("d", "b"), ("c", "b")])[0]
    assert _shape(forward) == [["a"], ["b", "c", "d"], ["e"]]
    assert forward == reverse


def test_several_links_are_all_avoided_when_a_point_allows() -> None:
    """Links `a`-`b` and `c`-`d` leave the boundary after `b` as the last clean point."""
    plans, _ = _plan([("a", "b"), ("c", "d")])
    assert _shape(plans) == [["a", "b"], ["c", "d", "e"]]


def test_a_single_column_wider_than_a_page_is_a_page_of_its_own() -> None:
    """A link cannot make a page hold a column that does not fit it."""
    widths = {**_WIDTHS, "c": 1500}
    plans, _ = _plan([("b", "c")], widths=widths)
    assert _shape(plans) == [["a"], ["b"], ["c"], ["d", "e"]]


@pytest.mark.parametrize("links", [[], [("b", "d")], [("a", "e")]])
def test_the_split_is_deterministic(links) -> None:
    """The same inputs give the same plans and findings."""
    assert _plan(links) == _plan(links)
