"""Speed guard: `derive.cable_cores`'s two cable indexes build once per digest.

`cable_products_by_part` (`derive/facts/cables.py`) and `_cores_by_cable` (`derive/cable_cores.py`)
replace two per-call O(n) scans (`_product_colours`'s linear search over every
"""

import sys
from typing import TYPE_CHECKING, cast

from scale_units_fixture import build_scale

from fransys_model.derive.cable_cores import (
    _cores_by_cable,
    cable_rows,
)
from fransys_model.derive.facts.cables import cable_products_by_part
from fransys_model.vocab.facets.cable import CableFacet
from fransys_model.vocab.tables import facets_of

if TYPE_CHECKING:
    from types import CodeType, FunctionType

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item

_TARGETS = (cable_products_by_part, _cores_by_cable)


def _cable_ids(model: Model) -> tuple[Id[Item], ...]:
    """Every cable item id in `model`: each `CableFacet`'s `subject`."""
    return tuple(facet.subject for facet in facets_of(model, CableFacet).values())


def _sweep_counts(model: Model) -> dict[str, int]:
    """The two builders' call counts over `cable_rows(model, cable, unit=None)` of every cable."""
    for target in _TARGETS:
        target.cache_clear()
    # `DigestCached` has no `__code__` of its own; `functools.update_wrapper` sets
    # `__wrapped__` to the undecorated `build` (`kernel/cache.py`), whose code object this reads.
    builds = [cast("FunctionType", vars(target)["__wrapped__"]) for target in _TARGETS]
    codes = {build.__code__: build.__name__ for build in builds}
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
    for name in ("cable_products_by_part", "_cores_by_cable"):
        assert counts8[name] > 0, f"{name} never ran: the counter saw nothing"
        assert counts8[name] == 1, f"{name} ran {counts8[name]} times at n=8: built once per digest, not once per cable"
        assert counts16[name] == 1, f"{name} ran {counts16[name]} times at n=16: built once per digest, not once per cable"
