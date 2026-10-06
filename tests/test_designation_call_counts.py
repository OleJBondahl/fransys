"""Decision model-0103's B5 and B10 fixes, proved by call count.

`.fransys/AUDIT-REPEATED-WORK.md`.

B5: the numbering pass's duplicate checks used to reach `designation.item_designation` with
neither `relative_to` nor `unit`, many times per item, and every call rendered live. B5 puts
`_plain_item_designations` (a `@digest_cached` map, built once per `model.digest`) in front of
the live render; `item_designation` now serves a plain-shape call from that map and only falls
through to the newly private `_render_item_designation` on a miss or a keyword call.

B10: `takes_parents_designation`'s subtree check used to run a fresh `descendants` BFS per item
asked about, O(depth) work every time. B10 replaces it with
`_items_with_a_function_at_or_below`, a `@digest_cached` set built once per digest; the
per-item BFS is gone from that call path entirely.

Counted by code object under `sys.monitoring` (PY_START), the same mechanism
`tests/test_freeze_field_derivation_counts.py` uses: a `unittest.mock.patch` on
`fransys.pipeline.number` would see nothing at the real call sites, because `pipeline.py`
calls `number` as a bare name bound into its own module at import time -- patching
`fransys_model.derive.passes.numbering.number` (the definition site) never touches that
binding. This module patches the bare-name binding itself (`pipeline.number`), the same way
`test_freeze_field_derivation_counts.py::_merged_draft` patches `pipeline.freeze`, only to
CAPTURE `number`'s own input once; the call counted for the assertions is a second, direct
`numbering.number(model)` call made explicitly under monitoring.

Gotcha: under `-n 2`/`-n 4` (parallel test workers sharing one process), a PRIOR test in the
same worker can leave `_plain_item_designations` or `_items_with_a_function_at_or_below`
already built for this exact model digest (both are `@digest_cached`, so they persist across
calls, unlike a memo scoped to one call). Left uncleared, that warm cache would make the B5
"live render" count read as low, or the B10 count read as already-satisfied, for reasons that
have nothing to do with the fix under test. `_count_render_and_descendants_calls` clears both
caches immediately before the one monitored call it measures, every time.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from fransys import pipeline  # noqa: E402
from scale_units_fixture import build_scale  # noqa: E402

from fransys_model.derive import designation  # noqa: E402
from fransys_model.derive.passes import numbering  # noqa: E402
from fransys_model.kernel import make_id  # noqa: E402
from fransys_model.vocab.core import Item  # noqa: E402
from fransys_model.vocab.unit_index import descendants  # noqa: E402

if TYPE_CHECKING:
    from types import CodeType

    from fransys_model.kernel import Model

# Part 0a/4 baseline (`claude-tools/profile_numbering.py`, run on the unmodified base commit
# 16ca1ec6): one `numbering.number(model)` call over `build_scale(8)`'s captured model,
# counting `designation.item_designation`'s OLD live-render call count (before B5's cache
# existed, so every call rendered live). Freshly measured after B5+B10: 144 calls into the new
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

    pipeline.number = capture  # ty: ignore[invalid-assignment]
    try:
        build_scale(n)
    finally:
        pipeline.number = original
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
    `descendants` directly from this test (never from `takes_parents_designation`), so both
    frame identities are checked against known values rather than assumed.
    """
    descendants_code = descendants.__code__
    seen: dict[str, bool] = {}

    def on_start(_code: CodeType, _offset: int) -> None:
        own_frame = sys._getframe(1)
        seen["own_frame_is_descendants"] = own_frame.f_code is descendants_code
        back = own_frame.f_back
        assert back is not None, "descendants' own frame has no caller frame: cannot be"
        seen["caller_is_this_test"] = (
            back.f_code is test_descendants_py_start_frame_one_up_is_its_own_caller.__code__
        )

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
    `designation._render_item_designation` (B5's live-render path) and calls into
    `unit_index.descendants` attributed to `takes_parents_designation`'s own frame (B10's old
    per-item subtree BFS, which the aggregate set now fully replaces).

    Clears both new `@digest_cached` builders immediately before the one monitored call: one
    `cache_clear()` pair covers both assertions, since both are counted over the same single
    `number(model)` call (simpler than clearing twice for two separate calls).
    """
    designation._plain_item_designations.cache_clear()
    designation._items_with_a_function_at_or_below.cache_clear()

    render_code = designation._render_item_designation.__code__
    descendants_code = descendants.__code__
    takes_parents_code = designation.takes_parents_designation.__code__

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
    """B5: before the fix, `claude-tools/profile_numbering.py`'s Part 0a measurement (base
    commit 16ca1ec6, `build_scale(8)`'s captured model, one `numbering.number(model)` call)
    counted 464 live renders of `item_designation` -- the hardcoded
    `_BASELINE_ITEM_DESIGNATION_CALLS_N8` above. This test counts the same call shape against
    the new private `_render_item_designation` after B5's plain-shape cache map sits in front
    of it, and measures 144: comfortably under `464 // 2 == 232`, the margin the audit's own
    "about one render per item" estimate implies (roughly an 8x reduction against the
    consumer-scale total), not merely under the bare baseline.

    B10: `takes_parents_designation`'s old per-item `descendants` BFS is fully replaced by
    `_items_with_a_function_at_or_below`, the once-per-digest aggregate set (model-0103); this
    asserts EXACTLY 0 calls attributed to `takes_parents_designation`'s own frame into
    `unit_index.descendants`, counted over the same single monitored `number(model)` call.
    """
    render_calls, descendants_calls = _count_render_and_descendants_calls(model_n8)
    assert render_calls < _BASELINE_ITEM_DESIGNATION_CALLS_N8 // 2, (
        f"_render_item_designation ran {render_calls} times, not under half the n=8 baseline "
        f"of {_BASELINE_ITEM_DESIGNATION_CALLS_N8} "
        f"({_BASELINE_ITEM_DESIGNATION_CALLS_N8 // 2}): B5's plain-shape cache is not shielding "
        "the live render path"
    )
    assert descendants_calls == 0, (
        f"takes_parents_designation called unit_index.descendants {descendants_calls} time(s): "
        "B10's aggregate membership set is not fully replacing the per-item subtree BFS"
    )
