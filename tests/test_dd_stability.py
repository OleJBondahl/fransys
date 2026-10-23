"""Stability on the example-sized fixture of `dd_stability_fixture`.

A change in one group moves records only on the pages that hold it and
on the pages in-order packing refills after it; pages before are byte-identical; a page that
keeps its group set is byte-identical; a derived key never changes because of another group.
"""

import dataclasses
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _dd_core import strings
from _drawn_pages import drawn_pages

from fransys_model.layout import Page, layout_of

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

_DRAWN: dict = {}  # model digest -> page Drawings, read at build time (the facade's memo is short)


def build_result(**options):
    """The fixture's build with its page Drawings kept here."""
    assert _FIXTURE is not None
    for _ in range(2):
        result = _FIXTURE.build_result(**options)
        if result.model.digest in _DRAWN:
            return result
        try:
            _DRAWN[result.model.digest] = dict(drawn_pages(result.model))
        except LookupError:  # the fixture's own cache outlived the memo: build again
            _FIXTURE.build_result.cache_clear()
        else:
            return result
    return result


def build(**options) -> Model:
    return build_result(**options).model


def _drawn_of(model: Model) -> dict:
    return _DRAWN[model.digest]


group_names = _FIXTURE.group_names

_ALL = ("symbols", "wires", "markers", "texts", "outlines")
_GEOMETRY = ("symbols", "wires", "texts", "outlines")  # the old placements, routes and labels


def _dump(drawn: dict, page_id, parts: tuple = _ALL) -> tuple:
    """What one page's Drawing holds of `parts`, in the order the core drew it."""
    drawing = drawn.get(page_id)
    return () if drawing is None else tuple(repr(getattr(drawing, part)) for part in parts)


def _page_dump(drawn: dict, page_id) -> tuple:
    """Every symbol, wire, marker, text and outline on one page."""
    return _dump(drawn, page_id)


def _pages_off_the_group(before: Model, after: Model, group: str) -> set:
    """Ids of the pages that hold no group sharing a page with `group`, before or after."""
    names = {id_: name for m in (before, after) for id_, name in group_names(m).items()}
    pages = [*layout_of(before, Page).values(), *layout_of(after, Page).values()]
    with_group = {p.id for p in pages if any(names[g.group] == group for g in p.groups)}
    sharing = {names[g.group] for p in pages if p.id in with_group for g in p.groups}
    return {p.id for p in pages if not {names[g.group] for g in p.groups} & sharing}


def _moved_off_the_group(before: Model, after: Model, group: str, drawn_after=None) -> list[str]:
    """The pages holding no group that shares a page with `group` whose records differ."""
    free = _pages_off_the_group(before, after, group)
    one, other = dict(_drawn_of(before)), dict(drawn_after or _drawn_of(after))
    return sorted(
        page.value[:8] for page in free if _page_dump(one, page) != _page_dump(other, page)
    )


def test_a_relay_in_the_last_device_group_moves_only_the_pages_of_that_group() -> None:
    """Pages holding no group that shares a page with `=F` are byte-identical, F's change."""
    # UNDO: stages/partition.py partition: `pack(sorted(runs, key=lambda r: -r.width), ...)`
    # (a plain reversal does NOT fail it; probed).
    before, after = build(), build(extra="F")
    assert _moved_off_the_group(before, after, "F") == []
    free = _pages_off_the_group(before, after, "F")
    assert len(free) >= 2
    assert all(_page_dump(_drawn_of(before), page) for page in free)
    drawn_before, drawn_after = _drawn_of(before), _drawn_of(after)
    seen = {s.id for d in drawn_before.values() for s in d.symbols}
    added_on = {
        page: {s.id for s in d.symbols} - seen
        for page, d in drawn_after.items()
        if page not in free
    }
    assert any(added_on.values())
    # model-0220: KX's wire makes X1's F terminal a star; it stands at each relay of =F
    printed = {text for page, ids in added_on.items() if ids for text in strings(drawn_after[page])}
    assert "-KX" in printed
    assert {t for t in printed if t.startswith("-X1")}
    assert {page for page, ids in added_on.items() if ids} <= set(layout_of(after, Page)) - free


def _moved(drawn: dict, page_id) -> dict:
    """`drawn` with the first symbol of page `page_id` moved 8 G right."""
    drawing = drawn[page_id]
    first, *rest = drawing.symbols
    symbols = (dataclasses.replace(first, x=first.x + 8), *rest)
    return {**drawn, page_id: dataclasses.replace(drawing, symbols=symbols)}


def test_the_stability_check_can_fail() -> None:
    """A moved record on a page off the group is flagged; one on its own or shared page is not."""
    # UNDO: `_moved_off_the_group` / `_pages_off_the_group`: return [] and the first assert fails.
    before, after = build(), build(extra="F")
    off = _pages_off_the_group(before, after, "F")
    on = {p.id for p in layout_of(after, Page).values()} - off
    assert off
    assert on
    drawn = dict(_drawn_of(after))
    on_page = next(p for p in drawn if p in on)
    off_page = next(p for p in drawn if p in off)
    assert _moved_off_the_group(before, after, "F", _moved(drawn, off_page))
    assert _moved_off_the_group(before, after, "F", _moved(drawn, on_page)) == []


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


