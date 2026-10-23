"""A pytest plugin: the listed red cases become strict xfails naming their gap row (FLIP-NOW F4)."""

from typing import TYPE_CHECKING

from _gap_flip import mark_gaps

if TYPE_CHECKING:
    import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    mark_gaps(items)
