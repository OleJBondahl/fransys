"""Layout: typed accessors over `Model.tables` for `layout.*` kinds (design/layout-namespace.md)."""

from typing import Any

from fransys_model.kernel import Id, Model, SchemaError, namespace_of
from fransys_model.vocab.core import Unit  # noqa: TC001 -- signature hints resolve at runtime
from fransys_model.vocab.tables import kind_of, table_of
lazy from fransys_model.vocab.enums import PageKind

from .formats import (
    Profile,
    SheetFormat,
    default_profile,
)
from .kinds import DERIVED_KINDS
from .paper import PaperChoice
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


def paper_of(model: Model) -> PaperChoice:
    """The build's `PaperChoice`; raises when the facade wrote none (a model never built)."""
    found = layout_of(model, PaperChoice)
    if not found:
        msg = (
            "this model carries no layout.paper record, so it has no default sheet: "
            "build it through `fransys.build`, which writes the paper from `fr.settings`"
        )
        raise SchemaError(msg, kind="layout.paper")
    return next(iter(found.values()))


def sheet_format_of(model: Model, sheet_format: Id[SheetFormat] | None) -> SheetFormat:
    """The sheet a page names by `sheet_format`, or the build's default paper for `None`."""
    if sheet_format is None:
        sheet_format = paper_of(model).default
    return layout_of(model, SheetFormat)[sheet_format]


def sheet_for(model: Model, kind: PageKind, unit: Id[Unit] | None = None) -> SheetFormat:
    """The sheet of a page of `kind` of `unit`: the one function that gives a page kind's sheet.

    In order: the sheet the unit's profile names (until SETTINGS-C), the build's paper for
    `kind`, then the build's default paper (ST4).
    """
    authored = profile_of(model, unit).sheet_format
    if authored is not None:
        return sheet_format_of(model, authored)
    paper = paper_of(model)
    return sheet_format_of(model, paper.by_kind.get(kind.value, paper.default))


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