def _moved_before_the_group(
    before: Model, after: Model, group: str, kinds: tuple, drawn_after=None
) -> list:
    """The pages numbered before `group`'s first page whose records differ."""
    first = _first_page(before, after, group)
    early = [p.id for p in layout_of(before, Page).values() if p.number < first]
    one, other = dict(_drawn_of(before)), dict(drawn_after or _drawn_of(after))
    return [page for page in early if _dump(one, page, kinds) != _dump(other, page, kinds)]


def _moved_on_kept_pages(
    before: Model, after: Model, kinds: tuple, changed: str, drawn_after=None
) -> list:
    """Pages that keep their set of groups and hold no `changed` group whose
    records differ. A page holding the changed group changes by definition: it is exempt."""
    one, other = _by_group_set(before), _by_group_set(after)
    d_one, d_other = dict(_drawn_of(before)), dict(drawn_after or _drawn_of(after))
    return sorted(
        (sorted(kept), one[kept].value[:8])
        for kept in one.keys() & other.keys()
        if changed not in kept
        and _dump(d_one, one[kept], kinds) != _dump(d_other, other[kept], kinds)
    )


@pytest.mark.parametrize("extra", ["C", "D", "E", "F"])
def test_the_pages_before_the_changed_groups_first_page_are_byte_identical(extra: str) -> None:
    """Placements, routes and labels on the earlier pages do not move."""
    # UNDO: stages/partition.py partition: right-aligned packing,
    # `for page in [p[::-1] for p in pack(runs[::-1], ...)][::-1]` (probed, fails for [C]).
    before, after = build(), build(extra=extra)
    first = _first_page(before, after, extra)
    assert first >= 2
    assert _moved_before_the_group(before, after, extra, _GEOMETRY) == []
    drawn = dict(_drawn_of(before))
    assert all(
        _dump(drawn, p.id, _GEOMETRY) for p in layout_of(before, Page).values() if p.number < first
    )


@pytest.mark.parametrize("extra", ["B", "C", "D", "E", "F"])
def test_a_page_that_keeps_its_groups_is_byte_identical_apart_from_its_number(extra: str) -> None:
    """A page with the same group set, holding no changed group, is identical."""
    # UNDO: stages/place.py place: a page-local offset by the total placement count (which the
    # extra relay changes) leaks the change onto pages that do not hold it.
    before, after = build(), build(extra=extra)
    kept = _by_group_set(before).keys() & _by_group_set(after).keys()
    assert {group for pages in kept if extra not in pages for group in pages}
    assert _moved_on_kept_pages(before, after, _GEOMETRY, extra) == []


def _marker_keys_on_kept_pages(before: Model, after: Model, changed: str) -> list:
    """On pages that keep their group set and hold no `changed` group, the pages
    whose marker ids (the render ids of the marker records, which their keys make) changed."""
    one, other = _by_group_set(before), _by_group_set(after)
    drawn = [dict(_drawn_of(m)) for m in (before, after)]

    def keys(model_drawn, page) -> set:
        return {m.id for m in model_drawn[page].markers}

    return sorted(
        sorted(kept)
        for kept in one.keys() & other.keys()
        if changed not in kept and keys(drawn[0], one[kept]) != keys(drawn[1], other[kept])
    )


# A derived key that holds a page or position (`star/1/4` -> `star/1/5`) does not show with
# one extra relay on this fixture: since each group has a page of its own, so no page number
# moves when a relay joins a group. The reproduction that shifts a later page is
# `test_a_marker_key_survives_an_extra_relay_that_shifts_a_later_page` below.
@pytest.mark.parametrize("extra", ["B", "C", "D", "E", "F"])
def test_a_derived_key_never_changes_because_of_another_group(extra: str) -> None:
    """Per model-0025, the link-marker keys of a page that keeps its groups stay."""
    # UNDO: engines/schematic/write/markers.py link_markers.key_to: append `str(len(layout.placed))`
    # to the returned tuple (probed, fails for [B]..[F]). Appending `str(one.page)` fails none of
    # them, since no page shifts here: that is the job of
    # `test_a_marker_key_survives_an_extra_relay_that_shifts_a_later_page`.
    before, after = build(), build(extra=extra)
    kept = _by_group_set(before).keys() & _by_group_set(after).keys()
    assert {group for pages in kept if extra not in pages for group in pages}
    assert _marker_keys_on_kept_pages(before, after, extra) == []


