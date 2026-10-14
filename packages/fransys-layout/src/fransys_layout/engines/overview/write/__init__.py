"""Overview engine, writing: placed views to derived `layout.overview_*` records."""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.overview.defaults import ENGINE_NAME, ENGINE_VERSION
from fransys_layout.engines.overview.write.records import view_records
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import OVERVIEW_KINDS, derived_layout_ids

if TYPE_CHECKING:
    from fransys_model.kernel import Model


def write_overview(model: Model, records: tuple[Any, ...]) -> Model:
    """Replace every overview-kind `layout.*` record of `model` with `records`."""
    stamp = f"fransys-layout/{ENGINE_NAME} {ENGINE_VERSION}"
    origin = Origin(file=stamp, line=1, note="derived layout record")
    remove = derived_layout_ids(model, kinds=OVERVIEW_KINDS)
    return evolve(model, remove=remove, put=records, origin=origin)


__all__ = ("view_records", "write_overview")
