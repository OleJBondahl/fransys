from typing import TYPE_CHECKING

import pytest
from hypothesis import settings
from kind_registry import restored_kind_registry

if TYPE_CHECKING:
    from collections.abc import Iterator


# Decision 0020: derandomized so `just ci` is deterministic, no deadline so a slow CI runner
# never flakes a property, max_examples bounded so the property suite stays fast.
settings.register_profile("fransys", deadline=None, derandomize=True, max_examples=25)
settings.load_profile("fransys")


@pytest.fixture(autouse=True)
def _restore_kind_registry() -> Iterator[None]:
    """Give each test the kind registry it found, so the suite can run twice in one process."""
    yield from restored_kind_registry()
