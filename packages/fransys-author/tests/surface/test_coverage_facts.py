"""Coverage facts: each call writes or reads exactly what the engine call does."""

from typing import Any

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

lazy from fransys_model.kernel import Draft


def _records(d) -> list[Any]:
    return d.draft().records()


def test_project_and_revision_write_the_engine_records(parts: Draft) -> None:
    d, e = design(parts), design(parts)
    d.project(title="T", number="N", customer="C", revision=2, author="A")
    d.revision(1, date="2026-01-01", text="first", created="A", checked="B")
    d.revision(2, date="2026-02-01", text="second", created="A", version=3)
    e._engine.project(title="T", number="N", customer="C", revision=2, author="A")
    e._engine.revision(1, date="2026-01-01", text="first", created="A", checked="B")
    e._engine.revision(2, date="2026-02-01", text="second", created="A", version=3)
    assert _records(d) == _records(e)
    assert len(_records(d)) > len(_records(design(parts)))


def test_project_notice_raises_naming_the_new_home(parts: Draft) -> None:
    d = design(parts)
    with pytest.raises(AuthorError, match=r"fr\.document\(\.\.\., notice="):
        d.project(title="T", number="N", customer="C", revision=1, author="A", notice="CE")
    assert _records(d) == _records(design(parts))


def test_design_has_no_interface_call(parts: Draft) -> None:
    assert not hasattr(design(parts), "interface")
