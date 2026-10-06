"""`fr.AuthorError` is public (decision 0113): a consumer catches an authoring refusal by name."""

import fransys as fr
import fransys_author
import pytest


def test_an_authoring_refusal_is_caught_as_fr_author_error() -> None:
    """A run with no size that is not bridged is refused at the call."""
    strip = fr.design("demo_parts", place="HALL").terminal_strip("X1", "DEMO-TB-2.5")
    with pytest.raises(fr.AuthorError, match="a run with no size is bridged=True"):
        strip.run("A")


def test_fr_author_error_is_the_authors_class() -> None:
    assert fr.AuthorError is fransys_author.AuthorError
    assert "AuthorError" in fr.__all__
