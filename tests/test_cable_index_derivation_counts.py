"""Speed guard for RW4: `derive.reports`'s two cable indexes build once per digest.

`_cable_products_by_part` and `_cores_by_cable` (`derive/reports.py`) replace two per-call
O(n) scans (`_product_colours`'s linear search over every `CableProductFacet`, and
`cable_rows`'s per-call rebuild of `core_of` plus its scan of every conductor) with a
`digest_cached` index apiece. The whole point of the change is that each index builds once
per model digest, not once per `cable_rows` call: this test counts the DECORATED builder's
own call, by code object, under `sys.monitoring` (`PY_START`), the same mechanism
`test_freeze_field_derivation_counts.py` uses. `DigestCached` (`kernel/cache.py`) wraps
`build` in a `functools.lru_cache` and has no `__code__` of its own; `functools.update_wrapper`
sets `self.__wrapped__ = build`, so `target.__wrapped__.__code__` is the code object that
actually ran on a cache miss -- a cache hit never re-enters it.

Uses `tests/scale_units_fixture.py::build_scale` at n=8 and n=16: `pump_cabinet` authors
exactly one cable (`w1c`) per cabinet instance, so an n-cabinet model has n cables
(`facets_of(model, CableFacet)`, each facet's `subject` a cable item id). Calling
`cable_rows(model, cable, unit=None)` for every cable in the model exercises each index
once per cable; a per-digest builder must still show exactly one call at each size.

This is the only test in its module and takes over 1s (two full `build_scale` runs, at
n=8 and n=16, each merged and frozen, plus a `cable_rows` sweep over every cable under
`sys.monitoring`): it cannot share a module fixture's build with another test, since the
size it needs to build is itself the thing under test.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from scale_units_fixture import build_scale  # noqa: E402

from fransys_model.derive.reports import (  # noqa: E402
    _cable_products_by_part,
    _cores_by_cable,
    cable_rows,
)
from fransys_model.vocab.facets.cable import CableFacet  # noqa: E402
from fransys_model.vocab.tables import facets_of  # noqa: E402

if TYPE_CHECKING:
    from types import CodeType

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item

_TARGETS = (_cable_products_by_part, _cores_by_cable)


def _cable_ids(model: Model) -> tuple[Id[Item], ...]:
    """Every cable item id in `model`: each `CableFacet`'s `subject`."""
    return tuple(facet.subject for facet in facets_of(model, CableFacet).values())


def _sweep_counts(model: Model) -> dict[str, int]:
    """The two builders' call counts over `cable_rows(model, cable, unit=None)` of every cable."""
    for target in _TARGETS:
        target.cache_clear()
    # `DigestCached` has no `__code__` of its own; `functools.update_wrapper` sets
    # `__wrapped__` to the undecorated `build` (`kernel/cache.py`), whose code object this reads.
    codes = {
        target.__wrapped__.__code__: target.__name__  # ty: ignore[unresolved-attribute]
        for target in _TARGETS
    }
    counts = dict.fromkeys(codes.values(), 0)
    tool = 3
    try:
        sys.monitoring.use_tool_id(tool, "cable-index-derivation-count")
    except ValueError:  # a previous, un-freed use in this process (shared with scale_counter)
        tool = 4
        sys.monitoring.use_tool_id(tool, "cable-index-derivation-count")

    def on_start(code: CodeType, _offset: int) -> None:
        counts[codes[code]] += 1

    try:
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, on_start)
        for code in codes:
            sys.monitoring.set_local_events(tool, code, sys.monitoring.events.PY_START)
        for cable in _cable_ids(model):
            cable_rows(model, cable, unit=None)
    finally:
        for code in codes:
            sys.monitoring.set_local_events(tool, code, 0)
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, None)
        sys.monitoring.free_tool_id(tool)
    return counts


def test_cable_indexes_build_once_per_digest_not_once_per_cable() -> None:
    model8 = build_scale(8).model
    model16 = build_scale(16).model
    counts8 = _sweep_counts(model8)
    counts16 = _sweep_counts(model16)
    for name in ("_cable_products_by_part", "_cores_by_cable"):
        assert counts8[name] > 0, f"{name} never ran: the counter saw nothing"
        assert counts8[name] == 1, (
            f"{name} ran {counts8[name]} times at n=8: built once per digest, not once per cable"
        )
        assert counts16[name] == 1, (
            f"{name} ran {counts16[name]} times at n=16: built once per digest, not once per cable"
        )
