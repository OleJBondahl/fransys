"""Layout: typed accessors over `Model.tables` for `layout.*` kinds (design/layout-namespace.md)."""

from typing import Any

from fransys_model.kernel import Id, Model, SchemaError, namespace_of
from fransys_model.vocab.core import Unit  # noqa: TC001 -- signature hints resolve at runtime
from fransys_model.vocab.enums import PageKind
from fransys_model.vocab.tables import kind_of, table_of

from .formats import (
    Profile,
    SheetFormat,
    a2_sheet_format,
    default_profile,
    default_sheet_format,
)
from .kinds import DERIVED_KINDS
from .results import DrawingSet, Page


def layout_of[R](model: Model, record_type: type[R]) -> frozendict[Id[R], R]:
    """Return every record of layout kind `record_type` in `model`, by id.

    Generic like `vocab.facets_of`: callers pass the class (`Chain`, `Page`) and never
    spell a kind string. The model's own table, or an empty one.

    Raises:
        SchemaError: `record_type` is not a `@record` class of the `layout` namespace.
    """
    kind = kind_of(record_type)
    if namespace_of(kind) != "layout":
        msg = f"{record_type.__qualname__} is not a layout kind: {kind} is not in that namespace"
        raise SchemaError(msg, kind=kind)
    return table_of(model, record_type)


def profile_of(model: Model, unit: Id[Unit] | None = None) -> Profile:
    """The profile `unit` authors (`None`: the top design), or the house one (`default_profile()`).

    The one reader of a profile. It matches `unit` exactly and never falls back to a containing
    unit or to the top's: a unit with no profile of its own draws with the house numbers.
    """
    found = (one for one in layout_of(model, Profile).values() if one.unit == unit)
    return next(found, default_profile())


def profile_of_page(model: Model, page: Page) -> Profile:
    """The profile of the unit `page`'s drawing set belongs to: how that page is drawn."""
    return profile_of(model, layout_of(model, DrawingSet)[page.drawing_set].unit)


def sheet_format_of(model: Model, sheet_format: Id[SheetFormat] | None) -> SheetFormat:
    """The sheet a page names by `sheet_format`, or the house sheet for `None`."""
    if sheet_format is None:
        return default_sheet_format()
    return layout_of(model, SheetFormat)[sheet_format]


def sheet_for(model: Model, kind: PageKind, unit: Id[Unit] | None = None) -> SheetFormat:
    """The sheet of a page of `kind` of `unit`: the one function that gives a page kind's sheet.

    A block diagram is on the house A2 sheet; every other kind is on the unit's profile's sheet,
    the authored `SheetFormat` it names or the house A3.
    """
    if kind is PageKind.BLOCK_DIAGRAM:
        return a2_sheet_format()
    return sheet_format_of(model, profile_of(model, unit).sheet_format)


def derived_layout_ids(
    model: Model, kinds: tuple[type, ...] = DERIVED_KINDS
) -> tuple[Id[Any], ...]:
    """Return the id of every `layout.*` result of `kinds` in `model`, sorted.

    What a layout pass hands to `evolve(remove=...)` before writing a fresh result:
    results are replaced wholesale, never patched. The schematic pass takes the default,
    the cable pass `CABLE_KINDS` (Q3); each leaves the other's records and every authored
    kind alone.
    """
    return tuple(sorted(record_id for kind in kinds for record_id in table_of(model, kind)))
