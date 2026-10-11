"""Tests: project metadata."""

import pytest
from examples import core_model

from fransys_model.kernel import Id, Origin, SchemaError, evolve
from fransys_model.vocab.project import Project


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


def test_evolve_refuses_a_second_project_too() -> None:
    """A pass adding a project to a model that has one is refused the same way."""
    with pytest.raises(SchemaError, match="at most one record of this kind"):
        evolve(
            core_model(),
            put=(_project("9"),),
            origin=Origin(file="test_project.py", line=1, note="pass"),
        )
