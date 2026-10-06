import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hypothesis import settings

from fransys_model.kernel import registry

if TYPE_CHECKING:
    from collections.abc import Iterator

# --import-mode=importlib leaves the test directories off sys.path; the tests import their helpers
# by name. Workspace rule: tests conftests append to sys.path, never insert(0), so no directory
# comes ahead of another and the winner of a bare name never depends on load order.
for directory in ("derive", "kernel", "layout", "usecases", "vocab"):
    sys.path.append(str(Path(__file__).parent / directory))

# Decision 0020: derandomized so `just ci` is deterministic, no deadline so a slow CI runner
# never flakes a property, max_examples bounded so the property suite stays fast (measured
# in WORK-ORDER-PROPS.md's hand-back).
settings.register_profile("fransys", deadline=None, derandomize=True, max_examples=25)
settings.load_profile("fransys")


@pytest.fixture(autouse=True)
def _restore_kind_registry() -> Iterator[None]:
    """Give each test the kind registry it found, so the suite can run twice in one process.

    Tests register throwaway kinds (`@record(kind="ghost_probe")`) and assert on the exact name,
    so the name cannot vary per call. `mutmut` runs the whole suite twice in one interpreter
    (stats, then the clean test); without this the second pass meets `kind ... is already
    registered`. Restored in place, so a module that bound `registry._kinds` by name still sees
    the live dict.
    """
    kinds = dict(registry._kinds)
    by_name = {name: list(classes) for name, classes in registry._records_by_name.items()}
    values = set(registry._value_classes)
    yield
    registry._kinds.clear()
    registry._kinds.update(kinds)
    registry._records_by_name.clear()
    registry._records_by_name.update(by_name)
    registry._value_classes.clear()
    registry._value_classes.update(values)
