from typing import TYPE_CHECKING

import pytest
from kind_registry import restored_kind_registry

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _restore_kind_registry() -> Iterator[None]:
    """Give each test the kind registry it found, so the suite can run twice in one process."""
    yield from restored_kind_registry()
