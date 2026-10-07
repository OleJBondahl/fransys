"""Layout: typed accessors over `Model.tables` for `layout.*` kinds (design/layout-namespace.md)."""

from typing import Any

from fransys_model.kernel import Id, Model, SchemaError, namespace_of
from fransys_model.vocab.tables import kind_of, table_of

from .formats import Profile, SheetFormat, default_profile, default_sheet_format
from .kinds import DERIVED_KINDS


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


def profile_of(model: Model) -> Profile:
    """The profile `model` authors, or the house one (`default_profile()`).

    `Profile` is a singleton layout kind: `layout_of(model, Profile)` has 0 or 1 entries.
    """
    profiles = layout_of(model, Profile)
    if not profiles:
        return default_profile()
    return next(iter(profiles.values()))


def sheet_format_of(model: Model, sheet_format: Id[SheetFormat] | None) -> SheetFormat:
    """The sheet a page names by `sheet_format`, or the house sheet for `None`."""
    if sheet_format is None:
        return default_sheet_format()
    return layout_of(model, SheetFormat)[sheet_format]


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
