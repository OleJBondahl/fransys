"""Shared fixtures for `derive` acceptance skeletons."""

import pytest

from fransys_model.kernel import Origin


@pytest.fixture
def origin() -> Origin:
    """A stable `Origin` for tests that don't care which line authored a record."""
    return Origin(file="conftest.py", line=1, note="fixture")
