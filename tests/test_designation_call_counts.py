"""Decision model-0103's fixes, proved by call count.

The numbering pass's duplicate checks used to reach `designation.item_designation` with
neither `relative_to` nor `unit`, many times per item, and every call rendered live. The cache puts
"""

import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from fransys import pipeline
from scale_units_fixture import build_scale

from fransys_model.derive import designation, designation_label
from fransys_model.derive.facts.unit_index import descendants
from fransys_model.derive.passes import numbering
from fransys_model.derive.texts import designation_render
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item

if TYPE_CHECKING:
    from types import CodeType

    from fransys_model.kernel import Model

# Baseline (run before the caches existed):
# one `numbering.number(model)` call over `build_scale(8)`'s captured model,
# counting `designation.item_designation`'s OLD live-render call count (before the cache
# existed, so every call rendered live). Freshly measured after both caches: 144 calls into the new
# `_render_item_designation` over the same shape, comfortably under the `< 464 // 2 == 232`
# bound below.
_BASELINE_ITEM_DESIGNATION_CALLS_N8 = 464


def _captured_model(n: int) -> Model:
    """`number()`'s own input for `build_scale(n)`: `allocate_plc`'s output (`pipeline.py`
    ~lines 250-252), not `freeze`'s -- deliberate, not a shortcut. Captured live by patching
    the bare-name `pipeline.number` binding, the same "capture, then restore" shape
    `test_freeze_field_derivation_counts.py::_merged_draft` uses on `pipeline.freeze`.
    """
    captured: dict[str, Model] = {}
    original = pipeline.number

    def capture(model: Model):
        captured["model"] = model
        return original(model)

    with patch.object(pipeline, "number", capture):
        build_scale(n)
    return captured["model"]


@pytest.fixture(scope="module")
def model_n8() -> Model:
    """`build_scale(8)`'s captured model, built once for the whole module.

    `build_scale(8)` (plus the two monitored calls the module's tests make) is fast enough to
    build once per module rather than once per test (root CLAUDE.md's "gate stays fast" rule).
    """
    return _captured_model(8)


def _use_tool_id() -> int:
    tool = 3
    try:
        sys.monitoring.use_tool_id(tool, "designation-call-counts")
    except ValueError:  # a previous, un-freed use in this process (e.g. shared with scale_counter)
        tool = 4
        sys.monitoring.use_tool_id(tool, "designation-call-counts")
    return tool


def test_descendants_py_start_frame_one_up_is_its_own_caller() -> None:
    """Re-confirms, rather than trusting `claude-tools/profile_numbering.py`'s own comment,
    that inside a PY_START callback registered on `unit_index.descendants`,
    `sys._getframe(1)` is `descendants`' OWN frame (already pushed onto the stack by the time
    PY_START fires) and `.f_back.f_code` is the code object that actually called it. Calls
    """
    descendants_code = descendants.__code__
    seen: dict[str, bool] = {}

    def on_start(_code: CodeType, _offset: int) -> None:
        own_frame = sys._getframe(1)
        seen["own_frame_is_descendants"] = own_frame.f_code is descendants_code
        back = own_frame.f_back
        assert back is not None, "descendants' own frame has no caller frame: cannot be"
        seen["caller_is_this_test"] = back.f_code is test_descendants_py_start_frame_one_up_is_its_own_caller.__code__

    tool = _use_tool_id()
    probe_root = make_id(Item, ("probe", "root"))
    try:
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, on_start)
        sys.monitoring.set_local_events(tool, descendants_code, sys.monitoring.events.PY_START)
        # An empty map has no children; any `Id[Item]` root works as a probe.
        descendants(frozendict(), probe_root)
    finally:
        sys.monitoring.set_local_events(tool, descendants_code, 0)
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, None)
        sys.monitoring.free_tool_id(tool)

    assert seen["own_frame_is_descendants"] is True, (
        "sys._getframe(1) inside descendants' own PY_START callback is not descendants' own "
        "frame: the frame-index technique this test and the profile script both rely on is wrong"
    )
    assert seen["caller_is_this_test"] is True, (
        "sys._getframe(1).f_back.f_code did not resolve to the real caller: the frame-index "
        "technique this test and the profile script both rely on is wrong"
    )


def _count_render_and_descendants_calls(model: Model) -> tuple[int, int]:
    """One monitored `numbering.number(model)` call: counts calls into the new private
    `designation_render.designation_text` (the live-render path) and calls into
    `unit_index.descendants` attributed to `takes_parents_designation`'s own frame (the old
    """
    designation._plain_item_designations.cache_clear()
    designation_label._items_with_a_function_at_or_below.cache_clear()

    render_code = designation_render.designation_text.__code__
    descendants_code = descendants.__code__
    takes_parents_code = designation_label.takes_parents_designation.__code__

    counts = {"render": 0, "descendants_from_takes_parents": 0}

    def on_start(code: CodeType, _offset: int) -> None:
        if code is render_code:
            counts["render"] += 1
            return
        own_frame = sys._getframe(1)
        back = own_frame.f_back
        assert back is not None, "descendants' own frame has no caller frame: cannot be"
        if back.f_code is takes_parents_code:
            counts["descendants_from_takes_parents"] += 1

    tool = _use_tool_id()
    try:
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, on_start)
        sys.monitoring.set_local_events(tool, render_code, sys.monitoring.events.PY_START)
        sys.monitoring.set_local_events(tool, descendants_code, sys.monitoring.events.PY_START)
        numbering.number(model)
    finally:
        sys.monitoring.set_local_events(tool, render_code, 0)
        sys.monitoring.set_local_events(tool, descendants_code, 0)
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, None)
        sys.monitoring.free_tool_id(tool)

    return counts["render"], counts["descendants_from_takes_parents"]


def test_item_designation_render_and_accessory_subtree_check_stay_cheap(
    model_n8: Model,
) -> None:
    """Before the fix, the profiling measurement
    (pre-cache code, `build_scale(8)`'s captured model, one `numbering.number(model)` call)
    counted 464 live renders of `item_designation` -- the hardcoded
    """
    render_calls, descendants_calls = _count_render_and_descendants_calls(model_n8)
    assert render_calls < _BASELINE_ITEM_DESIGNATION_CALLS_N8 // 2, (
        f"designation_text ran {render_calls} times, not under half the n=8 baseline "
        f"of {_BASELINE_ITEM_DESIGNATION_CALLS_N8} "
        f"({_BASELINE_ITEM_DESIGNATION_CALLS_N8 // 2}): the plain-shape cache is not shielding "
        "the live render path"
    )
    assert descendants_calls == 0, (
        f"takes_parents_designation called unit_index.descendants {descendants_calls} time(s): "
        "the aggregate membership set is not fully replacing the per-item subtree BFS"
    )
