"""HL21 (layout-0153 P2c): a unit group is one packing unit: whole on one page, first on it."""

import dataclasses

from samples import NO_HINTS, PROFILE, SHEET, column, hid

from fransys_layout.stages import (
    ColumnWidth,
    GroupInfo,
    GroupSet,
    LocationInfo,
    PageHints,
    Role,
    partition,
)
from fransys_layout.stages._gather import Band, banded, gather
from fransys_layout.stages._packing import Unit
from fransys_layout.stages.partition import GROUP_SPLIT, UNIT_GROUP_SPLIT, ColumnTables
lazy from fransys_model.kernel import AuthoringKey, Severity

LOCATIONS = (LocationInfo(location=hid("aspect_node", 100), label="C1"),)


def _key(name: str) -> AuthoringKey:
    return ("invented", name)


def _band(upper: str, lower: str, outline: int = 100) -> Band:
    return Band(
        upper=frozenset(_key(n) for n in upper),
        lower=frozenset(_key(n) for n in lower),
        outline=outline,
    )


def _plan(widths: dict[str, int], bands: list[Band], hints: PageHints = NO_HINTS):
    """One column per name, each in its own group, in name order, packed with `bands`."""
    names = sorted(widths)
    columns = tuple(column(n, (i + 1,), group=i + 1) for i, n in enumerate(names))
    groups = tuple(
        GroupInfo(
            group=hid("aspect_node", i + 1),
            key=("invented", f"group{i + 1}"),
            label=f"G{i + 1}",
            description=f"Invented group {i + 1}",
        )
        for i in range(len(names))
    )
    tables = ColumnTables(
        widths=tuple(ColumnWidth(column=_key(n), width=w) for n, w in widths.items()),
        groups=groups,
        locations=LOCATIONS,
        units=(),
        bands=banded(bands),
    )
    return partition(columns, tables, hints=hints, profile=PROFILE, sheet=SHEET)


def _shape(pages) -> list[list[str]]:
    return [[c.column[1] for c in p.columns] for p in pages]


def test_a_group_packs_whole_at_its_first_columns_place() -> None:
    """Today b and d split over two pages; as one group (b above, d below) they share page 1."""
    widths = dict.fromkeys("abcde", 400)
    assert _shape(_plan(widths, [])[0]) == [["a", "b", "c"], ["d", "e"]]
    pages, findings = _plan(widths, [_band("b", "d")])
    assert _shape(pages) == [["a", "b", "d", "c"], ["e"]]
    assert findings == ()


def test_a_group_that_does_not_fit_beside_the_columns_before_it_moves_whole() -> None:
    """Today b fits beside a and c spills; the group b over c is as wide as c and moves whole."""
    widths = {"a": 1000, "b": 200, "c": 400}
    assert _shape(_plan(widths, [])[0]) == [["a", "b"], ["c"]]
    pages, findings = _plan(widths, [_band("b", "c")])
    assert _shape(pages) == [["a"], ["b", "c"]]
    assert findings == ()


def test_two_groups_share_a_page_side_by_side_as_they_fold() -> None:
    """HL20: two groups, each as wide as its wider band, pack together with the column after."""
    widths = {"a": 1000, "b": 300, "c": 300, "d": 300, "e": 300, "f": 300}
    assert _shape(_plan(widths, [])[0]) == [["a"], ["b", "c", "d", "e"], ["f"]]
    pages, _ = _plan(widths, [_band("b", "c"), _band("d", "e")])
    assert _shape(pages) == [["a"], ["b", "c", "d", "e", "f"]]


def _unit(name: str, width: int) -> Unit:
    return Unit(
        groups=(None,), columns=(_key(name),), width=width, break_before=False, role=Role.CONTROL
    )


def test_a_group_is_as_wide_as_its_wider_band_or_outline_a_shared_column_below() -> None:
    widths: dict[AuthoringKey, int] = {_key("a"): 100, _key("b"): 200, _key("c"): 300}
    units = [_unit(n, w) for (_, n), w in widths.items()]
    wide = gather(units, banded([_band("ab", "bc")]), widths)
    assert [(u.columns, u.width) for u in wide] == [((_key("a"), _key("b"), _key("c")), 500)]
    outline = gather(units[:1], banded([_band("a", "", outline=900)]), widths)
    assert [u.width for u in outline] == [900]


def test_two_bands_sharing_a_column_are_one_unit_side_by_side() -> None:
    """HL20: the shared column b stays with the first band; the second adds its own width."""
    widths: dict[AuthoringKey, int] = {_key("a"): 100, _key("b"): 200, _key("c"): 300}
    widths[_key("d")] = 50
    units = [_unit(n, w) for (_, n), w in widths.items()]
    found = gather(units, banded([_band("a", "b", 10), _band("b", "c", 10)]), widths)
    assert [(u.columns, u.width) for u in found] == [
        ((_key("a"), _key("b"), _key("c")), 200 + 300),
        ((_key("d"),), 50),
    ]


def test_a_band_whose_columns_an_earlier_band_kept_still_counts_its_outline() -> None:
    """The fold still draws the second outline beside the first, so the estimate holds both."""
    widths: dict[AuthoringKey, int] = {_key("a"): 100, _key("b"): 200}
    units = [_unit(n, w) for (_, n), w in widths.items()]
    found = gather(units, banded([_band("a", "b", 10), _band("b", "", 400)]), widths)
    assert [u.width for u in found] == [200 + 400]


def test_a_break_before_on_an_absorbed_unit_starts_the_groups_page() -> None:
    widths: dict[AuthoringKey, int] = {_key("a"): 100, _key("b"): 200}
    units = [_unit("a", 100), dataclasses.replace(_unit("b", 200), break_before=True)]
    found = gather(units, banded([_band("a", "b")]), widths)
    assert [(u.columns, u.break_before) for u in found] == [((_key("a"), _key("b")), True)]


def test_a_keep_together_set_takes_the_unit_group_whole() -> None:
    """Groups 1 and 3 keep together; 3's column c is in the group over b, which comes along."""
    hints = PageHints(
        keep_together=(GroupSet(groups=(hid("aspect_node", 1), hid("aspect_node", 3))),),
        break_before=(),
        order=(),
    )
    pages, findings = _plan(dict.fromkeys("abcd", 400), [_band("b", "c")], hints)
    assert _shape(pages) == [["a", "b", "c", "d"]]
    assert findings == ()


def test_a_unit_group_wider_than_the_page_splits_with_unit_group_split() -> None:
    """HL21 (designer ruling): a group wider than the page splits, with its own WARNING code."""
    widths = dict.fromkeys("abc", 600)
    pages, findings = _plan(widths, [_band("", "abc")])
    assert _shape(pages) == [["a", "b"], ["c"]]
    assert [(f.code, f.severity) for f in findings] == [(UNIT_GROUP_SPLIT, Severity.WARNING)]
    assert GROUP_SPLIT not in {f.code for f in findings}
    assert "split over pages 1, 2" in findings[0].message
