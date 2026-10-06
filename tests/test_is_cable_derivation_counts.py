"""Speed guard for RW4: `vocab.cables`'s `cable_items` builds once per digest (model-0108).

`is_cable(model, item)` reads `cable_items(model)` for every item it is asked about; the whole
point is that the underlying `digest_cached` builder runs once per model digest, not once per
`is_cable` call. This test counts the DECORATED builder's own call, by code object, under
`sys.monitoring` (`PY_START`), the same mechanism `test_cable_index_derivation_counts.py` and
`test_freeze_field_derivation_counts.py` use. `DigestCached` (`kernel/cache.py`) wraps `build`
in a `functools.lru_cache` and has no `__code__` of its own; `functools.update_wrapper` sets
`self.__wrapped__ = build`, so `target.__wrapped__.__code__` is the code object that actually
ran on a cache miss -- a cache hit never re-enters it.

Uses `tests/scale_units_fixture.py::build_scale` at n=8 and n=16. The sweep calls
`is_cable(model, item)` for every item in the model, not just the existing cables: the point is
to prove `cable_items` runs once per digest no matter how many times `is_cable` is called
against it, and sweeping every item also gives the "never ran" self-check for free, since a
model always has at least one item.

This is the only test in its module and takes over 1s (two full `build_scale` runs, at n=8 and
n=16, each merged and frozen, plus an `is_cable` sweep over every item under `sys.monitoring`):
it cannot share a module fixture's build with another test, since the size it needs to build is
itself the thing under test.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from scale_units_fixture import build_scale  # noqa: E402

from fransys_model.vocab.cables import cable_items, is_cable  # noqa: E402
from fransys_model.vocab.tables import items  # noqa: E402

if TYPE_CHECKING:
    from types import CodeType

    from fransys_model.kernel import Model

_TARGET = cable_items


def _sweep_count(model: Model) -> int:
    """`cable_items`'s own call count over `is_cable(model, item)` of every item in `model`."""
    _TARGET.cache_clear()
    # `DigestCached` has no `__code__` of its own; `functools.update_wrapper` sets `__wrapped__`
    # to the undecorated `build` (`kernel/cache.py`), whose code object this reads.
    code = _TARGET.__wrapped__.__code__  # ty: ignore[unresolved-attribute]
    count = 0
    tool = 3
    try:
        sys.monitoring.use_tool_id(tool, "is-cable-derivation-count")
    except ValueError:  # a previous, un-freed use in this process (shared with scale_counter)
        tool = 4
        sys.monitoring.use_tool_id(tool, "is-cable-derivation-count")

    def on_start(_code: CodeType, _offset: int) -> None:
        nonlocal count
        count += 1

    try:
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, on_start)
        sys.monitoring.set_local_events(tool, code, sys.monitoring.events.PY_START)
        for item in items(model).values():
            is_cable(model, item.id)
    finally:
        sys.monitoring.set_local_events(tool, code, 0)
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, None)
        sys.monitoring.free_tool_id(tool)
    return count


def test_cable_items_builds_once_per_digest_not_once_per_item() -> None:
    model8 = build_scale(8).model
    model16 = build_scale(16).model
    count8 = _sweep_count(model8)
    count16 = _sweep_count(model16)
    assert count8 > 0, "cable_items never ran: the counter saw nothing"
    assert count8 == 1, (
        f"cable_items ran {count8} times at n=8: built once per digest, not once per item"
    )
    assert count16 == 1, (
        f"cable_items ran {count16} times at n=16: built once per digest, not once per item"
    )
