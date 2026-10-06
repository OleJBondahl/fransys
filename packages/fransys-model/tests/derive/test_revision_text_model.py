"""Tests for `derive.revision_text`, the one printed form of a revision (FD4)."""

import pytest

from fransys_model import derive


@pytest.mark.parametrize(
    ("version", "revision", "text"),
    [(1, 1, "1.1"), (2, 1, "2.1"), (1, 10, "1.10"), (10, 2, "10.2")],
)
def test_the_revision_prints_as_version_dot_revision(
    version: int, revision: int, text: str
) -> None:
    """Distinct values, so a swapped pair or a padded revision fails."""
    assert derive.revision_text(version, revision) == text
