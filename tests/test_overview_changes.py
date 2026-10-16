"""The changes layer of the overview page (OVERVIEW O19).

The page's data marks, per view, each box and line a `ListingDiff` names as added or changed, and
lists the removed rows the model can no longer draw. No diff means no switch. Each test names what
breaks it.
"""

import dataclasses
import json
import re
from typing import TYPE_CHECKING, Any

import fransys as fr
import fransys_parts
from fransys import pipeline
from fransys_overview import html
from fransys_overview._app import APP_JS
from test_overview_page import _laid
from test_units_worked_example import _system_design

from fransys_model.derive.baseline import change_subjects, diff, dumps, listing

if TYPE_CHECKING:
    from pathlib import Path

_CHANGED = "=FLD+FLD-K1"
_ADDED = "=FLD+FLD-M1"
_GHOST = "-ZZ9"


def _previous() -> Any:
    """The released listing: one device not yet there, one with another MPN, one since removed."""
    model = _laid()[0]
    now = listing(model, None)
    rows = [r for r in now.items if r.designation != _ADDED]
    rows = [dataclasses.replace(r, mpn="OLD") if r.designation == _CHANGED else r for r in rows]
    rows.append(dataclasses.replace(now.items[0], designation=_GHOST))
    return dataclasses.replace(now, items=tuple(rows), conductors=now.conductors[1:])


def _page(change: Any) -> dict[str, Any]:
    found = re.search(r'id="overview-data">(.*?)</script>', html(_laid()[0], changes=change))
    assert found is not None
    return json.loads(found.group(1))


def _marks() -> dict[str, Any]:
    model = _laid()[0]
    return _page(diff(_previous(), listing(model, None)))


def test_an_added_and_a_changed_item_are_marked_on_their_boxes() -> None:
    """Breaks if the kind lands on another box, or a changed field is shown as added."""
    data = _marks()
    system = next(v for v, view in enumerate(data["views"]) if view["unit"] is None)
    boxes = data["views"][system]["boxes"]
    marked = {boxes[b]["lines"][0]: kind for b, kind in data["changes"]["views"][system][0]}
    assert marked == {"+FLD-M1": "added", "+FLD-K1": "changed"}


def test_an_added_conductor_marks_the_line_that_joins_its_ends() -> None:
    """Breaks if a conductor row marks a box, or a line that does not join its two ends."""
    data = _marks()
    lines = [(v, at, k) for v, rows in enumerate(data["changes"]["views"]) for at, k in rows[1]]
    assert lines
    assert {k for _v, _at, k in lines} == {"added"}
    for v, at, _k in lines:
        line = data["views"][v]["lines"][at]
        assert line["a"] != line["b"]


def test_a_removed_row_is_listed_not_marked() -> None:
    """Breaks if a removed item, which the model no longer holds, is marked or dropped."""
    data = _marks()
    assert ["removed", _GHOST] in data["changes"]["rest"]


def test_no_previous_release_means_no_changes_data() -> None:
    """Breaks if the switch would show for a page with nothing to compare with."""
    assert _page(None)["changes"] is None


def test_an_empty_diff_still_names_the_release() -> None:
    """Breaks if an unchanged system loses the switch, or marks something."""
    model = _laid()[0]
    data = _page(diff(listing(model, None), listing(model, None)))
    assert data["changes"]["since"] == "P-1001 1.1"
    assert data["changes"]["rest"] == []
    assert all(not boxes and not lines for boxes, lines in data["changes"]["views"])


def test_every_subject_text_of_the_listing_names_its_model_thing() -> None:
    """Breaks if `change_subjects` drifts from the listing's own subject texts."""
    model = _laid()[0]
    now = listing(model, None)
    found = change_subjects(model, None)
    assert {s for sec, s in found if sec == "items"} == {r.designation for r in now.items}
    assert len([k for k in found if k[0] == "conductors"]) == len(now.conductors)
    assert len([k for k in found if k[0] == "units"]) == sum(len(u.instances) for u in now.units)


def _store(root: Path, folder: str, stored: Any) -> None:
    target = root / "P-1001" / folder / "baseline"
    target.mkdir(parents=True)
    (target / "listing.json").write_text(dumps(stored), encoding="utf-8")


def _written_changes(monkeypatch: Any, root: Path, **kwargs: Any) -> Any:
    design, _field1, _field2 = _system_design(fransys_parts.load("demo_parts"))
    result = fr.build(fransys_parts.load("demo_parts"), design.draft())
    seen: list[Any] = []

    def spy(*_args: Any, changes: Any = None, **_kwargs: Any) -> dict[str, bytes]:
        seen.append(changes)
        return {}

    monkeypatch.setattr(pipeline, "_exports", spy)
    fr.write(result, root / "out", **kwargs)
    return seen[0], listing(result.model, None)


def test_write_without_releases_or_a_stored_release_passes_no_diff(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Breaks if the page would get a diff (and a switch) with no previous release to compare."""
    assert _written_changes(monkeypatch, tmp_path)[0] is None
    assert _written_changes(monkeypatch, tmp_path, releases=tmp_path / "none")[0] is None


def test_write_passes_the_diff_since_the_previous_release(monkeypatch: Any, tmp_path: Path) -> None:
    """Breaks if `write` ignores `releases=` or diffs against the wrong release."""
    previous = dataclasses.replace(
        _previous(), unit=dataclasses.replace(listing(_laid()[0], None).unit, revision=0)
    )
    _store(tmp_path / "rel", "1.0", previous)
    passed, now = _written_changes(monkeypatch, tmp_path, releases=tmp_path / "rel")
    assert passed == diff(previous, now)
    assert any(c.change == "removed" and c.subject == _GHOST for c in passed.changes)


def test_write_prefers_the_release_stored_at_the_models_own_revision(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Breaks if edits made since the release at this revision are not what the page marks."""
    stored = _previous()
    _store(tmp_path / "rel", "1.1", stored)
    passed, now = _written_changes(monkeypatch, tmp_path, releases=tmp_path / "rel")
    assert passed == diff(stored, now)


def test_every_removed_row_reaches_the_page_and_nothing_caps_the_list() -> None:
    """Breaks if the removed list is cut at a size (it was 40) or loses its count heading."""
    model = _laid()[0]
    now = listing(model, None)
    ghosts = [dataclasses.replace(now.items[0], designation=f"-ZZ{n}") for n in range(45)]
    data = _page(diff(dataclasses.replace(now, items=(*now.items, *ghosts)), now))
    assert len(data["changes"]["rest"]) == 45
    assert "CHANGE_LIST_MAX" not in APP_JS
    assert ".slice(0," not in APP_JS.split("const drawRemoved")[1].split("};")[0]
    assert "name + ' (' + group.length + ')'" in APP_JS


def _marked_kinds(mode: str) -> dict[str, str]:
    """Each marked box of the system view in `mode`, by reference kind and first text line."""
    data = _marks()
    for v, view in enumerate(data["views"]):
        if view["unit"] is None and view["mode"] == mode:
            boxes = view["boxes"]
            return {boxes[b]["lines"][0]: kind for b, kind in data["changes"]["views"][v][0]}
    raise AssertionError(mode)


def test_a_place_box_and_a_field_box_take_the_mark_of_the_items_they_hold() -> None:
    """Breaks if `diff_marks` cannot name a `place:` or `fields:` box (overview-0011)."""
    assert _marked_kinds("location") == {"+FLD": "added"}
    assert _marked_kinds("fields")["Field devices (1)"] == "added"