def test_a_marker_key_survives_an_extra_relay_that_shifts_a_later_page() -> None:
    """Per layout-0052, crowding `B` onto a second page renumbers the pages
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
        {m.id for m in dict(_drawn_of(model))[ids[last]].markers}
        for model, ids in ((before, one), (after, other))
    ]
    assert stars[0]
    assert stars[0] == stars[1]
    assert _marker_keys_on_kept_pages(before, after, "B") == []


@pytest.mark.parametrize("branch", ["C", "D"])
def test_a_star_marker_key_survives_an_earlier_branch_in_another_group(branch: str) -> None:
    """Per layout-0052, a star net gains a branch in another group; the reference and
    branch keys on the pages that keep their groups are the same (no first-branch segment)."""
    # UNDO: engines/schematic/write/markers.py link_markers.star_key: end a star marker's key with
    # `*port_key[one.star_partner]` (the partner's port key) and this fails (the reference on
    # `{A}` names its first branch, which the new branch `KV` sorts before).
    before, after = build(), build(branch=branch)
    one, other = _by_group_set(before), _by_group_set(after)
    drawn = [dict(_drawn_of(m)) for m in (before, after)]
    seen = set()
    for kept in one.keys() & other.keys():
        if branch in kept:
            continue
        stars = [
            {m.id: m.key for m in model_drawn[ids[kept]].markers}
            for model_drawn, ids in ((drawn[0], one), (drawn[1], other))
        ]
        seen |= set(stars[0].values())
        assert stars[0] == stars[1], sorted(kept)
    assert len(seen) == 2  # a reference and a branch marker (the library key tells them apart)
    new = {m.id for m in _all_markers(drawn[1])} - {m.id for m in _all_markers(drawn[0])}
    assert new  # the added branch is a marker of its own


def _all_markers(drawn: dict) -> list:
    return [m for drawing in drawn.values() for m in drawing.markers]


@pytest.mark.parametrize("terminal", ["D", "E"])
def test_a_star_marker_key_survives_a_new_reference_pick_in_another_group(terminal: str) -> None:
    """Per layout-0052, two terminals added to the star net in another
    group move its reference from the terminal `XA` (page `{A}`) to the PLC output (page
    `{F, PLC}`), which was a branch; each keeps its marker, its role flips, its key stays,
    because the role is a field and never in the key."""
    # UNDO: engines/schematic/write/markers.py link_markers.star_key_of: put `one.side.value` back
    # after the port key (the role of the marker, the reference's pick) and this fails.
    before, after = build(), build(terminal=terminal)
    one, other = _by_group_set(before), _by_group_set(after)
    kept = [pages for pages in one.keys() & other.keys() if terminal not in pages]
    drawn = [dict(_drawn_of(m)) for m in (before, after)]

    def reference_markers(model_drawn: dict, ids: dict) -> set:
        """The (id, library key) of the markers on the kept pages."""
        return {(m.id, m.key) for pages in kept for m in model_drawn[ids[pages]].markers}

    # the pick did move: a marker keeps its id and its library key (the role) flips
    assert reference_markers(drawn[0], one) != reference_markers(drawn[1], other)
    assert {frozenset({"A"}), frozenset({"F", "PLC"})} <= set(kept)  # both markers are compared
    assert _marker_keys_on_kept_pages(before, after, terminal) == []


def test_no_route_crosses_a_text_on_the_d_page() -> None:
    """Per layout-0090, the `[D]` build of the test above.

    Its set 1 page 6, the `{F, PLC}` page, draws the star reference the two new terminals moved
    to the PLC output. That port is wired, so the reference turns (layout-0053), and a turned
    marker has one place. Before layout-0090 the tags were placed first, and a `tag.point` of
    another function stood on its stub (one `TEXT_CROSSED_BY_ROUTE`, accepted on the branch
    at 2b-7).
    The markers now go through the placer first, and the tags' call holds each marker's box
    and stub, so the tag steps off: no text of the build is crossed by a route.
    """
    # UNDO: stages/pagerun.py `first_labels`: drop `*markers` from `occupied` and this fails.
    result = build_result(terminal="D")
    ids = _by_group_set(result.model)
    references = dict(_drawn_of(result.model))[ids[frozenset({"F", "PLC"})]].markers
    assert references  # the moved reference is drawn on the page
    assert [f for f in result.findings if f.code == "TEXT_CROSSED_BY_ROUTE"] == []


def test_the_new_stability_checks_can_fail() -> None:
    """A symbol moved on an earlier or a kept page is flagged; on the changed page it is not."""
    # UNDO: `_moved_before_the_group` / `_moved_on_kept_pages` return [] and this test fails.
    before, after = build(), build(extra="F")
    drawn = dict(_drawn_of(after))
    names = group_names(after)
    pages = {p.id: {names[g.group] for g in p.groups} for p in layout_of(after, Page).values()}
    early = next(i for i in drawn if pages[i] == {"A"})
    changed = next(i for i in drawn if "F" in pages[i])
    on_early, on_changed = _moved(drawn, early), _moved(drawn, changed)
    assert _moved_before_the_group(before, after, "F", _GEOMETRY, on_early)
    assert _moved_on_kept_pages(before, after, _GEOMETRY, "F", on_early)
    assert _moved_before_the_group(before, after, "F", _GEOMETRY, on_changed) == []
    assert _moved_on_kept_pages(before, after, _GEOMETRY, "F", on_changed) == []
