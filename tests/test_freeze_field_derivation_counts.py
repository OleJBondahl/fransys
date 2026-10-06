"""PERF-FREEZE Part 3: `fields_of`/`annotations_of` (kernel/schema.py) run once per class
touched during a freeze, not once per record (decision model-0102). `checks.record_problems`
and the hashing loop in `freeze._freeze` each build one `{class: FieldInfo}` memo
(`schema.cached_field_info`) and share it across every record and nested `@value` class the
walk enters, so a kind or a value type used by many records is resolved once, not once per
occurrence.

Counted by code object under `sys.monitoring` (PY_START), the same mechanism
`tests/scale_counter.py` uses: a `unittest.mock.patch` on `schema.fields_of`/`annotations_of`
would see nothing, because `conform.py`, `encode.py` and `record.py` each import the name into
their own module and call it as a bare local -- patching the `schema` module attribute never
touches those bindings.

Uses `tests/scale_units_fixture.py::build_scale`, the fixture `test_scale_call_counts.py` also
uses, at n=8 and n=16: both sizes repeat the same cabinet and board units, so they touch the
same kinds and nested `@value` types -- only the record COUNT doubles. A per-class count must
then be equal at both sizes; a per-record one would grow.

This is the only test in its module and takes over 1s (two full `build_scale` runs, at n=8 and
n=16, each merged and frozen under `sys.monitoring`): it cannot share a module fixture's build
with another test, since the size it needs to build is itself the thing under test.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from fransys import pipeline  # noqa: E402
from scale_units_fixture import build_scale  # noqa: E402

from fransys_model.kernel import schema  # noqa: E402
from fransys_model.kernel.freeze import freeze  # noqa: E402

if TYPE_CHECKING:
    from types import CodeType

    from fransys_model.kernel import Draft, Model

_TARGETS = (schema.fields_of, schema.annotations_of)


def _merged_draft(n: int) -> Draft:
    """The `Draft` `fr.build`'s `merge(*drafts)` produces for `build_scale(n)`, captured live."""
    captured: dict[str, Draft] = {}
    original = pipeline.freeze

    def capture(draft: Draft) -> Model:
        captured["draft"] = draft
        return original(draft)

    pipeline.freeze = capture  # ty: ignore[invalid-assignment]
    try:
        build_scale(n)
    finally:
        pipeline.freeze = original
    return captured["draft"]


def _derivation_counts(draft: Draft) -> dict[str, int]:
    """`{fields_of, annotations_of}`'s call counts over one `freeze(draft)`, by code object."""
    codes = {target.__code__: target.__name__ for target in _TARGETS}
    counts = dict.fromkeys(codes.values(), 0)
    tool = 3
    try:
        sys.monitoring.use_tool_id(tool, "freeze-field-derivation-count")
    except ValueError:  # a previous, un-freed use in this process (shared with scale_counter)
        tool = 4
        sys.monitoring.use_tool_id(tool, "freeze-field-derivation-count")

    def on_start(code: CodeType, _offset: int) -> None:
        counts[codes[code]] += 1

    try:
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, on_start)
        for code in codes:
            sys.monitoring.set_local_events(tool, code, sys.monitoring.events.PY_START)
        freeze(draft)
    finally:
        for code in codes:
            sys.monitoring.set_local_events(tool, code, 0)
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, None)
        sys.monitoring.free_tool_id(tool)
    return counts


def test_field_derivation_runs_once_per_class_not_once_per_record() -> None:
    # UNDO: conform.py, `_check_record` -> derive `annotations_of(cls)`/`fields_of(cls)`
    #     directly instead of `cached_field_info(type(record), specs)` (the per-record
    #     derivation `check_record` had before B8): the counts below then grow with n.
    draft8 = _merged_draft(8)
    draft16 = _merged_draft(16)
    counts8 = _derivation_counts(draft8)
    counts16 = _derivation_counts(draft16)
    for name in ("fields_of", "annotations_of"):
        assert counts8[name] > 0, f"{name} never ran: the counter saw nothing"
        assert counts16[name] == counts8[name], (
            f"{name} ran {counts8[name]} times at n=8 but {counts16[name]} times at n=16: "
            "per-record derivation is back"
        )
