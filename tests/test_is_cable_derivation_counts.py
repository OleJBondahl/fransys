"""Speed guard: `derive.facts.item_predicates`'s `cable_items` builds once per digest (model-0108).

`is_cable(model, item)` reads `cable_items(model)` for every item it is asked about; the whole
point is that the underlying `digest_cached` builder runs once per model digest, not once per
"""

import sys
from typing import TYPE_CHECKING, cast

from scale_units_fixture import build_scale

from fransys_model.derive.facts.item_predicates import cable_items, is_cable
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from types import CodeType, FunctionType

    from fransys_model.kernel import Model

_TARGET = cable_items


def _sweep_count(model: Model) -> int:
    """`cable_items`'s own call count over `is_cable(model, item)` of every item in `model`."""
    _TARGET.cache_clear()
    # `DigestCached` has no `__code__` of its own; `functools.update_wrapper` sets `__wrapped__`
    # to the undecorated `build` (`kernel/cache.py`), whose code object this reads.
    code = cast("FunctionType", vars(_TARGET)["__wrapped__"]).__code__
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
    assert count8 == 1, f"cable_items ran {count8} times at n=8: built once per digest, not once per item"
    assert count16 == 1, f"cable_items ran {count16} times at n=16: built once per digest, not once per item"
