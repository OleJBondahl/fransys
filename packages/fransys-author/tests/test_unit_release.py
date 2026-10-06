"""`Scope.unit` writes a `UnitRelease` and a `Unit` of it; revision keys are per release (SC2)."""

import pytest
from fransys_author import AuthorError, Design

from fransys_model.kernel import MergeConflict, make_id
from fransys_model.vocab import Placement, Project, Revision, Unit, UnitRelease


def _of(design: Design, kind: type) -> list:
    return [r for r in design.draft().records() if isinstance(r, kind)]


def _project(d: Design, **kwargs) -> None:
    d.project(title="P", number="N", customer="C", revision=1, author="A", **kwargs)


def test_unit_writes_the_release_record_and_an_instance_pointing_at_it(parts):
    d = Design(parts)
    d.scope("u1").unit("cab", revision=1, interface="1", title="T", number="N")
    (release,) = _of(d, UnitRelease)
    (unit,) = _of(d, Unit)
    assert (release.name, release.version, release.revision) == ("cab", 1, 1)
    assert (release.interface, release.title, release.number) == ("1", "T", "N")
    assert release.key == ("unit_release", "cab", "1", "1")
    assert release.id == make_id(UnitRelease, release.key)
    assert unit.release == release.id
    assert unit.key == ("u1", "unit")


def test_an_explicit_version_lands_on_the_release_and_its_key(parts):
    d = Design(parts)
    d.scope("u1").unit("cab", version=2, revision=1, interface="1")
    (release,) = _of(d, UnitRelease)
    assert release.version == 2
    assert release.key == ("unit_release", "cab", "2", "1")


def test_a_unit_without_title_and_number_has_them_empty_on_its_release(parts):
    d = Design(parts)
    d.scope("u1").unit("cab", revision=1, interface="1")
    (release,) = _of(d, UnitRelease)
    assert (release.title, release.number) == ("", "")


def test_two_instances_of_an_identical_release_build_one_release_record(parts):
    d = Design(parts)
    d.scope("u1").unit("cab", revision=1, interface="1", title="T")
    d.scope("u2").unit("cab", revision=1, interface="1", title="T")
    (release,) = _of(d, UnitRelease)
    units = _of(d, Unit)
    assert len(units) == 2
    assert {unit.release for unit in units} == {release.id}


def test_a_release_of_the_same_name_version_revision_with_other_content_is_a_merge_conflict(
    parts,
):
    d = Design(parts)
    d.scope("u1").unit("cab", revision=1, interface="1", title="T")
    with pytest.raises(MergeConflict) as caught:
        d.scope("u2").unit("cab", revision=1, interface="1", title="Other")
    assert caught.value.origin_a != caught.value.origin_b
    assert caught.value.origin_a.file == __file__
    assert caught.value.origin_b.file == __file__
    assert caught.value.origin_a.line != caught.value.origin_b.line


def test_a_different_version_is_a_different_release_not_a_conflict(parts):
    d = Design(parts)
    d.scope("u1").unit("cab", revision=1, interface="1", title="T")
    d.scope("u2").unit("cab", version=2, revision=1, interface="1", title="Other")
    assert len(_of(d, UnitRelease)) == 2


def test_scope_revision_key_uses_the_release_version_by_default_and_the_given_one(parts):
    d = Design(parts)
    u = d.scope("u1").unit("cab", version=3, revision=2, interface="1")
    u.revision(1, date="2026-09-23", text="a", created="OJB")
    u.revision(2, date="2026-09-24", text="b", created="OJB", version=2)
    by_revision = {r.revision: r for r in _of(d, Revision)}
    assert by_revision[1].key == ("unit_release", "cab", "3", "2", "revision", "3", "1")
    assert by_revision[1].version == 3
    assert by_revision[2].key == ("unit_release", "cab", "3", "2", "revision", "2", "2")
    assert by_revision[2].version == 2
    release_id = _of(d, UnitRelease)[0].id
    assert {r.release for r in by_revision.values()} == {release_id}


def test_three_instances_writing_the_same_entries_keep_one_entry_per_revision(parts):
    d = Design(parts)
    for prefix in ("u1", "u2", "u3"):
        u = d.scope(prefix).unit("cab", revision=2, interface="1")
        u.revision(1, date="2026-09-23", text="First", created="OJB")
        u.revision(2, date="2026-09-24", text="Second", created="OJB")
    assert len(_of(d, Unit)) == 3
    assert len(_of(d, UnitRelease)) == 1
    assert sorted(r.revision for r in _of(d, Revision)) == [1, 2]


def test_an_instance_writing_a_different_entry_text_is_a_merge_conflict(parts):
    d = Design(parts)
    d.scope("u1").unit("cab", revision=1, interface="1").revision(
        1, date="2026-09-23", text="First", created="OJB"
    )
    u2 = d.scope("u2").unit("cab", revision=1, interface="1")
    with pytest.raises(MergeConflict) as raised:
        u2.revision(1, date="2026-09-23", text="Changed", created="OJB")
    assert raised.value.origin_a != raised.value.origin_b


def test_project_version_is_written_and_used_by_an_unversioned_revision(parts):
    d = Design(parts)
    _project(d, version=2)
    d.revision(1, date="2026-09-23", text="First", created="OJB")
    (project,) = _of(d, Project)
    (entry,) = _of(d, Revision)
    assert project.version == 2
    assert entry.version == 2
    assert entry.release is None
    assert entry.key == ("revision", "2", "1")


def test_project_version_defaults_to_one_and_an_explicit_revision_version_wins(parts):
    d = Design(parts)
    _project(d)
    d.revision(1, date="2026-09-23", text="First", created="OJB", version=3)
    (project,) = _of(d, Project)
    (entry,) = _of(d, Revision)
    assert project.version == 1
    assert (entry.version, entry.key) == (3, ("revision", "3", "1"))


def test_project_after_an_unversioned_revision_with_another_version_is_refused(parts):
    d = Design(parts)
    d.revision(1, date="2026-09-23", text="First", created="OJB")
    with pytest.raises(AuthorError, match=r"call d\.project\(\.\.\.\) first"):
        _project(d, version=2)
    assert _of(d, Project) == []


def test_project_after_an_unversioned_revision_is_fine_when_the_versions_agree(parts):
    d = Design(parts)
    d.revision(1, date="2026-09-23", text="First", created="OJB")
    _project(d, version=1)
    d2 = Design(parts)
    d2.revision(1, date="2026-09-23", text="First", created="OJB", version=2)
    _project(d2, version=2)
    assert [p.version for p in _of(d, Project)] == [1]
    assert [p.version for p in _of(d2, Project)] == [2]


def test_a_unit_written_inside_a_scope_that_has_its_own_unit_gets_that_unit_as_parent(parts):
    d = Design(parts)
    outer = d.scope("u1").unit("cab", revision=1, interface="1")
    inner = outer.scope("sub")
    inner.unit("board", revision=1, interface="1")
    units = {u.key: u for u in _of(d, Unit)}
    assert units[("u1", "unit")].parent is None
    assert units[("u1", "sub", "unit")].parent == outer.unit_id


def test_unit_forwards_the_scopes_at_so_an_item_through_it_defaults_there(parts):
    d = Design(parts)
    c1 = d.location("C1", "cabinet")
    u = d.scope("u1", at=c1).unit("cab", revision=1, interface="1")
    item = u.item("TEST-RLY-2CO", tag="K1")
    placements = [p for p in _of(d, Placement) if p.item == item.id]
    assert any(p.node == c1.id for p in placements)
