"""WP8 tests: project metadata (ROADMAP WP8, design/vocabulary.md 6 "Project")."""

import dataclasses

import pytest
from examples import core_model

from fransys_model.kernel import Draft, FreezeError, Id, Origin, SchemaError, evolve, freeze
from fransys_model.vocab.project import Project
from fransys_model.vocab.tables import projects


def _project(key: str) -> Project:
    return Project(
        id=Id(kind="project", value=key * 32),
        key=("examples", "project", key),
        title="Invented pump station",
        number="P-0001",
        customer="Invented Customer AS",
        revision=1,
        author="N. N.",
    )


def test_project_has_the_designed_fields() -> None:
    """`Project` carries the title-block fields."""
    project = _project("1")
    assert project.title == "Invented pump station"
    assert project.revision == 1


def test_project_notice_defaults_to_empty_and_round_trips() -> None:
    """The title block's IP notice cell text; empty leaves the cell empty (spec R11.4)."""
    assert _project("1").notice == ""
    noticed = dataclasses.replace(_project("1"), notice="Invented IP notice, all rights reserved.")
    draft = Draft()
    draft.add(noticed, origin=Origin(file="test_project.py", line=1, note="fixture"))
    model = freeze(draft)
    assert projects(model)[noticed.id].notice == "Invented IP notice, all rights reserved."


def test_second_project_is_a_freeze_error() -> None:
    """Two different `Project` records in one model fail `freeze()`."""
    draft = Draft()
    origin = Origin(file="test_project.py", line=1, note="fixture")
    draft.extend((_project("1"), _project("2")), origin=origin)
    with pytest.raises(FreezeError):
        freeze(draft)


def test_one_project_freezes_and_is_the_only_entry_of_its_table() -> None:
    """`projects(model)` has at most one entry: `Project` is a singleton."""
    draft = Draft()
    draft.add(_project("1"), origin=Origin(file="test_project.py", line=1, note="fixture"))
    assert set(projects(freeze(draft))) == {_project("1").id}


def test_the_second_project_error_names_the_later_one() -> None:
    """The first by id is fine; the offender is the second, and it is a `SchemaError`."""
    draft = Draft()
    draft.extend(
        (_project("2"), _project("1")), origin=Origin(file="test_project.py", line=1, note="x")
    )
    with pytest.raises(FreezeError) as excinfo:
        freeze(draft)
    (error,) = excinfo.value.errors
    assert isinstance(error, SchemaError)
    assert error.record_id == _project("2").id


def test_evolve_refuses_a_second_project_too() -> None:
    """A pass adding a project to a model that has one is refused the same way."""
    with pytest.raises(SchemaError, match="at most one record of this kind"):
        evolve(
            core_model(),
            put=(_project("9"),),
            origin=Origin(file="test_project.py", line=1, note="pass"),
        )
