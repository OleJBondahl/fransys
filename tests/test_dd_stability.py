"""F5-C, D17 (stability) on the example-sized fixture of `dd_stability_fixture`.

D17 (amended 2026-09-24): a change in one group moves records only on the pages that hold it and
on the pages in-order packing refills after it; pages before are byte-identical; a page that
keeps its group set is byte-identical; a derived key never changes because of another group.
"""

import dataclasses
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from fransys_model.layout import (
    Label,
    LinkMarker,
    Page,
    Route,
    StarKind,
    SymbolPlacement,
    layout_of,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_PATH = Path(__file__).with_name("dd_stability_fixture.py")
# Root tests run under `--import-mode=importlib`: load the sibling helper by path, once.
_FIXTURE = sys.modules.get("dd_stability_fixture")
if _FIXTURE is None:
    _SPEC = importlib.util.spec_from_file_location("dd_stability_fixture", _PATH)
    assert _SPEC is not None
    assert _SPEC.loader is not None
    _FIXTURE = importlib.util.module_from_spec(_SPEC)
    sys.modules["dd_stability_fixture"] = _FIXTURE
    _SPEC.loader.exec_module(_FIXTURE)

build = _FIXTURE.build
build_result = _FIXTURE.build_result
group_names = _FIXTURE.group_names

_KINDS = (SymbolPlacement, Route, Label, LinkMarker)


def _page_dump(model: Model, page_id) -> tuple:
    """Every placement, route, label and marker on one page, in a canonical order."""
    return tuple(
        sorted(
            (kind.__name__, id_.value, repr(record))
            for kind in _KINDS
            for id_, record in layout_of(model, kind).items()
            if record.page == page_id
        )
    )


def _pages_off_the_group(before: Model, after: Model, group: str) -> set:
    """Ids of the pages that hold no group sharing a page with `group`, before or after."""
    names = {id_: name for m in (before, after) for id_, name in group_names(m).items()}
    pages = [*layout_of(before, Page).values(), *layout_of(after, Page).values()]
    with_group = {p.id for p in pages if any(names[g.group] == group for g in p.groups)}
    sharing = {names[g.group] for p in pages if p.id in with_group for g in p.groups}
    return {p.id for p in pages if not {names[g.group] for g in p.groups} & sharing}


def _moved_off_the_group(before: Model, after: Model, group: str) -> list[str]:
    """D17: the pages holding no group that shares a page with `group` whose records differ."""
    free = _pages_off_the_group(before, after, group)
    return sorted(
        page.value[:8] for page in free if _page_dump(before, page) != _page_dump(after, page)
    )


def test_a_relay_in_the_last_device_group_moves_only_the_pages_of_that_group() -> None:
    """D17: pages holding no group that shares a page with `=F` are byte-identical, F's change."""
    # UNDO: stages/partition.py partition: `pack(sorted(runs, key=lambda r: -r.width), ...)`
    # (a plain reversal does NOT fail it; probed).
    before, after = build(), build(extra="F")
    assert _moved_off_the_group(before, after, "F") == []
    free = _pages_off_the_group(before, after, "F")
    assert len(free) >= 2
    assert all(_page_dump(before, page) for page in free)
    added = set(layout_of(after, SymbolPlacement)) - set(layout_of(before, SymbolPlacement))
    assert added
    assert {layout_of(after, SymbolPlacement)[i].key[3] for i in added} == {"KX"}
    assert {layout_of(after, SymbolPlacement)[i].page for i in added} <= set(
        layout_of(after, Page)
    ) - free


def _tampered(model: Model, kind_table: str, id_, **changes) -> Model:
    """`model` with one record altered through `dataclasses.replace`."""
    table = model.tables[kind_table]
    edited = type(table)({**table, id_: dataclasses.replace(cast("Any", table[id_]), **changes)})
    return dataclasses.replace(
        model, tables=type(model.tables)({**model.tables, kind_table: edited})
    )


def test_the_stability_check_can_fail() -> None:
    """A moved record on a page off the group is flagged; one on its own or shared page is not."""
    # UNDO: `_moved_off_the_group` / `_pages_off_the_group`: return [] and the first assert fails.
    before, after = build(), build(extra="F")
    off = _pages_off_the_group(before, after, "F")
    on = {p.id for p in layout_of(after, Page).values()} - off
    assert off
    assert on
    table = layout_of(after, SymbolPlacement)
    on_page = next(i for i, r in table.items() if r.page in on)
    off_page = next(i for i, r in table.items() if r.page in off)
    assert _moved_off_the_group(
        before, _tampered(after, "layout.symbol_placement", off_page, x=table[off_page].x + 8), "F"
    )
    assert (
        _moved_off_the_group(
            before,
            _tampered(after, "layout.symbol_placement", on_page, x=table[on_page].x + 8),
            "F",
        )
        == []
    )


_GEOMETRY = (SymbolPlacement, Route, Label)


def _dump(model: Model, page_id, kinds: tuple) -> tuple:
    """Every record of `kinds` on one page, in a canonical order."""
    return tuple(
        sorted(
            (kind.__name__, id_.value, repr(record))
            for kind in kinds
            for id_, record in layout_of(model, kind).items()
            if record.page == page_id
        )
    )


def _by_group_set(model: Model) -> dict:
    """The page ids by the set of group names each page holds."""
    names = group_names(model)
    return {
        frozenset(names[g.group] for g in page.groups): page.id
        for page in layout_of(model, Page).values()
    }


def _first_page(before: Model, after: Model, group: str) -> int:
    """The lowest page number that holds `group` in either model."""
    return min(
        page.number
        for m in (before, after)
        for page in layout_of(m, Page).values()
        if group in {group_names(m)[g.group] for g in page.groups}
    )


def _moved_before_the_group(before: Model, after: Model, group: str, kinds: tuple) -> list:
    """D17 clause 1: the pages numbered before `group`'s first page whose records differ."""
    first = _first_page(before, after, group)
    early = [p.id for p in layout_of(before, Page).values() if p.number < first]
    return [page for page in early if _dump(before, page, kinds) != _dump(after, page, kinds)]


def _moved_on_kept_pages(before: Model, after: Model, kinds: tuple, changed: str) -> list:
    """D17 clause 2: pages that keep their set of groups and hold no `changed` group whose
    records differ. A page holding the changed group changes by definition: it is exempt."""
    one, other = _by_group_set(before), _by_group_set(after)
    return sorted(
        (sorted(kept), one[kept].value[:8])
        for kept in one.keys() & other.keys()
        if changed not in kept
        and _dump(before, one[kept], kinds) != _dump(after, other[kept], kinds)
    )


@pytest.mark.parametrize("extra", ["C", "D", "E", "F"])
def test_the_pages_before_the_changed_groups_first_page_are_byte_identical(extra: str) -> None:
    """D17 clause 1: placements, routes and labels on the earlier pages do not move."""
    # UNDO: stages/partition.py partition: right-aligned packing,
    # `for page in [p[::-1] for p in pack(runs[::-1], ...)][::-1]` (probed, fails for [C]).
    before, after = build(), build(extra=extra)
    first = _first_page(before, after, extra)
    assert first >= 2
    assert _moved_before_the_group(before, after, extra, _GEOMETRY) == []
    assert all(
        _dump(before, p.id, _GEOMETRY) for p in layout_of(before, Page).values() if p.number < first
    )


@pytest.mark.parametrize("extra", ["B", "C", "D", "E", "F"])
def test_a_page_that_keeps_its_groups_is_byte_identical_apart_from_its_number(extra: str) -> None:
    """D17 clause 2: a page with the same group set, holding no changed group, is identical."""
    # UNDO: stages/place.py place: a page-local offset by the total placement count (which the
    # extra relay changes) leaks the change onto pages that do not hold it.
    before, after = build(), build(extra=extra)
    kept = _by_group_set(before).keys() & _by_group_set(after).keys()
    assert {group for pages in kept if extra not in pages for group in pages}
    assert _moved_on_kept_pages(before, after, _GEOMETRY, extra) == []


def _marker_keys_on_kept_pages(before: Model, after: Model, changed: str) -> list:
    """D17 clause 3: on pages that keep their group set and hold no `changed` group, the pages
    whose link-marker keys changed."""
    one, other = _by_group_set(before), _by_group_set(after)
    markers = [layout_of(m, LinkMarker) for m in (before, after)]

    def keys(model_markers, page) -> set:
        return {r.key for r in model_markers.values() if r.page == page}

    return sorted(
        sorted(kept)
        for kept in one.keys() & other.keys()
        if changed not in kept and keys(markers[0], one[kept]) != keys(markers[1], other[kept])
    )


# B1 (a derived key that holds a page or position, `star/1/4` -> `star/1/5`) does not show with
# one extra relay on this fixture: since B2 each group has a page of its own, so no page number
# moves when a relay joins a group. The reproduction that shifts a later page is
# `test_a_marker_key_survives_an_extra_relay_that_shifts_a_later_page` below (EF-C part 1).
@pytest.mark.parametrize("extra", ["B", "C", "D", "E", "F"])
def test_a_derived_key_never_changes_because_of_another_group(extra: str) -> None:
    """D17 clause 3 (model-0025): the link-marker keys of a page that keeps its groups stay."""
    # UNDO: engines/schematic/write/markers.py link_markers.key_to: append `str(len(layout.placed))`
    # to the returned tuple (probed, fails for [B]..[F]). Appending `str(one.page)` fails none of
    # them, since no page shifts here: that is the job of
    # `test_a_marker_key_survives_an_extra_relay_that_shifts_a_later_page`.
    before, after = build(), build(extra=extra)
    kept = _by_group_set(before).keys() & _by_group_set(after).keys()
    assert {group for pages in kept if extra not in pages for group in pages}
    assert _marker_keys_on_kept_pages(before, after, extra) == []


def test_a_marker_key_survives_an_extra_relay_that_shifts_a_later_page() -> None:
    """D17 clause 3, B1 (layout-0052): crowding `B` onto a second page renumbers the pages
    after it; the star markers of a later page that keeps its groups keep their keys."""
    # UNDO: engines/schematic/write/markers.py link_markers.key_to: append `str(one.page)` to the
    # returned tuple and this fails (`{F, PLC}` moves 6 -> 7); the old `star/1/4` -> `star/1/5`.
    before, after = build(), build(crowd="B")
    one, other = _by_group_set(before), _by_group_set(after)
    pages = [layout_of(m, Page) for m in (before, after)]
    shifted = {
        kept
        for kept in one.keys() & other.keys()
        if "B" not in kept and pages[0][one[kept]].number != pages[1][other[kept]].number
    }
    last = frozenset({"F", "PLC"})
    assert last in shifted
    stars = [
        {r.key for r in layout_of(m, LinkMarker).values() if r.page == ids[last] and r.star}
        for m, ids in ((before, one), (after, other))
    ]
    assert stars[0]
    assert stars[0] == stars[1]
    assert _marker_keys_on_kept_pages(before, after, "B") == []


@pytest.mark.parametrize("branch", ["C", "D"])
def test_a_star_marker_key_survives_an_earlier_branch_in_another_group(branch: str) -> None:
    """D17 clause 3, layout-0052: a star net gains a branch in another group; the reference and
    branch keys on the pages that keep their groups are the same (no first-branch segment)."""
    # UNDO: engines/schematic/write/markers.py link_markers.star_key: end a star marker's key with
    # `*port_key[one.star_partner]` (the partner's port key) and this fails (the reference on
    # `{A}` names its first branch, which the new branch `KV` sorts before).
    before, after = build(), build(branch=branch)
    one, other = _by_group_set(before), _by_group_set(after)
    seen = set()
    for kept in one.keys() & other.keys():
        if branch in kept:
            continue
        stars = [
            {r.key: r.star for r in layout_of(m, LinkMarker).values() if r.page == ids[kept]}
            for m, ids in ((before, one), (after, other))
        ]
        seen |= {kind for kind in stars[0].values() if kind is not None}
        assert stars[0] == stars[1], sorted(kept)
    assert seen == {StarKind.REF, StarKind.BRANCH}  # both stand on pages that kept their groups
    new = set(layout_of(after, LinkMarker)) - set(layout_of(before, LinkMarker))
    assert new  # the added branch is a marker of its own


@pytest.mark.parametrize("terminal", ["D", "E"])
def test_a_star_marker_key_survives_a_new_reference_pick_in_another_group(terminal: str) -> None:
    """D17 clause 3, layout-0052 (D17 ruling): two terminals added to the star net in another
    group move its reference from the terminal `XA` (page `{A}`) to the PLC output (page
    `{F, PLC}`), which was a branch; each keeps its marker, its role flips, its key stays,
    because the role is a field and never in the key."""
    # UNDO: engines/schematic/write/markers.py link_markers.star_key_of: put `one.side.value` back
    # after the port key (the role of the marker, the reference's pick) and this fails.
    before, after = build(), build(terminal=terminal)
    one, other = _by_group_set(before), _by_group_set(after)
    kept = [pages for pages in one.keys() & other.keys() if terminal not in pages]

    def reference_ports(model: Model, ids: dict) -> set:
        return {
            r.port
            for pages in kept
            for r in layout_of(model, LinkMarker).values()
            if r.page == ids[pages] and r.star is StarKind.REF
        }

    assert reference_ports(before, one) != reference_ports(after, other)  # the pick did move
    assert {frozenset({"A"}), frozenset({"F", "PLC"})} <= set(kept)  # both markers are compared
    assert _marker_keys_on_kept_pages(before, after, terminal) == []


def test_no_route_crosses_a_text_on_the_d_page() -> None:
    """S20 (layout-0090; ADDENDUM 7 point 8, ADDENDUM 10): the `[D]` build of the test above.

    Its set 1 page 6, the `{F, PLC}` page, draws the star reference the two new terminals moved
    to the PLC output. That port is wired, so the reference turns (layout-0053), and a turned
    marker has one place. Before S20 the tags were placed first, and a `tag.point` of another
    function stood on its stub (one `TEXT_CROSSED_BY_ROUTE`, accepted on the branch at 2b-7).
    The markers now go through the placer first, and the tags' call holds each marker's box
    and stub, so the tag steps off: no text of the build is crossed by a route.
    """
    # UNDO: stages/pagerun.py `first_labels`: drop `*markers` from `occupied` and this fails.
    result = build_result(terminal="D")
    ids = _by_group_set(result.model)
    references = [
        r
        for r in layout_of(result.model, LinkMarker).values()
        if r.page == ids[frozenset({"F", "PLC"})] and r.star is StarKind.REF
    ]
    assert references  # the moved reference is drawn on the page
    assert [f for f in result.findings if f.code == "TEXT_CROSSED_BY_ROUTE"] == []


def test_the_new_stability_checks_can_fail() -> None:
    """A placement moved on an earlier or a kept page is flagged; on the changed page it is not."""
    # UNDO: `_moved_before_the_group` / `_moved_on_kept_pages` return [] and this test fails.
    before, after = build(), build(extra="F")
    table = layout_of(after, SymbolPlacement)
    names = group_names(after)
    pages = {p.id: {names[g.group] for g in p.groups} for p in layout_of(after, Page).values()}
    early = next(i for i, r in table.items() if pages[r.page] == {"A"})
    changed = next(i for i, r in table.items() if "F" in pages[r.page])

    def moved(id_):
        return _tampered(after, "layout.symbol_placement", id_, x=table[id_].x + 8)

    assert _moved_before_the_group(before, moved(early), "F", _GEOMETRY)
    assert _moved_on_kept_pages(before, moved(early), _GEOMETRY, "F")
    assert _moved_before_the_group(before, moved(changed), "F", _GEOMETRY) == []
    assert _moved_on_kept_pages(before, moved(changed), _GEOMETRY, "F") == []
